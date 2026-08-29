"""Signing experiment runner — cogym-style.

Runs signers on SigningWorld, scores decisions, optimizes thresholds,
produces calibration reports.
"""

from __future__ import annotations

import json
import math
import os
import time
import numpy as np
from dataclasses import dataclass, field

from .signing_world import (
    SigningWorld, DocPacket, SigningDecision, SigningScore,
    SigningSignature, build_signing_signature, score_signing,
    neutral_signing_decision, Verdict,
)
from .signing_generator import generate_all_worlds, HARD_WORLD_GENERATORS
from .metrics import compute_all_metrics, CalibrationMetrics


@dataclass
class SigningRecord:
    doc_index: int
    decision: SigningDecision
    score: SigningScore
    packet: DocPacket


@dataclass
class SigningRun:
    world_id: str
    hard_world: str
    condition: str
    records: tuple[SigningRecord, ...]
    signature: SigningSignature

    @property
    def mean_utility(self) -> float:
        return sum(r.score.utility for r in self.records) / max(1, len(self.records))

    @property
    def mean_log_score(self) -> float:
        return sum(r.score.log_score for r in self.records) / max(1, len(self.records))

    @property
    def false_positive_rate(self) -> float:
        return sum(r.score.false_positive for r in self.records) / max(1, len(self.records))

    @property
    def false_negative_rate(self) -> float:
        return sum(r.score.false_negative for r in self.records) / max(1, len(self.records))


@dataclass
class ThresholdResult:
    threshold: float
    coverage: float
    risk: float
    utility: float
    false_positive_rate: float
    false_negative_rate: float
    n_sign: int
    n_refuse: int
    n_defer: int


# ─── Naive signers (baselines) ──────────────────────────────────────

def naive_signer(packet: DocPacket) -> SigningDecision:
    """Always sign if confidence > 0.5."""
    conf = packet.signals.nutrient_confidence
    if conf > 0.5:
        return SigningDecision("SIGN", 0.8, 0.15, 0.05, conf, 1 - conf)
    else:
        return SigningDecision("REFUSE", 0.15, 0.3, 0.55, conf, 1 - conf)


def always_defer_signer(packet: DocPacket) -> SigningDecision:
    """Always defer — zero risk, zero utility."""
    return SigningDecision("DEFER", 1 / 3, 1 / 3, 1 / 3, 0.3, 0.5)


def match_label_signer(packet: DocPacket) -> SigningDecision:
    """Sign only on id_match, refuse on not_found, defer on fuzzy."""
    ms = packet.signals.match_score
    conf = packet.signals.nutrient_confidence
    if ms >= 0.9:
        return SigningDecision("SIGN", 0.85, 0.1, 0.05, conf, 0.2)
    elif ms <= 0.1:
        return SigningDecision("REFUSE", 0.05, 0.2, 0.75, conf, 0.8)
    else:
        return SigningDecision("DEFER", 0.3, 0.4, 0.3, conf, 0.5)


def threshold_signer(threshold: float):
    """Sign if nutrient_confidence >= threshold."""
    def signer(packet: DocPacket) -> SigningDecision:
        conf = packet.signals.nutrient_confidence
        if conf >= threshold:
            return SigningDecision("SIGN", conf, (1 - conf) * 0.3, (1 - conf) * 0.7, conf, 1 - conf)
        else:
            return SigningDecision("REFUSE", conf, (1 - conf) * 0.3, (1 - conf) * 0.7, conf, 1 - conf)
    return signer


def fusion_signer(threshold: float = 0.5):
    """Multi-signal fusion signer — uses all Nutrient signals."""
    def signer(packet: DocPacket) -> SigningDecision:
        s = packet.signals
        # Weighted combination (learned from benchmark)
        score = (
            0.25 * s.nutrient_confidence +
            0.20 * s.match_score +
            0.20 * s.grounding_score +
            0.15 * s.margin_score +
            0.10 * s.cross_doc_consistency +
            0.10 * s.field_completeness
        )
        risk = 1.0 - score
        if score >= threshold:
            return SigningDecision("SIGN", score, risk * 0.3, risk * 0.7, score, risk)
        elif score >= threshold - 0.2:
            return SigningDecision("DEFER", score * 0.8, risk * 0.5, risk * 0.5, score, risk)
        else:
            return SigningDecision("REFUSE", score * 0.3, risk * 0.3, risk * 0.7, score, risk)
    return signer


