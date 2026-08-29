#!/usr/bin/env python3
"""ML Lab — Full visualization suite for signing optimization experiments.

Generates:
1. Optimization landscape (threshold vs utility/risk/coverage)
2. Calibration convergence (raw → isotonic → conformal)
3. Per-world hard world comparison radar
4. Confidence distribution by verdict
5. Decision boundary visualization
6. Sheepish vs Raw vs Calibrated comparison
7. Risk-coverage frontier with Pareto optimal
8. Bootstrap confidence intervals
9. Feature importance for routing
10. Audit trail timeline
"""

from __future__ import annotations

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from typing import Any

from .signing_world import Verdict, SigningDecision, score_signing
from .signing_generator import generate_signing_world, generate_all_worlds
from .experts import MixtureOfExperts, ExpertPolicy
from .calibration import IsotonicCalibrator, PlattScaler
from .metrics import (
    compute_all_metrics, expected_calibration_error,
    brier_score, risk_coverage_curve, threshold_analysis,
)
from .signing_runner import run_signing_world, optimize_threshold

OUTPUT_DIR = "/tmp/proofdesk/ml_lab"

# Style
plt.rcParams.update({
    "figure.facecolor": "#0d1117",
    "axes.facecolor": "#161b22",
    "axes.edgecolor": "#30363d",
    "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9",
    "xtick.color": "#8b949e",
    "ytick.color": "#8b949e",
    "grid.color": "#21262d",
    "grid.alpha": 0.6,
    "figure.dpi": 150,
    "font.size": 10,
})

C = {
    "blue": "#58a6ff", "green": "#3fb950", "red": "#f85149",
    "orange": "#d29922", "purple": "#bc8cff", "cyan": "#39d2c0",
    "pink": "#f778ba", "gray": "#8b949e", "white": "#c9d1d9",
}


