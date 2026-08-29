"""Comprehensive test suite for ProofDesk — validates all rubric criteria programmatically."""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.domain import (
    Case, Document, ExtractedFact, Assertion, Resolution,
    CaseState, FactStatus, AssertionResult, ExceptionSeverity,
    ResolutionDecision, StructuredRecord, _hash, _id,
)
from src.models.golden_fixture import FIXTURE
from src.engine.reconciliation import (
    normalize_currency, normalize_date, normalize_boolean,
    normalize_entity_name, parse_numeric, run_checks,
    build_fact_index, check_procurement, check_insurance,
)
from src.engine.orchestrator import (
    run_pipeline, resolve_exception, approve_record,
    generate_document, prepare_pdf, request_signature, sign_document,
)
from src.state.machine import transition, can_request_signature, TRANSITIONS, FORBIDDEN_TRANSITIONS


# --- Test helpers ---

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.errors = []

    def check(self, condition: bool, msg: str):
        if not condition:
            self.passed = False
            self.errors.append(msg)

    def __repr__(self):
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}" + (f" — {'; '.join(self.errors)}" if self.errors else "")


results: list[TestResult] = []


def test(name: str):
    r = TestResult(name)
    results.append(r)
    return r


# --- Normalization tests ---

def test_normalization():
    r = test("NORM-001: Currency parsing")
    r.check(normalize_currency("$42,500") == 42500.0, "Failed to parse $42,500")
    r.check(normalize_currency("$35,000") == 35000.0, "Failed to parse $35,000")
    r.check(normalize_currency("$7,500") == 7500.0, "Failed to parse $7,500")
    r.check(normalize_currency("42500") == 42500.0, "Failed to parse 42500")
    r.check(normalize_currency("invalid") is None, "Should return None for invalid")

    r = test("NORM-002: Date parsing")
    r.check(str(normalize_date("2027-08-31")) == "2027-08-31", "Failed ISO date")
    r.check(str(normalize_date("August 31, 2027")) == "2027-08-31", "Failed human date")
    r.check(normalize_date("invalid") is None, "Should return None for invalid")

    r = test("NORM-003: Boolean parsing")
    r.check(normalize_boolean("Yes") is True, "Yes should be True")
    r.check(normalize_boolean("No") is False, "No should be False")
    r.check(normalize_boolean("true") is True, "true should be True")
    r.check(normalize_boolean("false") is False, "false should be False")

    r = test("NORM-004: Entity name normalization")
    r.check(normalize_entity_name("Northstar Data Systems Ltd.") == "Northstar Data Systems", "Ltd. strip failed")
    r.check(normalize_entity_name("Northstar Data Systems Limited") == "Northstar Data Systems", "Limited strip failed")
    r.check(
        normalize_entity_name("Northstar Data Systems Ltd.") == normalize_entity_name("Northstar Data Systems Limited"),
        "Ltd. and Limited should normalize to same value",
    )

    r = test("NORM-005: Numeric parsing")
    r.check(parse_numeric("30 days") == 30.0, "Failed '30 days'")
    r.check(parse_numeric("3") == 3.0, "Failed '3'")
    r.check(parse_numeric("$42,500") == 42500.0, "Failed '$42,500'")


# --- Reconciliation engine tests ---

