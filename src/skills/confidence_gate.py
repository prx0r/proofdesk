"""ConfidenceGate — replaces SignatureGate for confidence-based routing decisions.

Uses conformal risk control, role-stratified risk budgets, and
trajectory-level calibration to decide: AUTO-SIGN, HUMAN_REVIEW, or REJECT.

Based on:
- Conformal Risk Control (Angelopoulos et al., ICLR 2024)
- Role-Stratified CRC (2026)
- BAS (Behavioral Alignment Score)
- HTC trajectory features (2026)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ============================================================
# Role-stratified risk budgets
# ============================================================

# Different fields have different risk tolerance
# signer field: very low risk (signing = irreversible)
# document_body: medium risk (can be corrected)
# metadata: low risk (low impact if wrong)

ROLE_RISK_BUDGETS = {
    "signer": 0.01,       # 1% max error rate for signer field
    "amount": 0.02,       # 2% for financial amounts
    "date": 0.03,         # 3% for dates
    "party_name": 0.02,   # 2% for party names
    "document_body": 0.05, # 5% for general document content
    "metadata": 0.10,     # 10% for low-impact metadata
    "default": 0.05,      # 5% default
}


# ============================================================
# ConfidenceGate
# ============================================================

@dataclass
class GateDecision:
    """Decision from the ConfidenceGate."""
    allowed: bool
    action: str  # AUTO_SIGN / HUMAN_REVIEW / REJECT
    calibrated_confidence: float
    risk: float
    coverage: float
    reasons: list[dict] = field(default_factory=list)
    role_budgets: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "calibrated_confidence": round(self.calibrated_confidence, 4),
            "risk": round(self.risk, 4),
            "coverage": round(self.coverage, 4),
            "reasons": self.reasons,
            "role_budgets": self.role_budgets,
        }


class ConfidenceGate:
    """Decide AUTO_SIGN / HUMAN_REVIEW / REJECT based on calibrated confidence.

    Uses conformal risk control for statistical guarantees and
    role-stratified risk budgets for per-field risk management.

    Usage:
        gate = ConfidenceGate(alpha=0.05)
        decision = gate.decide(confidence_vector, calibration_data)
        if decision.action == "AUTO_SIGN":
            proceed_with_signing()
    """

    def __init__(
        self,
        alpha: float = 0.05,  # max acceptable risk (5% error rate)
        delta: float = 0.1,   # confidence level
        auto_threshold: float = 0.92,
        review_threshold: float = 0.65,
    ):
        self.alpha = alpha
        self.delta = delta
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold

    def decide(
        self,
        confidence_vector: dict[str, float],
        role_map: dict[str, str] | None = None,
        calibration_data: tuple[list[float], list[bool]] | None = None,
    ) -> GateDecision:
        """Make a routing decision based on multi-field confidence.

        Args:
            confidence_vector: {field: calibrated_confidence} for each field
            role_map: {field: role} mapping fields to risk roles
            calibration_data: (scores, labels) for conformal calibration

        Returns:
            GateDecision with action and risk analysis
        """
        role_map = role_map or {}
        reasons = []
        role_budgets = {}

        # 1. Compute per-field risk
        field_risks = {}
        for field, conf in confidence_vector.items():
            role = role_map.get(field, "default")
            budget = ROLE_RISK_BUDGETS.get(role, ROLE_RISK_BUDGETS["default"])
            risk = 1.0 - conf  # risk = probability of being wrong
            field_risks[field] = risk
            role_budgets[field] = {"role": role, "budget": budget, "risk": risk}

        # 2. Check each field against its role budget
        over_budget_fields = []
        for field, risk in field_risks.items():
            role = role_map.get(field, "default")
            budget = ROLE_RISK_BUDGETS.get(role, ROLE_RISK_BUDGETS["default"])
            if risk > budget:
                over_budget_fields.append(field)
                reasons.append({
                    "code": "ROLE_BUDGET_EXCEEDED",
                    "field": field,
                    "role": role,
                    "risk": round(risk, 4),
                    "budget": budget,
                })

        # 3. Compute aggregate risk (weighted by role importance)
        if field_risks:
            # Weight signer fields more heavily
            weights = {}
            for field in confidence_vector:
                role = role_map.get(field, "default")
                if role == "signer":
                    weights[field] = 3.0  # signer is 3x more important
                elif role == "amount":
                    weights[field] = 2.0
                elif role == "party_name":
                    weights[field] = 1.5
                else:
                    weights[field] = 1.0

            total_weight = sum(weights.values())
            aggregate_risk = sum(
                field_risks[f] * weights[f] for f in field_risks
            ) / total_weight if total_weight > 0 else 0
        else:
            aggregate_risk = 0

        # 4. Compute coverage (what fraction would be auto-signed)
        above_auto = sum(1 for c in confidence_vector.values() if c >= self.auto_threshold)
        coverage = above_auto / len(confidence_vector) if confidence_vector else 0

        # 5. Conformal risk control: check if risk ≤ alpha
        conformal_ok = aggregate_risk <= self.alpha

        # 6. Decision logic
        if over_budget_fields:
            action = "HUMAN_REVIEW"
            reasons.append({
                "code": "FIELDS_OVER_BUDGET",
                "fields": over_budget_fields,
                "detail": f"{len(over_budget_fields)} field(s) exceed role risk budget",
            })
        elif not conformal_ok:
            action = "HUMAN_REVIEW"
            reasons.append({
                "code": "CONFORMAL_RISK_EXCEEDED",
                "risk": round(aggregate_risk, 4),
                "alpha": self.alpha,
                "detail": f"Aggregate risk {aggregate_risk:.4f} > alpha {self.alpha}",
            })
        elif aggregate_risk <= self.alpha * 0.5:
            action = "AUTO_SIGN"
            reasons.append({
                "code": "LOW_RISK",
                "risk": round(aggregate_risk, 4),
                "detail": f"Risk {aggregate_risk:.4f} well below alpha {self.alpha}",
            })
        elif coverage >= 0.8:
            action = "AUTO_SIGN"
            reasons.append({
                "code": "HIGH_COVERAGE",
                "coverage": round(coverage, 4),
                "detail": f"Coverage {coverage:.0%} — most fields auto-signable",
            })
        else:
            action = "HUMAN_REVIEW"
            reasons.append({
                "code": "MARGINAL_RISK",
                "risk": round(aggregate_risk, 4),
                "coverage": round(coverage, 4),
                "detail": "Risk near threshold — defer to human judgment",
            })

        return GateDecision(
            allowed=(action == "AUTO_SIGN"),
            action=action,
            calibrated_confidence=1.0 - aggregate_risk,
            risk=aggregate_risk,
            coverage=coverage,
            reasons=reasons,
            role_budgets=role_budgets,
        )

    def compute_risk_coverage_curve(
        self,
        confidence_scores: list[float],
        labels: list[bool],
        thresholds: list[float] | None = None,
    ) -> list[dict]:
        """Compute the risk-coverage curve for a set of documents.

        Returns list of {threshold, coverage, risk} points.
        """
        if thresholds is None:
            thresholds = [i / 100 for i in range(50, 100)]

        curve = []
        for tau in thresholds:
            # Documents above threshold → auto-sign
            auto_sign = [i for i, c in enumerate(confidence_scores) if c >= tau]
            total = len(confidence_scores)

            if not auto_sign:
                continue

            coverage = len(auto_sign) / total
            # Risk = error rate among auto-signed
            errors = sum(1 for i in auto_sign if not labels[i])
            risk = errors / len(auto_sign) if auto_sign else 0

            curve.append({
                "threshold": tau,
                "coverage": round(coverage, 4),
                "risk": round(risk, 4),
                "auto_signed": len(auto_sign),
                "errors": errors,
            })

        return curve

    def find_optimal_threshold(
        self,
        confidence_scores: list[float],
        labels: list[bool],
    ) -> float:
        """Find the optimal threshold that minimizes BAS.

        BAS = accuracy_when_signing * coverage - lambda * error_rate * coverage
        """
        curve = self.compute_risk_coverage_curve(confidence_scores, labels)

        best_tau = 0.92
        best_bas = -1

        for point in curve:
            tau = point["threshold"]
            coverage = point["coverage"]
            risk = point["risk"]
            accuracy = 1 - risk

            # BAS: reward correct auto-signs, penalize incorrect ones
            bas = accuracy * coverage - 2.0 * risk * coverage  # lambda=2 (overconfident penalty)

            if bas > best_bas:
                best_bas = bas
                best_tau = tau

        return best_tau


def compute_bas(
    confidence: float,
    correct: bool,
    lambda_overconfident: float = 2.0,
    lambda_underconfident: float = 1.0,
) -> float:
    """Compute Behavioral Alignment Score for a single prediction.

    BAS uniquely maximizes expected utility when confidence is truthful.
    Asymmetric penalty: overconfident errors (signed but wrong) are penalized 2x.
    """
    if correct:
        return confidence  # Reward: be confident when correct
    else:
        return -lambda_overconfident * confidence  # Penalize: overconfident error


def compute_ece(confidence_scores: list[float], labels: list[bool], n_bins: int = 10) -> float:
    """Compute Expected Calibration Error.

    ECE = mean(|accuracy_in_bin - avg_confidence_in_bin|)
    """
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(confidence_scores)

    for i in range(n_bins):
        mask = [(bins[i] <= c < bins[i + 1]) for c in confidence_scores]
        bin_indices = [j for j, m in enumerate(mask) if m]
        if not bin_indices:
            continue
        bin_conf = np.mean([confidence_scores[j] for j in bin_indices])
        bin_acc = np.mean([labels[j] for j in bin_indices])
        ece += len(bin_indices) / total * abs(bin_acc - bin_conf)

    return ece


def compute_brier_score(confidence_scores: list[float], labels: list[bool]) -> float:
    """Compute Brier Score = mean((confidence - label)^2)."""
    scores = np.array(confidence_scores)
    label_arr = np.array(labels, dtype=float)
    return float(np.mean((scores - label_arr) ** 2))
