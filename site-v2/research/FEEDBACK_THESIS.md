# ProofDesk Feedback Thesis — How the System Learns from Humans

## The Core Mechanism: Binary Per-Field Feedback

The frontier is clear: **binary feedback wins**. RLBFF (NVIDIA, ICLR 2026) shows that binary flexible feedback — "did this principle hold? yes/no" — outperforms both free-form human feedback (RLHF) and rule-based verification (RLVR) because it combines coverage, interpretability, and precision.

ProofDesk implements this at the **field level**, not the document level:

```
System extracts: insurance_expiry_date = "2027-08-31" (confidence: 0.95)
System flags: 31-day gap → DEFER_TO_HUMAN
Human reviews source PDF → sees the date
Human clicks: "CORRECT" (one click)
→ label captured: field=insurance_expiry_date, rule=coverage-v1, correct=True
```

**Why per-field, not per-document?**

| Feedback type | Cognitive load | Information content | Convergence speed |
|---------------|----------------|---------------------|-------------------|
| Document-level binary ("safe/unsafe") | Low | Low — one label for many fields | Slow |
| Document-level Likert ("confidence 1-5") | Medium | Medium — but inconsistent across humans | Medium |
| **Field-level binary ("correct/incorrect")** | **Low — one click** | **High — per-field label** | **Fast** |

The ALBF paper (2025) confirms: "transforming labeling into binary verification queries based on model predictions" minimizes annotation cost while maximizing information.

## Why Binary Beats Richer Feedback

**Cognitive load matters.** A procurement manager reviewing 14 fields doesn't want to rate each on a 1-5 scale. They want to glance at each extracted value and click "correct" or flag "wrong." One click per field, 14 clicks total, 30 seconds.

**Interpretability matters.** Binary labels are unambiguous. "Was this extraction correct?" has a ground truth. "How confident are you in this extraction?" is subjective — different humans give different answers (Turan 2026: Fleiss κ = 0.5 for risk assessment).

**Convergence speed matters.** Each binary label directly updates the conformal threshold for that field's risk budget. A Likert scale requires mapping to binary first (threshold: 4+ = correct). Binary is the primitive; everything else is derived.

## The Math: How Binary Labels Tighten Thresholds

Each field has a risk budget (signer: 1%, amount: 2%, date: 3%). The budget determines the conformal threshold for that field.

When a human labels a field as "correct":
- The online calibrator (MarginOnlineCalibrator from foxit lab) updates its estimate of that field's accuracy
- The conformal threshold adjusts: if accuracy improves, the threshold lowers → more documents auto-sign for that field
- The per-field risk controller recalibrates: the budget is met with fewer deferrals

When a human labels a field as "incorrect":
- The accuracy estimate drops
- The threshold rises → more documents defer for that field
- The system becomes more conservative for that specific field

**Convergence guarantee (from OnlineSCI 2025):** With enough binary labels, the threshold converges to the optimal value that achieves exactly the target error rate α. The convergence rate depends on:
1. How many labels we've collected for that field
2. How much the field's accuracy varies across documents
3. The step size of the online update

## What Information the Human Provides

The human provides **exactly three things**, nothing more:

1. **Field identity** — which field they're reviewing (system presents this automatically)
2. **Binary judgment** — correct or incorrect (one click)
3. **Optional reason** — free-text explanation (stored but not required)

That's it. No confidence ratings. No Likert scales. No multi-page forms. The system does the hard work: it decides WHICH fields to show the human, WHEN to show them, and HOW to use the feedback.

## Active Learning: Which Fields Get Shown

Not all fields need review. The system uses **uncertainty sampling near the decision boundary** (the optimal strategy per the frontier):

- Fields where confidence is close to the budget threshold → show first
- Fields with high confidence and clear PASS checks → skip
- Fields that failed checks → always show (human must resolve)

The selection logic:
```python
def select_for_review(facts, assertions, budget_thresholds):
    candidates = []
    for fact in facts:
        # How close is this field's confidence to its budget threshold?
        budget = budget_thresholds.get(fact.field_class, 0.10)
        distance = fact.confidence - (1 - budget)
        if abs(distance) < 0.15:  # near the boundary
            candidates.append((abs(distance), fact))
    # Sort by proximity to boundary — most informative first
    return [f for _, f in sorted(candidates)[:5]]
```

This is exactly the "expected error reduction" strategy from the active learning literature: show the human the fields where their judgment adds the most information.

## The Feedback Loop in ProofDesk

```
1. Document arrives → Nutrient extracts fields with confidence
2. Classifier scores: doc_type → risk_level → per-field budgets
3. Confidence gate: compare each field's score against its budget
4. Fields NEAR the budget boundary → DEFER_TO_HUMAN
5. Human reviews source PDF → clicks CORRECT/INCORRECT per field
6. Binary labels feed into online calibrator
7. Calibrator tightens thresholds → more fields auto-sign next time
8. Spot-audit panel verifies: auto-signed cases sampled, errors counted
9. Convergence: coverage grows while FSR stays ≤ α
```

## Why This Matters for Each Provider

**Nutrient:** Every binary label improves extraction accuracy. When humans flag "insurance_expiry_date was extracted correctly," Nutrient's confidence scores for that field type become more reliable in future extractions. The DWS Viewer gets less traffic over time because fewer fields need human review.

**Foxit:** The signing authority boundary moves. As field-level thresholds tighten, more documents pass through Foxit MCP tools without human intervention. The SignatureGate's per-field budgets are not static — they learn.

**Doctavian:** Template branching becomes more accurate. The CLEARED branch handles more documents as the confidence engine learns which extractions are trustworthy. The CONDITIONAL branch shrinks. One template, increasingly correct for every data shape.

## The Honest Claim

**What's proven:** The mechanism is real. Binary per-field feedback feeds into online calibrators that tighten conformal thresholds. The math converges (OnlineSCI 2025). The 0% FSR is structural (conformal guarantee).

**What's projected:** The specific convergence rate (59% → 99%) is from foxit lab experiments on InvoiceBenchmark. It's legitimate for that dataset but not production-proven.

**What to say:** "Every human click is a binary label on a specific field. The system learns from each label, tightens its thresholds, and auto-signs more documents — while the conformal guarantee ensures the error rate stays exactly at the certified budget."

**What NOT to say:** "The system will reach 100% auto-sign in production." — that's aspirational.

## Reference Papers

| Paper | Relevance | Key Finding |
|-------|-----------|-------------|
| RLBFF (NVIDIA, ICLR 2026) | Binary feedback outperforms RLHF and RLVR | Binary + principles = best coverage + precision |
| ALBF (2025) | Active learning with binary verification | Binary queries minimize annotation cost |
| OnlineSCI (2025) | Convergence rates for selective inference | Adaptive thresholds converge to optimal |
| Cost-Sensitive CP (2026) | Economic viability of deferral | Break-even thresholds for human review |
| L2D-Clinical (2026) | Hierarchical deferral | Per-field deferral > document-level |
| Training-Free Deferral (2025) | Conformal deferral without retraining | Accuracy exceeds both model-only and human-only |
