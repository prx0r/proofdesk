# Production Safety: How to Handle 1000 Documents with Zero Wrong Signs

## The Problem

Someone uploads 1000 documents. Even 1 being signed wrong is unacceptable.

## The Solution: Pipeline Gates

The solution is NOT to make the model perfect. The solution is to make the **PIPELINE** catch errors at every stage.

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE GATES                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Stage 1: EXTRACTION                                         │
│    Gate: Is extraction quality acceptable?                   │
│    Method: RaV-IDP reconstruction validation                 │
│    Action: If no → reject, flag for manual extraction        │
│                                                              │
│  Stage 2: CLASSIFICATION                                     │
│    Gate: Is confidence above threshold?                      │
│    Method: Conformal risk control + EXTRACTCONF              │
│    Action: If no → defer to human review                     │
│                                                              │
│  Stage 3: SIGNING                                            │
│    Gate: Is signature authorized?                            │
│    Method: SignatureGate (5 conditions)                      │
│    Action: If no → reject, require human approval            │
│                                                              │
│  Stage 4: POST-SIGN                                          │
│    Gate: Is spot audit clean?                                │
│    Method: Random sampling + error tracking                  │
│    Action: If no → tighten thresholds, retrain               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Each Gate Is:

| Property | Description |
|----------|-------------|
| **DETERMINISTIC** | Same input → same decision |
| **AUDITABLE** | Every decision logged with reasons |
| **REVERSIBLE** | Can undo if gate was wrong |
| **BLAME-ASSIGNED** | Human decides at each gate |

## How to Implement Each Gate

### Gate 1: Extraction Quality (RaV-IDP)

**Problem:** Nutrient extracts wrong data with high confidence.

**Solution:** Reconstruction validation
1. After extraction, reconstruct the document region
2. Compare reconstruction to original
3. Fidelity score = grounded quality signal
4. If fidelity < threshold → route to fallback

**Code location:** `src/providers/nutrient.py`

### Gate 2: Classification Confidence (EXTRACTCONF)

**Problem:** Model confidence doesn't match actual accuracy.

**Solution:** Dual-call verification
1. Hunter call: field-guided extraction
2. Mapper call: document-guided extraction
3. Disagreement = reliability signal
4. If Hunter ≠ Mapper → defer to human

**Code location:** `src/providers/classifier.py`

### Gate 3: Signature Authorization (SignatureGate)

**Problem:** Wrong person signs, or signs without approval.

**Solution:** 5-condition gate
1. No unresolved blockers
2. Human approval present
3. Artifact hash matches
4. Signer authorized
5. Score above threshold

**Code location:** `src/state/machine.py`

### Gate 4: Spot Audit (FeedbackLoop)

**Problem:** Auto-signed docs might be wrong.

**Solution:** Random sampling
1. Sample 1% of auto-signed docs
2. Send to human for verification
3. Track error rate over time
4. If error rate > threshold → tighten thresholds

**Code location:** `src/engine/feedback.py`

## The Hackathon Story

"We don't claim our model is perfect. We claim our PIPELINE catches errors at every stage. Each gate is deterministic, auditable, and blame-assigned. If something goes wrong, we know exactly which gate failed and which human made the decision.

This is how you build trust in AI systems: not by making them perfect, but by making them catch their own mistakes."

## What's Missing

| Gap | Status | Fix |
|-----|--------|-----|
| Extraction quality verification | NOT IMPLEMENTED | RaV-IDP reconstruction |
| Distribution shift detection | NOT IMPLEMENTED | ConfBench monitoring |
| Continuous calibration | PARTIAL | Wire FeedbackLoop |
| Extraction confidence check | NOT IMPLEMENTED | EXTRACTCONF dual-call |
| Active learning | PARTIAL | Wire select_for_review |
| Spot audit | PARTIAL | Wire record_auto_sign |

## Implementation Priority

1. **P0:** Wire FeedbackLoop into pipeline (already exists)
2. **P0:** Add extraction quality check (RaV-IDP style)
3. **P1:** Add distribution shift detection
4. **P1:** Wire active learning (select_for_review)
5. **P2:** Add spot audit mechanism
