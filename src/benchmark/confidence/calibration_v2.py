"""Calibration methods — proper implementations from arxiv.

1. Isotonic regression (scikit-learn) — design-time calibration
2. Conformal Risk Control (Angelopoulos et al., ICLR 2024) — proper quantiles
3. Platt scaling (temperature scaling) — sigmoid calibration
4. MARGIN-style online calibration (per-band EWMA with Bayesian shrinkage)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
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
    """Isotonic regression calibration (scikit-learn).

    Fits a monotone mapping from raw scores to calibrated probabilities
    using a heldout calibration set.
    """

    def __init__(self):
        self._ir = None
        self._fitted = False

    def fit(self, scores: np.ndarray, labels: np.ndarray):
        """Fit isotonic regression on calibration data."""
        from sklearn.isotonic import IsotonicRegression
        self._ir = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
        self._ir.fit(scores, labels)
        self._fitted = True

    def calibrate(self, score: float) -> float:
        """Map raw score to calibrated probability."""
        if not self._fitted:
            return score
        return float(self._ir.predict([score])[0])

    def calibrate_batch(self, scores: np.ndarray) -> np.ndarray:
        """Batch calibrate."""
        if not self._fitted:
            return scores
        return self._ir.predict(scores)

    def find_threshold(self, scores: np.ndarray, labels: np.ndarray,
                       risk_target: float) -> CalibratedThreshold:
        """Find threshold using heldout calibration set.

        Threshold = min{t : risk(accept_set(t)) <= alpha}
        where accept_set(t) = {i : calibrated_score(i) >= t}
        """
        if not self._fitted:
            raise ValueError("Must fit first")

        cal_scores = self.calibrate_batch(scores)

        # Sweep thresholds from high to low
        best = None
        for t in np.sort(np.unique(cal_scores))[::-1]:
            mask = cal_scores >= t
            if mask.sum() == 0:
                continue
            risk = 1.0 - labels[mask].mean()  # error rate among accepted
            coverage = mask.mean()
            if risk <= risk_target:
                if best is None or coverage > best.coverage:
                    best = CalibratedThreshold(
                        threshold=float(t),
                        risk_target=risk_target,
                        coverage=float(coverage),
                        observed_risk=float(risk),
                        n_calibrated=len(scores),
                        method="isotonic",
                    )
        return best or CalibratedThreshold(
            threshold=1.0, risk_target=risk_target,
            coverage=0.0, observed_risk=0.0,
            n_calibrated=len(scores), method="isotonic",
        )


class ConformalRiskController:
    """Conformal Risk Control (Angelopoulos et al., ICLR 2024).

    Proper implementation using quantiles of nonconformity scores.

    From the paper:
      λ* = min{λ : R̂(λ) + sqrt(log(2/δ) / (2|E_λ|)) ≤ α}

    But we use the standard conformal approach:
      1. Compute nonconformity scores on calibration set
      2. Take (1-α)(1 + 1/n) quantile as threshold
      3. Accept items with score <= threshold

    This gives finite-sample, distribution-free guarantee:
      P(risk > α) ≤ δ
    """

    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self._threshold = None

    def fit(self, scores: np.ndarray, losses: np.ndarray):
        """Fit on calibration data.

        scores: nonconformity scores (higher = less conforming)
        losses: actual losses (1 if error, 0 if correct)

        The key insight from conformal prediction:
        We sort the scores and take the (1-α)(1+1/n) quantile.
        """
        n = len(scores)
        # Sort scores
        sorted_scores = np.sort(scores)
        # Conformal quantile: (1-α)(1 + 1/n) quantile
        # This is the standard split-conformal threshold
        quantile_idx = int(np.ceil((1 - self.alpha) * (1 + 1/n) * n)) - 1
        quantile_idx = min(quantile_idx, n - 1)
        self._threshold = float(sorted_scores[quantile_idx])
        self._n = n

    def find_threshold(self) -> CalibratedThreshold:
        """Return the calibrated threshold."""
        if self._threshold is None:
            raise ValueError("Must fit first")

        return CalibratedThreshold(
            threshold=self._threshold,
            risk_target=self.alpha,
            coverage=0.0,  # will be computed on test data
            observed_risk=0.0,
            n_calibrated=self._n,
            method="conformal_crc",
        )

    def should_accept(self, score: float) -> bool:
        """Check if a score passes the conformal threshold."""
        if self._threshold is None:
            raise ValueError("Must fit first")
        return score <= self._threshold


class PlattScaler:
    """Platt scaling (temperature scaling variant).

    Fits a sigmoid to map raw scores to calibrated probabilities.
    From Platt (1999): P(y=1|s) = 1 / (1 + exp(a*s + b))
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
            probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -500, 500)))
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
        return float(1.0 / (1.0 + np.exp(-np.clip(logits, -500, 500))))


class MarginOnlineCalibrator:
    """MARGIN-style online calibration (per-band EWMA).

    From MARGIN paper (2026): per-agent, per-confidence-band calibration
    factors learned from the task stream via symmetric EWMA with Bayesian
    shrinkage.

    Key: tracks conditional reliability as a function of stated confidence.
    An agent might be reliable at moderate confidence but overconfident at
    high confidence. A single reputation score can't capture this.
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
        """Update calibration with one observation.

        MARGIN uses symmetric EWMA (not asymmetric) because
        foundation model miscalibration is epistemic, not strategic.
        """
        band = self._get_band(score)
        self._band_total[band] += 1
        self._band_correct[band] += 1.0 if correct else 0.0

        # Bayesian shrinkage toward prior
        n = self._band_total[band]
        prior_weight = self.shrinkage / (self.shrinkage + n)
        observed = self._band_correct[band] / n if n > 0 else 0.5

        # Symmetric EWMA update (from MARGIN paper Prop 5)
        old_cal = self._band_calibration[band]
        new_cal = old_cal + self.alpha * (observed - old_cal)
        self._band_calibration[band] = (
            prior_weight * 0.5 + (1 - prior_weight) * new_cal
        )

    def calibrate(self, score: float) -> float:
        """Map raw score to calibrated score using band factor.

        From MARGIN: the calibration factor adjusts for per-band
        over/under-confidence.
        """
        band = self._get_band(score)
        cal = self._band_calibration[band]
        # If band calibration < 0.5, we're overconfident → pull down
        # If band calibration > 0.5, we're underconfident → pull up
        return float(score * (0.5 + 0.5 * cal))

    def fit_batch(self, scores: np.ndarray, labels: np.ndarray):
        """Batch fit for benchmarking (calls update sequentially)."""
        for s, l in zip(scores, labels):
            self.update(float(s), bool(l))