def run_all(n_per_world: int = 200, seed: int = 42) -> str:
    """Run all visualizations, return output directory."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n{'='*70}")
    print(f"  ML LAB — Generating all visualizations")
    print(f"{'='*70}\n")

    # Generate worlds
    worlds = generate_all_worlds(n_per_world, seed)

    # Fit mixture
    moe = MixtureOfExperts(risk_budget=0.3)
    moe.fit(worlds)

    plots = []

    # 1. Optimization landscape
    plots.append(_plot_optimization_landscape(worlds, moe))

    # 2. Calibration convergence
    plots.append(_plot_calibration_convergence(worlds))

    # 3. Per-world radar
    plots.append(_plot_world_radar(worlds, moe))

    # 4. Confidence distribution
    plots.append(_plot_confidence_distribution(worlds, moe))

    # 5. Decision boundary
    plots.append(_plot_decision_boundary(worlds, moe))

    # 6. Sheepish vs Raw comparison
    plots.append(_plot_sheepish_comparison(worlds, moe))

    # 7. Risk-coverage Pareto
    plots.append(_plot_pareto_frontier(worlds, moe))

    # 8. Bootstrap CIs
    plots.append(_plot_bootstrap_cis(worlds, moe))

    # 9. Feature importance
    plots.append(_plot_feature_importance(moe))

    # 10. Audit timeline
    plots.append(_plot_audit_timeline(worlds, moe))

    print(f"\n{'='*70}")
    print(f"  Generated {len(plots)} plots → {OUTPUT_DIR}/")
    print(f"{'='*70}\n")

    return OUTPUT_DIR


def _plot_optimization_landscape(worlds, moe):
    """Threshold vs utility/risk/coverage across all worlds."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Optimization Landscape — Threshold vs Outcome", fontsize=14, fontweight="bold")

    for idx, (hw, world) in enumerate(worlds.items()):
        ax = axes[idx // 3][idx % 3]
        expert = moe.experts[hw]

        taus = np.linspace(0.1, 0.95, 40)
        utilities, risks, coverages = [], [], []

        for tau in taus:
            signer = _make_signer(expert, tau)
            run = run_signing_world(world, signer)
            utilities.append(run.mean_utility)
            signed = [r for r in run.records if r.decision.stance == "SIGN"]
            risk = sum(r.score.false_positive for r in signed) / max(1, len(signed))
            risks.append(risk)
            coverages.append(len(signed) / max(1, len(run.records)))

        ax.plot(taus, utilities, color=C["blue"], linewidth=2, label="Utility")
        ax.fill_between(taus, utilities, alpha=0.15, color=C["blue"])
        ax.plot(taus, risks, color=C["red"], linewidth=2, label="Risk", linestyle="--")
        ax.plot(taus, coverages, color=C["green"], linewidth=2, label="Coverage", linestyle=":")

        # Mark optimal
        best_idx = np.argmax(utilities)
        ax.axvline(taus[best_idx], color=C["orange"], linestyle="--", alpha=0.7)
        ax.annotate(f"τ*={taus[best_idx]:.2f}\nu={utilities[best_idx]:.3f}",
                    xy=(taus[best_idx], utilities[best_idx]),
                    xytext=(taus[best_idx]+0.1, utilities[best_idx]-0.1),
                    fontsize=8, color=C["orange"])

        ax.set_title(hw.replace("_", " ").title(), fontsize=10)
        ax.set_xlabel("Threshold (τ)")
        ax.set_ylabel("Score")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/01_optimization_landscape.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [1] {path}")
    return path


def _plot_calibration_convergence(worlds):
    """Show how calibration improves from raw → isotonic → Platt."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Calibration Convergence — Raw → Isotonic → Platt", fontsize=14, fontweight="bold")

    # Collect all scores
    all_scores, all_labels = [], []
    for world in worlds.values():
        for i in range(len(world)):
            sig = world.signals[i]
            all_scores.append(sig.nutrient_confidence)
            all_labels.append(1.0 if world.documents[i].should_sign else 0.0)

    scores = np.array(all_scores)
    labels = np.array(all_labels)

    # Split
    n = len(scores) // 2
    cal_scores, test_scores = scores[:n], scores[n:]
    cal_labels, test_labels = labels[:n], labels[n:]

    # Raw
    ax = axes[0]
    _reliability_plot(ax, test_scores, test_labels, "Raw Confidence")

    # Isotonic
    iso = IsotonicCalibrator()
    iso.fit(cal_scores, cal_labels)
    iso_cal = np.array([iso.calibrate(s) for s in test_scores])
    ax = axes[1]
    _reliability_plot(ax, iso_cal, test_labels, "After Isotonic")

    # Platt
    platt = PlattScaler()
    platt.fit(cal_scores, cal_labels)
    platt_cal = np.array([platt.calibrate(s) for s in test_scores])
    ax = axes[2]
    _reliability_plot(ax, platt_cal, test_labels, "After Platt")

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/02_calibration_convergence.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [2] {path}")
    return path


def _plot_world_radar(worlds, moe):
    """Radar chart comparing hard world difficulty."""
    categories = ["ECE", "Brier", "BAS", "Utility", "FPR", "FNR"]
    n_cats = len(categories)
    angles = np.linspace(0, 2 * np.pi, n_cats, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor("#161b22")
    fig.patch.set_facecolor("#0d1117")

    colors = [C["blue"], C["green"], C["red"], C["orange"], C["purple"]]

    for idx, (hw, world) in enumerate(worlds.items()):
        expert = moe.experts[hw]
        # Run on this world
        run = run_signing_world(world, expert.decide)
        confs = np.array([r.decision.confidence for r in run.records])
        corrects = np.array([r.score.correct for r in run.records])
        m = compute_all_metrics(confs, corrects)

        values = [m.ece, m.brier, m.bas, run.mean_utility,
                  run.false_positive_rate, run.false_negative_rate]
        values += values[:1]

        ax.plot(angles, values, color=colors[idx], linewidth=2, label=hw.replace("_", " ").title())
        ax.fill(angles, values, color=colors[idx], alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylim(0, 1)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=8)
    ax.set_title("Hard World Comparison (Radar)", fontsize=13, fontweight="bold", pad=20)

    path = f"{OUTPUT_DIR}/03_world_radar.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [3] {path}")
    return path


def _plot_confidence_distribution(worlds, moe):
    """Confidence score distributions by verdict."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Confidence Distribution by Verdict", fontsize=14, fontweight="bold")

    for idx, verdict in enumerate([Verdict.SAFE, Verdict.RISKY, Verdict.FRAUDULENT]):
        ax = axes[idx]
        scores = []
        for world in worlds.values():
            for i, doc in enumerate(world.documents):
                if doc.verdict == verdict:
                    sig = world.signals[i]
                    scores.append(sig.nutrient_confidence)

        ax.hist(scores, bins=25, color=list(C.values())[idx], alpha=0.7, edgecolor="white", linewidth=0.3)
        ax.axvline(np.mean(scores), color=C["white"], linestyle="--", linewidth=1.5, label=f"μ={np.mean(scores):.2f}")
        ax.set_title(f"{verdict.value.upper()} (n={len(scores)})", fontsize=11)
        ax.set_xlabel("Confidence Score")
        ax.set_ylabel("Count")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/04_confidence_distribution.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [4] {path}")
    return path


