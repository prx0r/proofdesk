"""Visualization module — plots, graphs, optimization tracking.

Generates:
  1. Risk-coverage curves (per method + oracle)
  2. Calibration reliability diagrams
  3. Threshold optimization landscape
  4. Per-hard-world comparison
  5. Calibration convergence (MARGIN-style online)
  6. Optimization evolution (cogym-style)
"""

from __future__ import annotations

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Any


# Consistent style
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

COLORS = {
    "blue": "#58a6ff",
    "green": "#3fb950",
    "red": "#f85149",
    "orange": "#d29922",
    "purple": "#bc8cff",
    "cyan": "#39d2c0",
    "pink": "#f778ba",
    "gray": "#8b949e",
    "white": "#c9d1d9",
}


def plot_risk_coverage_curves(
    curves: dict[str, list[tuple[float, float, float]]],
    title: str = "Risk-Coverage Curves",
    save_path: str | None = None,
) -> str:
    """Plot risk-coverage curves for multiple methods.

    curves: {method_name: [(threshold, coverage, risk), ...]}
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for i, (name, curve) in enumerate(curves.items()):
        coverages = [c[1] for c in curve]
        risks = [c[2] for c in curve]
        color = list(COLORS.values())[i % len(COLORS)]
        ax.plot(coverages, risks, color=color, linewidth=2, label=name, alpha=0.9)

    # Optimal corner
    ax.plot(1.0, 0.0, "o", color=COLORS["green"], markersize=12, label="Oracle (perfect)")

    ax.set_xlabel("Coverage (fraction auto-signed)", fontsize=12)
    ax.set_ylabel("Risk (error rate among auto-signed)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold", color=COLORS["white"])
    ax.legend(loc="upper right", fontsize=9, framealpha=0.3)
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3)
    ax.invert_xaxis()  # higher coverage = lower threshold = left

    plt.tight_layout()
    path = save_path or "/tmp/proofdesk/risk_coverage.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_reliability_diagram(
    confidences: np.ndarray,
    correct: np.ndarray,
    method_name: str = "Raw Confidence",
    save_path: str | None = None,
) -> str:
    """Plot calibration reliability diagram."""
    n_bins = 12
    bin_boundaries = np.linspace(0, 1, n_bins + 1)

    bin_confs = []
    bin_accs = []
    bin_counts = []

    for i in range(n_bins):
        mask = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
        if mask.sum() > 0:
            bin_confs.append(confidences[mask].mean())
            bin_accs.append(correct[mask].mean())
            bin_counts.append(mask.sum())

    bin_confs = np.array(bin_confs)
    bin_accs = np.array(bin_accs)
    bin_counts = np.array(bin_counts)

    fig, ax = plt.subplots(figsize=(8, 6))

    # Perfect calibration line
    ax.plot([0, 1], [0, 1], "--", color=COLORS["gray"], linewidth=1.5, label="Perfectly calibrated")

    # Bar chart
    bar_width = 0.06
    bars = ax.bar(bin_confs, bin_accs, width=bar_width, color=COLORS["blue"],
                  alpha=0.7, edgecolor=COLORS["cyan"], linewidth=0.5)

    # Add count labels
    for bc, ba, cnt in zip(bin_confs, bin_accs, bin_counts):
        ax.text(bc, ba + 0.02, f"n={cnt}", ha="center", va="bottom",
                fontsize=7, color=COLORS["gray"])

    # Gap lines
    for bc, ba in zip(bin_confs, bin_accs):
        ax.plot([bc, bc], [min(bc, ba), max(bc, ba)],
                color=COLORS["red"], linewidth=1, alpha=0.6)

    ax.set_xlabel("Mean predicted confidence", fontsize=12)
    ax.set_ylabel("Actual accuracy", fontsize=12)
    ax.set_title(f"Reliability Diagram — {method_name}", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = save_path or f"/tmp/proofdesk/reliability_{method_name.lower().replace(' ', '_')}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_threshold_landscape(
    threshold_results: list[dict],
    method_name: str = "",
    save_path: str | None = None,
) -> str:
    """Plot threshold optimization landscape."""
    thresholds = [r["threshold"] for r in threshold_results]
    coverages = [r["coverage"] for r in threshold_results]
    risks = [r["risk"] for r in threshold_results]
    fnrs = [r["false_negative_rate"] for r in threshold_results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: Coverage + Risk vs Threshold
    ax1.plot(thresholds, coverages, color=COLORS["blue"], linewidth=2, label="Coverage")
    ax1.plot(thresholds, risks, color=COLORS["red"], linewidth=2, label="Risk")
    ax1.fill_between(thresholds, risks, alpha=0.15, color=COLORS["red"])

    # Find optimal: max(coverage) where risk <= target
    target_risk = 0.1
    valid = [r for r in threshold_results if r["risk"] <= target_risk]
    if valid:
        best = max(valid, key=lambda x: x["coverage"])
        ax1.axvline(best["threshold"], color=COLORS["green"], linestyle="--",
                     alpha=0.7, label=f"Optimal τ={best['threshold']:.2f}")

    ax1.set_xlabel("Threshold (τ)")
    ax1.set_ylabel("Score")
    ax1.set_title(f"Coverage & Risk vs Threshold — {method_name}")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.2)

    # Right: False Negative Rate vs Threshold
    ax2.plot(thresholds, fnrs, color=COLORS["orange"], linewidth=2)
    ax2.fill_between(thresholds, fnrs, alpha=0.15, color=COLORS["orange"])
    ax2.set_xlabel("Threshold (τ)")
    ax2.set_ylabel("False Negative Rate")
    ax2.set_title("Missed Safe Documents vs Threshold")
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    path = save_path or f"/tmp/proofdesk/threshold_{method_name.lower().replace(' ', '_')}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_per_world_comparison(
    world_metrics: dict[str, dict[str, float]],
    save_path: str | None = None,
) -> str:
    """Plot comparison across hard world families.

    world_metrics: {world_name: {metric_name: value}}
    """
    worlds = list(world_metrics.keys())
    metric_names = list(next(iter(world_metrics.values())).keys())

    n_metrics = len(metric_names)
    fig, axes = plt.subplots(1, n_metrics, figsize=(4 * n_metrics, 5))
    if n_metrics == 1:
        axes = [axes]

    for ax, metric in zip(axes, metric_names):
        values = [world_metrics[w].get(metric, 0) for w in worlds]
        colors = [COLORS["green"] if v > 0.7 else COLORS["orange"] if v > 0.4 else COLORS["red"]
                  for v in values]

        bars = ax.barh(worlds, values, color=colors, alpha=0.8, edgecolor="white", linewidth=0.3)
        ax.set_xlim(0, 1)
        ax.set_title(metric.upper(), fontsize=10, fontweight="bold")
        ax.grid(True, alpha=0.2, axis="x")

        for bar, val in zip(bars, values):
            ax.text(val + 0.02, bar.get_y() + bar.get_height() / 2,
                    f"{val:.3f}", va="center", fontsize=8, color=COLORS["white"])

    fig.suptitle("Performance by Hard World Family", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = save_path or "/tmp/proofdesk/per_world.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_calibration_convergence(
    online_scores: list[float],
    title: str = "MARGIN Online Calibration Convergence",
    save_path: str | None = None,
) -> str:
    """Plot how online calibration converges over time."""
    fig, ax = plt.subplots(figsize=(10, 5))

    x = list(range(1, len(online_scores) + 1))
    ax.plot(x, online_scores, color=COLORS["cyan"], linewidth=1.5, alpha=0.7)

    # Rolling average
    window = min(50, len(online_scores) // 5)
    if window > 1:
        rolling = np.convolve(online_scores, np.ones(window) / window, mode="valid")
        ax.plot(range(window, len(online_scores) + 1), rolling,
                color=COLORS["green"], linewidth=2.5, label=f"Rolling avg (w={window})")

    ax.axhline(0.5, color=COLORS["gray"], linestyle="--", alpha=0.5, label="Random baseline")
    ax.set_xlabel("Document #")
    ax.set_ylabel("Calibrated Confidence")
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    path = save_path or "/tmp/proofdesk/convergence.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_optimization_evolution(
    generations: list[int],
    scores: list[float],
    auto_rates: list[float],
    risk_rates: list[float],
    title: str = "Optimization Evolution",
    save_path: str | None = None,
) -> str:
    """Plot cogym-style optimization evolution."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: Score evolution
    ax1.plot(generations, scores, color=COLORS["blue"], linewidth=2, marker="o", markersize=4)
    ax1.fill_between(generations, scores, alpha=0.15, color=COLORS["blue"])
    ax1.set_xlabel("Generation")
    ax1.set_ylabel("Composite Score")
    ax1.set_title(f"Score Evolution — {title}")
    ax1.grid(True, alpha=0.2)

    # Annotate best
    best_idx = np.argmax(scores)
    ax1.annotate(f"Best: {scores[best_idx]:.3f}",
                 xy=(generations[best_idx], scores[best_idx]),
                 xytext=(generations[best_idx] + 5, scores[best_idx] - 0.05),
                 arrowprops=dict(arrowstyle="->", color=COLORS["green"]),
                 fontsize=9, color=COLORS["green"])

    # Right: Auto-sign rate vs Risk rate
    ax2.plot(auto_rates, risk_rates, color=COLORS["purple"], linewidth=2, marker="s", markersize=4)
    ax2.set_xlabel("Auto-Sign Rate (coverage)")
    ax2.set_ylabel("Risk (error rate)")
    ax2.set_title("Auto-Sign Rate vs Risk Tradeoff")
    ax2.grid(True, alpha=0.2)

    # Mark progression
    n = len(auto_rates)
    for i in range(0, n, max(1, n // 5)):
        ax2.annotate(f"g{i}", (auto_rates[i], risk_rates[i]),
                     fontsize=7, color=COLORS["gray"])

    plt.tight_layout()
    path = save_path or "/tmp/proofdesk/evolution.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def plot_methods_comparison(
    metrics_by_method: dict[str, dict[str, float]],
    save_path: str | None = None,
) -> str:
    """Bar chart comparing all calibration methods."""
    methods = list(metrics_by_method.keys())
    metric_names = ["ece", "brier", "bas", "aurc"]

    fig, axes = plt.subplots(1, len(metric_names), figsize=(4 * len(metric_names), 5))
    if len(metric_names) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metric_names):
        values = [metrics_by_method[m].get(metric, 0) for m in methods]
        is_lower_better = metric in ("ece", "brier", "aurc")

        if is_lower_better:
            colors = [COLORS["green"] if v == min(values) else COLORS["blue"] for v in values]
        else:
            colors = [COLORS["green"] if v == max(values) else COLORS["blue"] for v in values]

        bars = ax.bar(methods, values, color=colors, alpha=0.8, edgecolor="white", linewidth=0.3)
        ax.set_title(metric.upper(), fontsize=11, fontweight="bold")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(True, alpha=0.2, axis="y")

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.005,
                    f"{val:.3f}", ha="center", fontsize=8, color=COLORS["white"])

    fig.suptitle("Calibration Methods Comparison", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = save_path or "/tmp/proofdesk/methods_comparison.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path
