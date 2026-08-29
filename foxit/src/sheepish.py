"""Sheepish Confidence Metric — asymmetric shrinkage from decision theory.

Inspired by BAS paper (Wu et al., 2026): overconfidence is more costly
than underconfidence in high-stakes signing decisions.

What the code actually implements (Bayesian shrinkage, not loss minimization):
  Given raw confidence c and estimated accuracy a:
  - If c > a (overconfident): shrink c toward a via weighted average
    s* = (λ_over * c + λ_under * a) / (λ_over + λ_under)
  - If c <= a (underconfident): leave c unchanged

  The weights control shrinkage: higher λ_over means more shrinkage
  when overconfident. This is a shrinkage estimator, not the minimizer
  of the stated quadratic loss (the loss has no c term).

CRITICAL: estimated_accuracy must come from Nutrient extraction signals
(e.g., field completeness, match scores), NOT from ground truth labels.
Using ground truth = label leakage. Callers MUST pass signal-derived estimates.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class SheepishResult:
    """Result of sheepish confidence transformation."""
    raw_score: float
    sheepish_score: float
    calibration_delta: float
    overconfidence_penalty: float
    risk_adjustment: float


def estimate_accuracy_from_signals(
    nutrient_confidence: float,
    match_score: float,
    field_count: int,
    text_length: int,
) -> float:
    """Estimate field accuracy from Nutrient extraction signals.

    This is the CRITICAL function that prevents label leakage.
    It estimates accuracy from signals available at inference time,
    NOT from ground truth labels.

    Args:
        nutrient_confidence: Average Nutrient extraction confidence (0-1)
        match_score: Fraction of fields that match expected schema (0-1)
        field_count: Number of fields extracted
        text_length: Length of extracted text (normalized)

    Returns:
        Estimated accuracy (0-1)
    """
    # Weighted combination of available signals
    # Nutrient confidence is the strongest signal
    # Match score confirms structural correctness
    # Field count and text length are secondary
    estimated = (
        0.5 * nutrient_confidence +
        0.3 * match_score +
        0.1 * min(field_count / 10.0, 1.0) +
        0.1 * min(text_length / 500.0, 1.0)
    )
    return max(0.0, min(1.0, estimated))


def sheepish_transform(
    raw_confidence: float,
    estimated_accuracy: float = 0.5,
    match_score: float = 0.5,
    grounding_score: float = 0.5,
    lambda_over: float = 3.0,
    lambda_under: float = 1.0,
) -> SheepishResult:
    """Transform raw confidence into sheepish confidence.

    Bayesian shrinkage with asymmetric penalty:
    - Overconfident (c > a): shrink toward a, weighted by loss ratio
    - Underconfident (c <= a): leave c unchanged

    CRITICAL: estimated_accuracy must come from Nutrient signals
    (via estimate_accuracy_from_signals), NOT from ground truth.

    Args:
        raw_confidence: Raw model confidence (0-1)
        estimated_accuracy: Estimated accuracy from signals (0-1), NOT ground truth
        match_score: Nutrient match quality (0-1)
        grounding_score: NLI grounding score (0-1)
        lambda_over: Overconfidence penalty weight (higher = more shrinkage)
        lambda_under: Underconfidence penalty weight (lower = less shrinkage)
    """
    if raw_confidence > estimated_accuracy:
        # Overconfident: shrink toward estimated accuracy
        sheepish = (lambda_over * raw_confidence + lambda_under * estimated_accuracy) / (lambda_over + lambda_under)
        overconfidence_penalty = raw_confidence - sheepish
    else:
        # Underconfident: leave unchanged
        sheepish = raw_confidence
        overconfidence_penalty = 0.0

    # Signal quality adjustment: low quality → increase uncertainty
    signal_quality = 0.4 * match_score + 0.3 * grounding_score + 0.3 * estimated_accuracy
    risk_adjustment = (1 - signal_quality) * 0.1
    sheepish = max(0.0, min(1.0, sheepish - risk_adjustment))

    calibration_delta = sheepish - raw_confidence

    return SheepishResult(
        raw_score=raw_confidence,
        sheepish_score=sheepish,
        calibration_delta=calibration_delta,
        overconfidence_penalty=overconfidence_penalty,
        risk_adjustment=risk_adjustment,
    )


def sheepish_batch(
    raw_scores: np.ndarray,
    estimated_accuracies: np.ndarray,
    match_scores: np.ndarray,
    grounding_scores: np.ndarray,
    **kwargs,
) -> np.ndarray:
    """Batch sheepish transformation.

    CRITICAL: estimated_accuracies must come from Nutrient signals,
    NOT from ground truth labels.
    """
    results = [
        sheepish_transform(r, a, m, g, **kwargs)
        for r, a, m, g in zip(raw_scores, estimated_accuracies, match_scores, grounding_scores)
    ]
    return np.array([r.sheepish_score for r in results])


def compare_strategies(
    raw_scores: np.ndarray,
    correct_labels: np.ndarray,
    estimated_accuracies: np.ndarray,
    match_scores: np.ndarray,
    grounding_scores: np.ndarray,
) -> dict:
    """Compare Raw vs Sheepish vs Calibrated strategies.

    Uses proper calibration methods (isotonic, Platt) as baselines.
    CRITICAL: estimated_accuracies must come from Nutrient signals,
    NOT from ground truth labels.
    """
    from .metrics import expected_calibration_error, brier_score
    from .calibration import IsotonicCalibrator, PlattScaler

    n = len(raw_scores)
    split = int(0.5 * n)

    # Train calibrators on first half
    iso = IsotonicCalibrator()
    iso.fit(raw_scores[:split], correct_labels[:split])

    platt = PlattScaler()
    platt.fit(raw_scores[:split], correct_labels[:split])

    # Evaluate on second half
    test_raw = raw_scores[split:]
    test_correct = correct_labels[split:]
    test_est_acc = estimated_accuracies[split:]
    test_match = match_scores[split:]
    test_ground = grounding_scores[split:]

    sheepish_scores = sheepish_batch(test_raw, test_est_acc, test_match, test_ground)
    iso_scores = iso.calibrate_batch(test_raw)
    platt_scores = np.array([platt.calibrate(s) for s in test_raw])

    strategies = {
        "Raw": test_raw,
        "Sheepish": sheepish_scores,
        "Isotonic": iso_scores,
        "Platt": platt_scores,
    }

    results = {}
    for name, scores in strategies.items():
        ece, _ = expected_calibration_error(scores, test_correct)
        brier = brier_score(scores, test_correct)
        results[name] = {
            "ece": ece,
            "brier": brier,
            "mean_confidence": float(np.mean(scores)),
            "std_confidence": float(np.std(scores)),
        }

    return results