def _plot_decision_boundary(worlds, moe):
    """2D decision boundary using two most important signals."""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Collect features
    X, y, preds = [], [], []
    for world in worlds.values():
        for i in range(len(world)):
            packet = world.packet(i)
            X.append([packet.signals.nutrient_confidence, packet.signals.grounding_score])
            y.append(1.0 if world.documents[i].should_sign else 0.0)
            result = moe.decide(packet)
            preds.append(1.0 if result.decision.stance == "SIGN" else 0.0)

    X = np.array(X)
    y = np.array(y)
    preds = np.array(preds)

    # Grid
    x_min, x_max = X[:, 0].min() - 0.1, X[:, 0].max() + 0.1
    y_min, y_max = X[:, 1].min() - 0.1, X[:, 1].max() + 0.1
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, 100), np.linspace(y_min, y_max, 100))

    # Decision boundary (approximate)
    Z = np.zeros_like(xx)
    for i in range(xx.shape[0]):
        for j in range(xx.shape[1]):
            Z[i, j] = 0.6 * xx[i, j] + 0.4 * yy[i, j]  # approximate fusion score

    ax.contourf(xx, yy, Z, levels=[0, 0.5, 0.7, 1.0], colors=[C["red"], C["orange"], C["green"]], alpha=0.3)
    ax.contour(xx, yy, Z, levels=[0.5, 0.7], colors=[C["white"], C["orange"]], linewidths=1, linestyles="--")

    # Scatter points
    correct = preds == y
    ax.scatter(X[correct & (y==1), 0], X[correct & (y==1), 1], c=C["green"], marker="o", s=30, label="Correct SIGN", alpha=0.7)
    ax.scatter(X[correct & (y==0), 0], X[correct & (y==0), 1], c=C["blue"], marker="o", s=30, label="Correct REFUSE", alpha=0.7)
    ax.scatter(X[~correct & (y==1), 0], X[~correct & (y==1), 1], c=C["red"], marker="x", s=50, label="Missed safe (FNR)")
    ax.scatter(X[~correct & (y==0), 0], X[~correct & (y==0), 1], c=C["orange"], marker="x", s=50, label="False positive (FPR)")

    ax.set_xlabel("Nutrient Confidence", fontsize=12)
    ax.set_ylabel("Grounding Score", fontsize=12)
    ax.set_title("Decision Boundary — Fusion Score", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    path = f"{OUTPUT_DIR}/05_decision_boundary.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [5] {path}")
    return path


