"""ConfBench: Distribution shift monitoring.

Based on ConfBench (Amazon, 2026):
- Track confidence distribution over time
- Detect drift via KS test or PSI
- Alert when distribution shifts significantly
- Retrain on new data

Key findings from ConfBench:
- OCR+Image modality = best confidence estimates
- Model capability dominates (not parameter count)
- Log-probability with first-token aggregation wins

This module monitors:
- Confidence score distributions
- Extraction quality metrics
- Decision distribution (AUTO_SIGN / DEFER / REJECT)
- Drift detection via PSI (Population Stability Index)
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import Any
from collections import deque


@dataclass
class DistributionSnapshot:
    """Point-in-time distribution of confidence scores."""
    timestamp: float
    confidence_scores: list[float]
    decisions: dict[str, int]  # AUTO_SIGN: 3, DEFER: 2, etc.
    doc_types: dict[str, int]
    
    @property
    def mean_confidence(self) -> float:
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores) / len(self.confidence_scores)
    
    @property
    def median_confidence(self) -> float:
        if not self.confidence_scores:
            return 0.0
        sorted_scores = sorted(self.confidence_scores)
        n = len(sorted_scores)
        if n % 2 == 0:
            return (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2
        return sorted_scores[n//2]
    
    @property
    def std_confidence(self) -> float:
        if len(self.confidence_scores) < 2:
            return 0.0
        mean = self.mean_confidence
        variance = sum((x - mean) ** 2 for x in self.confidence_scores) / (len(self.confidence_scores) - 1)
        return math.sqrt(variance)


class DistributionMonitor:
    """ConfBench-style distribution shift monitoring.
    
    Tracks confidence distributions over time and detects drift.
    
    PSI (Population Stability Index):
    - PSI < 0.1: No significant shift
    - 0.1 <= PSI < 0.25: Moderate shift (warning)
    - PSI >= 0.25: Significant shift (alert)
    """
    
    # PSI thresholds
    PSI_NO_SHIFT = 0.1
    PSI_MODERATE_SHIFT = 0.25
    
    def __init__(self, window_size: int = 100):
        """
        Args:
            window_size: Number of documents to keep in history
        """
        self.window_size = window_size
        self._history: deque[DistributionSnapshot] = deque(maxlen=window_size)
        self._baseline: DistributionSnapshot | None = None
        self._alerts: list[dict] = []
    
    def record_batch(
        self,
        confidence_scores: list[float],
        decisions: dict[str, int],
        doc_types: dict[str, int],
    ) -> DistributionSnapshot:
        """Record a batch of results for monitoring."""
        snapshot = DistributionSnapshot(
            timestamp=time.time(),
            confidence_scores=confidence_scores,
            decisions=decisions,
            doc_types=doc_types,
        )
        self._history.append(snapshot)
        
        # Check for drift
        if self._baseline:
            drift = self.detect_drift(snapshot)
            if drift["psi"] >= self.PSI_MODERATE_SHIFT:
                self._alerts.append({
                    "timestamp": time.time(),
                    "type": "SIGNIFICANT_SHIFT",
                    "psi": drift["psi"],
                    "detail": drift["detail"],
                })
            elif drift["psi"] >= self.PSI_NO_SHIFT:
                self._alerts.append({
                    "timestamp": time.time(),
                    "type": "MODERATE_SHIFT",
                    "psi": drift["psi"],
                    "detail": drift["detail"],
                })
        
        return snapshot
    
    def set_baseline(self, snapshot: DistributionSnapshot | None = None):
        """Set baseline distribution for drift detection."""
        if snapshot:
            self._baseline = snapshot
        elif self._history:
            self._baseline = self._history[-1]
    
    def detect_drift(self, current: DistributionSnapshot | None = None) -> dict:
        """Detect distribution shift between baseline and current.
        
        Returns:
            dict with psi, ks_statistic, detail
        """
        if not self._baseline:
            return {"psi": 0.0, "ks_statistic": 0.0, "detail": "No baseline set"}
        
        if not current and not self._history:
            return {"psi": 0.0, "ks_statistic": 0.0, "detail": "No current data"}
        
        current = current or self._history[-1]
        
        # Compute PSI
        psi = self._compute_psi(
            self._baseline.confidence_scores,
            current.confidence_scores,
        )
        
        # Compute KS statistic
        ks_statistic = self._compute_ks(
            self._baseline.confidence_scores,
            current.confidence_scores,
        )
        
        # Determine detail
        if psi >= self.PSI_MODERATE_SHIFT:
            detail = f"Significant shift: PSI={psi:.3f} (threshold={self.PSI_MODERATE_SHIFT})"
        elif psi >= self.PSI_NO_SHIFT:
            detail = f"Moderate shift: PSI={psi:.3f} (threshold={self.PSI_NO_SHIFT})"
        else:
            detail = f"No significant shift: PSI={psi:.3f}"
        
        return {
            "psi": round(psi, 4),
            "ks_statistic": round(ks_statistic, 4),
            "detail": detail,
            "baseline_mean": round(self._baseline.mean_confidence, 3),
            "current_mean": round(current.mean_confidence, 3),
            "mean_shift": round(current.mean_confidence - self._baseline.mean_confidence, 3),
        }
    
    def _compute_psi(self, baseline: list[float], current: list[float], bins: int = 10) -> float:
        """Compute Population Stability Index (PSI).
        
        PSI = sum((current% - baseline%) * ln(current% / baseline%))
        
        Args:
            baseline: Baseline distribution
            current: Current distribution
            bins: Number of bins for histogram
        
        Returns:
            PSI value (0.0 = no shift, >0.25 = significant shift)
        """
        if not baseline or not current:
            return 0.0
        
        # Create bins from baseline
        min_val = min(min(baseline), min(current))
        max_val = max(max(baseline), max(current))
        
        if min_val == max_val:
            return 0.0
        
        bin_edges = [min_val + (max_val - min_val) * i / bins for i in range(bins + 1)]
        
        # Count in each bin
        baseline_counts = self._count_in_bins(baseline, bin_edges)
        current_counts = self._count_in_bins(current, bin_edges)
        
        # Convert to proportions
        baseline_total = len(baseline)
        current_total = len(current)
        
        psi = 0.0
        for b, c in zip(baseline_counts, current_counts):
            # Avoid division by zero
            b_pct = (b + 1) / (baseline_total + bins)  # Laplace smoothing
            c_pct = (c + 1) / (current_total + bins)
            
            psi += (c_pct - b_pct) * math.log(c_pct / b_pct)
        
        return psi
    
    def _compute_ks(self, sample1: list[float], sample2: list[float]) -> float:
        """Compute Kolmogorov-Smirnov statistic between two samples."""
        if not sample1 or not sample2:
            return 0.0
        
        sorted1 = sorted(sample1)
        sorted2 = sorted(sample2)
        
        n1, n2 = len(sorted1), len(sorted2)
        i, j = 0, 0
        max_diff = 0.0
        
        while i < n1 and j < n2:
            if sorted1[i] < sorted2[j]:
                cdf1 = (i + 1) / n1
                cdf2 = j / n2
                i += 1
            else:
                cdf1 = i / n1
                cdf2 = (j + 1) / n2
                j += 1
            
            max_diff = max(max_diff, abs(cdf1 - cdf2))
        
        return max_diff
    
    def _count_in_bins(self, data: list[float], bin_edges: list[float]) -> list[int]:
        """Count data points in each bin."""
        counts = [0] * (len(bin_edges) - 1)
        
        for value in data:
            for i in range(len(bin_edges) - 1):
                if bin_edges[i] <= value < bin_edges[i + 1]:
                    counts[i] += 1
                    break
            else:
                # Value == max edge
                if value == bin_edges[-1] and len(counts) > 0:
                    counts[-1] += 1
        
        return counts
    
    def get_recommendation(self) -> dict:
        """Get recommendation based on current distribution state."""
        if not self._history:
            return {"action": "COLLECT_DATA", "detail": "No data collected yet"}
        
        drift = self.detect_drift()
        
        if drift["psi"] >= self.PSI_MODERATE_SHIFT:
            return {
                "action": "ALERT",
                "detail": f"Significant distribution shift detected (PSI={drift['psi']:.3f}). "
                         f"Consider retraining or adjusting thresholds.",
                "severity": "HIGH",
            }
        elif drift["psi"] >= self.PSI_NO_SHIFT:
            return {
                "action": "WARNING",
                "detail": f"Moderate distribution shift detected (PSI={drift['psi']:.3f}). "
                         f"Monitor closely.",
                "severity": "MEDIUM",
            }
        else:
            return {
                "action": "OK",
                "detail": f"Distribution stable (PSI={drift['psi']:.3f}).",
                "severity": "LOW",
            }
    
    def stats(self) -> dict:
        """Get monitoring statistics."""
        if not self._history:
            return {"total_batches": 0, "alerts": 0}
        
        total = len(self._history)
        latest = self._history[-1]
        
        return {
            "total_batches": total,
            "latest_mean_confidence": round(latest.mean_confidence, 3),
            "latest_median_confidence": round(latest.median_confidence, 3),
            "latest_std_confidence": round(latest.std_confidence, 3),
            "alerts": len(self._alerts),
            "recent_alerts": self._alerts[-5:] if self._alerts else [],
            "recommendation": self.get_recommendation(),
        }


# Global monitor instance
_monitor: DistributionMonitor | None = None


def get_monitor() -> DistributionMonitor:
    global _monitor
    if _monitor is None:
        _monitor = DistributionMonitor()
    return _monitor
