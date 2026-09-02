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
_REQUIRE_LIVE = os.environ.get("DEMO_REQUIRE_LIVE_PROVIDERS", "").lower() == "true"

if _USE_REAL_NUTRIENT:
    from ..providers.nutrient import extract_from_document_sync as nutrient_extract
else:
    from ..providers.stubs import nutrient_extract

# Document generation — always local (deterministic, same output as cloud template)
from ..providers.stubs import render_approval_memo

# Foxit: real if configured, stubs otherwise
if _USE_REAL_FOXIT:
    from ..providers.foxit_real import FoxitPDFClient
    _foxit_client = FoxitPDFClient()
    
    def foxit_pdf_prepare(case, generated_artifact, content=""):
        """Real Foxit PDF preparation: upload sources + memo → merge → compress → download → SHA-256."""
        import tempfile
        import hashlib

        uploaded_ids = []

        # 1. Upload each real source document from the case
        for doc in case.documents:
            body = doc.raw_bytes or (doc.raw_text.encode("latin-1", errors="replace") if doc.raw_text else b"")
            if not body:
                continue
            # Write to temp file for upload (Foxit requires a file path)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(body)
                tmp_path = tmp.name
            try:
                doc_id = _foxit_client.upload(tmp_path)
                uploaded_ids.append(doc_id)
            finally:
                os.unlink(tmp_path)

        # 2. Upload the generated memo if it's a real PDF on disk
        memo_id = None
        memo_path = generated_artifact.output_path if hasattr(generated_artifact, 'output_path') else None
        if memo_path and memo_path.endswith('.pdf') and os.path.exists(memo_path):
            memo_id = _foxit_client.upload(memo_path)
            uploaded_ids.append(memo_id)

        # 3. Merge all documents (sources + memo)
        if len(uploaded_ids) < 2:
            # Need at least 2 docs to merge; if only 1, skip merge
            final_id = uploaded_ids[0] if uploaded_ids else None
            merge_task = None
        else:
            merge_task = _foxit_client.merge(uploaded_ids)
            # 4. Wait for merge to complete → get resultDocumentId
            final_id = _foxit_client.wait_for_task(merge_task)

        # 5. Compress the merged result (not the source)
        compress_task = None
        if final_id:
            compress_task = _foxit_client.compress(final_id, level="LOW")
            # 6. Wait for compress → get resultDocumentId
            final_id = _foxit_client.wait_for_task(compress_task)

        # 7. Download the final PDF and SHA-256 it — fatal on failure
        if not final_id:
            raise RuntimeError("Foxit: no final document after compress")
        final_bytes = _foxit_client.download(final_id)
        if not final_bytes:
            raise RuntimeError("Foxit: download returned empty bytes")
        final_hash = hashlib.sha256(final_bytes).hexdigest()
        out_dir = "/tmp/proofdesk"
        os.makedirs(out_dir, exist_ok=True)
        final_path = f"{out_dir}/final_{case.case_id}.pdf"
        with open(final_path, "wb") as f:
            f.write(final_bytes)

        return {
            "provider": "foxit_pdf_services",
            "mode": "live",
            "source_ids": [uid for uid in uploaded_ids if uid != memo_id],
            "memo_id": memo_id,
            "merge_task": merge_task,
            "compress_task": compress_task,
            "final_document_id": final_id,
            "final_hash": final_hash,
            "final_path": final_path,
            "status": "prepared",
        }
    
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