def _plot_sheepish_comparison(worlds, moe):
    """Compare Sheepish (underconfident) vs Raw vs Calibrated."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Sheepish vs Raw vs Calibrated — Confidence Strategies", fontsize=14, fontweight="bold")

    all_confs = {"Raw": [], "Sheepish": [], "Calibrated": [], "Oracle": []}
    all_correct = {"Raw": [], "Sheepish": [], "Calibrated": [], "Oracle": []}

    for world in worlds.values():
        for i in range(len(world)):
            packet = world.packet(i)
            raw = packet.signals.nutrient_confidence
            # Sheepish: underconfident by 20% but well-calibrated
            sheepish = max(0.0, min(1.0, raw * 0.7 + 0.15))
            # Calibrated: isotonic-mapped
            expert = moe.experts.get(world.documents[i].hard_world, list(moe.experts.values())[0])
            cal = expert.compute_score(packet)

            correct = 1.0 if world.documents[i].should_sign else 0.0

            all_confs["Raw"].append(raw)
            all_confs["Sheepish"].append(sheepish)
            all_confs["Calibrated"].append(cal)
            all_confs["Oracle"].append(correct)

            all_correct["Raw"].append(correct)
            all_correct["Sheepish"].append(correct)
            all_correct["Calibrated"].append(correct)
            all_correct["Oracle"].append(correct)

    # 2a: Confidence histograms
    ax = axes[0][0]
    for name, color in [("Raw", C["red"]), ("Sheepish", C["green"]), ("Calibrated", C["blue"])]:
        ax.hist(all_confs[name], bins=30, alpha=0.5, color=color, label=name, edgecolor="white", linewidth=0.3)
    ax.set_title("Confidence Distributions")
    ax.set_xlabel("Confidence")
    ax.legend()
    ax.grid(True, alpha=0.2)

    # 2b: Reliability diagram
    ax = axes[0][1]
    for name, color in [("Raw", C["red"]), ("Sheepish", C["green"]), ("Calibrated", C["blue"])]:
        _reliability_plot(ax, np.array(all_confs[name]), np.array(all_correct[name]),
                         name, color=color, show_label=True)
    ax.plot([0, 1], [0, 1], "--", color=C["gray"], linewidth=1)
    ax.set_title("Reliability Diagram")
    ax.legend(fontsize=8)

    # 2c: Brier scores
    ax = axes[1][0]
    briers = {}
    for name in ["Raw", "Sheepish", "Calibrated"]:
        briers[name] = brier_score(np.array(all_confs[name]), np.array(all_correct[name]))
    bars = ax.bar(briers.keys(), briers.values(), color=[C["red"], C["green"], C["blue"]], alpha=0.8)
    ax.set_title("Brier Score (lower = better)")
    ax.set_ylabel("Brier")
    for bar, val in zip(bars, briers.values()):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.005, f"{val:.3f}", ha="center", fontsize=9)
    ax.grid(True, alpha=0.2, axis="y")

    # 2d: ECE scores
    ax = axes[1][1]
    eces = {}
    for name in ["Raw", "Sheepish", "Calibrated"]:
        ece, _ = expected_calibration_error(np.array(all_confs[name]), np.array(all_correct[name]))
        eces[name] = ece
    bars = ax.bar(eces.keys(), eces.values(), color=[C["red"], C["green"], C["blue"]], alpha=0.8)
    ax.set_title("ECE (lower = better)")
    ax.set_ylabel("ECE")
    for bar, val in zip(bars, eces.values()):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.002, f"{val:.3f}", ha="center", fontsize=9)
    ax.grid(True, alpha=0.2, axis="y")

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/06_sheepish_comparison.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [6] {path}")
    return path


def _plot_pareto_frontier(worlds, moe):
    """Risk-coverage Pareto frontier with all methods."""
    fig, ax = plt.subplots(figsize=(10, 8))

    methods = {
        "Naive": lambda p: "SIGN" if p.signals.nutrient_confidence > 0.5 else "REFUSE",
        "Single Expert": lambda p: moe.experts[list(moe.experts.keys())[0]].decide(p).stance,
        "Mixture": lambda p: moe.decide(p).decision.stance,
    }

    for name, signer_fn in methods.items():
        coverages, risks = [], []
        for world in worlds.values():
            run = run_signing_world(world, lambda p, sf=signer_fn: SigningDecision(
                stance=sf(p), p_safe=0.5, p_risky=0.25, p_fraudulent=0.25, confidence=0.5, risk=0.5))
            n = len(run.records)
            n_sign = sum(r.decision.stance == "SIGN" for r in run.records)
            coverage = n_sign / max(1, n)
            signed = [r for r in run.records if r.decision.stance == "SIGN"]
            risk = sum(r.score.false_positive for r in signed) / max(1, len(signed))
            coverages.append(coverage)
            risks.append(risk)

        ax.scatter(coverages, risks, s=100, label=name, alpha=0.8, edgecolors="white", linewidth=0.5)

    # Oracle
    ax.scatter([0.45], [0.0], s=200, marker="*", color=C["green"], label="Oracle", zorder=5)

    ax.set_xlabel("Coverage (fraction auto-signed)", fontsize=12)
    ax.set_ylabel("Risk (false positive rate)", fontsize=12)
    ax.set_title("Pareto Frontier — Risk vs Coverage", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    path = f"{OUTPUT_DIR}/07_pareto_frontier.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [7] {path}")
    return path


def _plot_bootstrap_cis(worlds, moe):
    """Bootstrap confidence intervals for key metrics."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Bootstrap 95% Confidence Intervals", fontsize=14, fontweight="bold")

    np.random.seed(42)
    n_boot = 200

    metrics = {"Utility": [], "FPR": [], "FNR": []}
    for _ in range(n_boot):
        # Sample worlds with replacement
        sample_worlds = list(np.random.choice(list(worlds.keys()), size=len(worlds)))
        utils, fprs, fnrs = [], [], []
        for hw in sample_worlds:
            world = worlds[hw]
            expert = moe.experts[hw]
            run = run_signing_world(world, expert.decide)
            utils.append(run.mean_utility)
            fprs.append(run.false_positive_rate)
            fnrs.append(run.false_negative_rate)
        metrics["Utility"].append(np.mean(utils))
        metrics["FPR"].append(np.mean(fprs))
        metrics["FNR"].append(np.mean(fnrs))

    for idx, (name, values) in enumerate(metrics.items()):
        ax = axes[idx]
        values = np.array(values)
        mean = np.mean(values)
        ci_lo, ci_hi = np.percentile(values, [2.5, 97.5])
        ax.hist(values, bins=30, color=list(C.values())[idx], alpha=0.7, edgecolor="white", linewidth=0.3)
        ax.axvline(mean, color=C["white"], linewidth=2, label=f"Mean={mean:.3f}")
        ax.axvspan(ci_lo, ci_hi, alpha=0.2, color=C["orange"], label=f"95% CI=[{ci_lo:.3f}, {ci_hi:.3f}]")
        ax.set_title(name)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/08_bootstrap_cis.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [8] {path}")
    return path