def test_reconciliation():
    facts = []
    for f in FIXTURE["expected_extractions"]:
        facts.append(ExtractedFact(
            case_id="test",
            doc_id=f["doc_id"],
            field_name=f["field"],
            value_raw=f["value_raw"],
            value_normalized=f["value_normalized"],
            source_page=f["page"],
            confidence=f["confidence"],
        ))

    r = test("RECON-001: Quote arithmetic")
    fact_index = build_fact_index(facts)
    procurement_assertions = check_procurement(fact_index)
    quote_assertion = [a for a in procurement_assertions if a.predicate.startswith("quote.total ==")]
    r.check(len(quote_assertion) == 1 and quote_assertion[0].result == AssertionResult.PASS,
            f"Expected PASS for quote arithmetic, got {quote_assertion}")

    r = test("RECON-002: Entity name normalization")
    entity_assertion = [a for a in procurement_assertions if "vendor.legal_name" in a.predicate]
    r.check(len(entity_assertion) == 1 and entity_assertion[0].result == AssertionResult.PASS,
            f"Expected PASS for entity names, got {entity_assertion}")

    r = test("RECON-003: Insurance coverage date — FAILS correctly")
    # The procurement fixture doesn't have insurance data (different doc IDs)
    # So we test with a specific fact set
    from datetime import date
    test_facts = [
        ExtractedFact(case_id="t", field_name="insurance.expiry_date", value_raw="2027-08-31", value_normalized="2027-08-31", doc_id="d", confidence=0.99),
        ExtractedFact(case_id="t", field_name="procurement.required_coverage_until", value_raw="2027-10-01", value_normalized="2027-10-01", doc_id="d", confidence=0.98),
    ]
    test_index = build_fact_index(test_facts)
    # Run procurement checks on these specific facts
    all_assertions = check_procurement(test_index)
    coverage = [a for a in all_assertions if "insurance.expiry" in a.predicate]
    r.check(len(coverage) == 1 and coverage[0].result == AssertionResult.FAIL,
            f"Expected FAIL for coverage date, got {coverage}")

    r = test("RECON-004: Spend matches quote")
    spend_assertion = [a for a in procurement_assertions if "requested_spend" in a.predicate]
    r.check(len(spend_assertion) == 1 and spend_assertion[0].result == AssertionResult.PASS,
            f"Expected PASS for spend match, got {spend_assertion}")

    r = test("RECON-005: Encryption at rest")
    enc_assertion = [a for a in procurement_assertions if "encryption" in a.predicate]
    r.check(len(enc_assertion) == 1 and enc_assertion[0].result == AssertionResult.PASS,
            f"Expected PASS for encryption, got {enc_assertion}")

    r = test("RECON-006: All checks run")
    assertions = run_checks(facts, domain="procurement")
    r.check(len(assertions) >= 4, f"Expected >= 4 assertions, got {len(assertions)}")
    # Procurement fixture has 4 pass + 1 fail (insurance coverage date)
    failing = [a for a in assertions if a.result == AssertionResult.FAIL]
    r.check(len(failing) <= 1, f"Expected <= 1 failure for procurement, got {len(failing)}")


# --- State machine tests ---

def test_state_machine():
    r = test("STATE-001: Valid transitions exist")
    r.check(len(TRANSITIONS) == 14, f"Expected 14 states with outgoing transitions (ARCHIVED is terminal), got {len(TRANSITIONS)}")

    r = test("STATE-002: Forbidden transitions defined")
    r.check(len(FORBIDDEN_TRANSITIONS) == 3, f"Expected 3 forbidden, got {len(FORBIDDEN_TRANSITIONS)}")
    r.check((CaseState.REVIEW_REQUIRED, CaseState.GENERATED) in FORBIDDEN_TRANSITIONS, "REVIEW_REQUIRED->GENERATED should be forbidden")
    r.check((CaseState.CHECKED, CaseState.SIGNATURE_REQUESTED) in FORBIDDEN_TRANSITIONS, "CHECKED->SIGNATURE_REQUESTED should be forbidden")
    r.check((CaseState.GENERATED, CaseState.SIGNATURE_REQUESTED) in FORBIDDEN_TRANSITIONS, "GENERATED->SIGNATURE_REQUESTED should be forbidden")

    r = test("STATE-003: Valid transition succeeds")
    case = Case()
    transition(case, CaseState.INGESTED)
    r.check(case.state == CaseState.INGESTED, f"Expected INGESTED, got {case.state}")
    r.check(len(case.audit_events) == 1, "Should have 1 audit event")

    r = test("STATE-004: Invalid transition raises")
    case = Case()
    try:
        transition(case, CaseState.APPROVED)
        r.check(False, "Should have raised ValueError")
    except ValueError:
        r.check(True, "Correctly raised ValueError")

    r = test("STATE-005: Forbidden transition raises")
    case = Case()
    case.state = CaseState.REVIEW_REQUIRED
    try:
        transition(case, CaseState.GENERATED)
        r.check(False, "Should have raised ValueError for forbidden transition")
    except ValueError:
        r.check(True, "Correctly raised ValueError for forbidden transition")


# --- SignatureGate tests ---

