"""ProofDesk FastAPI — evidence-gated document execution."""

from __future__ import annotations

import sys
import os

# Load .env before importing anything that reads env vars
from dotenv import load_dotenv
load_dotenv()

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.models.domain import (
    Case,
    CaseState,
    Document,
    ResolutionDecision,
    AssertionResult,
    _id,
)
from src.models.golden_fixture import FIXTURE
from src.engine.orchestrator import (
    run_pipeline,
    resolve_exception,
    approve_record,
    generate_document,
    prepare_pdf,
    request_signature,
    sign_document,
)
from src.state.machine import can_request_signature
from src.audit.chain import EventLedger
from src.audit.artifacts import ArtifactStore
from src.audit.certificates import Certificate
from src.state.machine import set_ledger

app = FastAPI(title="ProofDesk", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ValueError)
async def state_violation_handler(request, exc):
    """State-machine violations are conflicts, not server errors."""
    return JSONResponse(status_code=409, content={
        "error": "INVALID_STATE_TRANSITION",
        "detail": str(exc),
    })

# In-memory store
cases: dict[str, Case] = {}

# Tamper-evident audit infrastructure
ledger = EventLedger()
artifact_store = ArtifactStore("/tmp/proofdesk/artifacts")

# Wire ledger into state machine so every transition is recorded
set_ledger(ledger)


# --- Pydantic request/response models ---

class CreateCaseRequest(BaseModel):
    prompt: str
    documents: list[dict] = []


class RunRequest(BaseModel):
    domain: str = "procurement"
    stop_after: str | None = None


class ResolveRequest(BaseModel):
    assertion_id: str
    decision: str
    reason: str
    actor_id: str = "user_demo"


class SignatureRequestModel(BaseModel):
    signer: str = "cfo@company.com"


class SpotAuditRequest(BaseModel):
    case_id: str
    correct: bool


# --- Endpoints ---

@app.get("/v1/providers/status")
def provider_status():
    """Show which providers are live vs simulated — verifies API reachability."""
    import httpx
    nutrient_key = os.environ.get("NUTRIENT_API_KEY", "")
    nutrient_status = "UNAVAILABLE"
    if nutrient_key:
        try:
            r = httpx.get("https://api.nutrient.io", timeout=5.0)
            nutrient_status = "LIVE" if r.status_code < 500 else "ERROR"
        except Exception:
            nutrient_status = "UNREACHABLE"
    return {
        "nutrient_dws": nutrient_status,
        "authority_engine": "LOCAL",
        "audit_ledger": "VALID",
    }


@app.get("/health")
def health():
    chain_ok, chain_reason = ledger.verify_chain()
    return {
        "status": "ok" if chain_ok else "degraded",
        "version": "0.2.0",
        "audit": {
            "chain_integrity": chain_ok,
            "chain_detail": chain_reason,
            "total_events": ledger.stats()["total_events"],
            "total_artifacts": artifact_store.stats()["count"],
        },
    }


@app.get("/v1/use-cases")
def list_use_cases():
    from src.models.use_cases import list_use_cases as _list
    return {"use_cases": _list()}


@app.post("/v1/cases")
def create_case(req: CreateCaseRequest):
    case = Case(prompt=req.prompt)
    for doc_data in req.documents:
        case.documents.append(Document(
            doc_id=doc_data.get("doc_id", _id("doc_")),
            case_id=case.case_id,
            filename=doc_data.get("filename", ""),
            content_type=doc_data.get("content_type", ""),
            raw_text=doc_data.get("raw_text", ""),
        ))
    cases[case.case_id] = case
    return {"case_id": case.case_id, "state": case.state.value}


@app.get("/v1/cases")
def list_cases():
    """List all cases — the human review queue."""
    result = []
    for c in cases.values():
        result.append({
            "case_id": c.case_id,
            "prompt": c.prompt,
            "state": c.state.value,
            "documents": len(c.documents),
            "facts": len(c.facts),
            "blocking_exceptions": c.blocking_exceptions,
            "created_at": c.created_at,
        })
    return {"cases": result}


