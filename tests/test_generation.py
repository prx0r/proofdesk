"""Document generation tests — payload builder, branch logic, PDF output."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.providers.stubs import build_approval_payload as build_generation_payload
from src.providers.stubs import render_approval_memo
from src.models.domain import (
    Case, Document, GeneratedArtifact,
    CaseState, ResolutionDecision,
)
from src.engine.orchestrator import run_pipeline, generate_document, approve_record
from src.state.machine import can_request_signature


def _record(with_fail=True, with_resolution=False):
    assertions = [
        {"predicate": "quote.total == platform + support", "result": "PASS", "detail": "ok", "severity": "BLOCKER", "rule_version": "arith-v1"},
    ]
    if with_fail:
        assertions.append({
            "predicate": "insurance.expiry_date >= required_coverage_until",
            "result": "FAIL", "detail": "31-day gap", "severity": "BLOCKER",
            "rule_version": "coverage-v1",
        })
    resolutions = []
    if with_resolution:
        resolutions.append({"decision": "CONDITIONAL_ACCEPT", "reason": "Renewed cert required", "actor_id": "pm"})
    return {
        "case_id": "case_t1", "record_id": "rec_t1", "content_hash": "sha256:abc123",
        "facts": [
            {"field": "vendor.legal_name", "value_normalized": "Northstar Data Systems Ltd."},
            {"field": "quote.total", "value_normalized": "42500"},
        ],
        "assertions": assertions, "resolutions": resolutions,
    }


def test_payload_builder():
    p = build_generation_payload(_record(with_fail=False))
    assert p["risk_band"] == "CLEARED", p["risk_band"]
    assert p["has_conditions"] == "false" and p["condition_count"] == 0

    p = build_generation_payload(_record(with_resolution=True))
    assert p["risk_band"] == "CONDITIONAL"
    assert p["condition_count"] == 1

    p = build_generation_payload(_record())
    assert p["risk_band"] == "ESCALATED"

    p = build_generation_payload(_record(), {"confidence": 0.41, "band": "CONDITIONAL",
        "field_risks": [{"field": "insurance.expiry_date", "detail": "6% > 3% budget"}]})
    assert p["signing_confidence"] == "0.41"
    assert p["condition_count"] == 2

    a = build_generation_payload(_record()); b = build_generation_payload(_record())
    a.pop("generated_date"); b.pop("generated_date")
    assert a == b

    print("[PASS] GEN-001..005: payload builder bands, confidence wiring, determinism")


def test_generation_produces_pdf():
    artifact, content = render_approval_memo(_record(with_fail=False))
    assert artifact is not None
    assert artifact.output_path is not None
    assert artifact.output_path.endswith(".pdf"), f"expected PDF, got {artifact.output_path}"
    assert os.path.exists(artifact.output_path)

    with open(artifact.output_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", f"file does not start with %PDF: {header}"
    assert len(content) > 0
    assert "VENDOR" in content

    print("[PASS] GEN-006: local renderer produces valid PDF")


def test_generation_content_branches():
    cleared, content_cleared = render_approval_memo(_record(with_fail=False))
    escalated, content_escalated = render_approval_memo(_record(with_fail=True, with_resolution=False))

    with open(cleared.output_path, "rb") as f:
        c_bytes = f.read()
    with open(escalated.output_path, "rb") as f:
        e_bytes = f.read()

    # Check PDF header
    assert c_bytes[:5] == b"%PDF-"
    assert e_bytes[:5] == b"%PDF-"

    # Content is also in the returned string
    assert "APPROVED" in content_cleared or "CLEARED" in content_cleared
    assert "REQUIRES RESOLUTION" in content_escalated or "REJECTED" in content_escalated

    print("[PASS] GEN-007: risk band changes document content")


def test_gate_blocks_pre_resolution():
    case = Case(prompt="test")
    case.documents.append(Document(
        doc_id="doc1", case_id=case.case_id, filename="test.pdf",
        content_type="application/pdf", raw_text="test content",
    ))
    run_pipeline(case)
    gate = can_request_signature(case)
    assert not gate["allowed"], "gate must deny before resolution"
    print(f"[PASS] GEN-008: gate denies pre-resolution ({len(gate['reasons'])} reasons)")


if __name__ == "__main__":
    test_payload_builder()
    test_generation_produces_pdf()
    test_generation_content_branches()
    test_gate_blocks_pre_resolution()
    print("\nGeneration tests: ALL PASS")
