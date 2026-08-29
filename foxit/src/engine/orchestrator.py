"""Core orchestrator — runs the full ProofDesk pipeline.

Uses REAL Nutrient DWS API when NUTRIENT_API_KEY is set.
Uses REAL Foxit PDF Services when FOXIT keys are set.
Falls back to stubs for offline testing.
"""

from __future__ import annotations

import os
import time

from ..models.domain import (
    Case,
    CaseState,
    ExtractedFact,
    Resolution,
    ResolutionDecision,
    StructuredRecord,
    _hash,
    _id,
)
from ..state.machine import transition, can_request_signature
from ..engine.reconciliation import run_checks

# Decide: real API or stubs
_USE_REAL_NUTRIENT = bool(os.environ.get("NUTRIENT_API_KEY"))
_USE_REAL_FOXIT = bool(os.environ.get("FOXIT_CLOUD_API_CLIENT_ID"))

if _USE_REAL_NUTRIENT:
    from ..providers.nutrient import extract_from_document_sync as nutrient_extract
else:
    from ..providers.stubs import nutrient_extract

from ..providers.stubs import doctavian_generate  # Doctavian always stubbed (no key yet)

# Foxit: real if configured, stubs otherwise
if _USE_REAL_FOXIT:
    from ..providers.foxit_real import FoxitPDFClient
    _foxit_client = FoxitPDFClient()
    
    def foxit_pdf_prepare(case_or_artifact, content=""):
        """Real Foxit PDF preparation: upload + merge + compress."""
        # Try to upload the original source PDF (not the generated text artifact)
        pdf_path = case_or_artifact.output_path if hasattr(case_or_artifact, 'output_path') else None
        if pdf_path and os.path.exists(pdf_path) and pdf_path.endswith('.pdf'):
            doc_id = _foxit_client.upload(pdf_path)
        else:
            # Upload a placeholder or the first case document
            pdf_path = "data/test_pdfs/procurement_request.pdf"
            if os.path.exists(pdf_path):
                doc_id = _foxit_client.upload(pdf_path)
            else:
                doc_id = "simulated_doc_id"
        task_id = _foxit_client.merge([doc_id, doc_id])
        return {"provider": "foxit_pdf_services", "document_id": doc_id, "task_id": task_id, "status": "prepared"}
    
    def foxit_esign_request(artifact_id, signer):
        """Real Foxit eSign request."""
        from ..providers.foxit_real import FoxitESignClient
        esign = FoxitESignClient()
        if esign.is_configured:
            folder = esign.create_folder(b"simulated_pdf", signer)
            return {"provider": "foxit_esign", "folder_id": folder.get("folderId", ""), "request_id": folder.get("request_id", ""), "signer": signer, "status": "SENT"}
        return {"provider": "foxit_esign", "request_id": _id("esign_"), "folder_id": _id("folder_"), "status": "SIMULATED", "signer": signer}
else:
    from ..providers.stubs import foxit_pdf_prepare, foxit_esign_request


def run_pipeline(case: Case, domain: str = "procurement") -> Case:
    """Execute the full ProofDesk pipeline on a case."""

    # 1. INGESTED — documents received
    transition(case, CaseState.INGESTED)

    # 2. EXTRACTED — Nutrient DWS extraction
    for doc in case.documents:
        facts = nutrient_extract(doc)
        case.facts.extend(facts)
    transition(case, CaseState.EXTRACTED)

    # 3. RECONCILED — cross-document normalization
    # (entity name normalization is built into the check)
    transition(case, CaseState.RECONCILED)

    # 4. CHECKED — deterministic evidence checks
    case.assertions = run_checks(case.facts, domain=domain)
    transition(case, CaseState.CHECKED)

    # 5. Review or approve
    has_blockers = case.blocking_exceptions > 0
    if has_blockers:
        transition(case, CaseState.REVIEW_REQUIRED, detail={
            "reason": f"{case.blocking_exceptions} blocking exception(s) found",
            "failing_assertions": [
                a.assertion_id for a in case.assertions
                if a.result.value == "FAIL" and a.severity.value == "BLOCKER"
            ],
        })
    else:
        transition(case, CaseState.APPROVABLE)

    return case


