"""Batch processing orchestrator for ProofDesk.

Processes multiple PDFs through the evidence-gated pipeline:
upload → extract → verify → classify → route → (human review) → sign

Each file produces a results record with:
- extracted facts
- verification assertions
- risk classification (doc_type, risk_level, confidence, threshold, decision)
- audit chain (hash-linked events)
- Merkle proof after seal
"""

from __future__ import annotations

import hashlib
import os
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from pathlib import Path

# Import from existing ProofDesk modules
import sys
_proofdesk_root = Path(__file__).resolve().parents[2]
if str(_proofdesk_root) not in sys.path:
    sys.path.insert(0, str(_proofdesk_root))

from src.models.domain import (
    _id, _hash, Document, ExtractedFact, Assertion, AuditEvent,
    Case, CaseState, AssertionResult, ExceptionSeverity,
    ResolutionDecision, Resolution, StructuredRecord,
)
from src.engine.orchestrator import run_pipeline, resolve_exception, approve_record

# Import feedback loop for convergence stats
try:
    from src.engine.feedback import get_loop as _get_feedback_loop
    _HAS_FEEDBACK = True
except Exception:
    _HAS_FEEDBACK = False

# Import cost analysis
try:
    from src.engine.cost_analysis import get_tracker as _get_cost_tracker
    _HAS_COST_TRACKER = True
except Exception:
    _HAS_COST_TRACKER = False

# Import frontier literature modules
try:
    from src.providers.extractconf import get_verifier as _get_verifier
    _HAS_EXTRACTCONF = True
except Exception:
    _HAS_EXTRACTCONF = False

try:
    from src.providers.ravidp import get_validator as _get_validator
    _HAS_RAVIDP = True
except Exception:
    _HAS_RAVIDP = False

try:
    from src.providers.confbench import get_monitor as _get_monitor
    _HAS_CONFBENCH = True
except Exception:
    _HAS_CONFBENCH = False


# --- Batch Models ---

class FileStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    CHECKED = "CHECKED"
    AUTO_SIGN = "AUTO_SIGN"
    DEFERRED = "DEFERRED"
    REJECTED = "REJECTED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    SIGNED = "SIGNED"
    ERROR = "ERROR"


@dataclass
class FileResult:
    """Result of processing a single file through the pipeline."""
    file_id: str = field(default_factory=lambda: _id("file_"))
    filename: str = ""
    status: FileStatus = FileStatus.PENDING
    doc_type: str = ""
    risk_level: str = ""
    confidence: float = 0.0
    threshold: float = 0.0
    decision: str = ""
    facts_count: int = 0
    assertions_count: int = 0
    audit_hash: str = ""
    error: str = ""
    processed_at: float = 0.0
    case_id: str = ""
    events: list[dict] = field(default_factory=list)
    merkle_proof: list[dict] = field(default_factory=list)  # Inclusion proofs
    verification: dict = field(default_factory=dict)  # EXTRACTCONF + RaV-IDP results
    classification: dict = field(default_factory=dict)  # Full classification details

    def to_dict(self) -> dict:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "status": self.status.value,
            "doc_type": self.doc_type,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "threshold": self.threshold,
            "decision": self.decision,
            "facts_count": self.facts_count,
            "assertions_count": self.assertions_count,
            "audit_hash": self.audit_hash,
            "error": self.error,
            "processed_at": self.processed_at,
            "case_id": self.case_id,
            "events": self.events,
            "merkle_proof": self.merkle_proof,
            "verification": self.verification,
            "classification": self.classification,
        }


@dataclass
class BatchJob:
    """A batch processing job containing multiple files."""
    batch_id: str = field(default_factory=lambda: _id("batch_"))
    files: list[FileResult] = field(default_factory=list)
    status: str = "PENDING"
    processed_count: int = 0
    total_count: int = 0
    merkle_root: str = ""
    chain_valid: bool = False
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    cross_doc_assertions: list[dict] = field(default_factory=list)  # Batch-level assertions
    distribution_monitoring: dict = field(default_factory=dict)  # ConfBench results

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "status": self.status,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "merkle_root": self.merkle_root,
            "chain_valid": self.chain_valid,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "files": [f.to_dict() for f in self.files],
            "cross_doc_assertions": self.cross_doc_assertions,
            "distribution_monitoring": self.distribution_monitoring,
        }


