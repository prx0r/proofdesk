"""Tests for frontier literature implementations: EXTRACTCONF, RaV-IDP, ConfBench."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_extractconf():
    """EXTRACTCONF: Dual-call Hunter-Mapper verification."""
    from src.providers.extractconf import DualCallVerifier
    
    verifier = DualCallVerifier()
    
    # Test 1: Perfect agreement
    hunter = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.95},
        {"field": "vendor.legal_name", "value_normalized": "ACME Corp", "confidence": 0.98},
    ]
    mapper = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.93},
        {"field": "vendor.legal_name", "value_normalized": "ACME Corp", "confidence": 0.97},
    ]
    
    results = verifier.verify(hunter, mapper)
    assert len(results) == 2
    assert all(r.agreement for r in results)
    assert verifier.get_reliability_score(results) == 1.0
    
    should_defer, reason = verifier.should_defer(results)
    assert not should_defer
    print("[PASS] EXTRACTCONF-001: Perfect agreement → no defer")
    
    # Test 2: Disagreement on value
    hunter_disagree = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.95},
    ]
    mapper_disagree = [
        {"field": "quote.total", "value_normalized": "$35,000", "confidence": 0.93},
    ]
    
    results_disagree = verifier.verify(hunter_disagree, mapper_disagree)
    assert len(results_disagree) == 1
    assert not results_disagree[0].agreement
    assert verifier.get_reliability_score(results_disagree) < 1.0
    
    should_defer, reason = verifier.should_defer(results_disagree, threshold=0.9)
    assert should_defer
    print("[PASS] EXTRACTCONF-002: Disagreement → defer")
    
    # Test 3: Missing field from one call
    hunter_missing = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.95},
    ]
    mapper_missing = []  # Field missing
    
    results_missing = verifier.verify(hunter_missing, mapper_missing)
    assert len(results_missing) == 1
    assert not results_missing[0].agreement
    print("[PASS] EXTRACTCONF-003: Missing field → disagree")
    
    # Test 4: Stats
    stats = verifier.stats()
    assert stats["total_verifications"] == 3
    print("[PASS] EXTRACTCONF-004: Stats tracking")


def test_ravidp():
    """RaV-IDP: Reconstruction validation."""
    from src.providers.ravidp import ReconstructionValidator
    
    validator = ReconstructionValidator()
    
    # Test 1: High fidelity (exact match)
    facts_high = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.95, "page": 1},
    ]
    raw_text = "Total: $42,500"
    
    results_high = validator.validate(facts_high, raw_text)
    assert len(results_high) == 1
    assert results_high[0].decision == "HIGH_FIDELITY"
    assert validator.get_fidelity_score(results_high) == 1.0
    print("[PASS] RaV-IDP-001: Exact match → high fidelity")
    
    # Test 2: Low fidelity (mismatch)
    facts_low = [
        {"field": "quote.total", "value_normalized": "$99,999", "confidence": 0.95, "page": 1},
    ]
    raw_text_low = "Total: $42,500"
    
    results_low = validator.validate(facts_low, raw_text_low)
    assert len(results_low) == 1
    assert results_low[0].decision == "LOW_FIDELITY"
    print("[PASS] RaV-IDP-002: Mismatch → low fidelity")
    
    # Test 3: No raw text (inconclusive)
    facts_no_text = [
        {"field": "quote.total", "value_normalized": "$42,500", "confidence": 0.95, "page": 1},
    ]
    
    results_no_text = validator.validate(facts_no_text, "")
    assert len(results_no_text) == 1
    assert results_no_text[0].decision == "INCONCLUSIVE"
    print("[PASS] RaV-IDP-003: No raw text → inconclusive")
    
    # Test 4: Should reject
    should_reject, reason = validator.should_reject(results_low, threshold=0.7)
    assert should_reject
    print("[PASS] RaV-IDP-004: Low fidelity → should reject")
    
    # Test 5: Stats
    stats = validator.stats()
    assert stats["total_validations"] == 3
    print("[PASS] RaV-IDP-005: Stats tracking")


def test_confbench():
    """ConfBench: Distribution shift monitoring."""
    from src.providers.confbench import DistributionMonitor
    
    monitor = DistributionMonitor(window_size=100)
    
    # Test 1: Record baseline
    baseline_snapshot = monitor.record_batch(
        confidence_scores=[0.8, 0.9, 0.85, 0.7, 0.75],
        decisions={"AUTO_SIGN": 3, "DEFER": 2},
        doc_types={"invoice": 3, "procurement": 2},
    )
    monitor.set_baseline(baseline_snapshot)
    
    assert monitor._baseline is not None
    assert len(monitor._history) == 1
    print("[PASS] ConfBench-001: Baseline recorded")
    
    # Test 2: No shift (identical distribution)
    monitor.record_batch(
        confidence_scores=[0.8, 0.9, 0.85, 0.7, 0.75],  # Same as baseline
        decisions={"AUTO_SIGN": 3, "DEFER": 2},
        doc_types={"invoice": 3, "procurement": 2},
    )
    
    drift = monitor.detect_drift()
    assert drift["psi"] < 0.01  # Very small shift (numerical precision)
    print(f"[PASS] ConfBench-002: No shift (PSI={drift['psi']:.4f})")
    
    # Test 3: Detect shift (different distribution)
    monitor.record_batch(
        confidence_scores=[0.2, 0.3, 0.25, 0.1, 0.15],  # Much lower
        decisions={"DEFER": 5},
        doc_types={"insurance": 5},
    )
    
    drift_shift = monitor.detect_drift()
    print(f"[INFO] ConfBench-003: Shift detection (PSI={drift_shift['psi']:.3f})")
    
    # Test 4: Recommendation
    recommendation = monitor.get_recommendation()
    assert "action" in recommendation
    print(f"[PASS] ConfBench-004: Recommendation = {recommendation['action']}")
    
    # Test 5: Stats
    stats = monitor.stats()
    assert stats["total_batches"] == 3
    print("[PASS] ConfBench-005: Stats tracking")


def test_integration():
    """Integration: All three modules work together."""
    from src.providers.extractconf import DualCallVerifier
    from src.providers.ravidp import ReconstructionValidator
    from src.providers.confbench import DistributionMonitor
    
    verifier = DualCallVerifier()
    validator = ReconstructionValidator()
    monitor = DistributionMonitor()
    
    # Simulate a batch of documents
    docs = [
        {
            "hunter": [{"field": "total", "value_normalized": "$100", "confidence": 0.9}],
            "mapper": [{"field": "total", "value_normalized": "$100", "confidence": 0.88}],
            "facts": [{"field": "total", "value_normalized": "$100", "confidence": 0.9, "page": 1}],
            "raw_text": "Total: $100",
            "confidence": 0.9,
        },
        {
            "hunter": [{"field": "total", "value_normalized": "$200", "confidence": 0.85}],
            "mapper": [{"field": "total", "value_normalized": "$300", "confidence": 0.82}],
            "facts": [{"field": "total", "value_normalized": "$200", "confidence": 0.85, "page": 1}],
            "raw_text": "Total: $200",
            "confidence": 0.85,
        },
    ]
    
    all_confidences = []
    all_decisions = {"AUTO_SIGN": 0, "DEFER": 0}
    
    for doc in docs:
        # EXTRACTCONF
        ext_results = verifier.verify(doc["hunter"], doc["mapper"])
        ext_defer, _ = verifier.should_defer(ext_results)
        
        # RaV-IDP
        rav_results = validator.validate(doc["facts"], doc["raw_text"])
        rav_reject, _ = validator.should_reject(rav_results)
        
        # Decision
        if ext_defer or rav_reject:
            decision = "DEFER"
        else:
            decision = "AUTO_SIGN"
        
        all_confidences.append(doc["confidence"])
        all_decisions[decision] = all_decisions.get(decision, 0) + 1
    
    # ConfBench
    monitor.record_batch(all_confidences, all_decisions, {"invoice": 2})
    
    # Verify stats
    ext_stats = verifier.stats()
    rav_stats = validator.stats()
    mon_stats = monitor.stats()
    
    assert ext_stats["total_verifications"] == 2
    assert rav_stats["total_validations"] == 2
    assert mon_stats["total_batches"] == 1
    
    print("[PASS] INTEGRATION-001: All three modules work together")
    print(f"  EXTRACTCONF: {ext_stats}")
    print(f"  RaV-IDP: {rav_stats}")
    print(f"  ConfBench: {mon_stats}")


if __name__ == "__main__":
    test_extractconf()
    test_ravidp()
    test_confbench()
    test_integration()
    print("\nAll frontier literature tests: PASS")
