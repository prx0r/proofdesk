"""Tests for the tamper-evident audit system."""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audit.chain import EventLedger, GENESIS_HASH
from src.audit.merkle import (
    leaf_hash, node_hash, merkle_root, inclusion_path, verify_inclusion,
)
from src.audit.artifacts import ArtifactStore
from src.audit.signing import SignedAttestation, content_hash, generate_keypair
from src.audit.certificates import Certificate


# --- Merkle Tree Tests ---

def test_merkle_root_deterministic():
    data = [b"alpha", b"beta", b"gamma"]
    r1 = merkle_root(data)
    r2 = merkle_root(data)
    assert r1 == r2
    assert len(r1) == 64  # SHA-256 hex


def test_merkle_root_different_data():
    r1 = merkle_root([b"a", b"b"])
    r2 = merkle_root([b"a", b"c"])
    assert r1 != r2


def test_merkle_inclusion_proof():
    data = [b"a", b"b", b"c", b"d"]
    root = merkle_root(data)
    for i in range(len(data)):
        path = inclusion_path(data, i)
        assert verify_inclusion(data[i], i, path, root), f"Inclusion failed for index {i}"


def test_merkle_tamper_detection():
    data = [b"a", b"b", b"c", b"d"]
    root = merkle_root(data)
    path = inclusion_path(data, 0)
    # Tamper with leaf data
    assert not verify_inclusion(b"X", 0, path, root)


def test_merkle_single_leaf():
    data = [b"only"]
    root = merkle_root(data)
    path = inclusion_path(data, 0)
    assert verify_inclusion(data[0], 0, path, root)


# --- Hash Chain Tests ---

def test_chain_append_and_verify():
    ledger = EventLedger()
    ledger.append("case_1", "CREATED", "system", {"prompt": "test"})
    ledger.append("case_1", "EXTRACTED", "nutrient", {"fields": 5})
    ledger.append("case_1", "REVIEWED", "human", {"decision": "APPROVE"})
    ok, reason = ledger.verify_chain()
    assert ok, reason
    assert len(ledger.get_events()) == 3


def test_chain_detects_tamper():
    ledger = EventLedger()
    ledger.append("case_1", "CREATED", "system", {"prompt": "test"})
    ledger.append("case_1", "EXTRACTED", "nutrient", {"fields": 5})
    ledger.append("case_1", "REVIEWED", "human", {"decision": "APPROVE"})

    # Tamper with event payload
    ledger._events[1].payload["fields"] = 999
    # Recompute hash to match tampered payload (attacker covering tracks)
    ledger._events[1].compute_hashes()

    ok, reason = ledger.verify_chain()
    assert not ok
    assert "chain break" in reason.lower() or "mismatch" in reason.lower()


def test_chain_detects_hash_tamper():
    ledger = EventLedger()
    ledger.append("case_1", "CREATED", "system", {"prompt": "test"})
    ledger.append("case_1", "EXTRACTED", "nutrient", {"fields": 5})

    # Tamper with event_hash directly (without recomputing)
    ledger._events[1].event_hash = "tampered_hash_value"

    ok, reason = ledger.verify_chain()
    assert not ok


def test_chain_filters_by_case():
    ledger = EventLedger()
    ledger.append("case_1", "CREATED", "system", {})
    ledger.append("case_2", "CREATED", "system", {})
    ledger.append("case_1", "EXTRACTED", "nutrient", {})

    case1_events = ledger.get_events("case_1")
    case2_events = ledger.get_events("case_2")
    assert len(case1_events) == 2
    assert len(case2_events) == 1


def test_chain_prev_hash_links():
    ledger = EventLedger()
    e0 = ledger.append("c", "A", "sys", {})
    e1 = ledger.append("c", "B", "sys", {})
    e2 = ledger.append("c", "C", "sys", {})

    assert e0.prev_event_hash == GENESIS_HASH
    assert e1.prev_event_hash == e0.event_hash
    assert e2.prev_event_hash == e1.event_hash