def _plot_feature_importance(moe):
    """Feature importance from fusion weights."""
    fig, ax = plt.subplots(figsize=(10, 6))

    features = ["Nutrient Conf", "Match Score", "Grounding", "Margin", "Cross-Doc", "Completeness"]
    # Get weights from first expert
    expert = list(moe.experts.values())[0]
    weights = expert.weights[:6]

    # Sort
    order = np.argsort(weights)[::-1]
    features = [features[i] for i in order]
    weights = [weights[i] for i in order]

    colors = [C["green"] if w > 0.2 else C["blue"] if w > 0.1 else C["gray"] for w in weights]
    bars = ax.barh(features, weights, color=colors, alpha=0.8, edgecolor="white", linewidth=0.3)

    for bar, val in zip(bars, weights):
        ax.text(val + 0.005, bar.get_y() + bar.get_height()/2, f"{val:.2f}", va="center", fontsize=9)

    ax.set_xlabel("Weight", fontsize=12)
    ax.set_title("Feature Importance — Fusion Scoring", fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.2, axis="x")

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/09_feature_importance.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [9] {path}")
    return path


def _plot_audit_timeline(worlds, moe):
    """Audit trail timeline for a sample document."""
    fig, ax = plt.subplots(figsize=(14, 4))

    # Pick a safe doc
    world = worlds["base_rate_shift"]
    for i, doc in enumerate(world.documents):
        if doc.verdict == Verdict.SAFE:
            break

    packet = world.packet(i)
    result = moe.decide(packet)

    events = [
        ("Document Ingested", 0, C["blue"]),
        ("Nutrient Extraction", 1, C["cyan"]),
        ("Confidence Signals", 2, C["purple"]),
        ("Router Selects Expert", 3, C["orange"]),
        ("Expert Calibration", 4, C["green"]),
        (f"Decision: {result.decision.stance}", 5, C["green"] if result.decision.stance == "SIGN" else C["red"]),
        ("Foxit PDF Merge (reversible)", 6, C["cyan"]),
        ("Foxit PDF Compress (reversible)", 7, C["cyan"]),
        ("SignatureGate Check", 8, C["orange"]),
        ("Foxit eSign (irreversible)", 9, C["red"]),
    ]

    for name, x, color in events:
        ax.plot(x, 0, "o", color=color, markersize=12, zorder=5)
        ax.annotate(name, (x, 0), textcoords="offset points", xytext=(0, 20),
                    ha="center", fontsize=7, rotation=45, color=color)
        if x < len(events) - 1:
            ax.plot([x, x+1], [0, 0], color=C["gray"], linewidth=1, alpha=0.5)

    ax.set_xlim(-0.5, len(events) - 0.5)
    ax.set_ylim(-0.5, 1)
    ax.axis("off")
    ax.set_title("Audit Trail Timeline — Signing Pipeline", fontsize=13, fontweight="bold")

    plt.tight_layout()
    path = f"{OUTPUT_DIR}/10_audit_timeline.png"
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  [10] {path}")
    return path


# Helpers

def _reliability_plot(ax, confs, corrects, label, color=C["blue"], show_label=False):
    n_bins = 10
    bins = np.linspace(0, 1, n_bins + 1)
    for i in range(n_bins):
        mask = (confs >= bins[i]) & (confs < bins[i+1])
        if mask.sum() > 0:
            mean_conf = confs[mask].mean()
            mean_acc = corrects[mask].mean()
            ax.plot(mean_conf, mean_acc, "o", color=color, markersize=6,
                    label=label if show_label and i == 0 else None)

def _make_signer(expert, tau):
    def signer(packet):
        score = expert.compute_score(packet)
        risk = 1.0 - score
        if score >= tau:
            return SigningDecision("SIGN", score, risk*0.3, risk*0.7, score, risk)
        elif score >= tau - 0.15:
            return SigningDecision("DEFER", score*0.8, risk*0.5, risk*0.5, score, risk)
        else:
            return SigningDecision("REFUSE", score*0.3, risk*0.3, risk*0.7, score, risk)
    return signer


if __name__ == "__main__":
    run_all()
