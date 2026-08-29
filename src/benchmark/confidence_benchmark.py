"""ProofDesk confidence scoring benchmark — the core optimization.

Uses Nutrient DWS extraction + FactMiner verification to benchmark
confidence scoring across document types. cogymkernel optimizes thresholds.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.audit.chain import EventLedger
from src.audit.certificates import Certificate


# ============================================================
# Candidate configuration (what cogymkernel mutates)
# ============================================================

@dataclass
class Candidate:
    """A specific confidence threshold configuration."""
    auto_approve_threshold: float = 0.92
    human_review_threshold: float = 0.65
    method_per_type: dict = field(default_factory=lambda: {
        "invoice": "nutrient_extract",
        "contract": "nutrient_extract",
        "receipt": "ocr_then_extract",
        "kyc_id": "nutrient_extract",
        "trade": "nutrient_extract",
        "medical": "nutrient_extract",
    })
    verifier_per_type: dict = field(default_factory=lambda: {
        "invoice": "det_c017",
        "contract": "typed_dag",
        "receipt": "det_c017",
        "kyc_id": "det_c017",
        "trade": "det_c017",
        "medical": "nli_c026",
    })

    def classify(self, confidence: float) -> str:
        """Classify a fact by confidence into action bucket."""
        if confidence >= self.auto_approve_threshold:
            return "AUTO_APPROVE"
        elif confidence >= self.human_review_threshold:
            return "HUMAN_REVIEW"
        else:
            return "REJECT"


# ============================================================
# Quality gates (hard constraints)
# ============================================================

@dataclass
class QualityGates:
    min_accuracy: float = 0.80
    min_auto_approve_accuracy: float = 0.95
    max_false_positive_rate: float = 0.05
    max_cost_per_doc: float = 0.05
    max_latency_p50_ms: float = 10000

    def check(self, metrics: dict) -> dict[str, str]:
        results = {}
        results["min_accuracy"] = (
            f"PASS ({metrics['accuracy']:.3f} >= {self.min_accuracy})"
            if metrics["accuracy"] >= self.min_accuracy
            else f"FAIL ({metrics['accuracy']:.3f} < {self.min_accuracy})"
        )
        auto_acc = metrics.get("auto_approve_accuracy", 0)
        results["auto_approve_accuracy"] = (
            f"PASS ({auto_acc:.3f} >= {self.min_auto_approve_accuracy})"
            if auto_acc >= self.min_auto_approve_accuracy
            else f"FAIL ({auto_acc:.3f} < {self.min_auto_approve_accuracy})"
        )
        fpr = metrics.get("false_positive_rate", 0)
        results["false_positive_rate"] = (
            f"PASS ({fpr:.3f} <= {self.max_false_positive_rate})"
            if fpr <= self.max_false_positive_rate
            else f"FAIL ({fpr:.3f} > {self.max_false_positive_rate})"
        )
        cost = metrics.get("cost_per_doc", 0)
        results["cost_per_doc"] = (
            f"PASS (${cost:.4f} <= ${self.max_cost_per_doc})"
            if cost <= self.max_cost_per_doc
            else f"FAIL (${cost:.4f} > ${self.max_cost_per_doc})"
        )
        lat = metrics.get("latency_p50_ms", 0)
        results["latency_p50"] = (
            f"PASS ({lat:.0f}ms <= {self.max_latency_p50_ms:.0f}ms)"
            if lat <= self.max_latency_p50_ms
            else f"FAIL ({lat:.0f}ms > {self.max_latency_p50_ms:.0f}ms)"
        )
        all_pass = all("PASS" in v for v in results.values())
        results["overall"] = "ALL GATES PASS" if all_pass else "GATE FAILURE"
        return results


# ============================================================
# Evaluation result for a single document
# ============================================================

@dataclass
class DocResult:
    doc_id: str
    doc_type: str
    extracted: dict
    ground_truth: dict
    field_verdicts: dict  # field -> SUPPORTED/REFUTED/INSUFFICIENT
    confidences: dict     # field -> float
    action: str           # AUTO_APPROVE / HUMAN_REVIEW / REJECT
    correct: bool
    cost_credits: float
    latency_ms: float


# ============================================================
# Benchmark runner
# ============================================================

def evaluate_candidate(
    candidate: Candidate,
    test_docs: list[dict],
    nutrient_client=None,
) -> dict:
    """Run a candidate configuration against test documents.

    Returns metrics dict with accuracy, auto_approve_rate, etc.
    """
    results = []
    ledger = EventLedger()

    for doc in test_docs:
        start = time.time()

        # 1. Extract (simulate or real API)
        if nutrient_client:
            extracted, cost, metadata = nutrient_client.extract(
                doc["path"],
                doc.get("schema", {}),
            )
        else:
            # Simulated extraction with configurable confidence
            extracted = doc.get("simulated_extract", {})
            cost = 15.0
            metadata = doc.get("simulated_metadata", {})

        # 2. Get confidence per field
        confidences = {}
        for field_name, value in extracted.items():
            cite = metadata.get(field_name, {})
            confidences[field_name] = cite.get("confidence", 0.95)

        # 3. Verify each field (simulate or real FactMiner)
        field_verdicts = {}
        for field_name, expected in doc.get("ground_truth", {}).items():
            ext_val = extracted.get(field_name)
            if ext_val is None:
                field_verdicts[field_name] = "INSUFFICIENT"
            elif str(ext_val).strip().lower() == str(expected).strip().lower():
                field_verdicts[field_name] = "SUPPORTED"
            else:
                field_verdicts[field_name] = "REFUTED"

        # 4. Compute average confidence
        avg_confidence = (
            sum(confidences.values()) / len(confidences)
            if confidences else 0.0
        )

        # 5. Classify using candidate thresholds
        action = candidate.classify(avg_confidence)

        # 6. Check correctness
        supported = sum(1 for v in field_verdicts.values() if v == "SUPPORTED")
        total = len(field_verdicts) if field_verdicts else 1
        correct = (supported / total) >= 0.8  # 80% fields correct = correct doc

        latency = (time.time() - start) * 1000

        result = DocResult(
            doc_id=doc.get("id", "unknown"),
            doc_type=doc.get("type", "unknown"),
            extracted=extracted,
            ground_truth=doc.get("ground_truth", {}),
            field_verdicts=field_verdicts,
            confidences=confidences,
            action=action,
            correct=correct,
            cost_credits=cost,
            latency_ms=latency,
        )
        results.append(result)

        # Record in ledger
        ledger.append(
            case_id=doc.get("id", "unknown"),
            event_type="BENCHMARK_EVAL",
            actor="cogymkernel",
            payload={
                "doc_type": doc.get("type"),
                "action": action,
                "correct": correct,
                "avg_confidence": avg_confidence,
                "cost": cost,
            },
        )

    # Aggregate metrics
    total = len(results)
    if total == 0:
        return {"error": "no documents evaluated"}

    correct_count = sum(1 for r in results if r.correct)
    auto_approved = [r for r in results if r.action == "AUTO_APPROVE"]
    auto_correct = sum(1 for r in auto_approved if r.correct)
    total_credits = sum(r.cost_credits for r in results)
    latencies = [r.latency_ms for r in results]

    auto_approve_rate = len(auto_approved) / total
    auto_approve_accuracy = auto_correct / len(auto_approved) if auto_approved else 0
    false_positive_rate = (len(auto_approved) - auto_correct) / len(auto_approved) if auto_approved else 0
    latencies_sorted = sorted(latencies)
    latency_p50 = latencies_sorted[len(latencies_sorted) // 2] if latencies_sorted else 0

    metrics = {
        "total_docs": total,
        "accuracy": correct_count / total,
        "auto_approve_rate": auto_approve_rate,
        "auto_approve_accuracy": auto_approve_accuracy,
        "false_positive_rate": false_positive_rate,
        "cost_per_doc": total_credits / total,
        "total_credits": total_credits,
        "latency_p50_ms": latency_p50,
        "per_type": {},
    }

    # Per-type breakdown
    types = set(r.doc_type for r in results)
    for dt in types:
        type_results = [r for r in results if r.doc_type == dt]
        type_correct = sum(1 for r in type_results if r.correct)
        type_auto = [r for r in type_results if r.action == "AUTO_APPROVE"]
        type_auto_correct = sum(1 for r in type_auto if r.correct)
        metrics["per_type"][dt] = {
            "count": len(type_results),
            "accuracy": type_correct / len(type_results),
            "auto_approve_rate": len(type_auto) / len(type_results),
            "auto_approve_accuracy": type_auto_correct / len(type_auto) if type_auto else 0,
        }

    return {"metrics": metrics, "results": results, "ledger": ledger}


# ============================================================
# RunReceipt — content-addressed proof of benchmark
# ============================================================

@dataclass
class RunReceipt:
    run_id: str
    candidate: Candidate
    metrics: dict
    gate_results: dict
    timestamp: float = field(default_factory=time.time)
    merkle_root: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "candidate": {
                "auto_approve_threshold": self.candidate.auto_approve_threshold,
                "human_review_threshold": self.candidate.human_review_threshold,
            },
            "metrics": self.metrics,
            "gate_results": self.gate_results,
            "timestamp": self.timestamp,
            "merkle_root": self.merkle_root,
        }


def generate_receipt(
    candidate: Candidate,
    eval_result: dict,
    gates: QualityGates,
) -> RunReceipt:
    """Generate a content-addressed RunReceipt from benchmark results.

    eval_result can be either:
    - The raw metrics dict directly
    - A dict with "metrics" key containing the metrics dict
    """
    if isinstance(eval_result.get("metrics"), dict):
        metrics = eval_result["metrics"]
    else:
        metrics = eval_result
    gate_results = gates.check(metrics)

    # Content-address the receipt
    receipt_data = {
        "candidate": {
            "auto_approve": candidate.auto_approve_threshold,
            "human_review": candidate.human_review_threshold,
        },
        "metrics": {k: v for k, v in metrics.items() if k != "per_type"},
        "gate_results": {k: v for k, v in gate_results.items() if k != "overall"},
    }
    import hashlib
    receipt_hash = hashlib.sha256(
        json.dumps(receipt_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    return RunReceipt(
        run_id=f"blake3:{receipt_hash[:32]}",
        candidate=candidate,
        metrics=metrics,
        gate_results=gate_results,
        merkle_root=f"sha256:{receipt_hash}",
    )
