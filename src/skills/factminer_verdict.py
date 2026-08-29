"""FactMiner verdict skill — 4-way verification of extracted facts.

Maps to FactMiner's TypedDag architecture:
- SUPPORTED: fact verified against evidence
- REFUTED: fact contradicted by evidence
- CONFLICTING: sources disagree
- INSUFFICIENT: not enough evidence to verify

Each verdict carries a score for the calibration layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ============================================================
# Verdict types
# ============================================================

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
CONFLICTING = "CONFLICTING"
INSUFFICIENT = "INSUFFICIENT"


@dataclass
class FactVerdict:
    """Verdict on a single extracted fact."""
    field: str
    value: Any
    verdict: str  # SUPPORTED / REFUTED / CONFLICTING / INSUFFICIENT
    confidence: float = 0.0
    evidence: list[dict] = field(default_factory=list)  # source references
    detail: str = ""

    @property
    def score(self) -> float:
        """Numeric score for calibration (1=verified, 0=refuted/insufficient)."""
        return {"SUPPORTED": 1.0, "REFUTED": 0.0, "CONFLICTING": 0.3, "INSUFFICIENT": 0.0}.get(self.verdict, 0.0)

    @property
    def action(self) -> str:
        """Routing action based on verdict."""
        return {"SUPPORTED": "AUTO_APPROVE", "REFUTED": "REJECT", "CONFLICTING": "HUMAN_REVIEW", "INSUFFICIENT": "HUMAN_REVIEW"}.get(self.verdict, "HUMAN_REVIEW")


# ============================================================
# Deterministic checks (from ProofDesk reconciliation engine)
# ============================================================

def check_numeric_match(extracted: str, expected: str, tolerance: float = 0.01) -> bool:
    """Check if two numeric values match within tolerance."""
    try:
        ext_num = float(str(extracted).replace("$", "").replace(",", "").strip())
        exp_num = float(str(expected).replace("$", "").replace(",", "").strip())
        if exp_num == 0:
            return ext_num == 0
        return abs(ext_num - exp_num) / abs(exp_num) <= tolerance
    except (ValueError, TypeError):
        return False


def check_date_match(extracted: str, expected: str) -> bool:
    """Check if two dates match (various formats)."""
    ext = str(extracted).strip().lower()
    exp = str(expected).strip().lower()
    if ext == exp:
        return True
    # Try parsing common formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y"]:
        try:
            from datetime import datetime
            ext_dt = datetime.strptime(extracted.split("T")[0], fmt)
            exp_dt = datetime.strptime(expected.split("T")[0], fmt)
            return ext_dt == exp_dt
        except (ValueError, TypeError):
            continue
    return False


def check_string_match(extracted: str, expected: str, fuzzy: bool = True) -> tuple[bool, str]:
    """Check string match. Returns (match, label)."""
    ext = str(extracted).strip()
    exp = str(expected).strip()
    if ext.lower() == exp.lower():
        return True, "id_match"
    if fuzzy and (exp.lower() in ext.lower() or ext.lower() in exp.lower()):
        return True, "id_match_partial"
    # Check if they share significant tokens
    ext_tokens = set(ext.lower().split())
    exp_tokens = set(exp.lower().split())
    overlap = ext_tokens & exp_tokens
    if len(overlap) >= min(len(ext_tokens), len(exp_tokens)) * 0.5:
        return True, "fuzzy_match"
    return False, "not_found"


# ============================================================
# Verifier — deterministic 4-way verdict
# ============================================================

class FactMinerVerifier:
    """Verify extracted facts against ground truth or cross-document evidence.

    Usage:
        verifier = FactMinerVerifier()
        verdicts = verifier.verify(extracted, ground_truth)
        for v in verdicts:
            print(f"{v.field}: {v.verdict} (score={v.score})")
    """

    def verify(
        self,
        extracted: dict,
        ground_truth: dict,
        cross_doc_facts: list[dict] | None = None,
    ) -> list[FactVerdict]:
        """Verify each extracted field against ground truth.

        Args:
            extracted: {field: value} from extraction
            ground_truth: {field: expected_value}
            cross_doc_facts: Optional list of {field: value} from other documents

        Returns:
            List of FactVerdict for each field
        """
        verdicts = []

        for field_name, expected in ground_truth.items():
            ext_val = extracted.get(field_name)

            # Case 1: Not extracted → INSUFFICIENT
            if ext_val is None:
                verdicts.append(FactVerdict(
                    field=field_name,
                    value=None,
                    verdict=INSUFFICIENT,
                    detail="Field not extracted",
                ))
                continue

            # Case 2: Numeric comparison
            if isinstance(expected, (int, float)) or (isinstance(expected, str) and expected.replace(".", "").replace(",", "").isdigit()):
                if check_numeric_match(ext_val, expected):
                    verdicts.append(FactVerdict(
                        field=field_name,
                        value=ext_val,
                        verdict=SUPPORTED,
                        confidence=0.95,
                        detail=f"Numeric match: {ext_val} == {expected}",
                    ))
                else:
                    verdicts.append(FactVerdict(
                        field=field_name,
                        value=ext_val,
                        verdict=REFUTED,
                        confidence=0.9,
                        detail=f"Numeric mismatch: {ext_val} != {expected}",
                    ))
                continue

            # Case 3: Date comparison
            if isinstance(expected, str) and re.match(r"\d{4}[-/]\d{2}[-/]\d{2}", str(expected)):
                if check_date_match(str(ext_val), str(expected)):
                    verdicts.append(FactVerdict(
                        field=field_name,
                        value=ext_val,
                        verdict=SUPPORTED,
                        confidence=0.9,
                        detail=f"Date match: {ext_val} == {expected}",
                    ))
                else:
                    verdicts.append(FactVerdict(
                        field=field_name,
                        value=ext_val,
                        verdict=REFUTED,
                        confidence=0.85,
                        detail=f"Date mismatch: {ext_val} != {expected}",
                    ))
                continue

            # Case 4: String comparison
            match, label = check_string_match(str(ext_val), str(expected))
            if match:
                verdicts.append(FactVerdict(
                    field=field_name,
                    value=ext_val,
                    verdict=SUPPORTED,
                    confidence=0.9 if label == "id_match" else 0.7,
                    detail=f"String {label}: '{ext_val}' ~ '{expected}'",
                ))
            else:
                # Check cross-document consistency
                if cross_doc_facts:
                    cross_vals = [cf.get(field_name) for cf in cross_doc_facts if cf.get(field_name)]
                    if cross_vals:
                        all_match = all(
                            check_string_match(str(v), str(expected))[0] or check_string_match(str(v), str(ext_val))[0]
                            for v in cross_vals
                        )
                        if not all_match:
                            verdicts.append(FactVerdict(
                                field=field_name,
                                value=ext_val,
                                verdict=CONFLICTING,
                                confidence=0.5,
                                detail=f"Cross-doc conflict: extracted='{ext_val}', expected='{expected}', cross-doc={cross_vals}",
                            ))
                            continue

                verdicts.append(FactVerdict(
                    field=field_name,
                    value=ext_val,
                    verdict=REFUTED,
                    confidence=0.8,
                    detail=f"String mismatch: '{ext_val}' != '{expected}'",
                ))

        return verdicts

    def verify_fields(
        self,
        extracted: dict,
        ground_truth: dict,
    ) -> dict[str, FactVerdict]:
        """Verify and return as dict keyed by field name."""
        verdicts = self.verify(extracted, ground_truth)
        return {v.field: v for v in verdicts}

    def summary(self, verdicts: list[FactVerdict]) -> dict:
        """Summarize verdicts."""
        total = len(verdicts)
        if total == 0:
            return {"total": 0, "supported": 0, "refuted": 0, "conflicting": 0, "insufficient": 0}

        supported = sum(1 for v in verdicts if v.verdict == SUPPORTED)
        refuted = sum(1 for v in verdicts if v.verdict == REFUTED)
        conflicting = sum(1 for v in verdicts if v.verdict == CONFLICTING)
        insufficient = sum(1 for v in verdicts if v.verdict == INSUFFICIENT)

        return {
            "total": total,
            "supported": supported,
            "refuted": refuted,
            "conflicting": conflicting,
            "insufficient": insufficient,
            "support_rate": round(supported / total, 3),
        }