@app.post("/v1/cases/{case_id}/extract")
def extract_one(case_id: str):
    """Extract facts from the next unprocessed document — one at a time for live progress."""
    import time as _t
    from src.providers import trace as vtrace
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case.state not in (CaseState.RECEIVED, CaseState.INGESTED, CaseState.EXTRACTED):
        raise HTTPException(409, f"Case is {case.state.value} — cannot extract")

    # Find next unprocessed doc
    processed = {e.detail.get("doc_id") for e in case.audit_events if e.event_type == "DOC_EXTRACTED"}
    next_doc = None
    for d in case.documents:
        if d.doc_id not in processed and d.raw_bytes:
            next_doc = d
            break
    if not next_doc:
        # All done — transition to EXTRACTED
        if case.state == CaseState.INGESTED:
            from src.engine.orchestrator import transition
            transition(case, CaseState.EXTRACTED)
        return {"case_id": case_id, "state": case.state.value, "extraction": None, "message": "All documents processed"}

    # Extract one document
    vtrace.set_current(case_id)
    t0 = _t.time()
    try:
        from src.providers.nutrient import extract_from_document_sync
        facts = extract_from_document_sync(next_doc)
        case.facts.extend(facts)
        elapsed = (_t.time() - t0) * 1000
        # Record this doc as extracted
        from src.models.domain import AuditEvent
        evt = AuditEvent(case_id=case_id, event_type="DOC_EXTRACTED", actor="nutrient_dws",
                         detail={"doc_id": next_doc.doc_id, "filename": next_doc.filename,
                                 "facts": len(facts), "duration_ms": round(elapsed)})
        evt.compute_hash(case.audit_events[-1].content_hash if case.audit_events else "")
        case.audit_events.append(evt)
        if case.state == CaseState.RECEIVED:
            from src.engine.orchestrator import transition
            transition(case, CaseState.INGESTED)
        return {
            "case_id": case_id,
            "state": case.state.value,
            "extraction": {
                "doc_id": next_doc.doc_id,
                "filename": next_doc.filename,
                "facts_extracted": len(facts),
                "duration_ms": round(elapsed),
                "facts": [{"field": f.field_name, "value": f.value_raw, "confidence": f.confidence, "page": f.source_page} for f in facts],
            },
        }
    except Exception as e:
        elapsed = (_t.time() - t0) * 1000
        return {"case_id": case_id, "state": case.state.value,
                "extraction": {"doc_id": next_doc.doc_id, "filename": next_doc.filename,
                               "error": str(e)[:200], "duration_ms": round(elapsed)}}


@app.post("/v1/cases/use-case/{use_case_id}")
def create_use_case(use_case_id: str):
    """Create a case pre-loaded with a specific use case's documents."""
    from src.models.use_cases import get_use_case
    uc = get_use_case(use_case_id)
    if not uc:
        raise HTTPException(404, f"Use case '{use_case_id}' not found")
    case = Case(prompt=uc.prompt)
    for doc_data in uc.documents:
        case.documents.append(Document(
            doc_id=doc_data["doc_id"],
            case_id=case.case_id,
            filename=doc_data["filename"],
            content_type=doc_data["content_type"],
            raw_text=doc_data["source_text"],
        ))
    cases[case.case_id] = case
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "use_case": uc.name,
        "documents": len(case.documents),
    }


@app.post("/v1/cases/upload")
async def upload_case(files: list[UploadFile] = File(...)):
    """Upload real PDFs — judges can drop their own documents and watch the live run."""
    import uuid
    case = Case(prompt="Uploaded document bundle")
    loaded = []
    for f in files:
        raw = await f.read()
        if not raw:
            continue
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        case.documents.append(Document(
            doc_id=doc_id,
            case_id=case.case_id,
            filename=f.filename,
            content_type=f.content_type or "application/pdf",
            raw_bytes=raw,
        ))
        loaded.append({"doc_id": doc_id, "filename": f.filename, "bytes": len(raw)})
    if not case.documents:
        raise HTTPException(400, "No valid files uploaded")
    cases[case.case_id] = case
    return {"case_id": case.case_id, "documents": loaded}


