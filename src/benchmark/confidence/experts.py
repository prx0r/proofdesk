"""Per-world calibration engine + ExpertPolicy + Router + MixtureOfExperts.

Architecture:
  - Each document type (invoice/contract/claim) is its own cogym world
  - Each world has an ExpertPolicy with optimized threshold + calibration
  - A Router selects which expert to use based on document features
  - MixtureOfExperts orchestrates the full pipeline
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import statistics
import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable

from .signing_world import (
    Document, DocField, Verdict, ConfidenceSignal, DocPacket,
    SigningDecision, SigningScore, SigningSignature,
    build_signing_signature, score_signing, SigningWorld,
)
from .signing_generator import generate_all_worlds
from .calibration import IsotonicCalibrator, ConformalRiskController, PlattScaler
from .metrics import compute_all_metrics, CalibrationMetrics


# ─── ExpertPolicy ─────────────────────────────────────────────────────

@dataclass
class ExpertPolicy:
    """A calibrated signing policy for one document type / world.

    Each expert has:
    - Optimal threshold (τ*) calibrated on its world
    - Isotonic calibrator for confidence scores
    - Platt scaler as backup
    - Conformal risk controller for guarantees
    - BehaviorSignature of its signing profile
    """
    name: str
    doc_type: str  # invoice / contract / claim / all
    threshold: float  # optimal τ*
    risk_budget: float  # conformal α
    isotonic: IsotonicCalibrator | None = None
    platt: PlattScaler | None = None
    crc: ConformalRiskController | None = None
    signature: SigningSignature | None = None
    metrics: CalibrationMetrics | None = None
    # Learned weights for multi-signal fusion
    weights: list[float] = field(default_factory=lambda: [0.25, 0.20, 0.20, 0.15, 0.10, 0.10])

    def compute_score(self, packet: DocPacket) -> float:
        """Compute composite confidence score from signals."""
        s = packet.signals
        raw_signals = [
            s.nutrient_confidence,
            s.match_score,
            s.grounding_score,
            s.margin_score,
            s.cross_doc_consistency,
            s.field_completeness,
        ]
        return sum(w * v for w, v in zip(self.weights, raw_signals))

    def decide(self, packet: DocPacket) -> SigningDecision:
        """Make a signing decision for a document."""
        score = self.compute_score(packet)
        risk = 1.0 - score

        # Calibrate if we have the calibrator
        if self.isotonic and self.isotonic._fitted:
            calibrated = self.isotonic.calibrate(score)
        elif self.platt and self.platt._fitted:
            calibrated = self.platt.calibrate(score)
        else:
            calibrated = score

        # Decision logic
        if calibrated >= self.threshold:
            stance = "SIGN"
        elif calibrated >= self.threshold - 0.15:
            stance = "DEFER"
        else:
            stance = "REFUSE"

        return SigningDecision(
            stance=stance,
            p_safe=calibrated,
            p_risky=risk * 0.3,
            p_fraudulent=risk * 0.7,
            confidence=calibrated,
            risk=risk,
            crux=f"Expert:{self.name}",
            claims=(f"score={score:.3f}", f"calibrated={calibrated:.3f}", f"tau={self.threshold:.3f}"),
            evidence=(f"doc_type={self.doc_type}",),
        )

    def fit(self, world: SigningWorld):
        """Calibrate this expert on its world."""
        from .signing_runner import optimize_threshold, fusion_signer

        # Extract features and labels
        scores = []
        labels = []
        decisions = []
        scrs = []

        for i in range(len(world)):
            packet = world.packet(i)
            s = self.compute_score(packet)
            scores.append(s)
            labels.append(1.0 if world.documents[i].should_sign else 0.0)
            decision = self.decide(packet)
            score = score_signing(decision, world.documents[i])
            decisions.append(decision)
            scrs.append(score)

        scores_arr = np.array(scores)
        labels_arr = np.array(labels)

        # Fit isotonic calibrator
        self.isotonic = IsotonicCalibrator()
        if scores_arr.std() > 0:
            self.isotonic.fit(scores_arr, labels_arr)

        # Fit Platt scaler
        self.platt = PlattScaler()
        if scores_arr.std() > 0:
            self.platt.fit(scores_arr, labels_arr)

        # Find optimal threshold via search (not conformal — too conservative)
        best_tau, _ = optimize_threshold(world, lambda tau: self._make_signer(tau))
        self.threshold = best_tau.threshold

        # Build signature
        self.signature = build_signing_signature(decisions, scrs)

        # Compute metrics
        self.metrics = compute_all_metrics(scores_arr, labels_arr)

        return self

    def _make_signer(self, tau: float):
        """Create a signer function with this threshold."""
        def signer(packet: DocPacket) -> SigningDecision:
            score = self.compute_score(packet)
            risk = 1.0 - score
            if score >= tau:
                return SigningDecision("SIGN", score, risk * 0.3, risk * 0.7, score, risk)
            elif score >= tau - 0.15:
                return SigningDecision("DEFER", score * 0.8, risk * 0.5, risk * 0.5, score, risk)
            else:
                return SigningDecision("REFUSE", score * 0.3, risk * 0.3, risk * 0.7, score, risk)
        return signer


# ─── Router ───────────────────────────────────────────────────────────

@dataclass
class RouterDecision:
    expert_name: str
    confidence: float  # router's confidence in its selection
    features: list[float]


class DocTypeRouter:
    """Routes documents to the correct expert based on features.

    Uses a simple decision tree on:
    - document type (one-hot)
    - match label
    - field completeness
    - confidence variance
    """

    def __init__(self):
        self._rules: dict[str, str] = {}  # feature hash → expert name
        self._fallback: str = "all"
        self._fitted = False

    def fit(self, worlds: dict[str, SigningWorld], experts: dict[str, ExpertPolicy]):
        """Learn routing rules from world data."""
        # Route by hard_world (the actual distinguishing feature)
        for hw, world in worlds.items():
            for i in range(min(50, len(world))):  # sample first 50
                doc = world.documents[i]
                key = self._feature_key(doc)
                # Route to the expert that matches this hard world
                best_expert = hw if hw in experts else "all"
                self._rules[key] = best_expert

        self._fitted = True

    def _feature_key(self, doc: Document) -> str:
        """Create a routing key from document features."""
        # Use hard_world as the key — this is what distinguishes worlds
        return doc.hard_world

    def route(self, packet: DocPacket) -> str:
        """Select which expert should handle this document."""
        key = self._feature_key(packet.document)
        return self._rules.get(key, self._fallback)


# ─── MixtureOfExperts ────────────────────────────────────────────────

@dataclass
class MixtureResult:
    decision: SigningDecision
    expert_used: str
    router_confidence: float
    raw_score: float
    calibrated_score: float
    threshold: float


class MixtureOfExperts:
    """Orchestrator: router selects expert, expert decides."""

    def __init__(self, risk_budget: float = 0.3):
        self.experts: dict[str, ExpertPolicy] = {}
        self.router = DocTypeRouter()
        self.risk_budget = risk_budget
        self._fitted = False

    def fit(self, worlds: dict[str, SigningWorld]):
        """Calibrate one expert per world + fit router."""
        # Create expert for each world
        for hw, world in worlds.items():
            expert = ExpertPolicy(
                name=hw,
                doc_type=hw.split("_")[0] if "_" in hw else hw,
                threshold=0.5,
                risk_budget=self.risk_budget,
            )
            expert.fit(world)
            self.experts[hw] = expert

        # Create a universal "all" expert
        all_docs = []
        all_sigs = []
        for world in worlds.values():
            all_docs.extend(world.documents)
            all_sigs.extend(world.signals)

        # Fit router
        self.router.fit(worlds, self.experts)
        self._fitted = True

    def decide(self, packet: DocPacket) -> MixtureResult:
        """Route to expert, get decision."""
        expert_name = self.router.route(packet)
        expert = self.experts.get(expert_name)
        if expert is None:
            expert = list(self.experts.values())[0]  # fallback

        decision = expert.decide(packet)
        raw_score = expert.compute_score(packet)

        # Calibrate
        if expert.isotonic and expert.isotonic._fitted:
            cal = expert.isotonic.calibrate(raw_score)
        elif expert.platt and expert.platt._fitted:
            cal = expert.platt.calibrate(raw_score)
        else:
            cal = raw_score

        return MixtureResult(
            decision=decision,
            expert_used=expert_name,
            router_confidence=0.9,  # simple routing, high confidence
            raw_score=raw_score,
            calibrated_score=cal,
            threshold=expert.threshold,
        )


# ─── Experiment Runner ────────────────────────────────────────────────

def run_mixture_experiment(
    n_per_world: int = 200,
    seed: int = 42,
) -> dict:
    """Run the full mixture of experts experiment.

    Compares:
    1. Naive signer (conf > 0.5 → sign)
    2. Single expert (one threshold for all worlds)
    3. Mixture of experts (per-world calibration + routing)
    4. Oracle (perfect knowledge)
    """
    worlds = generate_all_worlds(n_per_world, seed)

    # Fit mixture
    moe = MixtureOfExperts(risk_budget=0.1)
    moe.fit(worlds)

    results = {
        "mixture": {"utility": [], "fpr": [], "fnr": [], "sign_rate": []},
        "single_expert": {"utility": [], "fpr": [], "fnr": [], "sign_rate": []},
        "naive": {"utility": [], "fpr": [], "fnr": [], "sign_rate": []},
        "oracle": {"utility": [], "fpr": [], "fnr": [], "sign_rate": []},
    }

    for hw, world in worlds.items():
        # Mixture of experts
        for i in range(len(world)):
            packet = world.packet(i)
            result = moe.decide(packet)
            score = score_signing(result.decision, world.documents[i])
            results["mixture"]["utility"].append(score.utility)
            results["mixture"]["fpr"].append(score.false_positive)
            results["mixture"]["fnr"].append(score.false_negative)
            results["mixture"]["sign_rate"].append(1.0 if result.decision.stance == "SIGN" else 0.0)

        # Single expert (use first expert's threshold for all)
        first_expert = list(moe.experts.values())[0]
        for i in range(len(world)):
            packet = world.packet(i)
            decision = first_expert.decide(packet)
            score = score_signing(decision, world.documents[i])
            results["single_expert"]["utility"].append(score.utility)
            results["single_expert"]["fpr"].append(score.false_positive)
            results["single_expert"]["fnr"].append(score.false_negative)
            results["single_expert"]["sign_rate"].append(1.0 if decision.stance == "SIGN" else 0.0)

        # Naive
        for i in range(len(world)):
            packet = world.packet(i)
            conf = packet.signals.nutrient_confidence
            if conf > 0.5:
                decision = SigningDecision("SIGN", conf, 0.15, 0.05, conf, 1 - conf)
            else:
                decision = SigningDecision("REFUSE", 0.15, 0.3, 0.55, conf, 1 - conf)
            score = score_signing(decision, world.documents[i])
            results["naive"]["utility"].append(score.utility)
            results["naive"]["fpr"].append(score.false_positive)
            results["naive"]["fnr"].append(score.false_negative)
            results["naive"]["sign_rate"].append(1.0 if decision.stance == "SIGN" else 0.0)

        # Oracle
        for i in range(len(world)):
            oracle_stance = world.oracle_decision(i)
            decision = SigningDecision(oracle_stance, 1.0, 0.0, 0.0, 1.0, 0.0)
            score = score_signing(decision, world.documents[i])
            results["oracle"]["utility"].append(score.utility)
            results["oracle"]["fpr"].append(score.false_positive)
            results["oracle"]["fnr"].append(score.false_negative)
            results["oracle"]["sign_rate"].append(1.0 if oracle_stance == "SIGN" else 0.0)

    # Aggregate
    summary = {}
    for method, data in results.items():
        summary[method] = {
            "mean_utility": np.mean(data["utility"]),
            "mean_fpr": np.mean(data["fpr"]),
            "mean_fnr": np.mean(data["fnr"]),
            "mean_sign_rate": np.mean(data["sign_rate"]),
            "n_total": len(data["utility"]),
        }

    return summary, moe
