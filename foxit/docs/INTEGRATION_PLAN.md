# Foxit + ProofDesk Integration Plan

## The Problem

We built two separate systems:
1. **ProofDesk** (Nutrient track): Full pipeline with extraction, evidence, gate, audit
2. **Foxit track**: Risk-adaptive thresholds, difficulty classification, benchmark

**These should be one integrated system.**

## The Solution

Add our confidence work as a **module inside ProofDesk**, not a separate system.

## Integration Points

### 1. Confidence Scoring (NEW)
Add to ProofDesk's orchestrator:
```python
from foxit.confidence import compute_signing_confidence

# After extraction
confidence = compute_signing_confidence(facts, assertions)
```

### 2. Risk-Adaptive Thresholds (NEW)
Add to ProofDesk's SignatureGate:
```python
from foxit.thresholds import get_threshold

threshold = get_threshold(case.document_type)
if confidence >= threshold:
    # Allow signing
```

### 3. Difficulty Classification (NEW)
Add to ProofDesk's router:
```python
from foxit.classifier import classify_difficulty

difficulty = classify_difficulty(document)
# Route to appropriate handling
```

## What Changes

### ProofDesk (existing)
- Add confidence scoring after extraction
- Add risk-adaptive thresholds to SignatureGate
- Add difficulty classification to router

### Foxit (our work)
- Confidence scoring → becomes a module in ProofDesk
- Risk-adaptive thresholds → becomes part of SignatureGate
- Difficulty classification → becomes part of router
- Benchmark → tests the integrated system

## The Correct Architecture

```
ProofDesk orchestrator
    ↓
Nutrient extraction → facts with confidence
    ↓
Evidence engine → assertions
    ↓
Confidence scoring (OUR MODULE) → signing confidence
    ↓
Difficulty classifier (OUR MODULE) → document type
    ↓
Risk-adaptive threshold (OUR MODULE) → threshold per type
    ↓
SignatureGate (EXISTS) → checks conditions
    ↓
Foxit MCP (EXISTS) → reversible work
    ↓
Foxit eSign (EXISTS) → irreversible signing
```

## What We Need to Build

1. `src/confidence.py` — Confidence scoring module
2. `src/thresholds.py` — Risk-adaptive thresholds
3. `src/classifier.py` — Difficulty classification
4. Integrate into `src/engine/orchestrator.py`
5. Integrate into `src/state/machine.py`

## Files to Modify

- `src/engine/orchestrator.py` — Add confidence scoring
- `src/state/machine.py` — Add risk-adaptive thresholds
- `src/providers/foxit_pipeline.py` — Use existing Foxit integration

## What to Delete

- `foxit/src/` — Most of it is duplicate of ProofDesk
- Keep only: confidence scoring, thresholds, classifier, benchmark

## The Correct Demo

1. ProofDesk receives procurement documents
2. Nutrient extracts fields
3. Evidence engine checks for mismatches
4. **Our confidence scoring** computes signing confidence
5. **Our difficulty classifier** identifies document type
6. **Our risk-adaptive thresholds** set the threshold
7. SignatureGate checks conditions
8. Foxit MCP prepares PDF (reversible)
9. Foxit eSign sends to human (irreversible)

**One system, not two.**