# --- Merkle Epoch Tests ---

def test_seal_epoch():
    ledger = EventLedger()
    for i in range(10):
        ledger.append("c", f"event_{i}", "sys", {"i": i})

    epoch = ledger.seal_epoch()
    assert epoch.event_count == 10
    assert len(epoch.root) == 64


def test_merkle_proof_after_seal():
    ledger = EventLedger()
    for i in range(8):
        ledger.append("c", f"event_{i}", "sys", {"i": i})

    ledger.seal_epoch()
    proof = ledger.proof_for_seq(3)
    assert proof is not None
    assert proof["verified"]


# --- Artifact Store Tests ---

def test_artifact_store_put_get_verify():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(tmpdir)
        data = b"hello world content"
        ref = store.put(data, media_type="text/plain")

        assert store.verify(ref["sha256"])
        assert store.get(ref["sha256"]) == data
        assert store.exists(ref["sha256"])


def test_artifact_store_same_bytes_same_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(tmpdir)
        ref1 = store.put(b"identical content")
        ref2 = store.put(b"identical content")
        assert ref1["sha256"] == ref2["sha256"]


def test_artifact_store_different_bytes_different_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(tmpdir)
        ref1 = store.put(b"content A")
        ref2 = store.put(b"content B")
        assert ref1["sha256"] != ref2["sha256"]


def test_artifact_store_detects_corruption():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(tmpdir)
        ref = store.put(b"original content")

        # Corrupt the blob on disk
        blob_path = store._key(ref["sha256"])
        blob_path.write_bytes(b"corrupted content")

        assert not store.verify(ref["sha256"])


# --- Signing Tests ---

def test_content_hash_deterministic():
    d = {"a": 1, "b": "hello"}
    h1 = content_hash(d)
    h2 = content_hash(d)
    assert h1 == h2
    assert len(h1) == 64


def test_signed_attestation_hash_only():
    att = SignedAttestation(
        attestation_type="approval",
        case_id="case_1",
        payload={"decision": "APPROVE"},
    )
    att.compute_hash()
    assert len(att.content_hash) == 64
    ok, reason = att.verify()
    assert ok  # unsigned is OK


def test_signed_attestation_with_key():
    private_pem, public_pem = generate_keypair()
    att = SignedAttestation(
        attestation_type="approval",
        case_id="case_1",
        payload={"decision": "APPROVE"},
    )
    att.compute_hash()
    att.sign(private_pem)

    ok, reason = att.verify()
    assert ok, reason
    assert att.signature != ""
    assert att.public_key != ""


def test_signed_attestation_detects_tamper():
    private_pem, _ = generate_keypair()
    att = SignedAttestation(
        attestation_type="approval",
        case_id="case_1",
        payload={"decision": "APPROVE"},
    )
    att.compute_hash()
    att.sign(private_pem)

    # Tamper with payload
    att.payload["decision"] = "REJECT"
    ok, reason = att.verify()
    assert not ok


# --- Certificate Tests ---

def test_certificate_self_hash():
    cert = Certificate(
        cert_type="approval",
        case_id="case_1",
        subject="Approved procurement for $42,500",
        evidence=[{"sha256": "abc123"}],
    )
    cert.compute_hash()
    assert cert.certificate_hash != ""
    assert len(cert.certificate_hash) == 64


def test_certificate_integrity():
    cert = Certificate(
        cert_type="approval",
        case_id="case_1",
        subject="Approved procurement",
    )
    cert.compute_hash()
    ok, reason = cert.verify_integrity()
    assert ok, reason


def test_certificate_detects_tamper():
    cert = Certificate(
        cert_type="approval",
        case_id="case_1",
        subject="Approved procurement",
    )
    cert.compute_hash()

    # Tamper with subject
    cert.subject = "TAMPERED"
    ok, reason = cert.verify_integrity()
    assert not ok
    assert "tampered" in reason.lower()


