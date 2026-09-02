# Confidence Metrics Research — Non-Hallucinated Approaches

## Key Papers

### 1. UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing (2026)
**Most relevant.** Token-margin uncertainty + isotonic regression → calibrated error probabilities (ECE=0.03).
- Extract per-token margin: `m_t = p_top1 - p_top2`
- Aggregate: `u(x) = 1 - mean(margins)`
- Calibrate via isotonic regression on heldout set
- Route based on calibrated error probability
- **Directly applicable to our threshold optimization**

### 2. Conformal Prediction for Risk-Controlled Medical Entity Extraction (2026)
Split-conformal calibration for LLM entity extraction. Finite-sample coverage guarantees across structured and free-text documents.
- **Directly applicable:** Our document extraction IS entity extraction

### 3. Unsupervised Confidence Calibration from Single Generation (Zollo et al., 2026)
No labeled data needed. Uses internal model signals + isotonic regression.
- **Useful when we don't have ground truth labels**

### 4. ConfidenceBench (2026)
Benchmarks verbalized confidence. Prompt design substantially affects calibration.
- **Takeaway:** How we ask for confidence matters as much as the method

### 5. A Survey of Confidence Estimation and Calibration in LLMs (Geng et al., NAACL 2024)
Definitive taxonomy:
- **Sampling-based:** variability across outputs (expensive)
- **Verbalization:** ask model for confidence (single-pass, scalable)
- **Logit-based:** token probabilities (requires model access)
- **Consistency-based:** self-consistency of multiple outputs

### 6. Fact-and-Reflection (FaR) (ACL 2024)
Fact-checking + reflection improves calibration.
- **Relevant:** Our FactMiner verification IS fact-checking

## Methods We Can Use

### Method A: Nutrient Match Labels (already available)
- `id_match` = high confidence (exact match)
- `fuzzy_match` = medium (route to review)
- `not_found` = low (must review)
- **Zero cost, built into API**

### Method B: Nutrient Confidence Score (already available)
- Composite score 0-1 from extraction engine
- **Not calibrated** — relative signal only
- Need isotonic regression to calibrate

### Method C: Token-Margin Uncertainty (UCCI approach)
- Extract top-1 and top-2 token probabilities
- Compute margin: `m = p1 - p2`
- Aggregate across sequence
- **Requires model access** — Nutrient doesn't expose this

### Method D: Split Conformal Prediction (CP)
- Holdout calibration set
- Compute nonconformity scores
- Derive threshold with coverage guarantee
- **Gold standard for calibrated thresholds**
- **Directly applicable to our benchmark**

### Method E: Multi-Signal Fusion
Combine Nutrient signals with our own:
```python
calibrated_confidence = (
    w1 * nutrient_confidence +       # from API
    w2 * match_label_score +          # from match label
    w3 * factminer_verdict_score +    # from verification
    w4 * cross_doc_consistency        # from cross-document check
)
```

## Recommended Architecture

```
NUTRIENT EXTRACT
  ├─ confidence (raw, uncalibrated)
  ├─ match label (id_match / fuzzy_match / not_found)
  └─ bbox + page (source grounding)
        ↓
CALIBRATION LAYER (from research)
  ├─ isotonic regression on heldout set → calibrated probability
  ├─ conformal prediction → coverage guarantee
  └─ multi-signal fusion → combined score
        ↓
THRESHOLD OPTIMIZATION (cogymkernel)
  ├─ mutate threshold per document type
  ├─ evaluate on frozen test set
  └─ select best: accuracy × auto_approve_rate
        ↓
ROUTING DECISION
  ├─ calibrated_confidence >= auto_threshold → AUTO-APPROVE
  ├─ calibrated_confidence >= review_threshold → HUMAN_REVIEW
  └─ else → REJECT
```

## Key Insight

Nutrient's `match` label is the strongest non-hallucinated signal:
- `id_match` = "I found exactly this value in the document" ( grounded)
- `fuzzy_match` = "I found something close but not exact" (uncertain)
- `not_found` = "I couldn't find this in the document" (ungrounded)

This is NOT a model confidence score — it's a deterministic grounding check. Combined with the confidence score (which IS a model signal), we get both grounded and probabilistic confidence.