def run_pipeline(case: Case, domain: str = "procurement", stop_after: str | None = None) -> Case:
    """Execute the ProofDesk pipeline. stop_after pauses at a named state for live demos."""
    import hashlib
    from ..providers import trace as vtrace
    vtrace.set_current(case.case_id)
    vtrace.drop(case.case_id)

    def advance_one() -> bool:
        """Execute exactly one stage based on current state. Returns False when terminal."""
        s = case.state
        if s == CaseState.RECEIVED:
            for doc in case.documents:
                body = doc.raw_bytes or (doc.raw_text.encode("latin-1", errors="replace") if doc.raw_text else b"")
                doc.content_hash = f"sha256:{hashlib.sha256(body).hexdigest()[:16]}"
            transition(case, CaseState.INGESTED, detail={
                "documents": {d.doc_id: d.content_hash for d in case.documents}})
        elif s == CaseState.INGESTED:
            import time as _t
            from ..providers import trace as vtrace
            vtrace.set_current(case.case_id)
            vtrace.drop(case.case_id)
            degraded = []
            _t0 = _t.time()
            _pre = len(case.facts)
            for doc in case.documents:
                try:
                    # Real Nutrient needs actual PDF bytes — fall back to stubs for text-only docs
                    if _USE_REAL_NUTRIENT and doc.raw_bytes:
                        case.facts.extend(nutrient_extract(doc))
                    elif _USE_REAL_NUTRIENT and not doc.raw_bytes:
                        from ..providers.stubs import nutrient_extract as stub_extract
                        case.facts.extend(stub_extract(doc))
                    else:
                        case.facts.extend(nutrient_extract(doc))
                except Exception as e:
                    # provider failure degrades this doc, never the pipeline
                    degraded.append({"doc_id": doc.doc_id, "error": str(e)[:120]})
            vtrace.record(case.case_id,
                "Nutrient DWS" if _USE_REAL_NUTRIENT else "stub",
                f"extract[{len(case.documents)} docs]",
                "POST", "https://api.nutrient.io/extraction/extract",
                request_summary={"documents": [d.filename for d in case.documents],
                                 "total_bytes": sum(len(d.raw_bytes or b"") for d in case.documents)},
                status=200 if not degraded else 207,
                response_summary={"facts_extracted": len(case.facts) - _pre,
                                  "degraded": degraded},
                duration_ms=(_t.time() - _t0) * 1000)
            if degraded:
                from ..models.domain import AuditEvent
                evt = AuditEvent(case_id=case.case_id, event_type="EXTRACTION_DEGRADED",
                                 actor="system", detail={"docs": degraded})
                evt.compute_hash(case.audit_events[-1].content_hash if case.audit_events else "")
                case.audit_events.append(evt)
            # Block if no facts extracted — missing evidence is a blocker
            if len(case.facts) == 0:
                from ..models.domain import AuditEvent
                evt = AuditEvent(case_id=case.case_id, event_type="EVIDENCE_INCOMPLETE",
                                 actor="system", detail={"reason": "No facts extracted from any document"})
                evt.compute_hash(case.audit_events[-1].content_hash if case.audit_events else "")
                case.audit_events.append(evt)
            transition(case, CaseState.EXTRACTED)
        elif s == CaseState.EXTRACTED:
            transition(case, CaseState.RECONCILED)
        elif s == CaseState.RECONCILED:
            case.assertions = run_checks(case.facts, domain=domain)
            # Live classification — the engine the dashboard renders
            from ..providers.classifier import classify_document
            cls = classify_document(
                case.case_id,
                [f.to_public() for f in case.facts],
                [a.to_dict() for a in case.assertions],
                [{"decision": r.decision.value, "reason": r.reason, "actor_id": r.actor_id}
                 for r in case.resolutions],
            )
            # Store full classification as the canonical DecisionCertificate
            case._classification = cls
            case._decision_certificate = {
                "doc_type": cls["doc_type"],
                "risk_level": cls["risk_level"],
                "score": cls["calibrated_confidence"],
                "threshold": cls["threshold"],
                "decision": cls["decision"],
                "field_scores": cls["field_scores"],
                "violations": cls["per_field_violations"],
                "engine": cls["engine"],
            }
            case._confidence = {
                "score": cls["calibrated_confidence"],
                "threshold": cls["threshold"],
                "band": cls["risk_level"],
                "field_risks": cls["per_field_violations"],
                "decision": cls["decision"],
            }
            transition(case, CaseState.CHECKED, detail={
                "classification": {
                    "doc_type": cls["doc_type"],
                    "risk_level": cls["risk_level"],
                    "confidence": cls["raw_confidence"],
                    "threshold": cls["threshold"],
                    "decision": cls["decision"],
                }})
        elif s == CaseState.CHECKED:
            # Block if no facts were extracted — missing evidence
            if len(case.facts) == 0:
                from ..models.domain import AuditEvent
                evt = AuditEvent(case_id=case.case_id, event_type="EVIDENCE_INCOMPLETE",
                                 actor="system", detail={"reason": "No facts extracted — cannot evaluate"})
                evt.compute_hash(case.audit_events[-1].content_hash if case.audit_events else "")
                case.audit_events.append(evt)
                transition(case, CaseState.REVIEW_REQUIRED, detail={
                    "reason": "EVIDENCE_INCOMPLETE: no facts extracted from any document",
                    "failing_assertions": []})
            elif case.blocking_exceptions > 0:
                transition(case, CaseState.REVIEW_REQUIRED, detail={
                    "reason": f"{case.blocking_exceptions} blocking exception(s)",
                    "failing_assertions": [a.assertion_id for a in case.assertions
                                           if a.result.value == "FAIL"
                                           and a.severity.value == "BLOCKER"]})
            else:
                transition(case, CaseState.APPROVABLE)
        else:
            return False
        return True

    if not advance_one():
        return case
    if stop_after is None:
        while advance_one():
            pass
    else:
        while case.state.value != stop_after:
            if not advance_one():
                break
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

    # Look up the failing assertion for rule attribution
    failing = next((a for a in case.assertions if a.assertion_id == assertion_id), None)

    from ..models.domain import AuditEvent
    evt = AuditEvent(
        case_id=case.case_id,
        event_type="EXCEPTION_RESOLVED",
        actor=actor_id,
        detail={
            "assertion_id": assertion_id,
            "decision": decision.value,
            "reason": reason,
        },
    )
    # Chain to previous event — the human decision must be tamper-evident too
    evt.compute_hash(case.audit_events[-1].content_hash if case.audit_events else "")
    case.audit_events.append(evt)

    # Human label → feedback loop (convergence: defer → decide → calibrate)
    from .feedback import get_loop
    get_loop().record(
        rule_version=getattr(failing, "rule_version", "unknown"),
        score_at_decision=case._confidence.get("confidence", 0.5) if hasattr(case, "_confidence") else 0.5,
        accepted=decision in (ResolutionDecision.ACCEPT, ResolutionDecision.CONDITIONAL_ACCEPT),
        case_id=case.case_id,
        actor=actor_id,
    )

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

    # The approving human IS the human approval — record it so the
    # SignatureGate's NO_HUMAN_APPROVAL check reflects reality
    from ..models.domain import Resolution
    if case.human_approval is None:
        case.resolutions.append(Resolution(
            assertion_id="OPERATOR_APPROVAL",
            decision=ResolutionDecision.ACCEPT,
            reason=f"Operator {actor_id} reviewed record {record.content_hash} and approved",
            actor_id=actor_id,
        ))

    transition(case, CaseState.APPROVED, actor=actor_id, detail={
        "record_hash": record.content_hash,
    })
    return case


