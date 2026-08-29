"""Strategy evolution — mutate harness configs, re-benchmark, select.

The loop:
1. Start with seed population (8 named strategies)
2. Evaluate each on frozen data
3. Quality gate: accuracy >= floor, FP <= ceiling, defect_rate >= floor
4. Among passing strategies: prefer lower cost, then lower latency
5. Mutate top performers to create new candidates
6. Re-evaluate, repeat

This is the Cogym pattern: gates dominate objectives.
"""

from __future__ import annotations

import random
import time
from dataclasses import asdict

from .harness import HarnessSpec, STRATEGIES, make_spec, mutate_spec
from .strategy_runner import evaluate_strategy, StrategyResult
from .synthetic import generate_bundles
from .ids import content_id


def evolve(n_generations: int = 3, population_size: int = 8,
           n_per_domain: int = 100, seed: int = 42) -> list[dict]:
    """Run evolution for n generations. Returns history of all evaluated strategies."""
    rng = random.Random(seed)
    history = []

    # Generate frozen benchmark data
    bundles = []
    for domain in ["procurement", "insurance", "trade"]:
        bundles.extend(generate_bundles(domain, n_per_domain, 0.3, seed))

    # Seed population
    candidates = []
    for name in list(STRATEGIES.keys())[:population_size]:
        spec = make_spec(name)
        result = evaluate_strategy(spec, bundles)
        entry = {
            "generation": 0,
            "name": spec.name,
            "spec": spec.to_dict(),
            "accuracy": result.accuracy,
            "f1": result.f1,
            "defect_detection_rate": result.defect_detection_rate,
            "false_positive_rate": result.false_positive_rate,
            "checks_per_episode": result.checks_per_episode,
            "avg_latency_ms": result.avg_latency_ms,
            "overall_pass": result.overall_pass,
            "parent": None,
        }
        history.append(entry)
        candidates.append((spec, result, entry))

    # Evolution loop
    for gen in range(1, n_generations + 1):
        # Select top performers (quality gate + lexicographic)
        passing = [(s, r, e) for s, r, e in candidates if e["overall_pass"]]
        if not passing:
            # Relax: just take top 3 by accuracy
            passing = sorted(candidates, key=lambda x: -x[1].accuracy)[:3]

        # Sort passing by: accuracy desc, then cost asc, then latency asc
        passing.sort(key=lambda x: (
            -x[1].accuracy,
            x[1].false_positive_rate,
            x[1].avg_latency_ms,
        ))

        # Keep top half as parents
        parents = passing[:max(len(passing) // 2, 2)]

        # Mutate to create new candidates
        new_candidates = []
        for spec, result, entry in parents:
            for _ in range(max(1, population_size // len(parents))):
                mutant = mutate_spec(spec, rng)
                mutant_result = evaluate_strategy(mutant, bundles)
                mutant_entry = {
                    "generation": gen,
                    "name": mutant.name,
                    "spec": mutant.to_dict(),
                    "accuracy": mutant_result.accuracy,
                    "f1": mutant_result.f1,
                    "defect_detection_rate": mutant_result.defect_detection_rate,
                    "false_positive_rate": mutant_result.false_positive_rate,
                    "checks_per_episode": mutant_result.checks_per_episode,
                    "avg_latency_ms": mutant_result.avg_latency_ms,
                    "overall_pass": mutant_result.overall_pass,
                    "parent": entry["name"],
                }
                history.append(mutant_entry)
                new_candidates.append((mutant, mutant_result, mutant_entry))

        candidates = new_candidates

    # Final ranking
    history.sort(key=lambda e: (
        not e["overall_pass"],
        not e["accuracy"] >= 0.95,
        -e["accuracy"],
        e["false_positive_rate"],
        e["avg_latency_ms"],
    ))

    return history


def print_evolution_report(history: list[dict]):
    """Print evolution history."""
    print(f"\n{'='*90}")
    print(f"  STRATEGY EVOLUTION REPORT")
    print(f"  {len(history)} strategies evaluated across {history[-1]['generation'] + 1} generations")
    print(f"{'='*90}")

    print(f"\n  {'Gen':>3} {'Strategy':<25} {'Acc':>6} {'F1':>6} {'Defects':>8} "
          f"{'FP%':>6} {'Checks':>7} {'ms/ep':>7} {'Gate':>5} {'Parent':<20}")
    print(f"  {'─'*3} {'─'*25} {'─'*6} {'─'*6} {'─'*8} {'─'*6} {'─'*7} {'─'*7} {'─'*5} {'─'*20}")

    for e in history:
        gate = "PASS" if e["overall_pass"] else "FAIL"
        parent = e.get("parent") or ""
        print(f"  {e['generation']:>3} {e['name']:<25} {e['accuracy']:>5.1%} "
              f"{e['f1']:>5.1%} {e['defect_detection_rate']:>7.1%} "
              f"{e['false_positive_rate']:>5.1%} {e['checks_per_episode']:>7.1f} "
              f"{e['avg_latency_ms']:>7.1f} {gate:>5} {parent:<20}")

    # Best ever
    best = max(history, key=lambda e: (e["overall_pass"], e["accuracy"], -e["false_positive_rate"]))
    print(f"\n  BEST STRATEGY: {best['name']}")
    print(f"  Accuracy: {best['accuracy']:.1%} | F1: {best['f1']:.1%} | "
          f"Defects: {best['defect_detection_rate']:.1%} | FP: {best['false_positive_rate']:.1%}")
    print(f"  Checks/ep: {best['checks_per_episode']:.1f} | Latency: {best['avg_latency_ms']:.1f}ms")
    print(f"{'='*90}\n")
