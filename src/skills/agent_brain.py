"""ProofDesk Agent Brain — classifies documents, selects skill chains, routes by confidence.

The brain:
1. Analyzes input files (extension + content)
2. Classifies document type
3. Selects the optimal skill chain
4. Executes skills in order
5. Routes uncertain cases to human review via calibrated confidence
6. Records every decision in the audit trail
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from ..skills.nutrient_extract import (
    NutrientExtractSkill,
    NutrientOCRSkill,
    NutrientRedactSkill,
    NutrientGenerateSkill,
    ExtractionResult,
    Citation,
)
from ..skills.calibration import ConfidenceCalibrator, ConfidenceSignals, MATCH_LABEL_SCORES
from ..skills.factminer_verdict import FactMinerVerifier, FactVerdict
from ..skills.multi_signal_fusion import MultiSignalFuser, FusedResult
from ..audit.chain import EventLedger
from ..audit.artifacts import ArtifactStore
from ..audit.certificates import Certificate


# ============================================================
# Document type classification
# ============================================================

DOC_TYPE_PATTERNS = {
    "invoice": ["invoice", "inv_", "vendor_invoice"],
    "contract": ["contract", "agreement", "terms"],
    "receipt": ["receipt", "rcp_", "pos_", "transaction"],
    "kyc_id": ["drivers_license", "passport", "kyc_id", "identity"],
    "kyc_address": ["proof_of_address", "utility_bill"],
    "kyc_bank": ["bank_statement", "bank_"],
    "trade_invoice": ["trade_invoice", "commercial_invoice", "proforma"],
    "trade_bol": ["bill_of_lading", "trade_bol", "bol_", "shipping"],
    "trade_certificate": ["certificate_origin", "trade_certificate", "co_"],
    "mortgage": ["appraisal", "mortgage", "property", "valuation"],
    "medical": ["intake_form", "patient", "medical", "clinical"],
    "procurement": ["procurement", "quote", "insurance", "security_questionnaire"],
}

EXTENSION_TYPES = {
    ".pdf": "document",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".tiff": "image",
    ".docx": "office",
    ".doc": "office",
    ".xlsx": "office",
    ".xls": "office",
    ".txt": "text",
}


def classify_document(filename: str, content_sample: str = "") -> str:
    """Classify a document by filename and optional content sample.

    Returns document type string.
    """
    name_lower = filename.lower()
    content_lower = content_sample.lower()[:500]

    # Check filename patterns
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in name_lower:
                return doc_type

    # Check content patterns
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        for pattern in patterns:
            if pattern in content_lower:
                return doc_type

    return "unknown"


# ============================================================
# Skill chain definitions
# ============================================================

SKILL_CHAINS = {
    "invoice": ["extract", "verify", "cross_check", "fuse", "audit"],
    "contract": ["extract", "verify", "cross_check", "fuse", "audit"],
    "receipt": ["ocr", "extract", "verify", "fuse", "audit"],
    "kyc_id": ["extract", "verify", "fuse", "redact", "audit"],
    "kyc_address": ["extract", "verify", "fuse", "audit"],
    "kyc_bank": ["extract", "verify", "fuse", "audit"],
    "trade_invoice": ["extract", "verify", "cross_check", "fuse", "audit"],
    "trade_bol": ["extract", "verify", "cross_check", "fuse", "audit"],
    "trade_certificate": ["extract", "verify", "fuse", "audit"],
    "mortgage": ["extract", "verify", "fuse", "audit"],
    "medical": ["extract", "verify", "fuse", "redact", "audit"],
    "unknown": ["extract", "verify", "fuse", "audit"],
}

# Schemas per document type
DOC_SCHEMAS = {
    "invoice": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string", "description": "Invoice identifier"},
            "total_amount": {"type": "number", "description": "Total amount including tax"},
            "vendor_name": {"type": "string", "description": "Vendor company name"},
            "customer_name": {"type": "string", "description": "Customer company name"},
            "invoice_date": {"type": "string", "format": "date", "description": "Invoice date"},
            "due_date": {"type": "string", "format": "date", "description": "Payment due date"},
            "payment_terms": {"type": "string", "description": "Payment terms (e.g. Net 30)"},
        },
        "required": ["invoice_number", "total_amount"],
    },
    "contract": {
        "type": "object",
        "properties": {
            "parties": {"type": "string", "description": "Contracting parties"},
            "effective_date": {"type": "string", "format": "date", "description": "Contract effective date"},
            "term": {"type": "string", "description": "Contract term/length"},
            "governing_law": {"type": "string", "description": "Governing law jurisdiction"},
        },
    },
    "receipt": {
        "type": "object",
        "properties": {
            "company": {"type": "string", "description": "Store or company name"},
            "date": {"type": "string", "format": "date", "description": "Transaction date"},
            "total": {"type": "string", "description": "Total amount paid"},
            "address": {"type": "string", "description": "Store address"},
        },
    },
    "kyc_id": {
        "type": "object",
        "properties": {
            "full_name": {"type": "string", "description": "Full legal name"},
            "date_of_birth": {"type": "string", "format": "date", "description": "Date of birth"},
            "license_number": {"type": "string", "description": "ID or license number"},
            "expiry_date": {"type": "string", "format": "date", "description": "ID expiry date"},
            "address": {"type": "string", "description": "Current address"},
        },
        "required": ["full_name"],
    },
    "kyc_address": {
        "type": "object",
        "properties": {
            "account_holder": {"type": "string", "description": "Account holder name"},
            "service_address": {"type": "string", "description": "Service address"},
            "amount_due": {"type": "number", "description": "Amount due"},
        },
    },
    "kyc_bank": {
        "type": "object",
        "properties": {
            "account_holder": {"type": "string", "description": "Account holder name"},
            "opening_balance": {"type": "number", "description": "Opening balance"},
            "closing_balance": {"type": "number", "description": "Closing balance"},
            "account_type": {"type": "string", "description": "Account type"},
        },
    },
    "trade_invoice": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string", "description": "Invoice number"},
            "shipper": {"type": "string", "description": "Shipper company"},
            "consignee": {"type": "string", "description": "Consignee company"},
            "total_value": {"type": "number", "description": "Total value in USD"},
            "origin": {"type": "string", "description": "Country of origin"},
            "incoterm": {"type": "string", "description": "Incoterm"},
        },
    },
    "trade_bol": {
        "type": "object",
        "properties": {
            "bl_number": {"type": "string", "description": "Bill of lading number"},
            "shipper": {"type": "string", "description": "Shipper"},
            "consignee": {"type": "string", "description": "Consignee"},
            "freight": {"type": "string", "description": "Freight terms"},
        },
    },
    "trade_certificate": {
        "type": "object",
        "properties": {
            "country_of_origin": {"type": "string", "description": "Country of origin"},
            "invoice_reference": {"type": "string", "description": "Invoice reference"},
            "hs_code": {"type": "string", "description": "HS code"},
        },
    },
    "mortgage": {
        "type": "object",
        "properties": {
            "property_address": {"type": "string", "description": "Property address"},
            "appraised_value": {"type": "number", "description": "Final appraised value"},
            "property_type": {"type": "string", "description": "Property type"},
            "year_built": {"type": "number", "description": "Year built"},
            "square_footage": {"type": "number", "description": "Square footage"},
        },
    },
    "medical": {
        "type": "object",
        "properties": {
            "patient_name": {"type": "string", "description": "Patient full name"},
            "date_of_birth": {"type": "string", "format": "date", "description": "Patient date of birth"},
            "chief_complaint": {"type": "string", "description": "Chief complaint"},
            "insurance_id": {"type": "string", "description": "Insurance ID"},
        },
        "required": ["patient_name"],
    },
}


# ============================================================
# Agent Brain
# ============================================================

@dataclass
class ProcessingResult:
    """Result of processing a single document."""
    doc_id: str
    filename: str
    doc_type: str
    skill_chain: list[str]
    extraction: ExtractionResult | None = None
    verdicts: list[FactVerdict] = field(default_factory=list)
    fused_results: list[FusedResult] = field(default_factory=list)
    needs_human: bool = False
    human_fields: list[str] = field(default_factory=list)
    action_summary: dict = field(default_factory=dict)
    audit_event: dict | None = None
    processing_time_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "doc_type": self.doc_type,
            "skill_chain": self.skill_chain,
            "fields": len(self.fused_results),
            "needs_human": self.needs_human,
            "human_fields": self.human_fields,
            "actions": self.action_summary,
            "latency_ms": round(self.processing_time_ms, 1),
        }


class AgentBrain:
    """The ProofDesk agent brain.

    Classifies documents, selects skill chains, executes extraction +
    verification + fusion, routes by calibrated confidence.

    Usage:
        brain = AgentBrain(api_key="pdf_live_...")
        result = brain.process_file("/path/to/invoice.pdf")
        print(result.to_dict())
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NUTRIENT_API_KEY", "")
        self.extract_skill = NutrientExtractSkill(api_key=self.api_key)
        self.ocr_skill = NutrientOCRSkill(api_key=self.api_key)
        self.redact_skill = NutrientRedactSkill(api_key=self.api_key)
        self.generate_skill = NutrientGenerateSkill(api_key=self.api_key)
        self.verifier = FactMinerVerifier()
        self.fuser = MultiSignalFuser()
        self.ledger = EventLedger()
        self.artifact_store = ArtifactStore("/tmp/proofdesk/artifacts")

    def classify(self, filename: str, content_sample: str = "") -> str:
        """Classify document type."""
        return classify_document(filename, content_sample)

    def get_schema(self, doc_type: str) -> dict:
        """Get extraction schema for document type."""
        return DOC_SCHEMAS.get(doc_type, DOC_SCHEMAS["invoice"])

    def get_skill_chain(self, doc_type: str) -> list[str]:
        """Get skill chain for document type."""
        return SKILL_CHAINS.get(doc_type, SKILL_CHAINS["unknown"])

    def process_file(
        self,
        file_path: str,
        ground_truth: dict | None = None,
        cross_doc_facts: list[dict] | None = None,
        thresholds: dict | None = None,
    ) -> ProcessingResult:
        """Process a single file through the full skill chain.

        Args:
            file_path: Path to PDF/image document
            ground_truth: Optional ground truth for evaluation
            cross_doc_facts: Optional facts from other documents for cross-check
            thresholds: Optional threshold overrides

        Returns:
            ProcessingResult with extraction, verdicts, fused results
        """
        start = time.time()
        filename = os.path.basename(file_path)
        doc_id = os.path.splitext(filename)[0]

        # 1. Classify
        doc_type = self.classify(filename)
        skill_chain = self.get_skill_chain(doc_type)
        schema = self.get_schema(doc_type)

        # 2. OCR if needed (for images)
        ext = os.path.splitext(filename)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".tiff") and "ocr" in skill_chain:
            # For images, we'd OCR first then extract from the result
            # For now, skip OCR on images (Nutrient handles images directly)
            pass

        # 3. Extract
        extraction = None
        if "extract" in skill_chain:
            try:
                extraction = self.extract_skill.extract(
                    pdf_path=file_path,
                    schema=schema,
                    mode="understand",
                    instructions=f"Extract all {doc_type} fields precisely.",
                    doc_id=doc_id,
                    schema_name=doc_type,
                )
            except Exception as e:
                # Extraction failed — record and return
                self.ledger.append(doc_id, "EXTRACTION_FAILED", "system", {"error": str(e)})
                return ProcessingResult(
                    doc_id=doc_id,
                    filename=filename,
                    doc_type=doc_type,
                    skill_chain=skill_chain,
                    needs_human=True,
                    human_fields=["*"],
                    processing_time_ms=(time.time() - start) * 1000,
                )

        # 4. Verify
        verdicts = []
        if extraction and ground_truth and "verify" in skill_chain:
            verdicts = self.verifier.verify(extraction.extracted, ground_truth)

        # 5. Fuse
        fused_results = []
        if extraction and "fuse" in skill_chain:
            fused_results = self.fuser.fuse_extraction(
                extracted=extraction.extracted,
                citations=extraction.citations,
                ground_truth=ground_truth,
                cross_doc_facts=cross_doc_facts,
                thresholds=thresholds,
            )

        # 6. Determine routing
        human_fields = [r.field for r in fused_results if r.action == "HUMAN_REVIEW"]
        needs_human = len(human_fields) > 0

        # 7. Audit
        action_summary = {}
        for r in fused_results:
            action_summary[r.action] = action_summary.get(r.action, 0) + 1

        self.ledger.append(
            case_id=doc_id,
            event_type="FILE_PROCESSED",
            actor="agent_brain",
            payload={
                "doc_type": doc_type,
                "skill_chain": skill_chain,
                "fields": len(fused_results),
                "actions": action_summary,
                "needs_human": needs_human,
            },
        )

        return ProcessingResult(
            doc_id=doc_id,
            filename=filename,
            doc_type=doc_type,
            skill_chain=skill_chain,
            extraction=extraction,
            verdicts=verdicts,
            fused_results=fused_results,
            needs_human=needs_human,
            human_fields=human_fields,
            action_summary=action_summary,
            processing_time_ms=(time.time() - start) * 1000,
        )

    def process_folder(
        self,
        folder_path: str,
        ground_truth_map: dict[str, dict] | None = None,
        thresholds: dict | None = None,
    ) -> dict:
        """Process a folder of mixed documents.

        Args:
            folder_path: Path to folder containing documents
            ground_truth_map: {filename: ground_truth_dict} for evaluation
            thresholds: Optional threshold overrides

        Returns:
            Summary dict with per-file results and aggregate metrics
        """
        results = []
        all_facts = []  # For cross-document checking

        # First pass: extract all documents
        for filename in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue
            ext = os.path.splitext(filename)[1].lower()
            if ext not in EXTENSION_TYPES:
                continue

            gt = ground_truth_map.get(filename) if ground_truth_map else None
            result = self.process_file(file_path, ground_truth=gt, thresholds=thresholds)
            results.append(result)

            # Collect facts for cross-doc checking
            if result.extraction:
                all_facts.append(result.extraction.extracted)

        # Second pass: cross-document verification
        for result in results:
            if result.extraction and any(r.doc_type == result.doc_type for r in results if r != result):
                # This document type appears multiple — cross-check
                other_facts = [
                    r.extraction.extracted
                    for r in results
                    if r != result and r.extraction and r.doc_type == result.doc_type
                ]
                if other_facts:
                    # Re-fuse with cross-doc context
                    result.fused_results = self.fuser.fuse_extraction(
                        extracted=result.extraction.extracted,
                        citations=result.extraction.citations,
                        cross_doc_facts=other_facts,
                        thresholds=thresholds,
                    )
                    result.human_fields = [r.field for r in result.fused_results if r.action == "HUMAN_REVIEW"]
                    result.needs_human = len(result.human_fields) > 0

        # Summary
        total_fields = sum(len(r.fused_results) for r in results)
        total_auto = sum(r.action_summary.get("AUTO_APPROVE", 0) for r in results)
        total_review = sum(r.action_summary.get("HUMAN_REVIEW", 0) for r in results)
        total_reject = sum(r.action_summary.get("REJECT", 0) for r in results)
        docs_needing_human = sum(1 for r in results if r.needs_human)

        return {
            "folder": folder_path,
            "total_files": len(results),
            "doc_types": list(set(r.doc_type for r in results)),
            "total_fields": total_fields,
            "auto_approve": total_auto,
            "human_review": total_review,
            "reject": total_reject,
            "docs_needing_human": docs_needing_human,
            "auto_approve_rate": total_auto / total_fields if total_fields > 0 else 0,
            "results": [r.to_dict() for r in results],
            "ledger_events": self.ledger.stats(),
        }