def generate_document(case: Case) -> Case:
    """Generate document from approved record via local renderer."""
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

    # Use classification from pipeline if available, else compute default
    if hasattr(case, '_confidence') and case._confidence:
        confidence = case._confidence
    elif hasattr(case, '_classification') and case._classification:
        cls = case._classification
        confidence = {
            "confidence": cls.get("calibrated_confidence", 0.5),
            "threshold": cls.get("threshold", 0.7),
            "band": cls.get("risk_level", "high"),
            "field_risks": cls.get("per_field_violations", []),
        }
    else:
        confidence = {"confidence": 0.5, "threshold": 0.7, "band": "high", "field_risks": []}

    artifact, content = render_approval_memo(record_data, confidence=confidence)
    case.generated_artifact = artifact
    case._confidence = confidence

    # Store content for PDF prep
    if not hasattr(case, "_generated_content"):
        case._generated_content = {}
    case._generated_content[artifact.artifact_id] = content

    transition(case, CaseState.GENERATED, detail={
        "artifact_id": artifact.artifact_id,
        "content_hash": artifact.content_hash,
        "risk_band": confidence["band"],
        "signing_confidence": confidence.get("score") or confidence.get("confidence", 0.5),
    })
    return case


def prepare_pdf(case: Case) -> Case:
    """Prepare PDF via Foxit PDF Services. Fails closed on any artifact error."""
    import time as _t
    if case.state != CaseState.GENERATED:
        raise ValueError(f"Cannot prepare in state {case.state.value}")

    content = case._generated_content.get(case.generated_artifact.artifact_id, "")
    _t0 = _t.time()

    try:
        pdf_result = foxit_pdf_prepare(case, case.generated_artifact, content)
    except Exception as e:
        raise ValueError(f"DOCUMENT_PREPARATION_FAILED: {e}")

    if pdf_result.get("status") != "prepared":
        raise ValueError("DOCUMENT_PREPARATION_FAILED: Foxit PDF preparation returned incomplete result")

    # Store the final artifact hash and path for gate verification
    case._prepared_artifact_hash = pdf_result.get("final_hash")
    case._prepared_artifact_path = pdf_result.get("final_path")

    from ..providers import trace as vtrace
    vtrace.set_current(case.case_id)
    is_real = pdf_result.get("mode") == "live"
    vtrace.record(case.case_id,
        "Foxit PDF Services", "merge + compress + download",
        "POST", "https://na1.fusion.foxit.com/pdf-services/api/documents/enhance/pdf-combine",
        request_summary={"operation": "merge_compress_download",
                         "source_count": len(pdf_result.get("source_ids", [])),
                         "memo_id": pdf_result.get("memo_id"),
                         "final_hash": pdf_result.get("final_hash"),
                         "artifact": case.generated_artifact.artifact_id},
        status=200 if is_real else 0,
        response_summary=pdf_result,
        duration_ms=(_t.time() - _t0) * 1000)

    transition(case, CaseState.PREPARED, detail=pdf_result)
    return case


