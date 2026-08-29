# Canonical Plan: Signing Confidence Module for ProofDesk

## Vision

A confidence scoring module that sits on top of ProofDesk's existing pipeline, using frontier algorithms to decide when to sign vs defer. Validated by arxiv research, uses Foxit MCP properly.

## Architecture

```
ProofDesk Pipeline (existing)
    ↓
Nutrient extraction → facts with confidence
    ↓
Evidence engine → assertions
    ↓
[CONFIDENCE MODULE] (our contribution)
  ├── Feature extraction (from Nutrient signals)
  ├── Calibration (isotonic + conformal)
  ├── Risk scoring (sheepish + frontier)
  └── Threshold optimization (per doc type)
    ↓
SignatureGate (existing) → checks conditions
    ↓
Foxit MCP (existing) → reversible work
    ↓
Foxit eSign (existing) → irreversible signing
```

## What We're Actually Building

### Not Building
- ❌ New extraction system
- ❌ New document classifier
- ❌ New PDF processing
- ❌ New signing mechanism

### Building
- ✅ Confidence scoring module (sits on ProofDesk)
- ✅ Per-doc-type thresholds (calibrated)
- ✅ Risk-adaptive decision logic
- ✅ Benchmark on real documents
- ✅ Frontier-validated algorithms

## Frontier Validation

### 1. Conformal Risk Control (Angelopoulos et al., ICLR 2024)

**What it does:** Sets thresholds with finite-sample guarantees.

**How we use it:**
```python
# From the paper:
# Given calibration set, find λ* such that P(risk > α) ≤ δ

crc = ConformalRiskController(alpha=0.1)
crc.fit(calibration_scores, calibration_losses)
threshold = crc.find_threshold()
```

**Our implementation:** `src/calibration.py` — `ConformalRiskController`

### 2. Isotonic Regression (Standard)

**What it does:** Non-parametric calibration of confidence scores.

**How we use it:**
```python
# Map raw scores to calibrated probabilities
iso = IsotonicCalibrator()
iso.fit(calibration_scores, calibration_labels)
calibrated_score = iso.calibrate(raw_score)
```

**Our implementation:** `src/calibration.py` — `IsotonicCalibrator`

### 3. Sheepish Metric (Our Contribution)

**What it does:** Penalizes overconfidence more than underconfidence.

**Formalization:** Asymmetric quadratic loss minimization
```python
# From decision theory:
# If c > a (overconfident): s* = (λ_over * c + λ_under * a) / (λ_over + λ_under)
# If c < a (underconfident): s* = c (keep as-is)
```

**Justification:** DUD (2026) shows "Humble Truths" are more reliable than "Stubborn Errors."

### 4. Per-Doc-Type Thresholds (Cogym-inspired)

**What it does:** Different thresholds for different document types.

**From frontier:** HIRA (CIKM 2026) uses Tier 1/Tier 2 with different thresholds.

**Our implementation:** `src/experts.py` — `ExpertPolicy` with per-world thresholds.

## Integration with ProofDesk

### Step 1: Add Confidence Module

```python
# In proofdesk/src/engine/orchestrator.py

from foxit.confidence import ConfidenceModule

class ConfidenceModule:
    def __init__(self):
        self.calibrator = IsotonicCalibrator()
        self.thresholds = {}  # per doc type
        
    def score(self, facts, assertions, doc_type):
        # Extract features from Nutrient signals
        features = self.extract_features(facts, assertions)
        
        # Compute confidence score
        score = self.compute_confidence(features)
        
        # Get doc-type-specific threshold
        threshold = self.thresholds.get(doc_type, 0.7)
        
        return score, threshold
```

### Step 2: Integrate into Pipeline

```python
# In proofdesk/src/engine/orchestrator.py

def run_pipeline(case, domain):
    # 1. Nutrient extraction (existing)
    facts = nutrient_extract(case.documents)
    
    # 2. Evidence engine (existing)
    assertions = run_checks(facts, domain)
    
    # 3. Confidence scoring (NEW — our module)
    confidence, threshold = confidence_module.score(facts, assertions, case.document_type)
    
    # 4. SignatureGate (existing)
    gate = can_request_signature(case)
    
    # 5. Check confidence against threshold
    if gate.allowed and confidence >= threshold:
        # Allow signing
        prepare_pdf(case)
        request_signature(case)
    else:
        # Defer to human
        transition(case, CaseState.REVIEW_REQUIRED)
```

### Step 3: Calibrate on ProofDesk Data

```python
# Use ProofDesk's golden fixture for calibration
from src.models.golden_fixture import FIXTURE

# Calibrate confidence on procurement documents
calibration_data = extract_features_from_fixture(FIXTURE)
confidence_module.calibrate(calibration_data)

# Set per-doc-type thresholds
confidence_module.thresholds = {
    "procurement": 0.70,
    "invoice": 0.70,
    "contract": 0.85,
    "kyc": 0.95,
    "mortgage": 0.95,
}
```

## What's Different from Our Current Work

### Current (Separate System)
- Built a separate Foxit repo
- Used simulated signals
- No integration with ProofDesk
- Ad-hoc thresholds

### Planned (Module in ProofDesk)
- Integrated into ProofDesk's pipeline
- Uses real Nutrient signals
- Uses frontier algorithms (conformal, isotonic)
- Calibrated on ProofDesk's golden fixture
- Uses Foxit MCP properly (30+ tools)

## Frontier Algorithms We'll Use

| Algorithm | Paper | What It Does | How We Use It |
|-----------|-------|--------------|---------------|
| Conformal Risk Control | Angelopoulos et al., ICLR 2024 | Threshold with guarantees | Set threshold per doc type |
| Isotonic Regression | Standard | Calibration | Map raw scores to calibrated probs |
| Platt Scaling | Standard | Calibration | Sigmoid mapping |
| Sheepish Metric | Our contribution | Asymmetric loss | Penalize overconfidence |
| Per-Type Thresholds | HIRA (CIKM 2026) | Tier 1/Tier 2 routing | Different thresholds per doc type |

## What We're NOT Claiming

- ❌ We invented calibration (isotonic is standard)
- ❌ We invented selective prediction (well-studied)
- ❌ We invented document classification (well-studied)
- ❌ Our benchmark is large-scale (250 docs is small)

## What We ARE Claiming

- ✅ Per-doc-type thresholds improve signing decisions
- ✅ The SignatureGate architecture is sound
- ✅ Foxit MCP integration works
- ✅ The confidence module integrates cleanly into ProofDesk

## Next Steps

1. **Integrate into ProofDesk** — add confidence module to orchestrator
2. **Calibrate on real data** — use ProofDesk's golden fixture
3. **Test on larger dataset** — CORD, FATURA, FUNSD
4. **Proper conformal guarantees** — implement Angelopoulos et al.
5. **Write honest paper** — acknowledge limitations, compare with frontier

## The Honest Pitch

"ProofDesk's confidence module uses frontier calibration algorithms to set per-doc-type signing thresholds, integrated into ProofDesk's existing Nutrient → Evidence → Gate → Foxit pipeline."

Not: "We invented a new signing system."

The module is the contribution. ProofDesk is the platform. Foxit is the tool.
