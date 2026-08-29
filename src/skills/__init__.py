"""ProofDesk Skills — composable Nutrient + FactMiner capabilities."""

from .nutrient_extract import (
    NutrientExtractSkill,
    NutrientParseSkill,
    NutrientOCRSkill,
    NutrientRedactSkill,
    NutrientGenerateSkill,
    Citation,
    ExtractionResult,
)
from .calibration import (
    ConfidenceCalibrator,
    ConfidenceSignals,
    MATCH_LABEL_SCORES,
    verdict_to_score,
)
from .factminer_verdict import (
    FactMinerVerifier,
    FactVerdict,
    SUPPORTED,
    REFUTED,
    CONFLICTING,
    INSUFFICIENT,
)
from .multi_signal_fusion import (
    MultiSignalFuser,
    FusedResult,
)

__all__ = [
    "NutrientExtractSkill",
    "NutrientParseSkill",
    "NutrientOCRSkill",
    "NutrientRedactSkill",
    "NutrientGenerateSkill",
    "Citation",
    "ExtractionResult",
    "ConfidenceCalibrator",
    "ConfidenceSignals",
    "FactMinerVerifier",
    "FactVerdict",
    "MultiSignalFuser",
    "FusedResult",
    "SUPPORTED",
    "REFUTED",
    "CONFLICTING",
    "INSUFFICIENT",
]
