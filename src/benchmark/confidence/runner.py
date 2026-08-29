#!/usr/bin/env python3
"""Confidence Benchmark Runner — full pipeline.

Generates documents → simulates signals → calibrates → benchmarks → plots.

Usage:
    python3 -m benchmark.confidence.runner --n 1000 --seed 42
    python3 -m benchmark.confidence.runner --quick  # 200 docs, fast
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import numpy as np

from .document_world import generate_world, HardWorld, DocumentVerdict
from .signals import simulate_signals, signals_to_vector, ConfidenceSignals
from .calibration import (
    IsotonicCalibrator,
    ConformalRiskController,
    MarginOnlineCalibrator,
    PlattScaler,
)
from .metrics import compute_all_metrics, CalibrationMetrics
from .plots import (
    plot_risk_coverage_curves,
    plot_reliability_diagram,
    plot_threshold_landscape,
    plot_per_world_comparison,
    plot_calibration_convergence,
    plot_optimization_evolution,
    plot_methods_comparison,
)


OUTPUT_DIR = "/tmp/proofdesk/confidence_benchmark"


def run_benchmark(
    n_docs: int = 1000,
    seed: int = 42,
    noise_level: float = 0.12,
    risk_target: float = 0.1,
    output_dir: str = OUTPUT_DIR,
) -> dict:
    """Run the full confidence benchmark."""
    os.makedirs(output_dir, exist_ok=True)
    rng = np.random.RandomState(seed)
    np_rng = np.random.RandomState(seed)

    print(f"\n{'='*70}")
    print(f"  CONFIDENCE BENCHMARK — {n_docs} documents, seed={seed}")
    print(f"{'='*70}\n")

    t0 = time.time()

    # === 1. Generate DocumentWorld ===
    print("[1/7] Generating DocumentWorld...")
    docs = generate_world(n_docs=n_docs, seed=seed, corruption_rate=0.18)
    print(f"      {len(docs)} documents across {len(HardWorld)} hard worlds")

    world_counts = {}
    for d in docs:
        world_counts[d.hard_world.value] = world_counts.get(d.hard_world.value, 0) + 1
    for w, c in sorted(world_counts.items()):
        print(f"        {w}: {c}")

    verdict_counts = {}
    for d in docs:
        verdict_counts[d.verdict.value] = verdict_counts.get(d.verdict.value, 0) + 1
    print(f"      Verdicts: {verdict_counts}")

    # === 2. Simulate Confidence Signals ===
    print("\n[2/7] Simulating Nutrient-style confidence signals...")
    signals = []
    for doc in docs:
        sig = simulate_signals(doc, np.random.RandomState(seed + hash(doc.doc_id) % 10000),
                               noise_level=noise_level)
        signals.append(sig)

    confidences_raw = np.array([s.nutrient_confidence for s in signals])
    correct_labels = np.array([s.should_sign for s in signals])
    print(f"      Raw confidence: mean={confidences_raw.mean():.3f}, "
          f"std={confidences_raw.std():.3f}")

    # === 3. Split into calibration / test ===
    print("\n[3/7] Splitting calibration / test (50/50)...")
    n_cal = len(signals) // 2
    indices = np_rng.permutation(len(signals))
    cal_idx = indices[:n_cal]
    test_idx = indices[n_cal:]

    cal_signals = [signals[i] for i in cal_idx]
    test_signals = [signals[i] for i in test_idx]

    cal_scores = np.array([s.nutrient_confidence for s in cal_signals])
    cal_labels = np.array([s.should_sign for s in cal_signals])
    test_scores = np.array([s.nutrient_confidence for s in test_signals])
    test_labels = np.array([s.should_sign for s in test_signals])

    print(f"      Calibration: {len(cal_signals)}, Test: {len(test_signals)}")

    # === 4. Calibrate ===
    print("\n[4/7] Running calibration methods...")

    # Method 1: Raw (no calibration)
    print("      [a] Raw (no calibration)")

    # Method 2: Isotonic regression
    print("      [b] Isotonic regression")
    isotonic = IsotonicCalibrator()
    isotonic.fit(cal_scores, cal_labels)
    isotonic_calibrated = np.array([isotonic.calibrate(s) for s in test_scores])

    # Method 3: Platt scaling
    print("      [c] Platt scaling")
    platt = PlattScaler()
    platt.fit(cal_scores, cal_labels)
    platt_calibrated = np.array([platt.calibrate(s) for s in test_scores])

    # Method 4: Conformal risk control
    print("      [d] Conformal risk control (α={risk_target})")
    # Nonconformity scores: 1 - confidence for correct, confidence for incorrect
    cal_nonconf = np.where(cal_labels, 1 - cal_scores, cal_scores)
    crc = ConformalRiskController(alpha=risk_target)
    crc.fit(cal_nonconf, cal_labels.astype(float))
    crc_threshold = crc.find_threshold()
    print(f"      CRC threshold: {crc_threshold.threshold:.3f}, "
          f"coverage: {crc_threshold.coverage:.1%}, "
          f"observed risk: {crc_threshold.observed_risk:.3f}")

    # Method 5: MARGIN online calibration
    print("      [e] MARGIN online calibration")
    margin = MarginOnlineCalibrator(n_bands=5, alpha=0.04)
    margin.fit_batch(cal_scores, cal_labels)
    margin_calibrated = np.array([margin.calibrate(s) for s in test_scores])

    # Method 6: Multi-signal fusion
    print("      [f] Multi-signal fusion")
    test_vectors = np.array([signals_to_vector(s) for s in test_signals])
    cal_vectors = np.array([signals_to_vector(s) for s in cal_signals])
    # Simple weighted average of signals (optimized via calibration set)
    weights = np.ones(cal_vectors.shape[1]) / cal_vectors.shape[1]
    # Fit weights via logistic regression on calibration set
    from sklearn.linear_model import LogisticRegression
    lr = LogisticRegression(C=1.0, max_iter=1000)
    lr.fit(cal_vectors, cal_labels)
    fusion_raw = lr.predict_proba(test_vectors)[:, 1]

    # === 5. Compute Metrics ===
    print("\n[5/7] Computing metrics...")
    methods = {
        "Raw": test_scores,
        "Isotonic": isotonic_calibrated,
        "Platt": platt_calibrated,
        "MARGIN": margin_calibrated,
        "Fusion (LR)": fusion_raw,
    }

    all_metrics = {}
    for name, scores in methods.items():
        m = compute_all_metrics(scores, test_labels)
        all_metrics[name] = m
        print(f"      {name:15s}  ECE={m.ece:.3f}  Brier={m.brier:.3f}  "
              f"BAS={m.bas:.3f}  AURC={m.aurc:.3f}")

    # === 6. Generate Plots ===
    print("\n[6/7] Generating plots...")

    # 6a: Risk-coverage curves
    curves = {}
    for name, scores in methods.items():
        from .metrics import risk_coverage_curve
        curves[name] = risk_coverage_curve(scores, test_labels)
    p = plot_risk_coverage_curves(curves, save_path=f"{output_dir}/risk_coverage.png")
    print(f"      -> {p}")

    # 6b: Reliability diagrams
    for name, scores in methods.items():
        p = plot_reliability_diagram(scores, test_labels, name,
                                     save_path=f"{output_dir}/reliability_{name.lower().replace(' ', '_')}.png")
        print(f"      -> {p}")

    # 6c: Threshold landscape for best method
    best_method = min(all_metrics.keys(), key=lambda k: all_metrics[k].aurc)
    best_scores = methods[best_method]
    from .metrics import threshold_analysis
    thresh_results = threshold_analysis(best_scores, test_labels)
    p = plot_threshold_landscape(thresh_results, best_method,
                                 save_path=f"{output_dir}/threshold_{best_method.lower().replace(' ', '_')}.png")
    print(f"      -> {p}")

    # 6d: Per-world comparison
    world_metrics = {}
    for hw in HardWorld:
        world_signals = [s for s in test_signals if s.hard_world == hw.value]
        if not world_signals:
            continue
        world_scores = np.array([s.nutrient_confidence for s in world_signals])
        world_labels = np.array([s.should_sign for s in world_signals])
        wm = compute_all_metrics(world_scores, world_labels)
        world_metrics[hw.value] = {
            "ece": wm.ece,
            "brier": wm.brier,
            "bas": wm.bas,
            "accuracy": wm.accuracy,
        }
    p = plot_per_world_comparison(world_metrics, save_path=f"{output_dir}/per_world.png")
    print(f"      -> {p}")

    # 6e: MARGIN convergence
    margin_online = MarginOnlineCalibrator(n_bands=5, alpha=0.04)
    online_scores_list = []
    for s, l in zip(test_scores, test_labels):
        margin_online.update(float(s), bool(l))
        online_scores_list.append(margin_online.calibrate(float(s)))
    p = plot_calibration_convergence(online_scores_list,
                                     save_path=f"{output_dir}/convergence.png")
    print(f"      -> {p}")

    # 6f: Methods comparison
    metrics_summary = {name: {
        "ece": m.ece, "brier": m.brier, "bas": m.bas, "aurc": m.aurc,
    } for name, m in all_metrics.items()}
    p = plot_methods_comparison(metrics_summary, save_path=f"{output_dir}/methods_comparison.png")
    print(f"      -> {p}")

    # === 7. Optimization Evolution ===
    print("\n[7/7] Running optimization evolution...")
    gen_scores = []
    gen_auto = []
    gen_risk = []

    for gen in range(20):
        # Mutate noise level
        gen_noise = noise_level + (gen - 10) * 0.01
        gen_docs = generate_world(n_docs=200, seed=seed + gen, corruption_rate=0.18)
        gen_signals = [simulate_signals(d, np.random.RandomState(seed + gen + hash(d.doc_id) % 10000),
                                        noise_level=max(0.01, gen_noise))
                       for d in gen_docs]
        gen_conf = np.array([s.nutrient_confidence for s in gen_signals])
        gen_corr = np.array([s.should_sign for s in gen_signals])

        gm = compute_all_metrics(gen_conf, gen_corr)
        gen_scores.append(gm.bas)
        # Coverage at 10% risk target
        valid = [r for r in gm.threshold_analysis if r["risk"] <= risk_target]
        gen_auto.append(max((r["coverage"] for r in valid), default=0.0))
        gen_risk.append(min((r["risk"] for r in valid), default=1.0))

    p = plot_optimization_evolution(
        list(range(20)), gen_scores, gen_auto, gen_risk,
        save_path=f"{output_dir}/evolution.png",
    )
    print(f"      -> {p}")

    elapsed = time.time() - t0

    # === Summary ===
    print(f"\n{'='*70}")
    print(f"  BENCHMARK COMPLETE — {elapsed:.1f}s")
    print(f"{'='*70}")
    print(f"\n  Output: {output_dir}/")
    print(f"  Plots:  {len(os.listdir(output_dir))} files")
    print(f"\n  Best method: {best_method}")
    print(f"  Best AURC:   {all_metrics[best_method].aurc:.4f}")
    print(f"  Best ECE:    {all_metrics[best_method].ece:.4f}")
    print(f"  Best BAS:    {all_metrics[best_method].bas:.4f}")

    # Save report
    report = {
        "n_docs": n_docs,
        "seed": seed,
        "noise_level": noise_level,
        "risk_target": risk_target,
        "elapsed_s": elapsed,
        "methods": {
            name: {
                "ece": m.ece, "mce": m.mce, "brier": m.brier,
                "bas": m.bas, "aurc": m.aurc, "accuracy": m.accuracy,
            }
            for name, m in all_metrics.items()
        },
        "best_method": best_method,
        "per_world": world_metrics,
        "crc_threshold": {
            "threshold": crc_threshold.threshold,
            "coverage": crc_threshold.coverage,
            "observed_risk": crc_threshold.observed_risk,
        },
    }
    report_path = f"{output_dir}/report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Confidence Benchmark Runner")
    parser.add_argument("--n", type=int, default=1000, help="Number of documents")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--noise", type=float, default=0.12, help="Noise level")
    parser.add_argument("--risk-target", type=float, default=0.1, help="Target risk level (alpha)")
    parser.add_argument("--quick", action="store_true", help="Quick mode (200 docs)")
    parser.add_argument("--output", type=str, default=OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    if args.quick:
        args.n = 200

    run_benchmark(
        n_docs=args.n,
        seed=args.seed,
        noise_level=args.noise,
        risk_target=args.risk_target,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
