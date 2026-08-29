"""Cost Analysis Module — tracks ROI metrics for the demo.

Shows judges the business value:
- Time saved (auto-sign vs manual review)
- Cost per decision
- Fraud prevention savings
- Total ROI
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DecisionCost:
    """Cost breakdown for a single decision."""
    auto_sign_time_saved: float = 0.0  # hours saved by auto-signing
    manual_review_time: float = 0.0    # hours spent on manual review
    fraud_prevented: float = 0.0       # $ saved by catching fraud
    decision_cost: float = 0.0         # $ cost of making this decision


@dataclass
class CostTracker:
    """Tracks cumulative costs and savings."""
    
    # Time tracking
    total_auto_signs: int = 0
    total_deferred: int = 0
    total_rejected: int = 0
    total_manual_reviews: int = 0
    
    # Cost assumptions (per document)
    manual_review_hours: float = 0.5  # 30 minutes per manual review
    hourly_rate: float = 75.0         # $75/hour for legal/compliance staff
    auto_sign_time_saved: float = 0.25  # 15 minutes saved per auto-sign
    
    # Fraud prevention
    fraud_caught: int = 0
    avg_fraud_value: float = 10000.0  # Average fraud attempt value
    
    # Confidence thresholds
    high_confidence_threshold: float = 0.9
    medium_confidence_threshold: float = 0.7
    
    def record_decision(self, decision: str, confidence: float, 
                        filename: str = "", facts_count: int = 0) -> DecisionCost:
        """Record a decision and calculate its cost."""
        cost = DecisionCost()
        
        if decision == "AUTO_SIGN":
            self.total_auto_signs += 1
            cost.auto_sign_time_saved = self.auto_sign_time_saved
            cost.decision_cost = 0.01  # Minimal cost for auto-sign
            
        elif decision == "DEFER_TO_HUMAN":
            self.total_deferred += 1
            self.total_manual_reviews += 1
            cost.manual_review_time = self.manual_review_hours
            cost.decision_cost = self.manual_review_hours * self.hourly_rate
            
        elif decision == "BLOCKED":
            self.total_rejected += 1
            self.fraud_caught += 1
            cost.fraud_prevented = self.avg_fraud_value
            cost.decision_cost = 0.05  # Small cost for rejection check
        
        return cost
    
    def get_summary(self) -> dict:
        """Get cost summary for the demo."""
        total_documents = self.total_auto_signs + self.total_deferred + self.total_rejected
        
        # Time savings
        auto_sign_hours_saved = self.total_auto_signs * self.auto_sign_time_saved
        manual_review_hours_spent = self.total_manual_reviews * self.manual_review_hours
        net_hours_saved = auto_sign_hours_saved - manual_review_hours_spent
        
        # Cost savings
        auto_sign_cost_saved = auto_sign_hours_saved * self.hourly_rate
        manual_review_cost = manual_review_hours_spent * self.hourly_rate
        fraud_savings = self.fraud_caught * self.avg_fraud_value
        net_cost_saved = auto_sign_cost_saved - manual_review_cost + fraud_savings
        
        # ROI
        total_cost = manual_review_cost
        total_savings = auto_sign_cost_saved + fraud_savings
        roi = (total_savings / total_cost * 100) if total_cost > 0 else 0
        
        return {
            "total_documents": total_documents,
            "decisions": {
                "auto_sign": self.total_auto_signs,
                "deferred": self.total_deferred,
                "rejected": self.total_rejected,
                "manual_reviews": self.total_manual_reviews,
            },
            "time_savings": {
                "auto_sign_hours_saved": round(auto_sign_hours_saved, 2),
                "manual_review_hours_spent": round(manual_review_hours_spent, 2),
                "net_hours_saved": round(net_hours_saved, 2),
            },
            "cost_savings": {
                "auto_sign_cost_saved": round(auto_sign_cost_saved, 2),
                "manual_review_cost": round(manual_review_cost, 2),
                "fraud_savings": round(fraud_savings, 2),
                "net_cost_saved": round(net_cost_saved, 2),
            },
            "roi": round(roi, 1),
            "fraud_prevention": {
                "fraud_caught": self.fraud_caught,
                "avg_fraud_value": self.avg_fraud_value,
                "total_fraud_prevented": round(fraud_savings, 2),
            },
            "efficiency": {
                "auto_sign_rate": round(self.total_auto_signs / max(total_documents, 1) * 100, 1),
                "manual_review_rate": round(self.total_manual_reviews / max(total_documents, 1) * 100, 1),
                "rejection_rate": round(self.total_rejected / max(total_documents, 1) * 100, 1),
            },
        }
    
    def print_summary(self):
        """Print a formatted summary for the demo."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("  COST ANALYSIS — BUSINESS VALUE")
        print("="*60)
        print(f"""
  DOCUMENTS PROCESSED: {summary['total_documents']}
  
  DECISIONS:
    Auto-signed:     {summary['decisions']['auto_sign']} ({summary['efficiency']['auto_sign_rate']}%)
    Manual review:   {summary['decisions']['deferred']} ({summary['efficiency']['manual_review_rate']}%)
    Rejected:        {summary['decisions']['rejected']} ({summary['efficiency']['rejection_rate']}%)
  
  TIME SAVINGS:
    Auto-sign time saved:     {summary['time_savings']['auto_sign_hours_saved']} hours
    Manual review time spent: {summary['time_savings']['manual_review_hours_spent']} hours
    Net hours saved:          {summary['time_savings']['net_hours_saved']} hours
  
  COST SAVINGS:
    Auto-sign cost saved:     ${summary['cost_savings']['auto_sign_cost_saved']}
    Manual review cost:       ${summary['cost_savings']['manual_review_cost']}
    Fraud prevention savings: ${summary['cost_savings']['fraud_savings']}
    Net cost saved:           ${summary['cost_savings']['net_cost_saved']}
  
  ROI: {summary['roi']}%
  
  FRAUD PREVENTION:
    Fraud attempts caught:    {summary['fraud_prevention']['fraud_caught']}
    Average fraud value:      ${summary['fraud_prevention']['avg_fraud_value']}
    Total fraud prevented:    ${summary['fraud_prevention']['total_fraud_prevented']}
  
  THE SYSTEM PAYS FOR ITSELF.
  Every auto-sign saves {0.25 * 60:.0f} minutes of manual review.
  Every caught fraud prevents ${10000:,} in losses.
        """)


# Global tracker instance
_tracker: CostTracker | None = None


def get_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
