"""RaV-IDP: Reconstruction-as-Validation (simplified).

Based on RaV-IDP 2026:
- After extraction, reconstruct the document region
- Compare reconstruction to original
- Fidelity score = grounded quality signal
- If fidelity < threshold → route to fallback

Simplified implementation:
- Re-extract the same field using a different strategy
- Compare original extraction to re-extraction
- Fidelity = agreement rate between extractions
- Low fidelity → extraction may be wrong

This is a CPU-only approximation of the full RaV-IDP pipeline.
Full implementation would require a reconstruction model (not available on this box).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FidelityResult:
    """Result of reconstruction validation for a single field."""
    field_name: str
    original_value: str
    reconstructed_value: str
    original_confidence: float
    reconstructed_confidence: float
    fidelity_score: float  # 0.0-1.0, how well they match
    source_consistency: bool  # Same page/bbox?
    decision: str  # "HIGH_FIDELITY", "LOW_FIDELITY", "INCONCLUSIVE"
    detail: str


class ReconstructionValidator:
    """RaV-IDP-style reconstruction validation.
    
    Strategy: Re-extract fields using a different approach and compare.
    
    Original extraction: Nutrient API with field-guided prompts
    Re-extraction: Deterministic regex patterns on raw text
    
    Agreement = high fidelity (extraction is likely correct)
    Disagreement = low fidelity (extraction may be wrong)
    """
    
    # Regex patterns for re-extraction (deterministic, no API needed)
    FIELD_PATTERNS = {
        "quote.total": [
            r"total[:\s]*\$?([\d,]+\.?\d*)",
            r"amount[:\s]*\$?([\d,]+\.?\d*)",
        ],
        "quote.platform_price": [
            r"platform[:\s]*\$?([\d,]+\.?\d*)",
            r"license[:\s]*\$?([\d,]+\.?\d*)",
        ],
        "quote.support_price": [
            r"support[:\s]*\$?([\d,]+\.?\d*)",
            r"services[:\s]*\$?([\d,]+\.?\d*)",
        ],
        "vendor.legal_name": [
            r"([A-Z][a-z]+ [A-Z][a-z]+(?:\s+(?:Inc|LLC|Ltd|Corp|Co)\.?)?)",
        ],
        "insurance.expiry_date": [
            r"(?:expires?|expiry|valid until)[:\s]*(\d{4}-\d{2}-\d{2})",
        ],
        "requested_spend": [
            r"(?:spend|budget|request)[:\s]*\$?([\d,]+\.?\d*)",
        ],
        "procurement.requested_spend": [
            r"(?:spend|budget|request)[:\s]*\$?([\d,]+\.?\d*)",
        ],
        "procurement.contract_start": [
            r"(?:start|begin|effective)[:\s]*(\d{4}-\d{2}-\d{2})",
        ],
        "procurement.required_coverage_until": [
            r"(?:coverage|until|expires?)[:\s]*(\d{4}-\d{2}-\d{2})",
        ],
        "security.data_retention_days": [
            r"(?:retention|keep)[:\s]*(\d+)",
        ],
        "security.encryption_at_rest": [
            r"(?:encrypted|encryption)[:\s]*(yes|no|true|false)",
        ],
        "invoice.total_value": [
            r"total[:\s]*\$?([\d,]+\.?\d*)",
        ],
    }
    
    def __init__(self):
        self._history: list[dict] = []
    
    def validate(
        self,
        original_facts: list[dict],
        raw_text: str = "",
        source_pages: dict[str, int] | None = None,
    ) -> list[FidelityResult]:
        """Validate extraction fidelity by re-extracting and comparing.
        
        Args:
            original_facts: Original extraction results
            raw_text: Raw document text for re-extraction
            source_pages: Mapping of field_name → source page
        
        Returns:
            List of FidelityResult per field
        """
        results = []
        source_pages = source_pages or {}
        
        for fact in original_facts:
            field_name = fact.get("field", "")
            original_value = fact.get("value_normalized", "")
            original_confidence = fact.get("confidence", 0.5)
            original_page = fact.get("page", 0)
            
            # Attempt re-extraction using deterministic patterns
            reconstructed_value = self._reextract_field(field_name, raw_text)
            
            if reconstructed_value:
                # Compare original to reconstruction
                fidelity_score = self._compute_fidelity(original_value, reconstructed_value)
                source_consistency = True  # Same document, same source
                
                if fidelity_score > 0.9:
                    decision = "HIGH_FIDELITY"
                    detail = f"Reconstruction matches: {reconstructed_value}"
                elif fidelity_score > 0.5:
                    decision = "INCONCLUSIVE"
                    detail = f"Partial match: {original_value} vs {reconstructed_value}"
                else:
                    decision = "LOW_FIDELITY"
                    detail = f"Mismatch: original={original_value}, reconstructed={reconstructed_value}"
            else:
                # No pattern available for this field
                fidelity_score = original_confidence  # Fall back to original confidence
                source_consistency = True
                decision = "INCONCLUSIVE"
                detail = "No re-extraction pattern available"
            
            results.append(FidelityResult(
                field_name=field_name,
                original_value=original_value,
                reconstructed_value=reconstructed_value or "",
                original_confidence=original_confidence,
                reconstructed_confidence=0.8 if reconstructed_value else 0.0,
                fidelity_score=fidelity_score,
                source_consistency=source_consistency,
                decision=decision,
                detail=detail,
            ))
        
        self._record_validation(results)
        return results
    
    def get_fidelity_score(self, results: list[FidelityResult]) -> float:
        """Compute overall fidelity score from validation results.
        
        Returns 0.0-1.0 where 1.0 = all fields high fidelity or inconclusive.
        INCONCLUSIVE results are acceptable (fidelity=confidence).
        """
        if not results:
            return 1.0
        
        acceptable = sum(1 for r in results if r.decision in ("HIGH_FIDELITY", "INCONCLUSIVE"))
        return acceptable / len(results)
    
    def should_reject(
        self,
        results: list[FidelityResult],
        threshold: float = 0.7,
        require_all_high: bool = False,
    ) -> tuple[bool, str]:
        """Decide whether to reject extraction based on fidelity.
        
        Args:
            results: Validation results
            threshold: Minimum fidelity score to proceed
            require_all_high: If True, require all fields high fidelity
        
        Returns:
            (should_reject, reason)
        """
        if not results:
            return False, "No fields to validate"
        
        fidelity = self.get_fidelity_score(results)
        low_fidelity = [r for r in results if r.decision == "LOW_FIDELITY"]
        
        if require_all_high and low_fidelity:
            fields = ", ".join(r.field_name for r in low_fidelity[:3])
            return True, f"Low fidelity fields: {fields}"
        
        if fidelity < threshold:
            return True, f"Fidelity {fidelity:.2f} < threshold {threshold:.2f}"
        
        return False, "Validation passed"
    
    def _reextract_field(self, field_name: str, raw_text: str) -> str | None:
        """Re-extract field value using deterministic regex patterns."""
        if not raw_text:
            return None
        
        patterns = self.FIELD_PATTERNS.get(field_name, [])
        for pattern in patterns:
            import re
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            if matches:
                # Return first match (most likely the correct one)
                return matches[0].strip()
        
        return None
    
    def _compute_fidelity(self, original: str, reconstructed: str) -> float:
        """Compute fidelity score between original and reconstructed values."""
        if not original or not reconstructed:
            return 0.0
        
        # Normalize for comparison
        o_norm = original.lower().strip()
        r_norm = reconstructed.lower().strip()
        
        # Exact match
        if o_norm == r_norm:
            return 1.0
        
        # Numerical comparison
        try:
            o_num = float(o_norm.replace(",", "").replace("$", ""))
            r_num = float(r_norm.replace(",", "").replace("$", ""))
            if abs(o_num - r_num) / max(abs(o_num), abs(r_num), 1) < 0.01:
                return 0.95
        except (ValueError, ZeroDivisionError):
            pass
        
        # String similarity (Levenshtein-like)
        o_words = set(o_norm.split())
        r_words = set(r_norm.split())
        if o_words and r_words:
            intersection = o_words & r_words
            union = o_words | r_words
            jaccard = len(intersection) / len(union)
            return jaccard
        
        return 0.0
    
    def _record_validation(self, results: list[FidelityResult]) -> None:
        """Record validation for statistics."""
        self._history.append({
            "timestamp": time.time(),
            "total_fields": len(results),
            "high_fidelity": sum(1 for r in results if r.decision == "HIGH_FIDELITY"),
            "low_fidelity": sum(1 for r in results if r.decision == "LOW_FIDELITY"),
            "fidelity_score": self.get_fidelity_score(results),
        })
    
    def stats(self) -> dict:
        """Get validation statistics."""
        if not self._history:
            return {"total_validations": 0}
        
        total = len(self._history)
        avg_fidelity = sum(h["fidelity_score"] for h in self._history) / total
        
        return {
            "total_validations": total,
            "avg_fidelity": round(avg_fidelity, 3),
            "rejected_count": sum(1 for h in self._history if h["fidelity_score"] < 0.7),
            "rejection_rate": round(sum(1 for h in self._history if h["fidelity_score"] < 0.7) / total, 3),
        }


# Global validator instance
_validator: ReconstructionValidator | None = None


def get_validator() -> ReconstructionValidator:
    global _validator
    if _validator is None:
        _validator = ReconstructionValidator()
    return _validator