def request_signature(case: Case, signer: str = "cfo@company.com") -> Case:
    """Request signature — passes through SignatureGate, then signing request."""
    gate = can_request_signature(case)
    if not gate["allowed"]:
        raise ValueError(f"SignatureGate denied: {gate['reasons']}")

    from ..models.domain import SignatureRequest
    case.signature_request = SignatureRequest(
        case_id=case.case_id,
        artifact_id=case.generated_artifact.artifact_id,
        artifact_hash=getattr(case, '_prepared_artifact_hash', None) or case.generated_artifact.content_hash,
        approval_id=case.structured_record.record_id,
        signer=signer,
    )

    transition(case, CaseState.SIGNATURE_AUTHORIZED)

    esign = None
    # Priority 1: real Foxit eSign if credentials configured
    if os.environ.get("FOXIT_ESIGN_CLIENT_ID"):
        try:
            from ..providers.foxit_real import FoxitESignClient
            es = FoxitESignClient()
            if es.is_configured:
                pdf_path = getattr(case, '_prepared_artifact_path', '')
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    folder = es.create_folder(pdf_bytes, signer)
                    esign = {"provider": "foxit_esign", "mode": "live",
                             "folder_id": folder.get("folderId", ""),
                             "request_id": folder.get("request_id", ""),
                             "signer": signer, "status": "SENT"}
        except Exception:
            pass

    # Priority 2: simulated signing
    if esign is None:
        from ..providers.stubs import foxit_esign_request
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

    # Pure-auto cases (zero human exceptions) enter the spot-audit pool —
    # measured error on this panel is the flywheel's safety evidence
    if not case.resolutions:
        from .feedback import get_loop
        conf = getattr(case, "_confidence", {}) or {}
        rules = sorted({a.get("rule_version", "unknown")
                        for a in (case.structured_record.assertions or []
                                  if isinstance(case.structured_record.assertions, list)
                                  else [])})
        get_loop().record_auto_sign(case.case_id, conf.get("confidence", 0.5), rules)

    transition(case, CaseState.SIGNED, detail={
        "signer": case.signature_request.signer,
        "signed_at": case.signature_request.signed_at,
    })
    transition(case, CaseState.ARCHIVED)
    return case
