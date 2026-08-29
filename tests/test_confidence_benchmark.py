"""Test the confidence scoring benchmark."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.benchmark.confidence_benchmark import (
    Candidate,
    QualityGates,
    evaluate_candidate,
    generate_receipt,
)


# ============================================================
# Simulated test documents (what Nutrient would extract)
# ============================================================

TEST_DOCS = [
    # Invoice — high confidence, correct
    {
        "id": "inv_001",
        "type": "invoice",
        "ground_truth": {"invoice_number": "INV-2026-7891", "total_amount": 315700, "vendor_name": "GlobalTech Manufacturing Co."},
        "simulated_extract": {"invoice_number": "INV-2026-7891", "total_amount": 315700, "vendor_name": "GlobalTech Manufacturing Co."},
        "simulated_metadata": {"invoice_number": {"confidence": 0.97}, "total_amount": {"confidence": 0.98}, "vendor_name": {"confidence": 0.95}},
    },
    # Invoice — high confidence, wrong vendor name
    {
        "id": "inv_002",
        "type": "invoice",
        "ground_truth": {"invoice_number": "INV-2026-7892", "total_amount": 45000, "vendor_name": "Acme Corp Ltd."},
        "simulated_extract": {"invoice_number": "INV-2026-7892", "total_amount": 45000, "vendor_name": "Acme Corp"},
        "simulated_metadata": {"invoice_number": {"confidence": 0.96}, "total_amount": {"confidence": 0.97}, "vendor_name": {"confidence": 0.72}},
    },
    # Receipt — low confidence on company
    {
        "id": "rcp_001",
        "type": "receipt",
        "ground_truth": {"company": "Walmart Supercenter", "date": "2026-08-20", "total": "67.42"},
        "simulated_extract": {"company": "Wal-Mart", "date": "2026-08-20", "total": "67.42"},
        "simulated_metadata": {"company": {"confidence": 0.55}, "date": {"confidence": 0.92}, "total": {"confidence": 0.88}},
    },
    # Receipt — correct
    {
        "id": "rcp_002",
        "type": "receipt",
        "ground_truth": {"company": "Target", "date": "2026-08-21", "total": "23.99"},
        "simulated_extract": {"company": "Target", "date": "2026-08-21", "total": "23.99"},
        "simulated_metadata": {"company": {"confidence": 0.94}, "date": {"confidence": 0.96}, "total": {"confidence": 0.95}},
    },
    # KYC — high confidence
    {
        "id": "kyc_001",
        "type": "kyc_id",
        "ground_truth": {"full_name": "Sarah Chen", "date_of_birth": "1990-03-15", "license_number": "D1234567"},
        "simulated_extract": {"full_name": "Sarah Chen", "date_of_birth": "1990-03-15", "license_number": "D1234567"},
        "simulated_metadata": {"full_name": {"confidence": 0.97}, "date_of_birth": {"confidence": 0.96}, "license_number": {"confidence": 0.95}},
    },
    # KYC — name mismatch
    {
        "id": "kyc_002",
        "type": "kyc_id",
        "ground_truth": {"full_name": "Robert Johnson", "date_of_birth": "1975-06-22", "license_number": "R4567890"},
        "simulated_extract": {"full_name": "Robert Johnsen", "date_of_birth": "1975-06-22", "license_number": "R4567890"},
        "simulated_metadata": {"full_name": {"confidence": 0.68}, "date_of_birth": {"confidence": 0.95}, "license_number": {"confidence": 0.93}},
    },
    # Trade — correct
    {
        "id": "trd_001",
        "type": "trade",
        "ground_truth": {"invoice_number": "INV-2026-7891", "shipper": "GlobalTech Manufacturing Co.", "total_value": 300000},
        "simulated_extract": {"invoice_number": "INV-2026-7891", "shipper": "GlobalTech Manufacturing Co.", "total_value": 300000},
        "simulated_metadata": {"invoice_number": {"confidence": 0.97}, "shipper": {"confidence": 0.95}, "total_value": {"confidence": 0.98}},
    },
    # Trade — wrong total
    {
        "id": "trd_002",
        "type": "trade",
        "ground_truth": {"invoice_number": "INV-2026-7893", "shipper": "Pacific Imports Ltd.", "total_value": 150000},
        "simulated_extract": {"invoice_number": "INV-2026-7893", "shipper": "Pacific Imports", "total_value": 148500},
        "simulated_metadata": {"invoice_number": {"confidence": 0.96}, "shipper": {"confidence": 0.70}, "total_value": {"confidence": 0.85}},
    },
    # Medical — PII extraction
    {
        "id": "med_001",
        "type": "medical",
        "ground_truth": {"patient_name": "Robert Johnson", "ssn": "123-45-6789", "phone": "(555) 234-5678"},
        "simulated_extract": {"patient_name": "Robert Johnson", "ssn": "123-45-6789", "phone": "(555) 234-5678"},
        "simulated_metadata": {"patient_name": {"confidence": 0.96}, "ssn": {"confidence": 0.94}, "phone": {"confidence": 0.93}},
    },
    # Medical — low confidence SSN
    {
        "id": "med_002",
        "type": "medical",
        "ground_truth": {"patient_name": "Maria Garcia", "ssn": "987-65-4321", "phone": "(555) 876-5432"},
        "simulated_extract": {"patient_name": "Maria Garcia", "ssn": "987-65-432X", "phone": "(555) 876-5432"},
        "simulated_metadata": {"patient_name": {"confidence": 0.95}, "ssn": {"confidence": 0.45}, "phone": {"confidence": 0.91}},
    },
]


def test_benchmark_basic():
    """Test basic benchmark execution."""
    candidate = Candidate()
    gates = QualityGates()

    eval_result = evaluate_candidate(candidate, TEST_DOCS)
    metrics = eval_result["metrics"]

    print(f"\n{'='*60}")
    print(f"  BENCHMARK RESULTS — Default Candidate")
    print(f"{'='*60}")
    print(f"  Total docs: {metrics['total_docs']}")
    print(f"  Accuracy: {metrics['accuracy']:.1%}")
    print(f"  Auto-approve rate: {metrics['auto_approve_rate']:.1%}")
    print(f"  Auto-approve accuracy: {metrics['auto_approve_accuracy']:.1%}")
    print(f"  False positive rate: {metrics['false_positive_rate']:.1%}")
    print(f"  Cost/doc: ${metrics['cost_per_doc']:.4f}")
    print(f"  Latency p50: {metrics['latency_p50_ms']:.0f}ms")

    print(f"\n  Per-type breakdown:")
    for dt, data in sorted(metrics["per_type"].items()):
        print(f"    {dt:<12} acc={data['accuracy']:.1%}  auto={data['auto_approve_rate']:.1%}")

    gate_results = gates.check(metrics)
    print(f"\n  Quality gates:")
    for gate, gate_msg in gate_results.items():
        icon = "✓" if "PASS" in gate_msg else "✗"
        print(f"    [{icon}] {gate}: {gate_msg}")

    # Generate receipt
    receipt = generate_receipt(candidate, eval_result, gates)
    print(f"\n  RunReceipt: {receipt.run_id}")
    print(f"  Merkle root: {receipt.merkle_root[:32]}...")

    assert metrics["total_docs"] == 10
    assert 0 <= metrics["accuracy"] <= 1
    return metrics


def test_threshold_sensitivity():
    """Test how different thresholds affect results."""
    print(f"\n{'='*60}")
    print(f"  THRESHOLD SENSITIVITY ANALYSIS")
    print(f"{'='*60}")
    print(f"\n  {'Threshold':<20} {'Accuracy':>10} {'Auto-Approve':>14} {'FP Rate':>10} {'Cost':>8}")
    print(f"  {'-'*20} {'-'*10} {'-'*14} {'-'*10} {'-'*8}")

    for auto_thresh in [0.80, 0.85, 0.90, 0.92, 0.95, 0.98]:
        candidate = Candidate(auto_approve_threshold=auto_thresh)
        result = evaluate_candidate(candidate, TEST_DOCS)
        m = result["metrics"]
        print(
            f"  auto>={auto_thresh:.2f}      "
            f"{m['accuracy']:>9.1%} "
            f"{m['auto_approve_rate']:>13.1%} "
            f"{m['false_positive_rate']:>9.1%} "
            f"${m['cost_per_doc']:>6.4f}"
        )


def test_mutation_improves():
    """Test that mutating thresholds can find a better candidate."""
    # Start with conservative thresholds
    baseline = Candidate(auto_approve_threshold=0.98)
    baseline_result = evaluate_candidate(baseline, TEST_DOCS)
    baseline_metrics = baseline_result["metrics"]

    # Try more aggressive thresholds
    aggressive = Candidate(auto_approve_threshold=0.85)
    aggressive_result = evaluate_candidate(aggressive, TEST_DOCS)
    aggressive_metrics = aggressive_result["metrics"]

    print(f"\n{'='*60}")
    print(f"  MUTATION COMPARISON")
    print(f"{'='*60}")
    print(f"\n  {'Config':<25} {'Accuracy':>10} {'Auto-Approve':>14} {'FP Rate':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*14} {'-'*10}")
    print(f"  {'Conservative (0.98)':<25} {baseline_metrics['accuracy']:>9.1%} {baseline_metrics['auto_approve_rate']:>13.1%} {baseline_metrics['false_positive_rate']:>9.1%}")
    print(f"  {'Aggressive (0.85)':<25} {aggressive_metrics['accuracy']:>9.1%} {aggressive_metrics['auto_approve_rate']:>13.1%} {aggressive_metrics['false_positive_rate']:>9.1%}")

    # The aggressive config should have higher auto-approve rate
    assert aggressive_metrics["auto_approve_rate"] >= baseline_metrics["auto_approve_rate"]
    print(f"\n  ✓ Aggressive config auto-approves more documents")


def test_per_type_optimization():
    """Test that different document types need different thresholds."""
    print(f"\n{'='*60}")
    print(f"  PER-TYPE OPTIMIZATION")
    print(f"{'='*60}")

    # Test: receipts need lower threshold (lower confidence extraction)
    receipt_docs = [d for d in TEST_DOCS if d["type"] == "receipt"]

    for thresh in [0.50, 0.60, 0.70, 0.80, 0.90]:
        candidate = Candidate(auto_approve_threshold=thresh)
        result = evaluate_candidate(candidate, receipt_docs)
        m = result["metrics"]
        print(f"  Receipt threshold={thresh:.2f}: accuracy={m['accuracy']:.1%} auto_approve={m['auto_approve_rate']:.1%}")


if __name__ == "__main__":
    test_benchmark_basic()
    test_threshold_sensitivity()
    test_mutation_improves()
    test_per_type_optimization()
    print(f"\n{'='*60}")
    print(f"  ALL TESTS PASSED")
    print(f"{'='*60}")
