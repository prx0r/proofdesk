"""Document verification world — wraps ProofDesk's reconciliation engine
into a deterministic, benchmarkable world.

Each episode:
1. Load a SyntheticBundle (or real document)
2. Run extraction (simulated or real Nutrient API)
3. Run domain-specific checks
4. Compare results against ground truth
5. Return metrics: accuracy, precision, recall, F1, cost, latency
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .ids import content_id, now_ns
from .synthetic import SyntheticBundle, SyntheticField
from ..engine.reconciliation import build_fact_index, run_checks
from ..models.domain import ExtractedFact, AssertionResult


@dataclass
class EpisodeResult:
    bundle_id: str
    domain: str
    # Per-check results
    checks_run: int
    checks_correct: int
    checks_incorrect: int
    checks_unknown: int
    # Ground truth comparison
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    # Metrics
    accuracy: float
    precision: float
    recall: float
    f1: float
    # Defect detection
    defects_total: int
    defects_detected: int
    defect_detection_rate: float
    # Cost/latency
    extraction_cost: float
    check_cost: float
    total_cost: float
    extraction_ms: float
    check_ms: float
    total_ms: float
    # Content hash
    receipt_hash: str


def _bundle_to_facts(bundle: SyntheticBundle) -> list[ExtractedFact]:
    """Convert synthetic bundle fields to ExtractedFact objects."""
    facts = []
    for f in bundle.fields:
        facts.append(ExtractedFact(
            case_id=bundle.bundle_id,
            doc_id=f.source_doc,
            field_name=f.name,
            value_raw=f.raw_value,
            value_normalized=str(f.value),
            source_page=1,
            confidence=f.confidence,
            extractor="synthetic",
            content_hash=content_id("fact", {"field": f.name, "value": f.value}),
        ))
    return facts


def run_episode(bundle: SyntheticBundle) -> EpisodeResult:
    """Run one verification episode and return results."""
    t0 = now_ns()

    # Convert bundle to facts
    facts = _bundle_to_facts(bundle)
    t_extract = now_ns()

    # Run checks
    assertions = run_checks(facts, domain=bundle.domain)
    t_check = now_ns()

    # Compare against ground truth
    gt = bundle.ground_truth
    tp = fp = tn = fn = 0
    correct = incorrect = unknown = 0

    for a in assertions:
        # Find matching ground truth by mapping assertion predicates to GT keys
        gt_key = None
        pred_lower = a.predicate.lower().replace(" ", "_")
        rule_version = a.rule_version or ""

        # Map by rule version first (most reliable)
        rule_to_gt = {
            "procurement-arith-v1": "quote_arithmetic",
            "procurement-entity-v1": "entity_match",
            "procurement-coverage-v1": "coverage_date",
            "procurement-spend-v1": "spend_match",
            "procurement-security-v1": "encryption",
            "insurance-amount-v1": "amount_match",
            "insurance-active-v1": "policy_active",
            "insurance-deductible-v1": "deductible",
            "insurance-sublimit-v1": "sublimit",
            "insurance-timeliness-v1": "timeliness",
            "trade-qty-v1": "qty_match",
            "trade-origin-v1": "origin_match",
            "trade-party-v1": "party_match",
            "trade-incoterm-v1": "incoterm",
            "receipt-company-v1": "company_present",
            "receipt-date-v1": "date_valid",
            "receipt-total-v1": "total_numeric",
            "receipt-address-v1": "address_present",
        }
        # CUAD clause checks map by prefix
        if rule_version and rule_version.startswith("cuad_clause_"):
            gt_key = rule_version
        else:
            gt_key = rule_to_gt.get(rule_version)

        # Fallback: fuzzy predicate matching
        if gt_key is None:
            for key in gt:
                key_words = key.replace("_", " ").lower().split()
                pred_words = pred_lower.split()
                if sum(1 for w in key_words if w in pred_words) >= len(key_words) // 2:
                    gt_key = key
                    break

        if gt_key is None or gt_key not in gt:
            unknown += 1
            continue

        expected = gt[gt_key]["expected"]
        actual_pass = a.result == AssertionResult.PASS
        actual_fail = a.result == AssertionResult.FAIL

        if expected and actual_pass:
            tp += 1
            correct += 1
        elif not expected and actual_fail:
            tn += 1
            correct += 1
        elif expected and actual_fail:
            fn += 1
            incorrect += 1
        elif not expected and actual_pass:
            fp += 1
            incorrect += 1
        else:
            unknown += 1

    total = tp + tn + fp + fn
    accuracy = correct / max(correct + incorrect, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    # Defect detection — map defect types to expected failing rules
    defects_total = bundle.defect_count
    defect_to_rule = {
        "wrong_total": "procurement-arith-v1",
        "insurance_gap": "procurement-coverage-v1",
        "amount_mismatch": "insurance-amount-v1",
        "incoterm_mismatch": "trade-incoterm-v1",
    }
    defects_detected = 0
    for dt in bundle.defect_types:
        expected_rule = defect_to_rule.get(dt, "")
        if any(a.rule_version == expected_rule and a.result == AssertionResult.FAIL
               for a in assertions):
            defects_detected += 1
    defect_rate = defects_detected / max(defects_total, 1)

    # Cost/latency
    extraction_ms = (t_extract - t0) / 1e6
    check_ms = (t_check - t_extract) / 1e6
    total_ms = (t_check - t0) / 1e6

    # Receipt hash
    receipt_data = {
        "bundle_id": bundle.bundle_id,
        "domain": bundle.domain,
        "checks_run": len(assertions),
        "correct": correct,
        "incorrect": incorrect,
    }
    receipt_hash = content_id("receipt", receipt_data)

    return EpisodeResult(
        bundle_id=bundle.bundle_id,
        domain=bundle.domain,
        checks_run=len(assertions),
        checks_correct=correct,
        checks_incorrect=incorrect,
        checks_unknown=unknown,
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        defects_total=defects_total,
        defects_detected=defects_detected,
        defect_detection_rate=defect_rate,
        extraction_cost=0.0,
        check_cost=0.0,
        total_cost=0.0,
        extraction_ms=extraction_ms,
        check_ms=check_ms,
        total_ms=total_ms,
        receipt_hash=receipt_hash,
    )


def run_benchmark(bundles: list[SyntheticBundle]) -> dict:
    """Run benchmark across a list of bundles. Returns aggregate metrics."""
    results = [run_episode(b) for b in bundles]

    n = len(results)
    if n == 0:
        return {"error": "no bundles"}

    # Aggregate
    total_tp = sum(r.true_positives for r in results)
    total_fp = sum(r.false_positives for r in results)
    total_tn = sum(r.true_negatives for r in results)
    total_fn = sum(r.false_negatives for r in results)
    total_correct = sum(r.checks_correct for r in results)
    total_incorrect = sum(r.checks_incorrect for r in results)
    total_checks = sum(r.checks_run for r in results)
    total_defects = sum(r.defects_total for r in results)
    total_defects_detected = sum(r.defects_detected for r in results)

    accuracy = total_correct / max(total_correct + total_incorrect, 1)
    precision = total_tp / max(total_tp + total_fp, 1)
    recall = total_tp / max(total_tp + total_fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    avg_latency_ms = sum(r.total_ms for r in results) / n

    return {
        "n_episodes": n,
        "domain": results[0].domain,
        "checks": {
            "total": total_checks,
            "correct": total_correct,
            "incorrect": total_incorrect,
            "unknown": sum(r.checks_unknown for r in results),
        },
        "confusion": {
            "tp": total_tp,
            "fp": total_fp,
            "tn": total_tn,
            "fn": total_fn,
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "defects": {
            "total": total_defects,
            "detected": total_defects_detected,
            "detection_rate": round(total_defects_detected / max(total_defects, 1), 4),
        },
        "performance": {
            "avg_latency_ms": round(avg_latency_ms, 2),
            "total_ms": round(sum(r.total_ms for r in results), 2),
        },
        "receipt_hashes": [r.receipt_hash for r in results],
    }