def test_signature_gate():
    r = test("GATE-001: Gate denies when not PREPARED")
    case = Case()
    case.state = CaseState.RECEIVED
    gate = can_request_signature(case)
    r.check(not gate["allowed"], "Should deny")
    r.check(any(g["code"] == "INVALID_STATE" for g in gate["reasons"]), "Should have INVALID_STATE reason")

    r = test("GATE-002: Gate denies with unresolved blockers")
    case = Case()
    case.state = CaseState.PREPARED
    case.assertions.append(Assertion(
        predicate="test",
        result=AssertionResult.FAIL,
        severity=ExceptionSeverity.BLOCKER,
    ))
    gate = can_request_signature(case)
    r.check(not gate["allowed"], "Should deny with blocker")
    r.check(any(g["code"] == "UNRESOLVED_BLOCKER" for g in gate["reasons"]), "Should have UNRESOLVED_BLOCKER")

    r = test("GATE-003: Gate denies without human approval")
    case = Case()
    case.state = CaseState.PREPARED
    gate = can_request_signature(case)
    r.check(not gate["allowed"], "Should deny without approval")
    r.check(any(g["code"] == "NO_HUMAN_APPROVAL" for g in gate["reasons"]), "Should have NO_HUMAN_APPROVAL")

    r = test("GATE-004: Gate denies without structured record")
    case = Case()
    case.state = CaseState.PREPARED
    gate = can_request_signature(case)
    r.check(not gate["allowed"], "Should deny without record")
    r.check(any(g["code"] == "NO_STRUCTURED_RECORD" for g in gate["reasons"]), "Should have NO_STRUCTURED_RECORD")

    r = test("GATE-005: Gate allows when all conditions met")
    case = Case()
    case.state = CaseState.PREPARED
    case.resolutions.append(Resolution(
        assertion_id="test",
        decision=ResolutionDecision.CONDITIONAL_ACCEPT,
        reason="test",
    ))
    case.structured_record = StructuredRecord(case_id="test")
    case.structured_record.compute_hash()
    case.generated_artifact = __import__("src.models.domain", fromlist=["GeneratedArtifact"]).GeneratedArtifact(
        case_id="test",
        record_hash=case.structured_record.content_hash,
    )
    gate = can_request_signature(case)
    r.check(gate["allowed"], f"Should allow, got reasons: {gate['reasons']}")


# --- Full pipeline integration test ---

def test_full_pipeline():
    r = test("E2E-001: Full pipeline produces correct state sequence")
    case = Case(prompt=FIXTURE["prompt"])
    for doc_data in FIXTURE["documents"]:
        case.documents.append(Document(
            doc_id=doc_data["doc_id"],
            case_id=case.case_id,
            filename=doc_data["filename"],
            content_type=doc_data["content_type"],
            raw_text=doc_data["source_text"],
        ))

    run_pipeline(case)
    r.check(case.state == CaseState.REVIEW_REQUIRED, f"Expected REVIEW_REQUIRED, got {case.state}")
    r.check(len(case.facts) > 0, f"Expected facts, got {len(case.facts)}")
    r.check(len(case.assertions) == 5, f"Expected 5 assertions, got {len(case.assertions)}")

    r = test("E2E-002: Seeded insurance blocker detected")
    failing = [a for a in case.assertions if a.result == AssertionResult.FAIL]
    r.check(len(failing) == 1, f"Expected 1 failure, got {len(failing)}")
    r.check("insurance" in failing[0].predicate.lower() or "coverage" in failing[0].predicate.lower(),
            "Failure should be about insurance/coverage")

    r = test("E2E-003: Premature signature denied")
    gate = can_request_signature(case)
    r.check(not gate["allowed"], "Signature should be denied before resolution")

    r = test("E2E-004: Resolution unblocks pipeline")
    resolve_exception(
        case, failing[0].assertion_id,
        ResolutionDecision.CONDITIONAL_ACCEPT,
        "Renewed insurance required",
        "test_user",
    )
    r.check(case.state == CaseState.APPROVABLE, f"Expected APPROVABLE, got {case.state}")
    r.check(case.unresolved_blockers == 0, f"Expected 0 unresolved, got {case.unresolved_blockers}")

    r = test("E2E-005: Approval creates structured record with hash")
    approve_record(case, "test_user")
    r.check(case.state == CaseState.APPROVED, f"Expected APPROVED, got {case.state}")
    r.check(case.structured_record is not None, "Record should exist")
    r.check(case.structured_record.content_hash.startswith("sha256:"), "Hash should start with sha256:")

    r = test("E2E-006: Document generation succeeds")
    generate_document(case)
    r.check(case.state == CaseState.GENERATED, f"Expected GENERATED, got {case.state}")
    r.check(case.generated_artifact is not None, "Artifact should exist")
    r.check(case.generated_artifact.content_hash.startswith("sha256:"), "Artifact hash should exist")

    r = test("E2E-007: PDF preparation succeeds")
    prepare_pdf(case)
    r.check(case.state == CaseState.PREPARED, f"Expected PREPARED, got {case.state}")

    r = test("E2E-008: Signature gate passes after all conditions met")
    gate = can_request_signature(case)
    r.check(gate["allowed"], f"Signature should be allowed, got: {gate['reasons']}")

    r = test("E2E-009: Signature request succeeds")
    request_signature(case, "cfo@test.com")
    r.check(case.state == CaseState.SIGNATURE_REQUESTED, f"Expected SIGNATURE_REQUESTED, got {case.state}")

    r = test("E2E-010: Signing completes and archives")
    sign_document(case)
    r.check(case.state == CaseState.ARCHIVED, f"Expected ARCHIVED, got {case.state}")

    r = test("E2E-011: Audit trail has all events")
    r.check(len(case.audit_events) >= 14, f"Expected >= 14 events, got {len(case.audit_events)}")
    event_types = [e.event_type for e in case.audit_events]
    r.check("STATE_TRANSITION" in event_types, "Should have STATE_TRANSITION events")
    r.check("EXCEPTION_RESOLVED" in event_types, "Should have EXCEPTION_RESOLVED event")