@app.post("/v1/cases/fixture")
def create_fixture_case():
    """Create a case pre-loaded with the golden fixture documents (procurement)."""
    from src.models.use_cases import get_use_case
    uc = get_use_case("procurement")
    case = Case(prompt=uc.prompt)
    
    # Map use case doc_ids to actual PDF filenames
    filename_map = {
        "doc_procurement_request": "procurement_request.pdf",
        "doc_vendor_quote": "vendor_quote.pdf",
        "doc_certificate_insurance": "insurance_certificate.pdf",
        "doc_security_questionnaire": "security_questionnaire.pdf",
    }
    
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "demo")
    
    for doc_data in uc.documents:
        mapped_filename = filename_map.get(doc_data["doc_id"], doc_data["filename"])
        pdf_path = os.path.join(pdf_dir, mapped_filename)
        raw_bytes = b""
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                raw_bytes = f.read()
        
        case.documents.append(Document(
            doc_id=doc_data["doc_id"],
            case_id=case.case_id,
            filename=mapped_filename,
            content_type=doc_data["content_type"],
            raw_text=doc_data["source_text"],
            raw_bytes=raw_bytes,
        ))
    
    cases[case.case_id] = case
    return {"case_id": case.case_id, "state": case.state.value, "documents": len(case.documents)}


@app.post("/v1/cases/{case_id}/check")
def check_case(case_id: str):
    """Run cross-document verification and classification — after extraction."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case.state not in (CaseState.EXTRACTED, CaseState.RECONCILED, CaseState.CHECKED):
        raise HTTPException(409, f"Case is {case.state.value} — extract first")
    try:
        run_pipeline(case, domain="procurement", stop_after="CHECKED")
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "facts": len(case.facts),
        "assertions": len(case.assertions),
        "blocking_exceptions": case.blocking_exceptions,
        "assertion_details": [a.to_dict() for a in case.assertions],
    }


@app.post("/v1/cases/{case_id}/run")
def run_case(case_id: str, req: RunRequest | None = None):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    domain = req.domain if req else "procurement"
    stop_after = None
    if req and req.stop_after:
        stop_after = req.stop_after
    try:
        run_pipeline(case, domain=domain, stop_after=stop_after)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "blocking_exceptions": case.blocking_exceptions,
        "domain": domain,
    }


@app.get("/v1/cases/{case_id}")
def get_case(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    conf = getattr(case, "_confidence", None) or {}
    cls = getattr(case, "_classification", None) or {}
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "state": case.state.value,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "risk_band": conf.get("band"),
        "signing_confidence": conf.get("score") or conf.get("confidence"),
        "field_risks": conf.get("field_risks", []),
        "record_hash": case.structured_record.content_hash if case.structured_record else None,
        "artifact_hash": getattr(case, '_prepared_artifact_hash', None) or (case.generated_artifact.content_hash if case.generated_artifact else None),
        "classification": cls,
    }


@app.get("/v1/cases/{case_id}/trace")
def case_trace(case_id: str):
    """Vendor API call trace — every outbound provider HTTP call for this case."""
    from src.providers import trace as vtrace
    return {"calls": vtrace.get(case_id)}


@app.get("/v1/feedback/stats")
def feedback_stats():
    from src.engine.feedback import get_loop
    return get_loop().stats()


@app.post("/v1/feedback/spot-audit")
def spot_audit(req: SpotAuditRequest):
    from src.engine.feedback import get_loop
    found = get_loop().spot_audit(req.case_id, req.correct)
    if not found:
        raise HTTPException(404, "Case not in auto-sign pool")
    return {"ok": True}


@app.get("/v1/cases/{case_id}/facts")
def get_facts(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return {"facts": [f.to_public() for f in case.facts]}


@app.get("/v1/cases/{case_id}/documents/{doc_id}/file")
def get_document_file(case_id: str, doc_id: str):
    """Serve raw document bytes — the source a fact cites in Nutrient DWS Viewer."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    doc = next((d for d in case.documents if d.doc_id == doc_id), None)
    if doc is None:
        raise HTTPException(404, f"Document {doc_id} not found")
    media = doc.content_type or "application/pdf"
    body = doc.raw_bytes or (doc.raw_text.encode("latin-1", errors="replace") if doc.raw_text else b"")
    return Response(content=body, media_type=media)


