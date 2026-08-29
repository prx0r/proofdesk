"""Calibration methods for confidence scores.

Implements:
  1. Isotonic regression (design-time, heldout calibration)
  2. Conformal risk control (finite-sample guarantees)
  3. MARGIN-style online calibration (per-band EWMA)
  4. Platt scaling (temperature scaling)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CalibratedThreshold:
    """Result of calibration: a threshold + risk guarantee."""
    threshold: float
    risk_target: float  # alpha
    coverage: float  # fraction of docs above threshold
    observed_risk: float  # error rate above threshold
    n_calibrated: int
    method: str


class IsotonicCalibrator:
    """Design-time isotonic regression calibration.

    Fits a monotone mapping from raw scores to calibrated probabilities
    using a heldout calibration set.
    """

    def __init__(self):
        self._thresholds = None
        self._values = None
        self._fitted = False

    def fit(self, scores: np.ndarray, labels: np.ndarray):
        """Fit isotonic regression on calibration data.

        scores: raw confidence scores (higher = more confident)
        labels: binary labels (1 = correct/signable, 0 = incorrect/risky)
        """
        from sklearn.isotonic import IsotonicRegression

        # Sort by score
        order = np.argsort(scores)
        sorted_scores = scores[order]
        sorted_labels = labels[order]

        # Fit isotonic regression
        ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
        ir.fit(sorted_scores, sorted_labels)

        self._thresholds = sorted_scores
        self._values = ir.transform(sorted_scores)
        self._ir = ir
        self._fitted = True

    def calibrate(self, score: float) -> float:
        """Map raw score to calibrated probability."""
        if not self._fitted:
            return score
        return float(self._ir.predict([score])[0])

    def find_threshold(self, risk_target: float) -> CalibratedThreshold:
        """Find threshold that achieves target risk level.

        risk_target: maximum acceptable error rate (alpha)
        """
        if not self._fitted:
            raise ValueError("Must fit first")

        # For each possible threshold, compute risk and coverage
        best = None
        for t in np.linspace(0, 1, 200):
            mask = self._values >= t
            if mask.sum() == 0:
                continue
            # Risk = 1 - accuracy among accepted
            # (This is a simplification; real conformal uses the calibration set)
            coverage = mask.mean()
            if coverage < 0.05:
                continue
            # We'll use the raw relationship for now
            risk = 1.0 - self._values[mask].mean()
            if risk <= risk_target:
                if best is None or coverage > best.coverage:
                    best = CalibratedThreshold(
                        threshold=float(t),
                        risk_target=risk_target,
                        coverage=float(coverage),
                        observed_risk=float(risk),
                        n_calibrated=len(self._values),
                        method="isotonic",
                    )
        return best or CalibratedThreshold(
            threshold=1.0, risk_target=risk_target,
            coverage=0.0, observed_risk=0.0,
            n_calibrated=len(self._values), method="isotonic",
        )


class ConformalRiskController:
    """Conformal Risk Control (Angelopoulos et al., ICLR 2024).

    Provides finite-sample guarantees on risk by calibrating
    an accept-or-abstain threshold.
    """

    def __init__(self, alpha: float = 0.1, delta: float = 0.05):
        self.alpha = alpha  # target risk level
        self.delta = delta  # confidence level
        self._scores = None
        self._losses = None

    def fit(self, scores: np.ndarray, losses: np.ndarray):
        """Fit on calibration data.

        scores: nonconformity scores (higher = less conforming)
        losses: actual losses (1 if error, 0 if correct)
        """
        self._scores = scores.copy()
        self._losses = losses.copy()

    def find_threshold(self) -> CalibratedThreshold:
        """Find threshold λ* = min{λ : upper_bound(R(λ)) ≤ α}."""
        if self._scores is None:
            raise ValueError("Must fit first")

        n = len(self._scores)
        best_threshold = 1.0

        for lam in np.linspace(0, 1, 500):
            # Accept set: items with score <= lambda
            mask = self._scores <= lam
            n_accept = mask.sum()

            if n_accept == 0:
                continue

            # Hoeffding upper bound on risk
            empirical_risk = self._losses[mask].mean() if n_accept > 0 else 0.0
            hoeffding_term = np.sqrt(np.log(2.0 / self.delta) / (2.0 * n_accept))
            upper_bound = empirical_risk + hoeffding_term

            if upper_bound <= self.alpha:
                best_threshold = float(lam)
                break

        # Compute metrics at this threshold
        mask = self._scores <= best_threshold
        coverage = mask.mean() if len(self._scores) > 0 else 0.0
        observed_risk = self._losses[mask].mean() if mask.sum() > 0 else 0.0

        return CalibratedThreshold(
            threshold=best_threshold,
            risk_target=self.alpha,
            coverage=float(coverage),
            observed_risk=float(observed_risk),
            n_calibrated=n,
            method="conformal_crc",
        )


class MarginOnlineCalibrator:
    """MARGIN-style online calibration (per-band EWMA).

    Learns per-confidence-band calibration factors from the task stream.
    No heldout data needed. Adapts to distribution shift.
    """

    def __init__(self, n_bands: int = 5, alpha: float = 0.04, shrinkage: int = 100):
        self.n_bands = n_bands
        self.alpha = alpha  # EWMA learning rate
        self.shrinkage = shrinkage  # Bayesian shrinkage parameter
        self._band_correct = np.zeros(n_bands)
        self._band_total = np.zeros(n_bands)
        self._band_calibration = np.full(n_bands, 0.5)  # prior

    def _get_band(self, score: float) -> int:
        """Map score to confidence band."""
        band = int(score * self.n_bands)
        return min(band, self.n_bands - 1)

    def update(self, score: float, correct: bool):
        """Update calibration with one observation."""
        band = self._get_band(score)
        self._band_total[band] += 1
        self._band_correct[band] += 1.0 if correct else 0.0

        # Bayesian shrinkage toward prior
        n = self._band_total[band]
        prior_weight = self.shrinkage / (self.shrinkage + n)
        observed = self._band_correct[band] / n if n > 0 else 0.5

        # EWMA update
        old_cal = self._band_calibration[band]
        new_cal = old_cal + self.alpha * (observed - old_cal)
        self._band_calibration[band] = (
            prior_weight * 0.5 + (1 - prior_weight) * new_cal
        )

    def calibrate(self, score: float) -> float:
        """Map raw score to calibrated score using band factor."""
        band = self._get_band(score)
        # Apply calibration factor
        raw = score
        cal = self._band_calibration[band]
        # Blend: if band calibration says we're overconfident, pull down
        return float(raw * (0.5 + 0.5 * cal))

    def fit_batch(self, scores: np.ndarray, labels: np.ndarray):
        """Batch fit for benchmarking (calls update sequentially)."""
        for s, l in zip(scores, labels):
            self.update(float(s), bool(l))


class PlattScaler:
    """Platt scaling (temperature scaling variant).

    Fits a sigmoid to map raw scores to calibrated probabilities.
    """

    def __init__(self):
        self._a = 1.0
        self._b = 0.0
        self._fitted = False

    def fit(self, scores: np.ndarray, labels: np.ndarray):
        """Fit Platt scaling on calibration data."""
        from scipy.optimize import minimize

        def neg_log_likelihood(params):
            a, b = params
            logits = a * scores + b
            probs = 1.0 / (1.0 + np.exp(-logits))
            probs = np.clip(probs, 1e-7, 1 - 1e-7)
            return -np.sum(labels * np.log(probs) + (1 - labels) * np.log(1 - probs))

        result = minimize(neg_log_likelihood, x0=[1.0, 0.0], method='Nelder-Mead')
        self._a, self._b = result.x
        self._fitted = True

    def calibrate(self, score: float) -> float:
        """Map raw score to calibrated probability."""
        if not self._fitted:
            return score
        logits = self._a * score + self._b
        return float(1.0 / (1.0 + np.exp(-logits)))