# ─── Experiment runner ────────────────────────────────────────────────

def run_signing_world(
    world: SigningWorld,
    signer_fn,
    condition: str = "default",
) -> SigningRun:
    """Run a signer on a SigningWorld, producing scored records."""
    records = []
    decisions = []
    for i in range(len(world)):
        packet = world.packet(i)
        decision = signer_fn(packet)
        score = score_signing(decision, world.documents[i])
        records.append(SigningRecord(i, decision, score, packet))
        decisions.append(decision)
    sig = build_signing_signature(decisions, [r.score for r in records])
    return SigningRun(
        world_id=world.manifest.world_id,
        hard_world=world.manifest.hard_world,
        condition=condition,
        records=tuple(records),
        signature=sig,
    )


def optimize_threshold(
    world: SigningWorld,
    signer_factory,
    n_thresholds: int = 50,
) -> tuple[ThresholdResult, list[ThresholdResult]]:
    """Find optimal threshold for a signer on a world.

    Returns best result + all candidates.
    """
    results = []
    for tau in np.linspace(0.1, 0.95, n_thresholds):
        signer = signer_factory(tau)
        run = run_signing_world(world, signer, condition=f"tau={tau:.3f}")
        n = len(run.records)
        n_sign = sum(r.decision.stance == "SIGN" for r in run.records)
        n_refuse = sum(r.decision.stance == "REFUSE" for r in run.records)
        n_defer = sum(r.decision.stance == "DEFER" for r in run.records)
        coverage = n_sign / max(1, n)
        # Risk = false positive rate among signed documents
        signed_records = [r for r in run.records if r.decision.stance == "SIGN"]
        if signed_records:
            risk = sum(r.score.false_positive for r in signed_records) / len(signed_records)
        else:
            risk = 0.0
        results.append(ThresholdResult(
            threshold=float(tau),
            coverage=coverage,
            risk=risk,
            utility=run.mean_utility,
            false_positive_rate=run.false_positive_rate,
            false_negative_rate=run.false_negative_rate,
            n_sign=n_sign,
            n_refuse=n_refuse,
            n_defer=n_defer,
        ))

    # Find best: maximize utility subject to risk <= 0.1
    valid = [r for r in results if r.risk <= 0.1]
    if valid:
        best = max(valid, key=lambda r: r.utility)
    else:
        best = min(results, key=lambda r: r.risk)
    return best, results


# ─── Multi-world benchmark ───────────────────────────────────────────

def run_full_benchmark(
    n_per_world: int = 200,
    seed: int = 42,
) -> dict:
    """Run the full signing benchmark across all hard worlds."""
    worlds = generate_all_worlds(n_per_world, seed)
    signers = {
        "naive": lambda: naive_signer,
        "always_defer": lambda: always_defer_signer,
        "match_label": lambda: match_label_signer,
        "threshold_0.5": lambda: threshold_signer(0.5),
        "threshold_0.7": lambda: threshold_signer(0.7),
        "fusion_0.5": lambda: fusion_signer(0.5),
        "fusion_0.7": lambda: fusion_signer(0.7),
    }

    results = {}
    for hw_name, world in worlds.items():
        world_results = {}
        for signer_name, signer_factory in signers.items():
            run = run_signing_world(world, signer_factory(), condition=signer_name)
            world_results[signer_name] = {
                "mean_utility": run.mean_utility,
                "mean_log_score": run.mean_log_score,
                "false_positive_rate": run.false_positive_rate,
                "false_negative_rate": run.false_negative_rate,
                "sign_rate": run.signature.sign_rate,
                "refuse_rate": run.signature.refuse_rate,
                "defer_rate": run.signature.defer_rate,
                "mean_confidence": run.signature.mean_confidence,
            }

        # Optimize fusion threshold
        best_tau, tau_results = optimize_threshold(world, fusion_signer)
        world_results["fusion_optimized"] = {
            "threshold": best_tau.threshold,
            "coverage": best_tau.coverage,
            "risk": best_tau.risk,
            "utility": best_tau.utility,
            "false_positive_rate": best_tau.false_positive_rate,
            "false_negative_rate": best_tau.false_negative_rate,
        }
        world_results["threshold_curve"] = [
            {"threshold": r.threshold, "coverage": r.coverage, "risk": r.risk, "utility": r.utility}
            for r in tau_results
        ]
        results[hw_name] = world_results

    return results
