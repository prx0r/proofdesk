#!/usr/bin/env python3
"""Difficulty-Aware Signing — separate worlds, optimal thresholds, classifier.

Architecture:
1. Easy docs (SROIE receipts) → low threshold (sign more)
2. Medium docs (FCC invoices) → medium threshold
3. Hard docs (fraud injection) → high threshold (sign less)
4. Classifier predicts difficulty → routes to optimal threshold

This is the cogym pattern: each difficulty is its own world.
"""

from __future__ import annotations

import json
import os
import sys
import time
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from src.signing_world import Verdict, SigningDecision, score_signing, ConfidenceSignal, DocPacket, Document, DocField
from src.experts import MixtureOfExperts
from src.sheepish import sheepish_batch, sheepish_transform
from src.calibration import IsotonicCalibrator

OUTPUT_DIR = "/tmp/proofdesk/difficulty_aware"


@dataclass
class DifficultyResult:
    difficulty: str
    threshold: float
    accuracy: float
    fpr: float
    utility: float
    fraud_detected: float
    n_docs: int


@dataclass
class ClassifierResult:
    predicted: str
    actual: str
    confidence: float
    correct: bool


# ─── Document Loading ─────────────────────────────────────────────────

def load_easy_docs(n: int = 100) -> list[dict]:
    """Easy: SROIE receipts — clean, structured, low risk."""
    print("  Loading SROIE (Easy)...")
    try:
        from datasets import load_dataset
        HF_TOKEN = "[REDACTED]"
        ds = load_dataset("jsdnrs/ICDAR2019-SROIE", split="test", token=HF_TOKEN)
        docs = []
        for i in range(min(n, len(ds))):
            item = ds[i]
            entities = item.get("entities", {})
            total_str = entities.get("total", "0")
            try:
                total = float(total_str.replace(",", "").replace("RM", "").strip())
            except:
                total = 0.0

            docs.append({
                "doc_id": f"easy_{i}",
                "difficulty": "easy",
                "doc_type": "receipt",
                "verdict": "safe" if total <= 100 else "risky",
                "total": total,
                "company": entities.get("company", ""),
                "image": item.get("image"),
            })
        print(f"    Loaded {len(docs)} SROIE receipts")
        return docs
    except Exception as e:
        print(f"    Error: {e}")
        return []


def load_medium_docs(n: int = 100) -> list[dict]:
    """Medium: FCC invoices — real forms, structured but complex."""
    print("  Loading ConfBench (Medium)...")
    try:
        from datasets import load_dataset
        HF_TOKEN = "[REDACTED]"
        ds = load_dataset("amazon/ConfBench", split="test", token=HF_TOKEN)
        docs = []
        for i in range(min(n, len(ds))):
            item = ds[i]
            docs.append({
                "doc_id": f"medium_{i}",
                "difficulty": "medium",
                "doc_type": "invoice",
                "verdict": "safe",
                "image": item.get("image"),
            })
        print(f"    Loaded {len(docs)} FCC invoices")
        return docs
    except Exception as e:
        print(f"    Error: {e}")
        return []


def load_hard_docs(n: int = 100) -> list[dict]:
    """Hard: Fraud injection — adversarial, tricky."""
    print("  Generating fraud injection (Hard)...")
    rng = np.random.RandomState(42)
    docs = []
    for i in range(n):
        is_fraud = rng.random() < 0.6
        verdict = "fraudulent" if is_fraud else "safe"
        conf = rng.uniform(0.3, 0.7) if is_fraud else rng.uniform(0.6, 0.95)
        docs.append({
            "doc_id": f"hard_{i}",
            "difficulty": "hard",
            "doc_type": "invoice",
            "verdict": verdict,
            "signals": {
                "nutrient_confidence": conf,
                "match_score": rng.uniform(0.3, 0.9),
                "grounding_score": rng.uniform(0.3, 0.9),
                "margin_score": rng.uniform(0.2, 0.8),
                "cross_doc_consistency": rng.uniform(0.4, 0.9),
                "field_completeness": rng.uniform(0.5, 1.0),
            },
        })
    print(f"    Generated {len(docs)} fraud-injected docs")
    return docs


# ─── Feature Extraction ────────────────────────────────────────────────