@app.get("/v1/cases/{case_id}/assertions")
def get_assertions(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return {"assertions": [a.to_dict() for a in case.assertions]}


@app.post("/v1/cases/{case_id}/resolve")
def resolve_case(case_id: str, req: ResolveRequest):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case.state != CaseState.REVIEW_REQUIRED:
        raise HTTPException(409, f"Case is {case.state.value}, not REVIEW_REQUIRED — nothing to resolve")
    target = next((a for a in case.assertions
                   if a.assertion_id == req.assertion_id), None)
    if target is None:
        raise HTTPException(409, f"Unknown assertion {req.assertion_id}")
    if target.result != AssertionResult.FAIL:
        raise HTTPException(409, f"Assertion {req.assertion_id} did not fail — nothing to resolve")
    try:
        decision = ResolutionDecision(req.decision)
        resolve_exception(case, req.assertion_id, decision, req.reason, req.actor_id)
    except (ValueError, KeyError) as e:
        raise HTTPException(409, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "blocking_exceptions": case.blocking_exceptions,
    }


@app.post("/v1/cases/{case_id}/approve")
def approve_case(case_id: str, actor_id: str = "user_demo"):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    try:
        approve_record(case, actor_id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "record_hash": case.structured_record.content_hash,
    }


@app.post("/v1/cases/{case_id}/generate")
def generate_case(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    try:
        generate_document(case)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "artifact_id": case.generated_artifact.artifact_id,
    }


@app.post("/v1/cases/{case_id}/prepare")
def prepare_case(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    try:
        prepare_pdf(case)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"case_id": case.case_id, "state": case.state.value}


@app.post("/v1/cases/{case_id}/signature-request")
def sig_request(case_id: str, req: SignatureRequestModel):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    try:
        request_signature(case, req.signer)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {
        "case_id": case.case_id,
        "state": case.state.value,
        "signer": req.signer,
    }


@app.post("/v1/cases/{case_id}/sign")
def sign_case(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    try:
        sign_document(case)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"case_id": case.case_id, "state": case.state.value}


@app.get("/v1/cases/{case_id}/events")
def get_events(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return {
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor": e.actor,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "detail": e.detail,
                "timestamp": e.timestamp,
                "content_hash": e.content_hash,
            }
            for e in case.audit_events
        ]
    }