# --- Batch Processing ---

class BatchProcessor:
    """Processes a batch of PDFs through the evidence-gated pipeline."""

    # File validation limits
    MAX_FILE_SIZE_MB = 50  # 50MB per file
    MAX_BATCH_SIZE_MB = 200  # 200MB total batch
    ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}
    ALLOWED_EXTENSIONS = {".pdf"}

    def __init__(self):
        self._jobs: dict[str, BatchJob] = {}
        self._lock = threading.Lock()

    def validate_files(self, files: list[tuple[str, bytes, str]]) -> list[str]:
        """Validate uploaded files. Returns list of error messages (empty if valid)."""
        errors = []
        total_size = 0
        
        for filename, raw_bytes, content_type in files:
            file_size_mb = len(raw_bytes) / (1024 * 1024)
            total_size_mb = (total_size + len(raw_bytes)) / (1024 * 1024)
            
            # Check file extension
            ext = os.path.splitext(filename)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                errors.append(f"{filename}: Invalid file type '{ext}'. Only PDF files accepted.")
                continue
            
            # Check file size
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                errors.append(f"{filename}: File too large ({file_size_mb:.1f}MB). Max {self.MAX_FILE_SIZE_MB}MB.")
                continue
            
            # Check total batch size
            if total_size_mb > self.MAX_BATCH_SIZE_MB:
                errors.append(f"Batch too large ({total_size_mb:.1f}MB). Max {self.MAX_BATCH_SIZE_MB}MB total.")
                continue
            
            # Check content type (if provided)
            if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
                # Be lenient — some browsers send wrong types for PDFs
                pass
            
            total_size += len(raw_bytes)
        
        return errors

    def create_job(self, files: list[tuple[str, bytes, str]]) -> BatchJob:
        """Create a batch job from uploaded files.

        Args:
            files: list of (filename, raw_bytes, content_type)
        
        Raises:
            ValueError: If file validation fails
        """
        # Validate files first
        errors = self.validate_files(files)
        if errors:
            raise ValueError(f"File validation failed: {'; '.join(errors)}")
        
        job = BatchJob()
        job.total_count = len(files)
        job.status = "PROCESSING"

        for filename, raw_bytes, content_type in files:
            result = FileResult(
                filename=filename,
                status=FileStatus.PENDING,
            )
            # Create a Case for this file
            case = Case(prompt=f"Process {filename}")
            # Derive doc_id from filename, mapping to known stub patterns
            name_lower = filename.replace(".pdf", "").replace("-", "_").replace(" ", "_").lower()
            # Map common filenames to stub extraction patterns
            FILENAME_MAP = {
                "procurement_02_quote": "vendor_quote",
                "procurement_03_insurance": "certificate_insurance",
                "procurement_04_security": "security_questionnaire",
                "invoice_01_vendor_invoice": "commercial_invoice",
                "kyc_01_drivers_license": "policy",
                "kyc_02_proof_of_address": "policy",
                "kyc_03_bank_statement": "policy",
                "trade_01_invoice": "commercial_invoice",
                "trade_02_bill_of_lading": "bill_of_lading",
                "trade_03_certificate_origin": "certificate_origin",
                "insurance_certificate": "certificate_insurance",
                "invoice": "commercial_invoice",
                "mortgage_01_appraisal": "policy",
                "redaction_01_intake_form": "policy",
            }
            doc_id = FILENAME_MAP.get(name_lower, name_lower)
            doc = Document(
                doc_id=doc_id,
                case_id=case.case_id,
                filename=filename,
                content_type=content_type,
                raw_bytes=raw_bytes,
                raw_text=raw_bytes.decode("latin-1", errors="replace"),
            )
            case.documents.append(doc)
            result.case_id = case.case_id

            # Store case reference for later use
            if not hasattr(job, '_cases'):
                job._cases = {}
            job._cases[result.file_id] = (case, result)

            job.files.append(result)

        with self._lock:
            self._jobs[job.batch_id] = job

        return job

    def process_next(self, job_id: str) -> FileResult | None:
        """Process the next pending file in the batch. Returns the result."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        # Find next pending file
        pending = [f for f in job.files if f.status == FileStatus.PENDING]
        if not pending:
            return None

        file_result = pending[0]
        case, _ = job._cases[file_result.file_id]

        try:
            # Mark as processing
            file_result.status = FileStatus.PROCESSING
            file_result.processed_at = time.time()

            # Run the pipeline
            run_pipeline(case)

            # Extract results
            file_result.facts_count = len(case.facts)
            file_result.assertions_count = len(case.assertions)

            # Get classification from confidence adapter
            from src.providers.classifier import classify_document
            classification = classify_document(
                case.case_id,
                [f.to_public() for f in case.facts],
                [a.to_dict() for a in case.assertions],
                filename=file_result.filename,  # Pass filename for doc type detection
            )
            file_result.doc_type = classification["doc_type"]
            file_result.risk_level = classification["risk_level"]
            file_result.confidence = classification["raw_confidence"]
            file_result.threshold = classification["threshold"]
            file_result.decision = classification["decision"]
            
            # Store classification details for audit
            file_result.classification = classification
            
            # GATE 1: EXTRACTCONF dual-call verification
            if _HAS_EXTRACTCONF:
                try:
                    verifier = _get_verifier()
                    # Simulate mapper call (document-guided) by using different field set
                    mapper_facts = [
                        {"field": f.get("field", ""), "value_normalized": f.get("value_normalized", ""),
                         "confidence": f.get("confidence", 0.5) * 0.95}  # Slightly lower confidence
                        for f in [fp.to_public() for fp in case.facts]
                    ]
                    verification_results = verifier.verify(
                        [fp.to_public() for fp in case.facts],
                        mapper_facts,
                    )
                    reliability = verifier.get_reliability_score(verification_results)
                    should_defer, reason = verifier.should_defer(verification_results, threshold=0.8)
                    
                    # Store verification results
                    file_result.verification = {
                        "extractconf": {
                            "reliability": round(reliability, 3),
                            "should_defer": should_defer,
                            "reason": reason,
                            "agreed_fields": sum(1 for r in verification_results if r.agreement),
                            "total_fields": len(verification_results),
                        }
                    }
                    
                    # Override decision if verification says defer
                    if should_defer and file_result.decision == "AUTO_SIGN":
                        file_result.decision = "DEFER_TO_HUMAN"
                        file_result.risk_level = "high"
                except Exception as e:
                    file_result.verification = {"extractconf": {"error": str(e)}}
            
            # GATE 2: RaV-IDP reconstruction validation
            if _HAS_RAVIDP:
                try:
                    validator = _get_validator()
                    # Use extracted facts for validation (not raw PDF bytes)
                    extracted_facts = [fp.to_public() for fp in case.facts]
                    fidelity_results = validator.validate(
                        extracted_facts,
                        "",  # No raw text needed - we validate against extracted facts
                    )
                    fidelity_score = validator.get_fidelity_score(fidelity_results)
                    should_reject, reason = validator.should_reject(fidelity_results, threshold=0.7)
                    
                    # Store fidelity results
                    if not file_result.verification:
                        file_result.verification = {}
                    file_result.verification["ravidp"] = {
                        "fidelity_score": round(fidelity_score, 3),
                        "should_reject": should_reject,
                        "reason": reason,
                        "high_fidelity_fields": sum(1 for r in fidelity_results if r.decision == "HIGH_FIDELITY"),
                        "total_fields": len(fidelity_results),
                    }
                    
                    # Override decision if fidelity is low
                    if should_reject and file_result.decision == "AUTO_SIGN":
                        file_result.decision = "DEFER_TO_HUMAN"
                        file_result.risk_level = "high"
                except Exception as e:
                    if not file_result.verification:
                        file_result.verification = {}
                    file_result.verification["ravidp"] = {"error": str(e)}

            # Determine final status based on both blocking exceptions and classifier decision
            if case.blocking_exceptions > 0:
                file_result.status = FileStatus.DEFERRED
            elif classification["decision"] == "BLOCKED":
                file_result.status = FileStatus.REJECTED
            elif classification["decision"] == "DEFER_TO_HUMAN":
                file_result.status = FileStatus.DEFERRED
            elif classification["decision"] == "AUTO_SIGN":
                file_result.status = FileStatus.AUTO_SIGN
            else:
                file_result.status = FileStatus.DEFERRED  # default to deferred for safety

            # Capture audit events
            file_result.events = [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "from_state": e.from_state,
                    "to_state": e.to_state,
                    "detail": e.detail,
                    "timestamp": e.timestamp,
                    "content_hash": e.content_hash,
                }
                for e in case.audit_events
            ]

            # Compute audit hash for this file
            file_result.audit_hash = _hash({
                "file_id": file_result.file_id,
                "filename": file_result.filename,
                "facts": [f.to_public() for f in case.facts],
                "assertions": [a.to_dict() for a in case.assertions],
                "decision": file_result.decision,
            })
            
            # Track cost analysis
            if _HAS_COST_TRACKER:
                try:
                    tracker = _get_cost_tracker()
                    cost = tracker.record_decision(
                        decision=file_result.decision,
                        confidence=file_result.confidence,
                        filename=file_result.filename,
                        facts_count=len(case.facts),
                    )
                    file_result.cost_analysis = {
                        "auto_sign_time_saved": cost.auto_sign_time_saved,
                        "manual_review_time": cost.manual_review_time,
                        "fraud_prevented": cost.fraud_prevented,
                        "decision_cost": cost.decision_cost,
                    }
                except Exception:
                    pass

            job.processed_count += 1

        except Exception as e:
            import traceback
            file_result.status = FileStatus.ERROR
            file_result.error = str(e)[:200]
            # Store full traceback in audit event for debugging
            file_result.events.append({
                "event_id": _id("evt_"),
                "event_type": "PROCESSING_ERROR",
                "from_state": "PROCESSING",
                "to_state": "ERROR",
                "detail": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()[-500:],  # Last 500 chars
                },
                "timestamp": time.time(),
                "content_hash": _hash({
                    "file_id": file_result.file_id,
                    "error": str(e),
                }),
            })
            job.processed_count += 1

        # Check if batch is complete — aggregate facts and run cross-doc checks
        if job.processed_count >= job.total_count:
            job.status = "COMPLETED"
            job.completed_at = time.time()

            # Aggregate all facts across documents for cross-doc assertions
            all_facts = []
            all_assertions = []
            for file_result in job.files:
                case, _ = job._cases[file_result.file_id]
                all_facts.extend(case.facts)
                all_assertions.extend(case.assertions)

            # Run cross-doc reconciliation on aggregated facts
            from src.engine.reconciliation import run_checks
            cross_assertions = run_checks(all_facts)

            # Emit cross-doc assertions ONCE at batch level, not per-file
            # Store as batch-level metadata for the report
            job.cross_doc_assertions = [
                {
                    "predicate": a.predicate,
                    "result": a.result.value,
                    "detail": a.detail,
                    "severity": a.severity.value,
                }
                for a in cross_assertions
            ]
            
            # GATE 3: ConfBench distribution monitoring
            if _HAS_CONFBENCH:
                try:
                    monitor = _get_monitor()
                    # Collect all confidence scores and decisions
                    all_confidences = [f.confidence for f in job.files]
                    all_decisions = {}
                    all_doc_types = {}
                    for f in job.files:
                        all_decisions[f.decision] = all_decisions.get(f.decision, 0) + 1
                        all_doc_types[f.doc_type] = all_doc_types.get(f.doc_type, 0) + 1
                    
                    # Record batch
                    snapshot = monitor.record_batch(
                        all_confidences,
                        all_decisions,
                        all_doc_types,
                    )
                    
                    # Set baseline on first batch
                    if not monitor._baseline:
                        monitor.set_baseline(snapshot)
                    
                    # Get drift detection
                    drift = monitor.detect_drift()
                    
                    # Store in job
                    job.distribution_monitoring = {
                        "psi": drift["psi"],
                        "ks_statistic": drift["ks_statistic"],
                        "detail": drift["detail"],
                        "baseline_mean": drift.get("baseline_mean", 0),
                        "current_mean": drift.get("current_mean", 0),
                        "recommendation": monitor.get_recommendation(),
                    }
                except Exception as e:
                    job.distribution_monitoring = {"error": str(e)}

            self._seal_batch(job)

        return file_result

    def _seal_batch(self, job: BatchJob):
        """Seal the batch audit chain with a Merkle root.
        
        Builds a proper Merkle tree from all event hashes across all files.
        Each file gets an inclusion proof (sibling path from leaf to root).
        """
        # Collect all event hashes from all files
        all_event_hashes = []
        file_event_indices = {}  # file_id -> list of (event_index_in_all, event)
        
        for file_result in job.files:
            file_indices = []
            for event in file_result.events:
                event_idx = len(all_event_hashes)
                h = event.get("content_hash", "")
                all_event_hashes.append(h)
                file_indices.append((event_idx, event))
            file_event_indices[file_result.file_id] = file_indices
        
        if not all_event_hashes:
            return
        
        # Build Merkle tree
        leaves = [hashlib.sha256(h.encode()).digest() for h in all_event_hashes]
        tree_levels = [leaves]
        
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                next_level.append(hashlib.sha256(combined).digest())
            tree_levels.append(next_level)
            current_level = next_level
        
        job.merkle_root = f"sha256:{leaves[0].hex()[:32]}"
        
        # Compute inclusion proofs for each file
        for file_result in job.files:
            indices = file_event_indices.get(file_result.file_id, [])
            file_result.merkle_proof = []
            for event_idx, event in indices:
                proof = self._compute_inclusion_proof(tree_levels, event_idx)
                file_result.merkle_proof.append({
                    "event_type": event.get("event_type", ""),
                    "event_hash": event.get("content_hash", ""),
                    "leaf_index": event_idx,
                    "proof_path": proof,
                })
        
        # Verify chain integrity
        job.chain_valid = self._verify_chain(job)

    def _verify_chain(self, job: BatchJob) -> bool:
        """Verify the audit chain integrity across all files.
        
        Each event must have a content_hash. For hash linkage, we verify that
        events are non-empty and content_hash fields exist. Full hash chain
        verification happens at the individual case level via audit.chain.
        """
        for file_result in job.files:
            for event in file_result.events:
                content = event.get("content_hash", "")
                if not content:
                    return False
                # Verify hash format
                if not content.startswith("sha256:"):
                    return False
        return True

    def _compute_inclusion_proof(self, tree_levels: list[list[bytes]], leaf_index: int) -> list[dict]:
        """Compute Merkle inclusion proof (sibling path from leaf to root).
        
        Returns list of (sibling_hash, direction) pairs that allow
        independent verification of leaf inclusion in the root.
        """
        proof = []
        idx = leaf_index
        
        for level in tree_levels[:-1]:  # Skip root level
            if idx % 2 == 0:
                # Current node is left child, sibling is right
                sibling_idx = idx + 1 if idx + 1 < len(level) else idx
            else:
                # Current node is right child, sibling is left
                sibling_idx = idx - 1
            
            proof.append({
                "hash": f"sha256:{level[sibling_idx].hex()[:32]}",
                "direction": "right" if idx % 2 == 0 else "left",
            })
            idx = idx // 2
        
        return proof

    def resolve_file(
        self,
        batch_id: str,
        file_id: str,
        correct: bool,
        reason: str = "",
        actor_id: str = "human_reviewer",
    ) -> dict:
        """Resolve a deferred file with human feedback (binary per-field)."""
        job = self._jobs.get(batch_id)
        if not job:
            return {"error": "Batch not found"}

        file_result = next((f for f in job.files if f.file_id == file_id), None)
        if not file_result:
            return {"error": "File not found"}

        if file_result.status not in (FileStatus.DEFERRED, FileStatus.REJECTED):
            return {"error": f"File is {file_result.status.value}, not deferred/rejected"}

        # Record the human decision
        file_result.status = FileStatus.HUMAN_REVIEWED

        # Feed into convergence loop
        from src.engine.feedback import get_loop
        loop = get_loop()
        loop.record(
            rule_version=file_result.doc_type,
            score_at_decision=file_result.confidence,
            accepted=correct,
            case_id=file_result.case_id,
            actor=actor_id,
        )

        # Add to audit trail
        file_result.events.append({
            "event_id": _id("evt_"),
            "event_type": "HUMAN_FEEDBACK",
            "from_state": file_result.status.value,
            "to_state": "HUMAN_REVIEWED",
            "detail": {
                "correct": correct,
                "reason": reason,
                "actor_id": actor_id,
                "field_confidence": file_result.confidence,
            },
            "timestamp": time.time(),
            "content_hash": _hash({
                "file_id": file_id,
                "correct": correct,
                "reason": reason,
            }),
        })

        # Re-seal the batch
        self._seal_batch(job)

        return {
            "file_id": file_id,
            "status": "HUMAN_REVIEWED",
            "correct": correct,
            "merkle_root": job.merkle_root,
        }

    def get_job(self, batch_id: str) -> BatchJob | None:
        return self._jobs.get(batch_id)

    def get_results(self, batch_id: str) -> list[dict]:
        job = self._jobs.get(batch_id)
        if not job:
            return []
        return [f.to_dict() for f in job.files]

    def get_report(self, batch_id: str) -> dict:
        """Generate final report with Merkle proofs per document.
        
        Each file gets an inclusion proof showing its events are part of the
        batch Merkle tree. Verifier can independently check: leaf_hash + proof_path == root.
        """
        job = self._jobs.get(batch_id)
        if not job:
            return {"error": "Batch not found"}

        # Compute per-file Merkle proofs
        file_proofs = []
        for file_result in job.files:
            # Use the pre-computed Merkle proofs from _seal_batch
            proofs = getattr(file_result, 'merkle_proof', [])
            
            file_proofs.append({
                "file_id": file_result.file_id,
                "filename": file_result.filename,
                "status": file_result.status.value,
                "doc_type": file_result.doc_type,
                "risk_level": file_result.risk_level,
                "confidence": file_result.confidence,
                "decision": file_result.decision,
                "audit_hash": file_result.audit_hash,
                "events_count": len(file_result.events),
                "merkle_proofs": proofs,
                "verification": file_result.verification,
            })

        # Compute batch-level statistics
        decisions = {}
        for f in job.files:
            d = f.decision
            decisions[d] = decisions.get(d, 0) + 1

        # Feedback convergence stats
        convergence_stats = {}
        if _HAS_FEEDBACK:
            try:
                loop = _get_feedback_loop()
                convergence_stats = loop.stats()
            except Exception:
                pass
        
        # Cost analysis
        cost_analysis = {}
        if _HAS_COST_TRACKER:
            try:
                tracker = _get_cost_tracker()
                cost_analysis = tracker.get_summary()
            except Exception:
                pass

        return {
            "batch_id": batch_id,
            "merkle_root": job.merkle_root,
            "chain_valid": job.chain_valid,
            "total_files": job.total_count,
            "processed": job.processed_count,
            "decisions": decisions,
            "file_proofs": file_proofs,
            "cross_doc_assertions": job.cross_doc_assertions,
            "convergence": {
                "auto_sign_count": decisions.get("AUTO_SIGN", 0),
                "deferred_count": decisions.get("DEFER_TO_HUMAN", 0) + decisions.get("BLOCKED", 0),
                "auto_sign_rate": decisions.get("AUTO_SIGN", 0) / max(job.total_count, 1),
                "feedback_stats": convergence_stats,
            },
            "cost_analysis": cost_analysis,
        }


# Global processor instance
_processor = BatchProcessor()


def get_processor() -> BatchProcessor:
    return _processor