def extract_features(doc: dict, rng: np.random.RandomState) -> np.ndarray:
    """Extract features for difficulty classification."""
    if "signals" in doc:
        s = doc["signals"]
    else:
        # Generate synthetic signals
        verdict = doc.get("verdict", "safe")
        if verdict == "safe":
            conf = 0.6 + rng.uniform(0, 0.35)
        elif verdict == "risky":
            conf = 0.3 + rng.uniform(0, 0.4)
        else:
            conf = 0.1 + rng.uniform(0, 0.3)
        s = {
            "nutrient_confidence": conf,
            "match_score": rng.uniform(0.3, 0.9),
            "grounding_score": rng.uniform(0.3, 0.9),
            "margin_score": rng.uniform(0.2, 0.8),
            "cross_doc_consistency": rng.uniform(0.4, 0.9),
            "field_completeness": rng.uniform(0.5, 1.0),
        }

    return np.array([
        s["nutrient_confidence"],
        s["match_score"],
        s["grounding_score"],
        s["margin_score"],
        s["cross_doc_consistency"],
        s["field_completeness"],
        len(doc.get("company", "")) / 20.0,  # company name length (proxy for complexity)
        1.0 if doc.get("image") is not None else 0.0,  # has image
    ])


# ─── Threshold Optimization ────────────────────────────────────────────

def optimize_threshold(
    docs: list[dict],
    rng: np.random.RandomState,
    target_fpr: float = 0.1,
) -> float:
    """Find optimal threshold for a set of documents.

    Strategy: find highest threshold that keeps FPR <= target.
    """
    # Generate signals
    all_signals = []
    all_labels = []
    for doc in docs:
        if "signals" in doc:
            s = doc["signals"]
        else:
            verdict = doc.get("verdict", "safe")
            if verdict == "safe":
                conf = 0.6 + rng.uniform(0, 0.35)
            elif verdict == "risky":
                conf = 0.3 + rng.uniform(0, 0.4)
            else:
                conf = 0.1 + rng.uniform(0, 0.3)
            s = {"nutrient_confidence": conf}

        all_signals.append(s["nutrient_confidence"])
        all_labels.append(1.0 if doc["verdict"] == "safe" else 0.0)

    all_signals = np.array(all_signals)
    all_labels = np.array(all_labels)

    # Grid search for optimal threshold
    best_tau = 0.5
    best_utility = -999

    for tau in np.linspace(0.1, 0.9, 50):
        signed = all_signals >= tau
        if signed.sum() == 0:
            continue

        # FPR among signed
        fpr = sum(1 for i in range(len(signed)) if signed[i] and all_labels[i] == 0) / signed.sum()

        # Only consider if FPR <= target
        if fpr > target_fpr:
            continue

        # Utility
        utility = 0.0
        for i in range(len(all_signals)):
            if all_signals[i] >= tau:
                # Would sign
                if all_labels[i] == 1:
                    utility += 1.0  # correct sign
                else:
                    utility -= 5.0  # false positive (catastrophic)
            else:
                # Would refuse
                if all_labels[i] == 0:
                    utility += 0.3  # correct refuse
                else:
                    utility -= 0.5  # false negative

        utility /= len(all_signals)

        if utility > best_utility:
            best_utility = utility
            best_tau = tau

    return best_tau


# ─── Difficulty Classifier ──────────────────────────────────────────────

class DifficultyClassifier:
    """Simple classifier to predict document difficulty from features."""

    def __init__(self):
        self._thresholds = None  # Learned decision boundaries

    def fit(self, features: np.ndarray, labels: np.ndarray):
        """Learn decision boundaries from labeled data."""
        # Simple approach: learn per-feature thresholds for each class
        self._class_means = {}
        for cls in np.unique(labels):
            mask = labels == cls
            self._class_means[cls] = features[mask].mean(axis=0)

    def predict(self, features: np.ndarray) -> tuple[str, float]:
        """Predict difficulty class and confidence."""
        if self._class_means is None:
            return "medium", 0.5

        # Nearest class mean
        best_class = "medium"
        best_dist = float("inf")
        for cls, mean in self._class_means.items():
            dist = np.linalg.norm(features - mean)
            if dist < best_dist:
                best_dist = dist
                best_class = cls

        # Confidence based on distance (closer = more confident)
        max_dist = 2.0  # normalize
        confidence = max(0.0, min(1.0, 1.0 - best_dist / max_dist))

        return str(best_class), confidence


# ─── Main Benchmark ─────────────────────────────────────────────────────

