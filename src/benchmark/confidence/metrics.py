"""Metrics for confidence calibration and signing decisions.

Core metrics:
  - ECE (Expected Calibration Error)
  - MCE (Maximum Calibration Error)
  - Brier Score
  - BAS (Behavioral Alignment Score)
  - AURC (Area Under Risk-Coverage curve)
  - Risk-coverage curve data
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field


@dataclass
class CalibrationMetrics:
    """Complete calibration report."""
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    brier: float  # Brier Score
    bas: float  # Behavioral Alignment Score
    aurc: float  # Area Under Risk-Coverage curve
    accuracy: float
    n_docs: int
    # Risk-coverage curve data
    risk_coverage_curve: list[tuple[float, float, float]] = field(default_factory=list)
    # Per-threshold metrics
    threshold_analysis: list[dict] = field(default_factory=list)


def expected_calibration_error(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_bins: int = 15,
) -> tuple[float, float]:
    """Compute ECE and MCE.

    Returns (ece, mce).
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n = len(confidences)

    for i in range(n_bins):
        mask = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_conf = confidences[mask].mean()
        bin_acc = correct[mask].mean()
        bin_weight = mask.sum() / n
        ece += bin_weight * abs(bin_acc - bin_conf)
        mce = max(mce, abs(bin_acc - bin_conf))

    return ece, mce


def brier_score(confidences: np.ndarray, correct: np.ndarray) -> float:
    """Compute Brier Score (lower is better, 0 is perfect)."""
    return float(np.mean((confidences - correct.astype(float)) ** 2))


def behavioral_alignment_score(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_risk_levels: int = 50,
) -> float:
    """Compute BAS (Behavioral Alignment Score).

    BAS balances calibration with decision-making utility across
    risk levels. Higher is better.

    From "BAS: A Decision-Theoretic Approach to Evaluating LLM Confidence"
    (Wu et al., 2026).
    """
    thresholds = np.linspace(0.05, 0.95, n_risk_levels)
    utilities = []

    for tau in thresholds:
        # u_ca = normalized net utility of correctly abstaining from incorrect
        # For signing: u_ca = tau (higher risk = more credit for abstaining)
        u_ca = tau

        # At threshold tau, we sign if confidence >= tau
        sign_mask = confidences >= tau
        abstain_mask = ~sign_mask

        n_sign = sign_mask.sum()
        n_abstain = abstain_mask.sum()

        if n_sign + n_abstain == 0:
            continue

        # Utility of signing: +1 if correct, -u_ca if incorrect
        if n_sign > 0:
            sign_correct = correct[sign_mask].sum()
            sign_incorrect = n_sign - sign_correct
            u_sign = (sign_correct * 1.0 - sign_incorrect * u_ca) / len(correct)
        else:
            u_sign = 0.0

        # Utility of abstaining: +u_ca if was incorrect (correctly avoided error)
        if n_abstain > 0:
            abstain_was_incorrect = (1 - correct[abstain_mask]).sum()
            u_abstain = (abstain_was_incorrect * u_ca) / len(correct)
        else:
            u_abstain = 0.0

        utilities.append(u_sign + u_abstain)

    # Normalize by oracle utility
    oracle_utility = 1.0  # perfect signer gets full credit
    return float(np.mean(utilities) / oracle_utility) if utilities else 0.0


def risk_coverage_curve(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_thresholds: int = 100,
) -> list[tuple[float, float, float]]:
    """Compute risk-coverage curve.

    Returns list of (threshold, coverage, risk) tuples.
    Coverage = fraction of docs above threshold (auto-signed).
    Risk = error rate among auto-signed docs.
    """
    curve = []
    thresholds = np.linspace(0, 1, n_thresholds)

    for tau in thresholds:
        mask = confidences >= tau
        coverage = mask.mean()
        if coverage == 0:
            risk = 0.0
        else:
            risk = 1.0 - correct[mask].mean()
        curve.append((float(tau), float(coverage), float(risk)))

    return curve


def area_under_risk_coverage(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_thresholds: int = 100,
) -> float:
    """Compute AURC (Area Under Risk-Coverage curve).

    Lower is better. Integrates risk over coverage from 0 to 1.
    """
    curve = risk_coverage_curve(confidences, correct, n_thresholds)
    coverages = [c[1] for c in curve]
    risks = [c[2] for c in curve]

    # Trapezoidal integration — coverage goes from 1 to 0
    # We integrate risk over coverage from 0 to 1 (left to right on the curve)
    # So we need to reverse the arrays
    coverages_arr = np.array(coverages[::-1])  # 0 to 1
    risks_arr = np.array(risks[::-1])  # corresponding risk values
    aurc = float(np.trapezoid(risks_arr, coverages_arr))
    return max(0.0, aurc)  # AURC should be non-negative


def threshold_analysis(
    confidences: np.ndarray,
    correct: np.ndarray,
    n_thresholds: int = 20,
) -> list[dict]:
    """Analyze metrics at different thresholds."""
    results = []
    thresholds = np.linspace(0.1, 0.95, n_thresholds)

    for tau in thresholds:
        mask = confidences >= tau
        coverage = mask.mean()
        if coverage == 0:
            continue

        accepted = correct[mask]
        n_accepted = len(accepted)
        accuracy = accepted.mean()
        risk = 1.0 - accuracy

        # False negative rate: docs we rejected that were actually safe
        reject_mask = confidences < tau
        n_rejected_safe = correct[reject_mask].sum() if reject_mask.sum() > 0 else 0
        n_total_safe = correct.sum()
        fnr = n_rejected_safe / n_total_safe if n_total_safe > 0 else 0.0

        results.append({
            "threshold": float(tau),
            "coverage": float(coverage),
            "risk": float(risk),
            "accuracy": float(accuracy),
            "n_accepted": int(n_accepted),
            "n_rejected": int((~mask).sum()),
            "false_negative_rate": float(fnr),
        })

    return results


def compute_all_metrics(
    confidences: np.ndarray,
    correct: np.ndarray,
) -> CalibrationMetrics:
    """Compute complete calibration metrics."""
    ece, mce = expected_calibration_error(confidences, correct)
    brier = brier_score(confidences, correct)
    bas = behavioral_alignment_score(confidences, correct)
    aurc = area_under_risk_coverage(confidences, correct)
    accuracy = correct.mean()
    curve = risk_coverage_curve(confidences, correct)
    thresh = threshold_analysis(confidences, correct)

    return CalibrationMetrics(
        ece=ece,
        mce=mce,
        brier=brier,
        bas=bas,
        aurc=aurc,
        accuracy=float(accuracy),
        n_docs=len(confidences),
        risk_coverage_curve=curve,
        threshold_analysis=thresh,
    )
