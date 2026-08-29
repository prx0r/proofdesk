"""Multi-signal confidence fusion — combines all signals into routing decisions.

Pipeline:
  Nutrient Extract → Citations → Fusion → Calibration → Threshold → Route

Signals fused:
  1. Nutrient confidence (model probability signal)
  2. Nutrient match label (deterministic grounding check — non-hallucinated)
  3. FactMiner verdict (4-way verification)
  4. Cross-document consistency (multi-doc reasoning)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .calibration import (
    ConfidenceCalibrator,
    ConfidenceSignals,
    MATCH_LABEL_SCORES,
    verdict_to_score,
)
from .factminer_verdict import FactVerdict, FactMinerVerifier


# ============================================================
# Fusion result for a single field
# ============================================================

@dataclass
class FusedResult:
    """Result of fusing all confidence signals for a single field."""
    field: str
    value: Any
    expected: Any = None  # ground truth (for evaluation)
    # Raw signals
    nutrient_confidence: float | None = None
    match_label: str | None = None
    match_score: float = 0.0
    factminer_verdict: str | None = None
    factminer_score: float = 0.0
    cross_doc_consistent: bool | None = None
    # Calibrated output
    raw_score: float = 0.0
    calibrated_confidence: float = 0.0
    action: str = "HUMAN_REVIEW"
    # Metadata
    source_page: int | None = None
    bbox: dict | None = None

    @property
    def correct(self) -> bool | None:
        """Was the extraction correct? None if no ground truth."""
        if self.expected is None:
            return None
        return str(self.value).strip().lower() == str(self.expected).strip().lower()

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "expected": self.expected,
            "verdict": self.factminer_verdict,
            "match": self.match_label,
            "nutrient_confidence": self.nutrient_confidence,
            "raw_score": round(self.raw_score, 4),
            "calibrated_confidence": round(self.calibrated_confidence, 4),
            "action": self.action,
            "correct": self.correct,
        }


# ============================================================
# Multi-signal fuser
# ============================================================

class MultiSignalFuser:
    """Fuse Nutrient citations, FactMiner verdicts, and cross-doc evidence
    into calibrated routing decisions.

    Usage:
        fuser = MultiSignalFuser()
        # Calibrate on labeled data
        fuser.calibrate(labeled_data)
        # Then fuse new extractions
        results = fuser.fuse(extraction_result, ground_truth)
    """

    def __init__(self, calibrator: ConfidenceCalibrator | None = None):
        self.calibrator = calibrator or ConfidenceCalibrator()
        self.verifier = FactMinerVerifier()

    def fuse_single(
        self,
        field: str,
        value: Any,
        expected: Any = None,
        nutrient_confidence: float | None = None,
        match_label: str | None = None,
        factminer_verdict: str | None = None,
        cross_doc_facts: list[dict] | None = None,
        source_page: int | None = None,
        bbox: dict | None = None,
        thresholds: dict | None = None,
    ) -> FusedResult:
        """Fuse all signals for a single field."""

        # Build signal object
        match_score = MATCH_LABEL_SCORES.get(match_label, 0.5) if match_label else 0.5
        fm_score = verdict_to_score(factminer_verdict) if factminer_verdict else 0.5

        # Cross-doc consistency
        cross_score = 0.5
        cross_consistent = None
        if cross_doc_facts and expected is not None:
            cross_vals = [cf.get(field) for cf in cross_doc_facts if cf.get(field)]
            if cross_vals:
                from .factminer_verdict import check_string_match
                matches = [check_string_match(str(v), str(expected))[0] or
                          check_string_match(str(v), str(value))[0]
                          for v in cross_vals]
                cross_consistent = all(matches)
                cross_score = sum(matches) / len(matches) if matches else 0.5

        signals = ConfidenceSignals(
            field=field,
            value=value,
            nutrient_confidence=nutrient_confidence,
            match_label=match_label,
            match_score=match_score,
            factminer_verdict=factminer_verdict,
            factminer_score=fm_score,
            cross_doc_consistent=cross_consistent,
            cross_doc_score=cross_score,
        )

        # Fuse and calibrate
        raw_score = self.calibrator.fuse_signals(signals)
        calibrated = self.calibrator.calibrate_probability(raw_score)
        action = self.calibrator.route(calibrated, thresholds)

        return FusedResult(
            field=field,
            value=value,
            expected=expected,
            nutrient_confidence=nutrient_confidence,
            match_label=match_label,
            match_score=match_score,
            factminer_verdict=factminer_verdict,
            factminer_score=fm_score,
            cross_doc_consistent=cross_consistent,
            raw_score=raw_score,
            calibrated_confidence=calibrated,
            action=action,
            source_page=source_page,
            bbox=bbox,
        )

    def fuse_extraction(
        self,
        extracted: dict,
        citations: dict,
        ground_truth: dict | None = None,
        cross_doc_facts: list[dict] | None = None,
        thresholds: dict | None = None,
    ) -> list[FusedResult]:
        """Fuse all signals for an entire extraction result.

        Args:
            extracted: {field: value} from Nutrient
            citations: {field: Citation} from Nutrient
            ground_truth: {field: expected_value} for evaluation
            cross_doc_facts: List of {field: value} from other documents
            thresholds: Override routing thresholds

        Returns:
            List of FusedResult, one per field
        """
        results = []

        for field_name, value in extracted.items():
            citation = citations.get(field_name)
            expected = ground_truth.get(field_name) if ground_truth else None

            # FactMiner verdict
            verdict = None
            if expected is not None:
                verdicts = self.verifier.verify({field_name: value}, {field_name: expected})
                if verdicts:
                    verdict = verdicts[0].verdict

            result = self.fuse_single(
                field=field_name,
                value=value,
                expected=expected,
                nutrient_confidence=citation.confidence if citation else None,
                match_label=citation.match if citation else None,
                factminer_verdict=verdict,
                cross_doc_facts=cross_doc_facts,
                source_page=citation.page if citation else None,
                bbox=citation.bbox if citation else None,
                thresholds=thresholds,
            )
            results.append(result)

        return results

    def summary(self, results: list[FusedResult]) -> dict:
        """Summarize fusion results."""
        total = len(results)
        if total == 0:
            return {"total": 0}

        actions = {}
        for r in results:
            actions[r.action] = actions.get(r.action, 0) + 1

        correct_eval = [r for r in results if r.correct is not None]
        correct_count = sum(1 for r in correct_eval if r.correct)

        return {
            "total": total,
            "actions": actions,
            "auto_approve_rate": actions.get("AUTO_APPROVE", 0) / total,
            "human_review_rate": actions.get("HUMAN_REVIEW", 0) / total,
            "reject_rate": actions.get("REJECT", 0) / total,
            "evaluated": len(correct_eval),
            "accuracy": correct_count / len(correct_eval) if correct_eval else None,
            "auto_approve_accuracy": (
                sum(1 for r in correct_eval if r.action == "AUTO_APPROVE" and r.correct) /
                max(actions.get("AUTO_APPROVE", 0), 1)
            ) if correct_eval else None,
        }