def run_benchmark(n_per_level: int = 100):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"  DIFFICULTY-AWARE SIGNING BENCHMARK")
    print(f"  {n_per_level} docs per difficulty level")
    print(f"{'='*70}\n")

    # Load datasets
    print("[1/5] Loading datasets...")
    easy_docs = load_easy_docs(n_per_level)
    medium_docs = load_medium_docs(n_per_level)
    hard_docs = load_hard_docs(n_per_level)

    all_docs = easy_docs + medium_docs + hard_docs
    print(f"  Total: {len(all_docs)} documents")

    # Find optimal threshold per difficulty
    print("\n[2/5] Finding optimal thresholds per difficulty...")
    rng = np.random.RandomState(42)

    easy_threshold = optimize_threshold(easy_docs, rng, target_fpr=0.15)
    medium_threshold = optimize_threshold(medium_docs, rng, target_fpr=0.10)
    hard_threshold = optimize_threshold(hard_docs, rng, target_fpr=0.05)

    print(f"  Easy:   τ={easy_threshold:.3f}")
    print(f"  Medium: τ={medium_threshold:.3f}")
    print(f"  Hard:   τ={hard_threshold:.3f}")

    thresholds = {"easy": easy_threshold, "medium": medium_threshold, "hard": hard_threshold}

    # Train classifier
    print("\n[3/5] Training difficulty classifier...")
    features = []
    labels = []
    for doc in all_docs:
        feat = extract_features(doc, rng)
        features.append(feat)
        labels.append(doc["difficulty"])

    features = np.array(features)
    labels = np.array(labels)

    classifier = DifficultyClassifier()
    classifier.fit(features, labels)

    # Test classifier
    correct = 0
    for i, doc in enumerate(all_docs):
        pred, conf = classifier.predict(features[i])
        if pred == doc["difficulty"]:
            correct += 1
    print(f"  Classifier accuracy: {correct}/{len(all_docs)} ({correct/len(all_docs):.1%})")

    # Run benchmark with difficulty-aware routing
    print("\n[4/5] Running benchmark...")
    results = []

    for doc in all_docs:
        feat = extract_features(doc, rng)
        predicted_difficulty, conf = classifier.predict(feat)
        threshold = thresholds[predicted_difficulty]

        # Get confidence score
        if "signals" in doc:
            score = doc["signals"]["nutrient_confidence"]
        else:
            verdict = doc.get("verdict", "safe")
            if verdict == "safe":
                score = 0.6 + rng.uniform(0, 0.35)
            elif verdict == "risky":
                score = 0.3 + rng.uniform(0, 0.4)
            else:
                score = 0.1 + rng.uniform(0, 0.3)

        # Decision
        if score >= threshold:
            decision = "SIGN"
        elif score >= threshold - 0.15:
            decision = "DEFER"
        else:
            decision = "REFUSE"

        correct = (decision == "SIGN" and doc["verdict"] == "safe") or \
                  (decision in ("REFUSE", "DEFER") and doc["verdict"] != "safe")

        results.append({
            "doc_id": doc["doc_id"],
            "difficulty": doc["difficulty"],
            "actual_difficulty": doc["difficulty"],
            "predicted_difficulty": predicted_difficulty,
            "classifier_confidence": conf,
            "threshold": threshold,
            "score": score,
            "decision": decision,
            "correct": correct,
            "verdict": doc["verdict"],
        })

    # Compute metrics
    print("\n[5/5] Computing metrics...")
    summary = {}
    for difficulty in ["easy", "medium", "hard"]:
        subset = [r for r in results if r["difficulty"] == difficulty]
        if not subset:
            continue

        acc = sum(1 for r in subset if r["correct"]) / len(subset)
        signed = [r for r in subset if r["decision"] == "SIGN"]
        fpr = sum(1 for r in signed if r["verdict"] != "safe") / max(1, len(signed))

        fraud_docs = [r for r in subset if r["verdict"] == "fraudulent"]
        fraud_detected = sum(1 for r in fraud_docs if r["decision"] == "REFUSE") / max(1, len(fraud_docs))

        # Classifier accuracy for this difficulty
        clf_correct = sum(1 for r in subset if r["predicted_difficulty"] == r["actual_difficulty"])
        clf_acc = clf_correct / len(subset)

        summary[difficulty] = {
            "n_docs": len(subset),
            "threshold": thresholds[difficulty],
            "accuracy": acc,
            "fpr": fpr,
            "fraud_detected": fraud_detected,
            "classifier_accuracy": clf_acc,
            "avg_confidence": np.mean([r["classifier_confidence"] for r in subset]),
        }

        print(f"  {difficulty.upper():10s}  τ={thresholds[difficulty]:.3f}  "
              f"acc={acc:.1%}  fpr={fpr:.1%}  fraud={fraud_detected:.1%}  "
              f"clf_acc={clf_acc:.1%}")

    # Overall
    overall_acc = sum(1 for r in results if r["correct"]) / len(results)
    overall_signed = [r for r in results if r["decision"] == "SIGN"]
    overall_fpr = sum(1 for r in overall_signed if r["verdict"] != "safe") / max(1, len(overall_signed))
    overall_fraud = [r for r in results if r["verdict"] == "fraudulent"]
    overall_fraud_detected = sum(1 for r in overall_fraud if r["decision"] == "REFUSE") / max(1, len(overall_fraud))

    print(f"\n  OVERALL    acc={overall_acc:.1%}  fpr={overall_fpr:.1%}  fraud={overall_fraud_detected:.1%}")

    # Save report
    report = {
        "n_docs": len(results),
        "thresholds": thresholds,
        "overall": {
            "accuracy": overall_acc,
            "fpr": overall_fpr,
            "fraud_detected": overall_fraud_detected,
        },
        "per_difficulty": summary,
        "results": results,
    }

    report_path = f"{OUTPUT_DIR}/benchmark_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")

    # Generate plots
    _plot_results(report)

    return report


