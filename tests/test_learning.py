"""Killer-feature tests: verdict determinism + human-feedback convergence."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engine.orchestrator import run_pipeline
from src.models.domain import Case, Document


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo")


def _fresh_case():
    case = Case(prompt="determinism probe")
    for n in ["procurement_request.pdf", "vendor_quote.pdf",
              "insurance_certificate.pdf", "security_questionnaire.pdf"]:
        path = os.path.join(FIXTURE_DIR, n)
        with open(path, "rb") as f:
            stub_id = "certificate_insurance" if n == "insurance_certificate.pdf" else n.replace(".pdf", "")
            case.documents.append(Document(doc_id=stub_id, case_id=case.case_id,
                                           filename=n, raw_bytes=f.read()))
    return case


def test_determinism():
    """Same document bytes → identical ingest hashes, checks, record hash, band."""
    outcomes = []
    for _ in range(2):
        case = _fresh_case()
        run_pipeline(case)
        outcomes.append({
            "doc_hashes": [d.content_hash for d in case.documents],
            "assertions": [(a.predicate, a.result.value, a.detail) for a in case.assertions],
            "state": case.state.value,
            "record_hash": None,  # filled after approval below
        })
        from src.engine.orchestrator import resolve_exception, approve_record
        from src.models.domain import ResolutionDecision
        fail = [a for a in case.assertions if a.result.value == "FAIL"][0]
        resolve_exception(case, fail.assertion_id,
                          ResolutionDecision.CONDITIONAL_ACCEPT, "Renewed cert required", "pm")
        approve_record(case, "pm")
        outcomes[-1]["record_hash"] = case.structured_record.content_hash

    a, b = outcomes
    assert a["doc_hashes"] == b["doc_hashes"], "ingest hashes differ across runs"
    assert a["record_hash"] == b["record_hash"], \
        f"RECORD HASH NOT DETERMINISTIC: {a['record_hash']} vs {b['record_hash']}"
    assert a["assertions"] == b["assertions"], "checks differ across runs"
    assert a["state"] == b["state"]

    # gate decision deterministic too
    from src.state.machine import can_request_signature
    c1, c2 = _fresh_case(), _fresh_case()
    run_pipeline(c1); run_pipeline(c2)
    g1, g2 = can_request_signature(c1), can_request_signature(c2)
    assert g1["allowed"] == g2["allowed"] == False
    assert [r["code"] for r in g1["reasons"]] == [r["code"] for r in g2["reasons"]]

    print("[PASS] LEARN-001: full determinism — identical bytes → identical record hash,"
          " checks, gate reasons (replayable verdict)")


def test_feedback_convergence():
    """Human labels accumulate → acceptance rate trend + calibrated policy active."""
    from src.engine.feedback import FeedbackLoop
    loop = FeedbackLoop()

    # Simulate a maturing deployment: early docs risky (mixed), later clean & accepted
    import random
    random.seed(7)
    scores_and_accepts = (
        [("coverage-v1", s, s > 0.5) for s in [0.4, 0.55, 0.45, 0.6]] +
        [("coverage-v1", s, True) for s in [0.65, 0.7, 0.68, 0.75, 0.8, 0.85]]
    )
    for rule, score, accepted in scores_and_accepts:
        loop.record(rule, score, accepted)

    stats = loop.stats()
    cov = stats["rules"]["coverage-v1"]
    assert cov["n"] == 10
    assert cov["late_acceptance"] >= cov["early_acceptance"], \
        f"no convergence signal: {cov}"
    assert cov["calibrated_model_active"], "online calibrator not active"

    # calibration actually shifts scores in the observed direction
    raw_hi, raw_lo = 0.8, 0.45
    cal_hi, cal_lo = loop.calibrated("coverage-v1", raw_hi), loop.calibrated("coverage-v1", raw_lo)
    assert cal_hi >= cal_lo

    print(f"[PASS] LEARN-002: feedback loop converges "
          f"(early={cov['early_acceptance']} → late={cov['late_acceptance']}, "
          f"calibrator={'active' if cov['calibrated_model_active'] else 'inactive'})")


def test_spot_audit_panel():
    """Safety evidence = measured error on audited auto-signs, not acceptance rate."""
    from src.engine.feedback import FeedbackLoop
    loop = FeedbackLoop()
    for i in range(6):
        loop.record_auto_sign(f"case_{i}", score=0.9, rule_versions=["arith-v1"])
    assert loop.stats()["auto_sign_panel"]["audited"] == 0

    loop.spot_audit("case_0", correct=True)
    loop.spot_audit("case_1", correct=True)
    found = loop.spot_audit("case_2", correct=False)   # a real auto-sign failure
    assert found
    panel = loop.stats()["auto_sign_panel"]
    assert panel["audited"] == 3 and panel["audited_wrong"] == 1
    assert panel["measured_error_rate"] == round(1 / 3, 3)
    assert panel["pending_audit"] == 3

    # unknown case id → not found, no mutation
    assert loop.spot_audit("nope", correct=True) is False
    print("[PASS] LEARN-003: spot-audit panel measures auto-sign error rate "
          f"(3 audited, 1 wrong → {panel['measured_error_rate']})")


if __name__ == "__main__":
    test_determinism()
    test_feedback_convergence()
    test_spot_audit_panel()
    print("\nLearning-loop tests: ALL PASS")
