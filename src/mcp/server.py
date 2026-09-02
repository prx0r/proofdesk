"""ProofDesk MCP Server — exposes the evidence-gated document pipeline as MCP tools.

Run: python3 -m src.mcp.server        (stdio transport)
Add to Hermes/Claude:
  hermes mcp add proofdesk --command <venv python> --args -m src.mcp.server --cwd <proofdesk dir>

Tools cover the full lifecycle: create/upload cases, staged live runs, facts,
checks, human resolution, approve → generate → sign, audit chain/Merkle proofs,
and convergence stats.
"""
from __future__ import annotations

import asyncio
import os
import sys

# make `src` importable when launched from anywhere
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("proofdesk")

# ── lazily-initialized pipeline state (in-process) ──────────────────
_state = {}


def _ensure():
    if _state.get("ready"):
        return
    from src.api.app import cases  # reuse the API's in-memory store + ledger wiring
    from src.engine.feedback import get_loop
    _state["cases"] = cases
    _state["feedback"] = get_loop()
    _state["ready"] = True


def _get_case(case_id):
    _ensure()
    case = _state["cases"].get(case_id)
    if not case:
        raise ValueError(f"Case {case_id} not found")
    return case


def _txt(data):
    return json.dumps(data, indent=2, default=str)


import json  # noqa: E402


# ── tool implementations ────────────────────────────────────────────

def t_create_case(prompt: str) -> dict:
    _ensure()
    from src.models.domain import Case
    from src.api.app import cases
    case = Case(prompt=prompt)
    cases[case.case_id] = case
    return {"case_id": case.case_id}


def t_upload_pdf(case_id: str, path: str) -> dict:
    case = _get_case(case_id)
    from src.models.domain import Document
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    doc_id = f"doc_{os.path.splitext(os.path.basename(path))[0][:12]}_{len(case.documents)}"
    case.documents.append(Document(
        doc_id=doc_id, case_id=case.case_id,
        filename=os.path.basename(path),
        content_type="application/pdf", raw_bytes=raw))
    return {"doc_id": doc_id, "filename": os.path.basename(path), "bytes": len(raw)}


def t_run_stage(case_id: str, stop_after: str | None = None) -> dict:
    case = _get_case(case_id)
    from src.engine.orchestrator import run_pipeline
    run_pipeline(case, stop_after=stop_after)
    return {"case_id": case_id, "state": case.state.value,
            "facts": len(case.facts), "assertions": len(case.assertions),
            "blocking_exceptions": case.blocking_exceptions}


def t_facts(case_id: str) -> dict:
    case = _get_case(case_id)
    return {"facts": [f.to_public() for f in case.facts]}


def t_assertions(case_id: str) -> dict:
    case = _get_case(case_id)
    return {"assertions": [a.to_dict() for a in case.assertions],
            "state": case.state.value,
            "unresolved_blockers": case.unresolved_blockers}


def t_resolve(case_id: str, assertion_id: str, decision: str, reason: str, actor_id: str = "reviewer") -> dict:
    case = _get_case(case_id)
    from src.engine.orchestrator import resolve_exception
    from src.models.domain import ResolutionDecision
    resolve_exception(case, assertion_id, ResolutionDecision(decision), reason, actor_id)
    return {"case_id": case_id, "state": case.state.value}


def t_advance(case_id: str, signer: str = "") -> dict:
    """Advance through approve→generate→prepare→signature-request→sign as far as valid."""
    case = _get_case(case_id)
    from src.engine.orchestrator import (
        approve_record, generate_document, prepare_pdf, request_signature, sign_document)
    log = []
    for name, fn in [("approve", lambda: approve_record(case, "operator")),
                     ("generate", lambda: generate_document(case)),
                     ("prepare", lambda: prepare_pdf(case)),
                     ("signature-request", lambda: request_signature(case, signer or "signer@example.com")),
                     ("sign", lambda: sign_document(case))]:
        try:
            fn(); log.append({name: "ok"})
        except ValueError as e:
            log.append({name: f"blocked: {e}"})
            break
    conf = getattr(case, "_confidence", None) or {}
    return {"case_id": case_id, "state": case.state.value,
            "risk_band": conf.get("band"), "log": log}