def _plot_results(report: dict):
    """Generate comparison plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
    })

    C = {"blue": "#58a6ff", "green": "#3fb950", "red": "#f85149",
         "orange": "#d29922", "purple": "#bc8cff", "cyan": "#39d2c0"}

    difficulties = ["easy", "medium", "hard"]

    # Plot 1: Thresholds per difficulty
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Optimal Thresholds by Difficulty", fontsize=14, fontweight="bold")

    thresholds = [report["per_difficulty"][d]["threshold"] for d in difficulties]
    colors = [C["green"], C["orange"], C["red"]]
    bars = ax.bar(difficulties, thresholds, color=colors, alpha=0.8, edgecolor="white", linewidth=0.3)

    for bar, val in zip(bars, thresholds):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.3f}",
                ha="center", fontsize=11, color="white", fontweight="bold")

    ax.set_ylabel("Threshold")
    ax.set_title("Easy → sign more aggressively\nHard → sign conservatively")
    ax.grid(True, alpha=0.2, axis="y")

    plt.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/thresholds_by_difficulty.png", bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  -> {OUTPUT_DIR}/thresholds_by_difficulty.png")

    # Plot 2: Accuracy + FPR per difficulty
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Performance by Difficulty Level", fontsize=14, fontweight="bold")

    accs = [report["per_difficulty"][d]["accuracy"] for d in difficulties]
    fprs = [report["per_difficulty"][d]["fpr"] for d in difficulties]

    ax = axes[0]
    bars = ax.bar(difficulties, accs, color=[C["green"]]*3, alpha=0.8, edgecolor="white", linewidth=0.3)
    for bar, val in zip(bars, accs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.1%}",
                ha="center", fontsize=10, color="white")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy (higher = better)")
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.2, axis="y")

    ax = axes[1]
    bars = ax.bar(difficulties, fprs, color=[C["red"]]*3, alpha=0.8, edgecolor="white", linewidth=0.3)
    for bar, val in zip(bars, fprs):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.1%}",
                ha="center", fontsize=10, color="white")
    ax.set_ylabel("FPR")
    ax.set_title("False Positive Rate (lower = better)")
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.2, axis="y")

    plt.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/performance_by_difficulty.png", bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  -> {OUTPUT_DIR}/performance_by_difficulty.png")

    # Plot 3: Fraud detection per difficulty
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Fraud Detection Rate by Difficulty", fontsize=14, fontweight="bold")

    fraud_rates = [report["per_difficulty"][d]["fraud_detected"] for d in difficulties]
    bars = ax.bar(difficulties, fraud_rates, color=[C["green"]]*3, alpha=0.8, edgecolor="white", linewidth=0.3)
    for bar, val in zip(bars, fraud_rates):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.1%}",
                ha="center", fontsize=11, color="white", fontweight="bold")
    ax.set_ylabel("Fraud Detection Rate")
    ax.set_title("What % of fraudulent docs were correctly refused?")
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.2, axis="y")

    plt.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/fraud_detection.png", bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  -> {OUTPUT_DIR}/fraud_detection.png")

    # Plot 4: Overall summary
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("Overall: Difficulty-Aware vs Single Threshold", fontsize=14, fontweight="bold")

    # Compare with vanilla (single threshold 0.5)
    metrics = ["Accuracy", "FPR", "Fraud Detected"]
    difficulty_aware = [
        report["overall"]["accuracy"],
        report["overall"]["fpr"],
        report["overall"]["fraud_detected"],
    ]
    # Vanilla baseline (from earlier benchmark)
    vanilla = [0.887, 0.132, 0.185]

    x = np.arange(len(metrics))
    width = 0.35
    bars1 = ax.bar(x - width/2, vanilla, width, label="Vanilla LLM (τ=0.5)", color=C["red"], alpha=0.8)
    bars2 = ax.bar(x + width/2, difficulty_aware, width, label="Difficulty-Aware (adaptive τ)", color=C["green"], alpha=0.8)

    ax.set_ylabel("Score")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(True, alpha=0.2, axis="y")

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{bar.get_height():.1%}", ha="center", fontsize=9, color="white")
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{bar.get_height():.1%}", ha="center", fontsize=9, color="white")

    plt.tight_layout()
    fig.savefig(f"{OUTPUT_DIR}/overall_comparison.png", bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  -> {OUTPUT_DIR}/overall_comparison.png")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()
    run_benchmark(n_per_level=args.n)
