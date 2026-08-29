"""ProofDesk FastAPI — evidence-gated document execution."""

from __future__ import annotations

import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.models.domain import (
    Case,
    CaseState,
    Document,
    ResolutionDecision,
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


class ResolveRequest(BaseModel):
    assertion_id: str
    decision: str
    reason: str
    actor_id: str = "user_demo"


class SignatureRequestModel(BaseModel):
    signer: str = "cfo@company.com"


# --- Endpoints ---

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
    
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test_pdfs")
    
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


@app.post("/v1/cases/{case_id}/run")
def run_case(case_id: str, req: RunRequest | None = None):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    domain = req.domain if req else "procurement"
    try:
        run_pipeline(case, domain=domain)
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
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "state": case.state.value,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


@app.get("/v1/cases/{case_id}/facts")
def get_facts(case_id: str):
    case = cases.get(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return {"facts": [f.to_public() for f in case.facts]}


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
    try:
        decision = ResolutionDecision(req.decision)
        resolve_exception(case, req.assertion_id, decision, req.reason, req.actor_id)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e))
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
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "final_state": case.state.value,
        "facts_extracted": len(case.facts),
        "assertions_checked": len(case.assertions),
        "resolutions": len(case.resolutions),
        "record_hash": case.structured_record.content_hash if case.structured_record else None,
        "artifact_hash": case.generated_artifact.content_hash if case.generated_artifact else None,
        "signature_status": case.signature_request.status if case.signature_request else None,
        "audit_events": len(case.audit_events),
    }


# --- Static files and SPA ---

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>ProofDesk</h1><p>Static files not found. Run the demo: python3 demo.py</p>")

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
