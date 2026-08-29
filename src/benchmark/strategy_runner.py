"""Strategy runner — evaluates multiple HarnessSpecs against the same
frozen benchmark data. Produces a leaderboard with quality gates.

The harness IS the strategy. This module answers:
"Which verification configuration gives the best accuracy-per-dollar?"
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .harness import HarnessSpec, STRATEGIES, make_spec
from .synthetic import SyntheticBundle, generate_bundles
from .ids import content_id
from ..engine.reconciliation import build_fact_index, run_checks
from ..models.domain import ExtractedFact, AssertionResult


@dataclass
class StrategyResult:
    spec_name: str
    spec_id: str
    description: str
    # Quality metrics
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    # Defect detection
    defect_detection_rate: float
    defects_detected: int
    defects_total: int
    # Cost metrics
    checks_per_episode: float
    episodes_per_second: float
    avg_latency_ms: float
    # Quality gate
    passes_accuracy_gate: bool
    passes_fp_gate: bool
    passes_defect_gate: bool
    overall_pass: bool
    # Raw
    n_episodes: int
    n_correct: int
    n_incorrect: int
    tp: int
    fp: int
    tn: int
    fn: int


def _bundle_to_facts(bundle: SyntheticBundle) -> list[ExtractedFact]:
    """Convert synthetic bundle to ExtractedFact objects."""
    from .document_world import _bundle_to_facts as _conv
    return _conv(bundle)


def _apply_harness(spec: HarnessSpec, bundle: SyntheticBundle) -> tuple[list, list]:
    """Run a harness config against a bundle. Returns (assertions, ground_truth)."""
    t0 = time.time()

    # Convert bundle to facts
    facts = _bundle_to_facts(bundle)

    # Apply confidence filter
    if spec.confidence_threshold > 0:
        facts = [f for f in facts if f.confidence >= spec.confidence_threshold]

    # Apply entity normalization
    # (in real system this would change normalization strictness)

    # Run checks — filter by severity if needed
    all_assertions = run_checks(facts, domain=bundle.domain)

    if spec.check_severity_filter == "blocker":
        assertions = [a for a in all_assertions if a.severity.value == "BLOCKER"]
    elif spec.check_severity_filter == "warning+":
        assertions = [a for a in all_assertions
                      if a.severity.value in ("BLOCKER", "WARNING")]
    else:
        assertions = all_assertions

    # Filter by enabled checks
    if spec.checks_enabled != ("all",):
        assertions = [a for a in assertions
                      if any(kw in a.predicate for kw in spec.checks_enabled)]

    # Early stop on fail
    if spec.early_stop_on_fail:
        stopped_assertions = []
        for a in assertions:
            stopped_assertions.append(a)
            if a.result == AssertionResult.FAIL:
                break
        assertions = stopped_assertions

    return assertions, bundle.ground_truth


def evaluate_strategy(spec: HarnessSpec, bundles: list[SyntheticBundle]) -> StrategyResult:
    """Evaluate one strategy against a set of bundles."""
    tp = fp = tn = fn = 0
    correct = incorrect = 0
    total_checks = 0
    total_defects = 0
    defects_detected = 0
    t0 = time.time()

    for bundle in bundles:
        assertions, gt = _apply_harness(spec, bundle)
        total_checks += len(assertions)
        total_defects += bundle.defect_count

        # Map assertions to ground truth
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
        for a in assertions:
            if a.rule_version and a.rule_version.startswith("cuad-clause-"):
                rule_to_gt[a.rule_version] = a.rule_version

        for a in assertions:
            gt_key = rule_to_gt.get(a.rule_version)
            if gt_key is None or gt_key not in gt:
                continue

            expected = gt[gt_key]["expected"]
            actual_pass = a.result == AssertionResult.PASS

            if expected and actual_pass:
                tp += 1; correct += 1
            elif not expected and not actual_pass:
                tn += 1; correct += 1
            elif expected and not actual_pass:
                fn += 1; incorrect += 1
            elif not expected and actual_pass:
                fp += 1; incorrect += 1

        # Defect detection
        defect_to_rule = {
            "wrong_total": "procurement-arith-v1",
            "insurance_gap": "procurement-coverage-v1",
            "amount_mismatch": "insurance-amount-v1",
            "incoterm_mismatch": "trade-incoterm-v1",
        }
        for dt in bundle.defect_types:
            expected_rule = defect_to_rule.get(dt, "")
            if any(a.rule_version == expected_rule and a.result == AssertionResult.FAIL
                   for a in assertions):
                defects_detected += 1

    elapsed = time.time() - t0
    n = len(bundles)

    total = tp + tn + fp + fn
    accuracy = correct / max(correct + incorrect, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    fp_rate = fp / max(fp + tn, 1)
    defect_rate = defects_detected / max(total_defects, 1)

    # Quality gates
    passes_acc = accuracy >= spec.accuracy_floor
    passes_fp = fp_rate <= spec.false_positive_ceiling
    passes_defect = defect_rate >= spec.defect_detection_floor
    overall = passes_acc and passes_fp and passes_defect

    return StrategyResult(
        spec_name=spec.name,
        spec_id=spec.spec_id,
        description=STRATEGIES.get(spec.name, {}).get("description", ""),
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        false_positive_rate=round(fp_rate, 4),
        defect_detection_rate=round(defect_rate, 4),
        defects_detected=defects_detected,
        defects_total=total_defects,
        checks_per_episode=round(total_checks / max(n, 1), 1),
        episodes_per_second=round(n / max(elapsed, 0.001), 1),
        avg_latency_ms=round(elapsed * 1000 / max(n, 1), 2),
        passes_accuracy_gate=passes_acc,
        passes_fp_gate=passes_fp,
        passes_defect_gate=passes_defect,
        overall_pass=overall,
        n_episodes=n,
        n_correct=correct,
        n_incorrect=incorrect,
        tp=tp, fp=fp, tn=tn, fn=fn,
    )


def run_leaderboard(n_per_domain: int = 200, seed: int = 42,
                    strategies: list[str] | None = None) -> list[StrategyResult]:
    """Run all strategies against the same frozen data and produce a leaderboard."""
    target_strategies = strategies or list(STRATEGIES.keys())

    # Generate frozen data (same for all strategies)
    all_bundles = []
    for domain in ["procurement", "insurance", "trade"]:
        all_bundles.extend(generate_bundles(domain, n_per_domain, 0.3, seed))

    results = []
    for name in target_strategies:
        spec = make_spec(name)
        result = evaluate_strategy(spec, all_bundles)
        results.append(result)

    # Sort: passing strategies first, then by accuracy, then by cost
    results.sort(key=lambda r: (
        not r.overall_pass,
        not r.passes_accuracy_gate,
        -r.accuracy,
        r.false_positive_rate,
    ))

    return results


def print_leaderboard(results: list[StrategyResult]):
    """Print a formatted leaderboard."""
    print(f"\n{'='*90}")
    print(f"  STRATEGY LEADERBOARD")
    print(f"  {len(results)} strategies × {results[0].n_episodes} episodes each")
    print(f"{'='*90}")
    print(f"\n  {'Strategy':<18} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} "
          f"{'FP%':>6} {'Defects':>8} {'Checks':>7} {'ms/ep':>7} {'Gate':>5}")
    print(f"  {'─'*18} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*6} {'─'*8} {'─'*7} {'─'*7} {'─'*5}")

    for r in results:
        gate = "PASS" if r.overall_pass else "FAIL"
        print(f"  {r.spec_name:<18} {r.accuracy:>5.1%} {r.precision:>5.1%} "
              f"{r.recall:>5.1%} {r.f1:>5.1%} {r.false_positive_rate:>5.1%} "
              f"{r.defect_detection_rate:>7.1%} {r.checks_per_episode:>7.1f} "
              f"{r.avg_latency_ms:>7.1f} {gate:>5}")

    # Winner
    passing = [r for r in results if r.overall_pass]
    if passing:
        w = passing[0]
        print(f"\n  WINNER: {w.spec_name}")
        print(f"  {w.description}")
        print(f"  Accuracy: {w.accuracy:.1%} | F1: {w.f1:.1%} | "
              f"Defects: {w.defect_detection_rate:.1%} | {w.avg_latency_ms:.1f}ms/episode")
    else:
        print(f"\n  NO STRATEGY PASSES ALL QUALITY GATES")
        print(f"  Consider relaxing accuracy_floor or defect_detection_floor")

    print(f"{'='*90}\n")
