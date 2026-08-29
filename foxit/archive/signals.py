"""Confidence signal simulator — Nutrient-style multi-signal output.

Simulates the signals a real extraction engine would produce:
  - nutrient_confidence: composite 0-1 (relative, uncalibrated)
  - match_label: id_match / fuzzy_match / not_found
  - grounding_score: does source support the value?
  - margin_score: gap between top-1 and top-2 candidates
  - cross_doc_consistency: do facts agree across documents?
  - field_completeness: what % of expected fields were found
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .document_world import DocumentVerdict, SigningDocument


@dataclass
class ConfidenceSignals:
    """Multi-signal confidence vector for a signing decision."""
    doc_id: str
    # Core signals (from extraction engine)
    nutrient_confidence: float  # 0-1, raw composite
    match_label: str  # id_match / fuzzy_match / not_found
    match_score: float  # 1.0 / 0.5 / 0.0
    grounding_score: float  # 0-1, NLI groundedness
    margin_score: float  # 0-1, gap between top candidates
    # Cross-document signals
    cross_doc_consistency: float  # 0-1, do facts agree
    field_completeness: float  # 0-1, % fields found
    # Trajectory signals (HTC-style)
    field_count: int
    avg_field_confidence: float
    confidence_variance: float  # how spread out are field confidences
    # Ground truth (for benchmarking only)
    should_sign: bool
    difficulty: float
    hard_world: str
    doc_type: str


def simulate_signals(
    doc: SigningDocument,
    rng: random.Random,
    noise_level: float = 0.1,
    calibration_bias: float = 0.0,
) -> ConfidenceSignals:
    """Simulate Nutrient-style confidence signals for a document.

    The signals are correlated with ground truth but noisy:
    - Safe docs tend to have higher confidence
    - Risky docs have medium confidence with fuzzy matches
    - Fraudulent docs have lower confidence with more not_found matches
    - Calibration bias shifts all signals up or down (simulates over/under-confidence)
    """
    accuracy = doc.field_accuracy
    n_fields = len(doc.fields)

    # --- Core signals ---
    # Nutrient confidence: correlated with field accuracy but noisy
    base_conf = accuracy * 0.7 + rng.normal(0, noise_level)
    nutrient_confidence = max(0.0, min(1.0, base_conf + calibration_bias))

    # Match labels: distribution depends on verdict
    if doc.verdict == DocumentVerdict.SAFE:
        match_weights = [0.7, 0.2, 0.1]  # mostly id_match
    elif doc.verdict == DocumentVerdict.RISKY:
        match_weights = [0.3, 0.5, 0.2]  # mostly fuzzy_match
    else:  # FRAUDULENT
        match_weights = [0.1, 0.3, 0.6]  # mostly not_found

    match_label = rng.choice(
        ["id_match", "fuzzy_match", "not_found"],
        p=match_weights,
    )
    match_score = {"id_match": 1.0, "fuzzy_match": 0.5, "not_found": 0.0}[match_label]

    # Grounding score: NLI groundedness
    grounding = accuracy * 0.8 + rng.normal(0, noise_level * 0.8)
    grounding_score = max(0.0, min(1.0, grounding + calibration_bias * 0.5))

    # Margin score: gap between top candidates
    if doc.verdict == DocumentVerdict.SAFE:
        margin = 0.7 + rng.normal(0, noise_level * 0.5)
    elif doc.verdict == DocumentVerdict.RISKY:
        margin = 0.4 + rng.normal(0, noise_level * 0.8)
    else:
        margin = 0.2 + rng.normal(0, noise_level)
    margin_score = max(0.0, min(1.0, margin))

    # --- Cross-document signals ---
    # Consistency: safe docs have more consistent cross-doc facts
    if doc.verdict == DocumentVerdict.SAFE:
        consistency = 0.85 + rng.normal(0, noise_level * 0.5)
    elif doc.verdict == DocumentVerdict.RISKY:
        consistency = 0.5 + rng.normal(0, noise_level)
    else:
        consistency = 0.3 + rng.normal(0, noise_level * 1.2)
    cross_doc_consistency = max(0.0, min(1.0, consistency))

    # Field completeness
    completeness = accuracy * 0.9 + rng.normal(0, noise_level * 0.3)
    field_completeness = max(0.0, min(1.0, completeness))

    # --- Trajectory signals ---
    field_confidences = [
        max(0.0, min(1.0, (1.0 if f.ground_truth_correct else 0.2) + rng.normal(0, noise_level)))
        for f in doc.fields
    ]
    avg_field_conf = sum(field_confidences) / len(field_confidences) if field_confidences else 0.0
    conf_var = sum((c - avg_field_conf) ** 2 for c in field_confidences) / len(field_confidences) if field_confidences else 0.0

    return ConfidenceSignals(
        doc_id=doc.doc_id,
        nutrient_confidence=nutrient_confidence,
        match_label=match_label,
        match_score=match_score,
        grounding_score=grounding_score,
        margin_score=margin_score,
        cross_doc_consistency=cross_doc_consistency,
        field_completeness=field_completeness,
        field_count=n_fields,
        avg_field_confidence=avg_field_conf,
        confidence_variance=conf_var,
        should_sign=doc.should_sign,
        difficulty=doc.difficulty,
        hard_world=doc.hard_world.value,
        doc_type=doc.doc_type,
    )


def signals_to_vector(sig: ConfidenceSignals) -> list[float]:
    """Convert signals to a flat numeric vector for calibration."""
    match_map = {"id_match": 1.0, "fuzzy_match": 0.5, "not_found": 0.0}
    return [
        sig.nutrient_confidence,
        match_map.get(sig.match_label, 0.0),
        sig.grounding_score,
        sig.margin_score,
        sig.cross_doc_consistency,
        sig.field_completeness,
        sig.avg_field_confidence,
        sig.confidence_variance,
        sig.field_count / 10.0,  # normalize
        sig.difficulty,
    ]


SIGNAL_NAMES = [
    "nutrient_confidence",
    "match_score",
    "grounding_score",
    "margin_score",
    "cross_doc_consistency",
    "field_completeness",
    "avg_field_confidence",
    "confidence_variance",
    "field_count_norm",
    "difficulty",
]
