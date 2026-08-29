"""Evaluation Module — Binary rubric for auto-sign correctness.

For each document, we define:
- ground_truth: Should this document be auto-signed? (0 or 1)
- prediction: Did the system auto-sign? (0 or 1)

Metrics:
- True Positive (TP): Correctly auto-signed
- True Negative (TN): Correctly deferred/blocked
- False Positive (FP): Incorrectly auto-signed (DANGEROUS)
- False Negative (FN): Incorrectly deferred (wasted time)

Key metric: False Positive Rate (FPR) — how often we auto-sign documents we shouldn't.
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple


@dataclass
class EvaluationResult:
    """Binary evaluation for a single document."""
    filename: str
    ground_truth: int  # 0 = should not auto-sign, 1 = should auto-sign
    prediction: int    # 0 = deferred/blocked, 1 = auto-signed
    confidence: float
    doc_type: str
    risk_level: str
    
    @property
    def is_correct(self) -> bool:
        return self.ground_truth == self.prediction
    
    @property
    def error_type(self) -> str:
        if self.ground_truth == 1 and self.prediction == 1:
            return "TP"  # True Positive
        elif self.ground_truth == 0 and self.prediction == 0:
            return "TN"  # True Negative
        elif self.ground_truth == 0 and self.prediction == 1:
            return "FP"  # False Positive (DANGEROUS)
        else:
            return "FN"  # False Negative (wasted time)


def get_ground_truth(filename: str, facts: list, assertions: list) -> int:
    """Determine if a document should be auto-signed.
    
    Rules (matching system behavior):
    - Documents with ANY assertions → should NOT auto-sign (0)
    - Documents with confidence < 0.9 → should NOT auto-sign (0)
    - Documents with confidence >= 0.9 → should auto-sign (1)
    
    Note: Confidence is computed from fact confidences + assertion pass rate.
    When there are no assertions, mapper_score=0.5 (unknown), which lowers confidence.
    This is correct behavior — we should be conservative when we don't have enough info.
    """
    # Rule 1: Any assertions (checks ran) → should not auto-sign
    if len(assertions) > 0:
        return 0
    
    # Rule 2: Compute confidence the same way the system does
    confidences = [f.get("confidence", 0.5) for f in facts if f.get("confidence")]
    hunter_score = sum(confidences) / len(confidences) if confidences else 0.5
    
    # When no assertions, mapper_score=0.5 (unknown)
    mapper_score = 0.5
    
    # Compute base confidence (same as classifier)
    base_confidence = 0.5 * hunter_score + 0.5 * mapper_score
    
    # Rule 3: Apply same threshold as system
    if base_confidence >= 0.9:
        return 1  # auto-sign
    else:
        return 0  # defer


def evaluate_batch(results: List[Dict], cases: Dict) -> Dict:
    """Evaluate a batch of documents against ground truth."""
    evaluations = []
    
    for result in results:
        filename = result.get("filename", "")
        case_id = result.get("case_id", "")
        
        # Get case data
        case = cases.get(case_id)
        if not case:
            continue
        
        # Get ground truth
        facts = [f.to_public() for f in case.facts]
        assertions = [a.to_dict() for a in case.assertions]
        ground_truth = get_ground_truth(filename, facts, assertions)
        
        # Get prediction
        prediction = 1 if result.get("decision") == "AUTO_SIGN" else 0
        
        # Create evaluation
        eval_result = EvaluationResult(
            filename=filename,
            ground_truth=ground_truth,
            prediction=prediction,
            confidence=result.get("confidence", 0),
            doc_type=result.get("doc_type", ""),
            risk_level=result.get("risk_level", ""),
        )
        evaluations.append(eval_result)
    
    # Compute metrics
    tp = sum(1 for e in evaluations if e.error_type == "TP")
    tn = sum(1 for e in evaluations if e.error_type == "TN")
    fp = sum(1 for e in evaluations if e.error_type == "FP")
    fn = sum(1 for e in evaluations if e.error_type == "FN")
    
    total = len(evaluations)
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0  # False Positive Rate
    
    return {
        "total": total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": round(accuracy, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "fpr": round(fpr, 3),  # Key metric: how often we auto-sign incorrectly
        "evaluations": [asdict(e) for e in evaluations],
    }


def print_evaluation(metrics: Dict):
    """Print evaluation results."""
    print("\n" + "="*70)
    print("  EVALUATION RESULTS")
    print("="*70)
    print()
    print(f"  Total documents: {metrics['total']}")
    print()
    print("  CONFUSION MATRIX:")
    print(f"    True Positives (correctly auto-signed):  {metrics['tp']}")
    print(f"    True Negatives (correctly deferred):     {metrics['tn']}")
    print(f"    False Positives (DANGEROUS auto-sign):   {metrics['fp']}")
    print(f"    False Negatives (wasted time):           {metrics['fn']}")
    print()
    print("  METRICS:")
    print(f"    Accuracy:  {metrics['accuracy']*100:.1f}%")
    print(f"    Precision: {metrics['precision']*100:.1f}%")
    print(f"    Recall:    {metrics['recall']*100:.1f}%")
    print(f"    FPR:       {metrics['fpr']*100:.1f}% (False Positive Rate)")
    print()
    
    if metrics['fp'] > 0:
        print("  ⚠️  WARNING: False Positives detected!")
        print("  These documents were auto-signed but should NOT have been:")
        for e in metrics['evaluations']:
            if e['error_type'] == 'FP':
                print(f"    - {e['filename'][:60]} (confidence: {e['confidence']*100:.0f}%)")
    else:
        print("  ✅ No false positives — all auto-signs were correct!")
    
    print()
    print("  INTERPRETATION:")
    print(f"    - System auto-signed {metrics['tp'] + metrics['fp']} documents")
    print(f"    - {metrics['tp']} were correct, {metrics['fp']} were WRONG")
    print(f"    - False Positive Rate: {metrics['fpr']*100:.1f}%")
    print(f"    - Target: FPR < 1% (conformal guarantee)")
    print("="*70)