def test_certificate_roundtrip():
    cert = Certificate(
        cert_type="generation",
        case_id="case_1",
        subject="Generated approval memo",
        metadata={"template": "v1"},
    )
    cert.compute_hash()

    d = cert.to_dict()
    cert2 = Certificate.from_dict(d)
    ok, _ = cert2.verify_integrity()
    assert ok


# --- Integration: Full Audit Trail ---

def test_full_audit_trail():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Event ledger
        ledger = EventLedger()
        e0 = ledger.append("case_1", "CREATED", "system", {"prompt": "procurement"})
        e1 = ledger.append("case_1", "EXTRACTED", "nutrient", {"fields": 12, "confidence": 0.95})
        e2 = ledger.append("case_1", "VERIFIED", "factminer", {"verdict": "SUPPORTED"})
        e3 = ledger.append("case_1", "REVIEWED", "human", {"decision": "CONDITIONAL_ACCEPT"})
        e4 = ledger.append("case_1", "GENERATED", "doctavian", {"template": "approval_memo"})
        e5 = ledger.append("case_1", "SIGNED", "foxit_esign", {"signer": "cfo@co.com"})

        ok, reason = ledger.verify_chain()
        assert ok, reason

        # 2. Seal and prove
        epoch = ledger.seal_epoch()
        proof = ledger.proof_for_seq(3)
        assert proof["verified"]

        # 3. Content-addressed artifacts
        store = ArtifactStore(os.path.join(tmpdir, "artifacts"))
        pdf_ref = store.put(b"%PDF-1.4 fake PDF content", media_type="application/pdf")
        assert store.verify(pdf_ref["sha256"])

        # 4. Self-hashing certificate
        cert = Certificate(
            cert_type="approval",
            case_id="case_1",
            subject="Procurement approved for $42,500",
            evidence=[pdf_ref],
            metadata={"record_hash": "sha256:abc123"},
        )
        cert.compute_hash()
        ok, _ = cert.verify_integrity()
        assert ok

        # 5. Signed attestation
        private_pem, _ = generate_keypair()
        att = SignedAttestation(
            attestation_type="resolution",
            case_id="case_1",
            payload={"decision": "CONDITIONAL_ACCEPT", "reason": "renew insurance"},
        )
        att.compute_hash()
        att.sign(private_pem)
        ok, _ = att.verify()
        assert ok

        # 6. Verify everything still holds
        ok, _ = ledger.verify_chain()
        assert ok
        assert store.verify(pdf_ref["sha256"])
        ok, _ = cert.verify_integrity()
        assert ok
        ok, _ = att.verify()
        assert ok

        print("✓ Full audit trail: chain + merkle + artifacts + certificate + signature")


if __name__ == "__main__":
    tests = [
        test_merkle_root_deterministic,
        test_merkle_root_different_data,
        test_merkle_inclusion_proof,
        test_merkle_tamper_detection,
        test_merkle_single_leaf,
        test_chain_append_and_verify,
        test_chain_detects_tamper,
        test_chain_detects_hash_tamper,
        test_chain_filters_by_case,
        test_chain_prev_hash_links,
        test_seal_epoch,
        test_merkle_proof_after_seal,
        test_artifact_store_put_get_verify,
        test_artifact_store_same_bytes_same_key,
        test_artifact_store_different_bytes_different_key,
        test_artifact_store_detects_corruption,
        test_content_hash_deterministic,
        test_signed_attestation_hash_only,
        test_signed_attestation_with_key,
        test_signed_attestation_detects_tamper,
        test_certificate_self_hash,
        test_certificate_integrity,
        test_certificate_detects_tamper,
        test_certificate_roundtrip,
        test_full_audit_trail,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__} — {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"  {passed} passed, {failed} failed out of {len(tests)}")
    print(f"{'='*50}")