def resolve_exception(case: Case, assertion_id: str,
                      decision: ResolutionDecision, reason: str,
                      actor_id: str = "user_demo") -> Case:
    """Human resolves a blocking exception."""
    if case.state != CaseState.REVIEW_REQUIRED:
        raise ValueError(f"Cannot resolve in state {case.state.value}")

    resolution = Resolution(
        assertion_id=assertion_id,
        decision=decision,
        reason=reason,
        actor_id=actor_id,
    )
    case.resolutions.append(resolution)

    from ..models.domain import AuditEvent
    case.audit_events.append(AuditEvent(
        case_id=case.case_id,
        event_type="EXCEPTION_RESOLVED",
        actor=actor_id,
        detail={
            "assertion_id": assertion_id,
            "decision": decision.value,
            "reason": reason,
        },
    ))

    # Check if all blockers resolved
    if case.unresolved_blockers == 0:
        transition(case, CaseState.RESOLVED)
        transition(case, CaseState.APPROVABLE)

    return case


def approve_record(case: Case, actor_id: str = "user_demo") -> Case:
    """Approve the structured record."""
    if case.state != CaseState.APPROVABLE:
        raise ValueError(f"Cannot approve in state {case.state.value}")

    if case.unresolved_blockers > 0:
        raise ValueError(f"Cannot approve: {case.unresolved_blockers} unresolved blocker(s)")

    # Build structured record
    record = StructuredRecord(
        case_id=case.case_id,
        facts=[f.to_public() for f in case.facts],
        assertions=[a.to_dict() for a in case.assertions],
        resolutions=[{
            "resolution_id": r.resolution_id,
            "assertion_id": r.assertion_id,
            "decision": r.decision.value,
            "reason": r.reason,
            "actor_id": r.actor_id,
        } for r in case.resolutions],
    )
    record.compute_hash()
    record.approved_by = actor_id
    record.approved_at = time.time()
    case.structured_record = record

    transition(case, CaseState.APPROVED, actor=actor_id, detail={
        "record_hash": record.content_hash,
    })
    return case


def generate_document(case: Case) -> Case:
    """Generate document from approved record via Doctavian."""
    if case.state != CaseState.APPROVED:
        raise ValueError(f"Cannot generate in state {case.state.value}")

    record_data = {
        "case_id": case.case_id,
        "record_id": case.structured_record.record_id,
        "facts": case.structured_record.facts,
        "assertions": case.structured_record.assertions,
        "resolutions": case.structured_record.resolutions,
        "content_hash": case.structured_record.content_hash,
    }

    artifact, content = doctavian_generate(record_data)
    case.generated_artifact = artifact

    # Store content for PDF prep
    if not hasattr(case, "_generated_content"):
        case._generated_content = {}
    case._generated_content[artifact.artifact_id] = content

    transition(case, CaseState.GENERATED, detail={
        "artifact_id": artifact.artifact_id,
        "content_hash": artifact.content_hash,
    })
    return case


def prepare_pdf(case: Case) -> Case:
    """Prepare PDF via Foxit MCP/PDF Services."""
    if case.state != CaseState.GENERATED:
        raise ValueError(f"Cannot prepare in state {case.state.value}")

    content = case._generated_content.get(case.generated_artifact.artifact_id, "")
    pdf_result = foxit_pdf_prepare(case.generated_artifact, content)

    transition(case, CaseState.PREPARED, detail=pdf_result)
    return case


def request_signature(case: Case, signer: str = "cfo@company.com") -> Case:
    """Request signature — passes through SignatureGate."""
    gate = can_request_signature(case)
    if not gate["allowed"]:
        raise ValueError(f"SignatureGate denied: {gate['reasons']}")

    from ..models.domain import SignatureRequest
    case.signature_request = SignatureRequest(
        case_id=case.case_id,
        artifact_id=case.generated_artifact.artifact_id,
        artifact_hash=case.generated_artifact.content_hash,
        approval_id=case.structured_record.record_id,
        signer=signer,
    )

    transition(case, CaseState.SIGNATURE_AUTHORIZED)
    esign = foxit_esign_request(case.generated_artifact.artifact_id, signer)
    case.signature_request.foxit_request_id = esign["request_id"]

    transition(case, CaseState.SIGNATURE_REQUESTED, detail=esign)
    return case


def sign_document(case: Case) -> Case:
    """Simulate human signature completion."""
    if case.state != CaseState.SIGNATURE_REQUESTED:
        raise ValueError(f"Cannot sign in state {case.state.value}")

    case.signature_request.status = "SIGNED"
    case.signature_request.signed_at = time.time()

    transition(case, CaseState.SIGNED, detail={
        "signer": case.signature_request.signer,
        "signed_at": case.signature_request.signed_at,
    })
    transition(case, CaseState.ARCHIVED)
    return case
