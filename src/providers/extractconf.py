"""EXTRACTCONF: Dual-call extraction verification.

Based on Kumar 2026 (EXTRACTCONF):
- Hunter call: field-guided extraction (what fields to look for)
- Mapper call: document-guided extraction (what the document contains)
- Disagreement = reliability signal
- If Hunter ≠ Mapper → defer to human

Key insight: OCR confidence > logprobs for extraction errors.
Hunter-Mapper disagreement = strongest signal for unreliable extraction.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    """Result from a single extraction call."""
    field_name: str
    value: str
    confidence: float
    source_page: int = 0
    source_bbox: list[float] = field(default_factory=list)
    extraction_method: str = ""  # "hunter" or "mapper"


@dataclass
class VerificationResult:
    """Result of dual-call verification."""
    field_name: str
    hunter_value: str
    mapper_value: str
    hunter_confidence: float
    mapper_confidence: float
    agreement: bool
    disagreement_score: float  # 0.0 = perfect agreement, 1.0 = complete disagreement
    decision: str  # "AGREED", "DISAGREED", "PARTIAL_MATCH"
    detail: str


class DualCallVerifier:
    """EXTRACTCONF-style dual-call extraction verification.
    
    Two independent extraction calls:
    1. Hunter: "Extract field X from this document"
    2. Mapper: "What fields are in this document?"
    
    Disagreement indicates extraction unreliability.
    """
    
    def __init__(self):
        self._history: list[dict] = []
    
    def verify(
        self,
        hunter_facts: list[dict],
        mapper_facts: list[dict],
        tolerance: float = 0.0,
    ) -> list[VerificationResult]:
        """Compare Hunter and Mapper extractions field-by-field.
        
        Args:
            hunter_facts: Extracted facts from Hunter call (field-guided)
            mapper_facts: Extracted facts from Mapper call (document-guided)
            tolerance: Numerical tolerance for value comparison
        
        Returns:
            List of VerificationResult per field
        """
        results = []
        
        # Index by field name
        hunter_by_field = {f.get("field", ""): f for f in hunter_facts}
        mapper_by_field = {f.get("field", ""): f for f in mapper_facts}
        
        # Check all fields from both calls
        all_fields = set(hunter_by_field.keys()) | set(mapper_by_field.keys())
        
        for field_name in all_fields:
            hunter = hunter_by_field.get(field_name)
            mapper = mapper_by_field.get(field_name)
            
            if not hunter or not mapper:
                # Missing from one call
                results.append(VerificationResult(
                    field_name=field_name,
                    hunter_value=hunter.get("value_normalized", "") if hunter else "",
                    mapper_value=mapper.get("value_normalized", "") if mapper else "",
                    hunter_confidence=hunter.get("confidence", 0.0) if hunter else 0.0,
                    mapper_confidence=mapper.get("confidence", 0.0) if mapper else 0.0,
                    agreement=False,
                    disagreement_score=1.0,
                    decision="DISAGREED",
                    detail=f"Field missing from {'mapper' if hunter else 'hunter'} call",
                ))
                continue
            
            # Compare values
            h_val = hunter.get("value_normalized", "")
            m_val = mapper.get("value_normalized", "")
            h_conf = hunter.get("confidence", 0.5)
            m_conf = mapper.get("confidence", 0.5)
            
            # Normalize for comparison
            h_normalized = self._normalize_for_comparison(h_val)
            m_normalized = self._normalize_for_comparison(m_val)
            
            # Check agreement
            if h_normalized == m_normalized:
                agreement = True
                disagreement_score = 0.0
                decision = "AGREED"
                detail = f"Exact match: {h_val}"
            elif self._fuzzy_match(h_normalized, m_normalized, tolerance):
                agreement = True
                disagreement_score = 0.1
                decision = "PARTIAL_MATCH"
                detail = f"Fuzzy match: {h_val} ≈ {m_val}"
            else:
                agreement = False
                # Disagreement score based on confidence difference
                conf_diff = abs(h_conf - m_conf)
                disagreement_score = min(1.0, 0.5 + conf_diff)
                decision = "DISAGREED"
                detail = f"Mismatch: hunter={h_val}, mapper={m_val}"
            
            results.append(VerificationResult(
                field_name=field_name,
                hunter_value=h_val,
                mapper_value=m_val,
                hunter_confidence=h_conf,
                mapper_confidence=m_conf,
                agreement=agreement,
                disagreement_score=disagreement_score,
                decision=decision,
                detail=detail,
            ))
        
        # Record for statistics
        self._record_verification(results)
        
        return results
    
    def get_reliability_score(self, results: list[VerificationResult]) -> float:
        """Compute overall reliability score from verification results.
        
        Returns 0.0-1.0 where 1.0 = all fields agreed.
        """
        if not results:
            return 1.0
        
        agreed = sum(1 for r in results if r.agreement)
        return agreed / len(results)
    
    def should_defer(
        self,
        results: list[VerificationResult],
        threshold: float = 0.8,
        require_all_agreed: bool = False,
    ) -> tuple[bool, str]:
        """Decide whether to defer to human based on verification.
        
        Args:
            results: Verification results
            threshold: Minimum reliability score to proceed
            require_all_agreed: If True, require 100% agreement
        
        Returns:
            (should_defer, reason)
        """
        if not results:
            return False, "No fields to verify"
        
        reliability = self.get_reliability_score(results)
        disagreed = [r for r in results if not r.agreement]
        
        if require_all_agreed and disagreed:
            fields = ", ".join(r.field_name for r in disagreed[:3])
            return True, f"Fields disagree: {fields}"
        
        if reliability < threshold:
            return True, f"Reliability {reliability:.2f} < threshold {threshold:.2f}"
        
        # Check for high-confidence disagreements
        high_conf_disagreed = [
            r for r in disagreed 
            if r.hunter_confidence > 0.9 or r.mapper_confidence > 0.9
        ]
        if high_conf_disagreed:
            fields = ", ".join(r.field_name for r in high_conf_disagreed[:3])
            return True, f"High-confidence disagreement on: {fields}"
        
        return False, "Verification passed"
    
    def _normalize_for_comparison(self, value: str) -> str:
        """Normalize value for comparison (lowercase, strip whitespace)."""
        if not value:
            return ""
        return str(value).lower().strip()
    
    def _fuzzy_match(self, a: str, b: str, tolerance: float) -> bool:
        """Check if two values are fuzzy matches."""
        if not a or not b:
            return False
        
        # Exact match
        if a == b:
            return True
        
        # Numerical comparison with tolerance
        try:
            a_num = float(a.replace(",", "").replace("$", ""))
            b_num = float(b.replace(",", "").replace("$", ""))
            if tolerance > 0 and abs(a_num - b_num) <= tolerance:
                return True
            if abs(a_num - b_num) / max(abs(a_num), abs(b_num), 1) < 0.01:
                return True
        except (ValueError, ZeroDivisionError):
            pass
        
        # String similarity (Jaccard)
        a_words = set(a.split())
        b_words = set(b.split())
        if a_words and b_words:
            intersection = a_words & b_words
            union = a_words | b_words
            jaccard = len(intersection) / len(union)
            if jaccard > 0.8:
                return True
        
        return False
    
    def _record_verification(self, results: list[VerificationResult]) -> None:
        """Record verification for statistics."""
        self._history.append({
            "timestamp": time.time(),
            "total_fields": len(results),
            "agreed": sum(1 for r in results if r.agreement),
            "disagreed": sum(1 for r in results if not r.agreement),
            "reliability": self.get_reliability_score(results),
        })
    
    def stats(self) -> dict:
        """Get verification statistics."""
        if not self._history:
            return {"total_verifications": 0}
        
        total = len(self._history)
        avg_reliability = sum(h["reliability"] for h in self._history) / total
        avg_disagreed = sum(h["disagreed"] for h in self._history) / total
        
        return {
            "total_verifications": total,
            "avg_reliability": round(avg_reliability, 3),
            "avg_disagreed_per_doc": round(avg_disagreed, 2),
            "deferred_count": sum(1 for h in self._history if h["reliability"] < 0.8),
        }


# Global verifier instance
_verifier: DualCallVerifier | None = None


def get_verifier() -> DualCallVerifier:
    global _verifier
    if _verifier is None:
        _verifier = DualCallVerifier()
    return _verifier