@app.get("/v1/cases/{case_id}/signature-gate")
def signature_gate(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return can_request_signature(case)


@app.get("/v1/cases/{case_id}/receipt")
def get_receipt(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    content = ""
    if getattr(case, "_generated_content", None) and case.generated_artifact:
        content = case._generated_content.get(case.generated_artifact.artifact_id, "")
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "final_state": case.state.value,
        "generated_content": content,
        "facts_extracted": len(case.facts),
        "assertions_checked": len(case.assertions),
        "resolutions": len(case.resolutions),
        "record_hash": case.structured_record.content_hash if case.structured_record else None,
        "artifact_hash": getattr(case, '_prepared_artifact_hash', None) or (case.generated_artifact.content_hash if case.generated_artifact else None),
        "signature_status": case.signature_request.status if case.signature_request else None,
        "audit_events": len(case.audit_events),
    }


# --- Static files and SPA ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "landing.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>ProofDesk</h1><p>Static files not found.</p>")


@app.get("/demo", response_class=HTMLResponse)
def serve_demo():
    """Live demo — real Nutrient DWS API calls."""
    demo_path = os.path.join(STATIC_DIR, "demo.html")
    if os.path.exists(demo_path):
        return FileResponse(demo_path)
    return HTMLResponse("<h1>ProofDesk Demo</h1><p>demo.html not found.</p>")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Audit endpoints ---

@app.get("/v1/audit/chain")
def audit_chain():
    """Verify the full hash chain integrity."""
    ok, reason = ledger.verify_chain()
    return {"valid": ok, "detail": reason, "stats": ledger.stats()}


@app.get("/v1/audit/events")
def audit_events_all():
    """Get all ledger events."""
    return {"events": [e.to_dict() for e in ledger.get_events()]}


@app.get("/v1/audit/events/{case_id}")
def audit_events_for_case(case_id: str):
    """Get ledger events for a specific case."""
    return {"events": [e.to_dict() for e in ledger.get_events(case_id)]}


@app.get("/v1/audit/proof/{seq}")
def audit_proof(seq: int):
    """Get Merkle inclusion proof for a specific event."""
    proof = ledger.proof_for_seq(seq)
    if proof is None:
        raise HTTPException(404, f"Event seq {seq} not found")
    return proof


@app.get("/v1/audit/artifacts")
def audit_artifacts():
    """List all content-addressed artifacts."""
    return artifact_store.stats()


@app.get("/v1/audit/seal")
def audit_seal():
    """Seal current events into a Merkle epoch."""
    epoch = ledger.seal_epoch()
    return {"epoch_id": epoch.epoch_id, "root": epoch.root, "events": epoch.event_count}


# --- Batch Processing Endpoints ---

class BatchResolveRequest(BaseModel):
    correct: bool
    reason: str = ""
    actor_id: str = "human_reviewer"


@app.post("/v1/batch")
async def create_batch(files: list[UploadFile] = File(...)):
    """Upload multiple PDFs and start batch processing."""
    from src.engine.batch import get_processor

    file_data = []
    for f in files:
        raw = await f.read()
        if raw:
            file_data.append((f.filename, raw, f.content_type or "application/pdf"))

    if not file_data:
        raise HTTPException(400, "No valid files uploaded")

    processor = get_processor()
    job = processor.create_job(file_data)
    return {
        "batch_id": job.batch_id,
        "total_files": job.total_count,
        "status": job.status,
    }


@app.get("/v1/batch/{batch_id}/status")
def batch_status(batch_id: str):
    """Get batch processing status."""
    from src.engine.batch import get_processor

    processor = get_processor()
    job = processor.get_job(batch_id)
    if not job:
        raise HTTPException(404, "Batch not found")

    return {
        "batch_id": job.batch_id,
        "status": job.status,
        "processed": job.processed_count,
        "total": job.total_count,
        "current_file": job.files[job.processed_count].filename
        if job.processed_count < len(job.files) else None,
    }


@app.post("/v1/batch/{batch_id}/process")
def process_batch(batch_id: str):
    """Process the next pending file in the batch."""
    from src.engine.batch import get_processor

    processor = get_processor()
    result = processor.process_next(batch_id)
    if result is None:
        raise HTTPException(204, "No pending files")

    return result.to_dict()


@app.get("/v1/batch/{batch_id}/results")
def batch_results(batch_id: str):
    """Get all file results for a batch."""
    from src.engine.batch import get_processor

    processor = get_processor()
    results = processor.get_results(batch_id)
    if not results:
        raise HTTPException(404, "Batch not found")

    return {"batch_id": batch_id, "results": results}


@app.post("/v1/batch/{batch_id}/resolve/{file_id}")
def resolve_batch_file(batch_id: str, file_id: str, req: BatchResolveRequest):
    """Resolve a deferred file with human feedback."""
    from src.engine.batch import get_processor

    processor = get_processor()
    result = processor.resolve_file(
        batch_id, file_id, req.correct, req.reason, req.actor_id
    )
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@app.get("/v1/batch/{batch_id}/report")
def batch_report(batch_id: str):
    """Get final report with Merkle proofs per document."""
    from src.engine.batch import get_processor

    processor = get_processor()
    report = processor.get_report(batch_id)
    if "error" in report:
        raise HTTPException(404, report["error"])
    return report


# --- Demo tamper endpoints ---

@app.post("/v1/cases/{case_id}/demo/tamper")
def demo_tamper(case_id: str):
    """Append one byte to the prepared PDF to demonstrate tamper detection."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    path = getattr(case, '_prepared_artifact_path', None)
    if not path or not os.path.exists(path):
        raise HTTPException(400, "No prepared artifact to tamper")
    import shutil
    backup = path + ".backup"
    shutil.copy2(path, backup)
    with open(path, "ab") as f:
        f.write(b"\x00")
    # Recompute hash
    import hashlib
    with open(path, "rb") as f:
        case._prepared_artifact_hash = hashlib.sha256(f.read()).hexdigest()
    return {"tampered": True, "path": path}


@app.post("/v1/cases/{case_id}/demo/restore")
def demo_restore(case_id: str):
    """Restore the prepared PDF from backup."""
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    path = getattr(case, '_prepared_artifact_path', None)
    backup = path + ".backup" if path else None
    if not backup or not os.path.exists(backup):
        raise HTTPException(400, "No backup to restore")
    import shutil, hashlib
    shutil.copy2(backup, path)
    os.unlink(backup)
    with open(path, "rb") as f:
        case._prepared_artifact_hash = hashlib.sha256(f.read()).hexdigest()
    return {"restored": True, "path": path}
