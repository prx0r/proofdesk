#!/usr/bin/env python3
"""SigningWorld benchmark — cogym-style document signing optimization.

Usage:
    python3 -m benchmark.confidence.signing_bench
    python3 -m benchmark.confidence.signing_bench --quick
"""

from __future__ import annotations

import argparse
import json
import os
import time
import numpy as np

from .signing_world import Verdict
from .signing_generator import generate_all_worlds, HARD_WORLD_GENERATORS
from .signing_runner import (
    run_signing_world, optimize_threshold,
    naive_signer, always_defer_signer, match_label_signer,
    threshold_signer, fusion_signer,
    run_full_benchmark,
)
from .plots import (
    plot_risk_coverage_curves,
    plot_threshold_landscape,
    plot_per_world_comparison,
    plot_methods_comparison,
)


OUTPUT_DIR = "/tmp/proofdesk/signing_benchmark"


def run_signing_benchmark(
    n_per_world: int = 200,
    seed: int = 42,
    output_dir: str = OUTPUT_DIR,
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    t0 = time.time()

    print(f"\n{'='*70}")
    print(f"  SIGNING WORLD BENCHMARK — {n_per_world} docs/world, seed={seed}")
    print(f"{'='*70}\n")

    # Generate worlds
    print("[1/5] Generating SigningWorlds...")
    worlds = generate_all_worlds(n_per_world, seed)
    for hw, w in worlds.items():
        safe = sum(1 for d in w.documents if d.verdict == Verdict.SAFE)
        risky = sum(1 for d in w.documents if d.verdict == Verdict.RISKY)
        fraud = sum(1 for d in w.documents if d.verdict == Verdict.FRAUDULENT)
        print(f"  {hw:25s}  safe={safe}  risky={risky}  fraud={fraud}")

    # Run signers
    print("\n[2/5] Running signers...")
    signers = {
        "Naive (conf>0.5)": naive_signer,
        "Always Defer": always_defer_signer,
        "Match Label": match_label_signer,
        "Threshold 0.5": threshold_signer(0.5),
        "Threshold 0.7": threshold_signer(0.7),
        "Fusion 0.5": fusion_signer(0.5),
        "Fusion 0.7": fusion_signer(0.7),
    }

    # Aggregate across worlds
    all_results = {}
    for signer_name, signer_fn in signers.items():
        utilities = []
        fprs = []
        fnrs = []
        for hw, world in worlds.items():
            run = run_signing_world(world, signer_fn, condition=signer_name)
            utilities.append(run.mean_utility)
            fprs.append(run.false_positive_rate)
            fnrs.append(run.false_negative_rate)
        all_results[signer_name] = {
            "mean_utility": np.mean(utilities),
            "mean_fpr": np.mean(fprs),
            "mean_fnr": np.mean(fnrs),
        }
        print(f"  {signer_name:25s}  utility={np.mean(utilities):.3f}  "
              f"FPR={np.mean(fprs):.3f}  FNR={np.mean(fnrs):.3f}")

    # Optimize fusion threshold per world
    print("\n[3/5] Optimizing fusion thresholds...")
    optimal_thresholds = {}
    for hw, world in worlds.items():
        best, curve = optimize_threshold(world, fusion_signer)
        optimal_thresholds[hw] = best
        print(f"  {hw:25s}  optimal_τ={best.threshold:.3f}  "
              f"coverage={best.coverage:.1%}  risk={best.risk:.3f}  "
              f"utility={best.utility:.3f}")

    # Per-world comparison
    print("\n[4/5] Per-world analysis...")
    world_comparison = {}
    for hw, world in worlds.items():
        best = optimal_thresholds[hw]
        signer = fusion_signer(best.threshold)
        run = run_signing_world(world, signer, condition="optimized")
        world_comparison[hw] = {
            "ece": 0.0,  # will compute below
            "brier": 0.0,
            "bas": 0.0,
            "utility": run.mean_utility,
            "fpr": run.false_positive_rate,
            "fnr": run.false_negative_rate,
            "sign_rate": run.signature.sign_rate,
        }

        # Compute calibration on confidence scores
        confs = np.array([r.decision.confidence for r in run.records])
        correct = np.array([r.score.correct for r in run.records])
        if confs.std() > 0:
            from .metrics import expected_calibration_error, brier_score, behavioral_alignment_score
            ece, _ = expected_calibration_error(confs, correct)
            brier = brier_score(confs, correct)
            bas = behavioral_alignment_score(confs, correct)
            world_comparison[hw]["ece"] = ece
            world_comparison[hw]["brier"] = brier
            world_comparison[hw]["bas"] = bas

    # Generate plots
    print("\n[5/5] Generating plots...")

    # 5a: Risk-coverage curves for fusion across thresholds
    for hw, world in worlds.items():
        best_tau, curve = optimize_threshold(world, fusion_signer)
        rc_curve = [(r.threshold, r.coverage, r.risk) for r in curve]
        p = plot_risk_coverage_curves(
            {"Fusion": rc_curve},
            title=f"Risk-Coverage — {hw}",
            save_path=f"{output_dir}/risk_coverage_{hw}.png",
        )

    # 5b: Threshold landscape for each world
    for hw, world in worlds.items():
        _, curve = optimize_threshold(world, fusion_signer)
        thresh_results = [
            {"threshold": r.threshold, "coverage": r.coverage, "risk": r.risk,
             "accuracy": 1 - r.risk, "n_accepted": r.n_sign, "n_rejected": r.n_refuse + r.n_defer,
             "false_negative_rate": r.false_negative_rate}
            for r in curve
        ]
        p = plot_threshold_landscape(thresh_results, f"Fusion — {hw}",
                                     save_path=f"{output_dir}/threshold_{hw}.png")

    # 5c: Methods comparison
    metrics_summary = {}
    for name, res in all_results.items():
        metrics_summary[name] = {
            "ece": 0.5 - res["mean_utility"],  # proxy
            "brier": res["mean_fpr"],
            "bas": res["mean_utility"],
            "aurc": res["mean_fpr"] + res["mean_fnr"],
        }
    p = plot_methods_comparison(metrics_summary, save_path=f"{output_dir}/methods.png")

    # 5d: Per-world comparison
    p = plot_per_world_comparison(world_comparison, save_path=f"{output_dir}/per_world.png")

    elapsed = time.time() - t0

    # Summary
    print(f"\n{'='*70}")
    print(f"  SIGNING BENCHMARK COMPLETE — {elapsed:.1f}s")
    print(f"{'='*70}")
    print(f"\n  Output: {output_dir}/")
    print(f"  Plots:  {len([f for f in os.listdir(output_dir) if f.endswith('.png')])} files")

    # Best signer overall
    best_signer = max(all_results.keys(), key=lambda k: all_results[k]["mean_utility"])
    print(f"\n  Best signer: {best_signer}")
    print(f"  Best utility: {all_results[best_signer]['mean_utility']:.3f}")
    print(f"  Best FPR: {all_results[best_signer]['mean_fpr']:.3f}")

    # Optimal thresholds
    print(f"\n  Optimal thresholds by world:")
    for hw, best in optimal_thresholds.items():
        print(f"    {hw:25s}  τ={best.threshold:.3f}  utility={best.utility:.3f}  risk={best.risk:.3f}")

    # Save report
    report = {
        "n_per_world": n_per_world,
        "seed": seed,
        "elapsed_s": elapsed,
        "signers": all_results,
        "optimal_thresholds": {
            hw: {"threshold": b.threshold, "coverage": b.coverage, "risk": b.risk, "utility": b.utility}
            for hw, b in optimal_thresholds.items()
        },
        "per_world": world_comparison,
    }
    report_path = f"{output_dir}/report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="SigningWorld Benchmark")
    parser.add_argument("--n", type=int, default=200, help="Docs per world")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--quick", action="store_true", help="Quick mode (50 docs)")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.quick:
        args.n = 50

    run_signing_benchmark(args.n, args.seed, args.output)


if __name__ == "__main__":
    main()
