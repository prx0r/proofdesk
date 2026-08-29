"""SigningWorld — deterministic document signing laboratory.

Cogym-style world where each step is a document needing a sign/refuse/defer
decision. Known ground truth. Deterministic replay. Hard worlds where naive
signing heuristics fail.

Architecture mirrors cogym/market/world.py:
  SigningWorld  →  replaces TradingWorld
  DocPacket     →  replaces MarketPacket
  SigningDecision →  replaces Decision
  score_signing() →  replaces score_decision()
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from enum import Enum


# ─── Ground Truth ────────────────────────────────────────────────────

class Verdict(Enum):
    SAFE = "safe"
    RISKY = "risky"
    FRAUDULENT = "fraudulent"


@dataclass(frozen=True)
class DocField:
    name: str
    value: str
    correct: bool
    page: int = 0


@dataclass(frozen=True)
class Document:
    doc_id: str
    doc_type: str
    fields: tuple[DocField, ...]
    verdict: Verdict
    difficulty: float  # 0-1
    base_rate_risk: float
    hard_world: str
    metadata: dict = field(default_factory=dict)

    @property
    def should_sign(self) -> bool:
        return self.verdict == Verdict.SAFE

    @property
    def field_accuracy(self) -> float:
        return sum(f.correct for f in self.fields) / max(1, len(self.fields))


# ─── Confidence Signals (Nutrient-style) ─────────────────────────────

@dataclass(frozen=True)
class ConfidenceSignal:
    nutrient_confidence: float  # 0-1 raw composite
    match_label: str  # id_match / fuzzy_match / not_found
    match_score: float  # 1.0 / 0.5 / 0.0
    grounding_score: float  # 0-1 NLI groundedness
    margin_score: float  # 0-1 gap between top candidates
    cross_doc_consistency: float  # 0-1
    field_completeness: float  # 0-1
    avg_field_confidence: float
    confidence_variance: float


# ─── DocPacket (what the signer sees) ────────────────────────────────

@dataclass(frozen=True)
class DocPacket:
    """Snapshot of a document + signals — what the signer sees at one step."""
    document: Document
    signals: ConfidenceSignal
    world_id: str
    doc_index: int
    # Context from prior documents in this session
    prior_verdicts: tuple[str, ...] = ()  # "safe"/"risky"/"fraudulent" for recent docs
    prior_accuracies: tuple[float, ...] = ()

    @property
    def features(self) -> list[float]:
        """Numeric feature vector for calibration."""
        s = self.signals
        return [
            s.nutrient_confidence,
            s.match_score,
            s.grounding_score,
            s.margin_score,
            s.cross_doc_consistency,
            s.field_completeness,
            s.avg_field_confidence,
            s.confidence_variance,
            self.document.field_accuracy,
            self.document.difficulty,
        ]


# ─── SigningDecision (replaces cogym Decision) ──────────────────────

@dataclass(frozen=True)
class SigningDecision:
    """Structured output from a signing decision step."""
    stance: str  # SIGN / REFUSE / DEFER
    p_safe: float  # probability document is safe to sign
    p_risky: float
    p_fraudulent: float
    confidence: float  # 0-1 how sure is the signer
    risk: float  # 0-1 assessed risk level
    crux: str = ""  # key uncertainty
    claims: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    falsifiers: tuple[str, ...] = ()  # what would disprove the claims
    reasoning_summary: str = ""
    raw: str = ""

    def to_dict(self) -> dict:
        return {
            "stance": self.stance,
            "p_safe": self.p_safe,
            "p_risky": self.p_risky,
            "p_fraudulent": self.p_fraudulent,
            "confidence": self.confidence,
            "risk": self.risk,
            "crux": self.crux,
            "claims": list(self.claims),
            "evidence": list(self.evidence),
            "uncertainties": list(self.uncertainties),
            "falsifiers": list(self.falsifiers),
            "reasoning_summary": self.reasoning_summary,
        }


def neutral_signing_decision(raw: str = "") -> SigningDecision:
    return SigningDecision("DEFER", 1 / 3, 1 / 3, 1 / 3, 0.0, 0.5, raw=raw)


def parse_signing_decision(text: str) -> SigningDecision:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        obj = json.loads(text[start:end])
        stance = str(obj.get("stance", "DEFER")).upper()
        if stance not in {"SIGN", "REFUSE", "DEFER"}:
            stance = "DEFER"
        probs = [max(0.0, float(obj.get(k, 0.0))) for k in ("p_safe", "p_risky", "p_fraudulent")]
        total = sum(probs) or 1.0
        probs = [p / total for p in probs]
        return SigningDecision(
            stance=stance,
            p_safe=probs[0],
            p_risky=probs[1],
            p_fraudulent=probs[2],
            confidence=max(0.0, min(1.0, float(obj.get("confidence", 0.5)))),
            risk=max(0.0, min(1.0, float(obj.get("risk", 0.5)))),
            crux=str(obj.get("crux", "")),
            claims=tuple(map(str, obj.get("claims", []))),
            evidence=tuple(map(str, obj.get("evidence", []))),
            uncertainties=tuple(map(str, obj.get("uncertainties", []))),
            falsifiers=tuple(map(str, obj.get("falsifiers", []))),
            reasoning_summary=str(obj.get("reasoning_summary", "")),
            raw=text,
        )
    except Exception:
        return neutral_signing_decision(text)


# ─── Scoring (replaces cogym score_decision) ────────────────────────

@dataclass(frozen=True)
class SigningScore:
    log_score: float
    brier: float
    correct: float  # 1.0 if stance matches ground truth
    risk_error: float  # |predicted risk - actual risk|
    utility: float  # decision-theoretic utility
    false_positive: float  # signed risky/fraudulent doc (CATASTROPHIC)
    false_negative: float  # refused safe doc (opportunity cost)


def outcome_class(doc: Document) -> int:
    """Map verdict to class index: 0=safe, 1=risky, 2=fraudulent."""
    return {Verdict.SAFE: 0, Verdict.RISKY: 1, Verdict.FRAUDULENT: 2}[doc.verdict]


def score_signing(decision: SigningDecision, doc: Document) -> SigningScore:
    """Score a signing decision against ground truth.

    Scoring philosophy (from BAS paper):
    - False positive (signing a fraudulent doc) is catastrophic → heavy penalty
    - False negative (refusing a safe doc) is costly but recoverable → moderate penalty
    - Correct decisions get positive utility
    """
    idx = outcome_class(doc)
    probs = (decision.p_safe, decision.p_risky, decision.p_fraudulent)
    p = max(probs[idx], 1e-12)
    log_score = math.log(p)

    y = [0.0, 0.0, 0.0]
    y[idx] = 1.0
    brier = sum((a - b) ** 2 for a, b in zip(probs, y)) / 3.0

    # Correct stance check
    correct_map = {"SIGN": 0, "REFUSE": 2, "DEFER": 1}
    correct = float(decision.stance == {0: "SIGN", 1: "DEFER", 2: "REFUSE"}[idx])

    # Risk error
    actual_risk = 0.0 if doc.verdict == Verdict.SAFE else (0.5 if doc.verdict == Verdict.RISKY else 1.0)
    risk_error = abs(decision.risk - actual_risk)

    # False positive: signed but doc was risky/fraudulent
    false_positive = 1.0 if (decision.stance == "SIGN" and idx > 0) else 0.0
    # False negative: refused/deferred but doc was safe
    false_negative = 1.0 if (decision.stance in ("REFUSE", "DEFER") and idx == 0) else 0.0

    # Utility: asymmetric (FP much worse than FN)
    if decision.stance == "SIGN":
        utility = 1.0 if idx == 0 else -5.0  # signing fraud is catastrophic
    elif decision.stance == "REFUSE":
        utility = 0.3 if idx == 2 else -0.5  # refusing safe has opportunity cost
    else:  # DEFER
        utility = 0.1  # always safe, never optimal

    return SigningScore(
        log_score=log_score,
        brier=brier,
        correct=correct,
        risk_error=risk_error,
        utility=utility,
        false_positive=false_positive,
        false_negative=false_negative,
    )


# ─── BehaviorSignature (replaces cogym BehaviorSignature) ────────────

@dataclass(frozen=True)
class SigningSignature:
    sign_rate: float
    refuse_rate: float
    defer_rate: float
    mean_confidence: float
    sd_confidence: float
    mean_risk: float
    sd_risk: float
    mean_forecast_entropy: float
    mean_claim_count: float
    mean_falsifier_count: float
    false_positive_rate: float
    false_negative_rate: float


def build_signing_signature(decisions: list[SigningDecision], scores: list[SigningScore]) -> SigningSignature:
    n = max(1, len(decisions))
    confidences = [d.confidence for d in decisions]
    risks = [d.risk for d in decisions]
    entropies = [
        -sum(p * math.log(max(p, 1e-12)) for p in (d.p_safe, d.p_risky, d.p_fraudulent))
        for d in decisions
    ]
    fps = sum(s.false_positive for s in scores)
    fns = sum(s.false_negative for s in scores)
    return SigningSignature(
        sign_rate=sum(d.stance == "SIGN" for d in decisions) / n,
        refuse_rate=sum(d.stance == "REFUSE" for d in decisions) / n,
        defer_rate=sum(d.stance == "DEFER" for d in decisions) / n,
        mean_confidence=statistics.mean(confidences) if confidences else 0.0,
        sd_confidence=statistics.pstdev(confidences) if len(confidences) > 1 else 0.0,
        mean_risk=statistics.mean(risks) if risks else 0.0,
        sd_risk=statistics.pstdev(risks) if len(risks) > 1 else 0.0,
        mean_forecast_entropy=statistics.mean(entropies) if entropies else 0.0,
        mean_claim_count=statistics.mean([float(len(d.claims)) for d in decisions]) if decisions else 0.0,
        mean_falsifier_count=statistics.mean([float(len(d.falsifiers)) for d in decisions]) if decisions else 0.0,
        false_positive_rate=fps / n,
        false_negative_rate=fns / n,
    )


def signing_signature_distance(a: SigningSignature, b: SigningSignature) -> float:
    av = (a.sign_rate, a.refuse_rate, a.defer_rate, a.mean_confidence, a.sd_confidence,
          a.mean_risk, a.sd_risk, a.mean_forecast_entropy, a.mean_claim_count / 5.0,
          a.mean_falsifier_count / 5.0, a.false_positive_rate, a.false_negative_rate)
    bv = (b.sign_rate, b.refuse_rate, b.defer_rate, b.mean_confidence, b.sd_confidence,
          b.mean_risk, b.sd_risk, b.mean_forecast_entropy, b.mean_claim_count / 5.0,
          b.mean_falsifier_count / 5.0, b.false_positive_rate, b.false_negative_rate)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(av, bv)) / len(av))


# ─── SigningWorld ─────────────────────────────────────────────────────

@dataclass
class SigningWorldManifest:
    name: str
    hard_world: str
    n_docs: int
    seed: int

    @property
    def world_id(self) -> str:
        raw = f"SIGNING_WORLD:{self.name}:{self.hard_world}:{self.n_docs}:{self.seed}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class SigningWorld:
    manifest: SigningWorldManifest
    documents: list[Document]
    signals: list[ConfidenceSignal]

    def packet(self, index: int, lookback: int = 5) -> DocPacket:
        """Get a document packet with context from prior decisions."""
        if index < 0 or index >= len(self.documents):
            raise IndexError(index)
        lo = max(0, index - lookback)
        prior_verds = tuple(self.documents[i].verdict.value for i in range(lo, index))
        prior_accs = tuple(self.documents[i].field_accuracy for i in range(lo, index))
        return DocPacket(
            document=self.documents[index],
            signals=self.signals[index],
            world_id=self.manifest.world_id,
            doc_index=index,
            prior_verdicts=prior_verds,
            prior_accuracies=prior_accs,
        )

    def oracle_decision(self, index: int) -> str:
        """Ground truth: what should the signer do?"""
        doc = self.documents[index]
        if doc.verdict == Verdict.SAFE:
            return "SIGN"
        elif doc.verdict == Verdict.RISKY:
            return "REFUSE"
        else:
            return "REFUSE"

    def realized_utility(self, index: int, decision: SigningDecision) -> float:
        """Utility of this decision (deterministic, from ground truth)."""
        score = score_signing(decision, self.documents[index])
        return score.utility

    def __len__(self):
        return len(self.documents)
