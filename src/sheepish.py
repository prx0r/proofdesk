"""Sheepish Confidence Metric — penalizes overconfidence more than underconfidence.

Inspired by DUD (2026) "Humble Truths vs Stubborn Errors":
- Overconfident errors are catastrophic (signed but wrong = -5.0 utility)
- Underconfident truths are recoverable (refused but safe = -0.5 utility)
- The sheepish transformation amplifies this asymmetry in the confidence score
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class SheepishResult:
    """Result of sheepish transformation."""
    original: float
    sheepish: float
    penalty: float
    reason: str


def sheepish_transform(
    score: float,
    match_score: float = 1.0,
    grounding_score: float = 1.0,
    field_accuracy: float = 1.0,
    overconfidence_threshold: float = 0.95,
) -> SheepishResult:
    """Transform a confidence score using sheepish logic.

    Overconfidence penalty: gap^1.2 (superlinear — stubborn errors punished hard)
    Humility bonus: gap^0.7 (sublinear — humble truths rewarded less)
    Signal quality modulation: weak signals amplify the correction.
    """
    # Signal quality factor (0-1)
    signal_quality = 0.4 * match_score + 0.3 * grounding_score + 0.3 * field_accuracy

    if score >= overconfidence_threshold:
        # Overconfident: penalize
        gap = score - overconfidence_threshold
        penalty = -(gap ** 1.2) * (0.5 + 0.5 * signal_quality)

        # Extra penalty for very overconfident
        if gap > 0.05:
            penalty *= 0.7  # strong penalty for stubborn errors

        sheepish = max(0.0, score + penalty)
        reason = f"overconfident (gap={gap:.3f}, signal_quality={signal_quality:.2f})"
    else:
        # Underconfident or well-calibrated: small bonus
        gap = overconfidence_threshold - score
        bonus = (gap ** 0.7) * 0.1 * signal_quality

        # Extra bonus for humble truths with good signals
        if gap > 0.1 and match_score > 0.5:
            bonus += 0.05

        sheepish = min(1.0, score + bonus)
        reason = f"{'humble' if gap > 0.1 else 'calibrated'} (gap={gap:.3f}, signal_quality={signal_quality:.2f})"

    return SheepishResult(
        original=score,
        sheepish=sheepish,
        penalty=penalty if score >= overconfidence_threshold else bonus,
        reason=reason,
    )


def sheepish_array(
    scores: np.ndarray,
    match_scores: np.ndarray | None = None,
    grounding_scores: np.ndarray | None = None,
    field_accuracies: np.ndarray | None = None,
) -> np.ndarray:
    """Apply sheepish transformation to an array of scores."""
    n = len(scores)
    if match_scores is None:
        match_scores = np.ones(n)
    if grounding_scores is None:
        grounding_scores = np.ones(n)
    if field_accuracies is None:
        field_accuracies = np.ones(n)

    results = [
        sheepish_transform(s, m, g, f)
        for s, m, g, f in zip(scores, match_scores, grounding_scores, field_accuracies)
    ]
    return np.array([r.sheepish for r in results])


def compare_strategies(scores, labels, match_scores=None, grounding_scores=None):
    """Compare Raw vs Sheepish vs Isotonic vs Platt on real data.

    Returns dict with ECE and Brier for each method.
    """
    from src.benchmark.confidence.calibration import IsotonicCalibrator, PlattScaler
    from src.benchmark.confidence.metrics import expected_calibration_error, brier_score

    scores_arr = np.array(scores)
    labels_arr = np.array(labels, dtype=float)

    results = {}

    # Raw
    ece, _ = expected_calibration_error(scores_arr, labels_arr)
    brier = brier_score(scores_arr, labels_arr)
    results["Raw"] = {"ece": ece, "brier": brier, "scores": scores_arr.tolist()}

    # Sheepish
    sheepish_scores = sheepish_array(
        scores_arr,
        match_scores=np.array(match_scores) if match_scores else None,
        grounding_scores=np.array(grounding_scores) if grounding_scores else None,
    )
    ece, _ = expected_calibration_error(sheepish_scores, labels_arr)
    brier = brier_score(sheepish_scores, labels_arr)
    results["Sheepish"] = {"ece": ece, "brier": brier, "scores": sheepish_scores.tolist()}

    # Isotonic
    iso = IsotonicCalibrator()
    iso.fit(scores_arr, labels_arr)
    iso_scores = np.array([iso.calibrate(s) for s in scores_arr])
    ece, _ = expected_calibration_error(iso_scores, labels_arr)
    brier = brier_score(iso_scores, labels_arr)
    results["Isotonic"] = {"ece": ece, "brier": brier, "scores": iso_scores.tolist()}

    # Platt
    platt = PlattScaler()
    platt.fit(scores_arr, labels_arr)
    platt_scores = np.array([platt.calibrate(s) for s in scores_arr])
    ece, _ = expected_calibration_error(platt_scores, labels_arr)
    brier = brier_score(platt_scores, labels_arr)
    results["Platt"] = {"ece": ece, "brier": brier, "scores": platt_scores.tolist()}

    return results