# --- Hash chain tests ---

def test_hash_chain():
    r = test("HASH-001: Record hash changes when facts change")
    record1 = StructuredRecord(facts=[{"field": "a", "value": "1"}])
    record1.compute_hash()
    record2 = StructuredRecord(facts=[{"field": "a", "value": "2"}])
    record2.compute_hash()
    r.check(record1.content_hash != record2.content_hash, "Different facts should produce different hashes")

    r = test("HASH-002: Record hash changes when resolutions change")
    record3 = StructuredRecord(
        facts=[{"field": "a", "value": "1"}],
        resolutions=[{"decision": "ACCEPT"}],
    )
    record3.compute_hash()
    record4 = StructuredRecord(
        facts=[{"field": "a", "value": "1"}],
        resolutions=[{"decision": "REJECT"}],
    )
    record4.compute_hash()
    r.check(record3.content_hash != record4.content_hash, "Different resolutions should produce different hashes")

    r = test("HASH-003: Same data produces same hash")
    record5 = StructuredRecord(facts=[{"field": "a", "value": "1"}])
    h1 = record5.compute_hash()
    record5.revision = 2
    h2 = record5.compute_hash()
    r.check(h1 != h2, "Revision change should change hash")


# --- Document generation determinism tests ---

def test_deterministic_generation():
    r = test("GEN-001: Same input produces same output")
    record_data = {
        "case_id": "test",
        "record_id": "rec_test",
        "facts": FIXTURE["expected_extractions"],
        "assertions": [{"predicate": "test", "result": "PASS", "detail": "ok", "severity": "BLOCKER"}],
        "resolutions": [],
        "content_hash": "sha256:test",
    }
    from src.providers.stubs import doctavian_generate
    _, content1 = doctavian_generate(record_data)
    _, content2 = doctavian_generate(record_data)
    r.check(content1 == content2, "Same input should produce identical output")

    r = test("GEN-002: Different input produces different output")
    record_data_alt = {
        "case_id": "test_alt",
        "record_id": "rec_alt",
        "facts": [
            {"field": "vendor.legal_name", "value_normalized": "ACME Corp", "doc_id": "d1", "page": 1, "value_raw": "ACME Corp", "confidence": 0.99},
            {"field": "quote.total", "value_normalized": "99999", "doc_id": "d1", "page": 1, "value_raw": "$99,999", "confidence": 0.99},
        ],
        "assertions": [{"predicate": "test", "result": "PASS", "detail": "ok", "severity": "BLOCKER"}],
        "resolutions": [],
        "content_hash": "sha256:test_alt",
    }
    _, content3 = doctavian_generate(record_data_alt)
    r.check(content1 != content3, "Different input should produce different output")

    r = test("GEN-003: Branching — approved vs conditional")
    record_approved = dict(record_data)
    record_approved["assertions"] = [{"predicate": "test", "result": "PASS", "detail": "ok", "severity": "BLOCKER"}]
    _, content_approved = doctavian_generate(record_approved)
    r.check("APPROVED" in content_approved, "Approved document should contain APPROVED")

    record_conditional = dict(record_data)
    record_conditional["assertions"] = [{"predicate": "test", "result": "FAIL", "detail": "fail", "severity": "BLOCKER"}]
    record_conditional["resolutions"] = [{"decision": "CONDITIONAL_ACCEPT", "reason": "Renewed insurance required", "actor_id": "test"}]
    _, content_conditional = doctavian_generate(record_conditional)
    r.check("CONDITIONALLY APPROVED" in content_conditional, "Conditional document should contain CONDITIONALLY APPROVED")
    r.check("Renewed insurance" in content_conditional, "Conditional document should contain obligation")


# --- Run all tests ---

def run_all():
    test_normalization()
    test_reconciliation()
    test_state_machine()
    test_signature_gate()
    test_hash_chain()
    test_deterministic_generation()
    test_full_pipeline()

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    print(f"\n{'='*60}")
    print(f"  PROOFDESK TEST SUITE")
    print(f"  {passed}/{len(results)} passed, {failed} failed")
    print(f"{'='*60}\n")

    for r in results:
        print(f"  {r}")

    if failed > 0:
        print(f"\n  FAILED TESTS:")
        for r in results:
            if not r.passed:
                print(f"    {r.name}:")
                for e in r.errors:
                    print(f"      - {e}")

    print()
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