def t_gate(case_id: str) -> dict:
    case = _get_case(case_id)
    from src.state.machine import can_request_signature
    return can_request_signature(case)


def t_audit(case_id: str = "", verify: bool = True) -> dict:
    _ensure()
    from src.audit.chain import EventLedger  # noqa: F401  (wired via set_ledger)
    from src.api.app import ledger
    ok, reason = ledger.verify_chain()
    out = {"chain_valid": ok, "detail": reason, **ledger.stats()}
    if case_id:
        evs = ledger.get_events(case_id)
        out["case_events"] = [{"seq": e.seq, "type": e.event_type,
                               "hash": e.event_hash[:16]} for e in evs]
    return out


def t_merkle_proof(seq: int) -> dict:
    _ensure()
    from src.api.app import ledger
    p = ledger.proof_for_seq(int(seq))
    if p is None:
        raise ValueError(f"No event at seq {seq}")
    return {"seq": p["seq"], "verified": p["verified"], "root": p["root"], "path_len": len(p["path"])}


def t_seal() -> dict:
    _ensure()
    from src.api.app import ledger
    epoch = ledger.seal_epoch()
    return {"epoch_id": epoch.epoch_id, "root": epoch.root, "events": epoch.event_count}


def t_stats() -> dict:
    _ensure()
    fb = _state["feedback"].stats()
    return {"convergence": fb}


@mcp.tool()
def proofdesk_create_case(prompt: str) -> dict:
    """Create a ProofDesk case. Returns case_id."""
    return t_create_case(prompt)

@mcp.tool()
def proofdesk_upload_pdf(case_id: str, path: str) -> dict:
    """Attach a local PDF file to a case for extraction."""
    return t_upload_pdf(case_id, path)

@mcp.tool()
def proofdesk_run_stage(case_id: str, stop_after: str = "") -> dict:
    """Run pipeline up to a stage: INGESTED, EXTRACTED, RECONCILED, CHECKED — or full run if empty."""
    return t_run_stage(case_id, stop_after or None)

@mcp.tool()
def proofdesk_facts(case_id: str) -> dict:
    """Extracted facts with confidence and source page provenance."""
    return t_facts(case_id)

@mcp.tool()
def proofdesk_checks(case_id: str) -> dict:
    """Deterministic verification assertions + unresolved blockers."""
    return t_assertions(case_id)

@mcp.tool()
def proofdesk_resolve(case_id: str, assertion_id: str, decision: str, reason: str, actor_id: str = "reviewer") -> dict:
    """Human resolution of a failing assertion (ACCEPT / CONDITIONAL_ACCEPT / REJECT)."""
    return t_resolve(case_id, assertion_id, decision, reason, actor_id)

@mcp.tool()
def proofdesk_advance(case_id: str, signer: str = "") -> dict:
    """Advance approve→generate→prepare→signature-request→sign; stops at first block."""
    return t_advance(case_id, signer)

@mcp.tool()
def proofdesk_authority_gate(case_id: str) -> dict:
    """Evaluate the Authority Gate: allowed? named reasons?"""
    return t_gate(case_id)

@mcp.tool()
def proofdesk_audit(case_id: str = "") -> dict:
    """Verify hash-chain integrity; optional per-case event list."""
    return t_audit(case_id)

@mcp.tool()
def proofdesk_merkle_proof(seq: int) -> dict:
    """Inclusion proof for ledger event at seq (RFC 6962)."""
    return t_merkle_proof(seq)

@mcp.tool()
def proofdesk_seal() -> dict:
    """Seal the ledger into a Merkle epoch; returns the root."""
    return t_seal()

@mcp.tool()
def proofdesk_convergence_stats() -> dict:
    """Human-feedback convergence stats + auto-sign spot-audit panel."""
    return t_stats()


if __name__ == "__main__":
    mcp.run(transport="stdio")
