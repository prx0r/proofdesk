# Build Plan: Risk-Adaptive Document Signing with Calibrated Confidence

## Paper Title
"Risk-Adaptive Document Signing: Calibrated Confidence for When Agents Should Defer to Human"

## Problem Statement
When should an AI agent sign a document vs defer to human review? Current approaches either always sign (dangerous) or always defer (useless). We propose risk-adaptive thresholds that adjust signing confidence based on document type and risk level.

## Datasets (Downloaded)

### 1. FATURA (10K invoices) ✅
- **Source**: HuggingFace `mathieu1256/FATURA2-invoices`
- **Size**: 8,600 train + 1,400 test
- **What**: Multi-layout invoice images with NER annotations
- **Use**: Test invoice signing decisions
- **Ground truth**: Seller, buyer, total, tax, line items

### 2. FUNSD (199 forms) ✅
- **Source**: HuggingFace `nielsr/funsd-layoutlmv3`
- **Size**: 149 train + 50 test
- **What**: Scanned forms with key-value annotations
- **Use**: Test form signing decisions
- **Ground truth**: Key-value extraction correctness

### 3. InvoiceBenchmark (200 invoices) ✅
- **Source**: HuggingFace `jngb-labs/InvoiceBenchmark`
- **Size**: 200 test invoices
- **What**: Synthetic invoices with cent-perfect ground truth
- **Use**: Test invoice verification accuracy
- **Ground truth**: correct_total vs rendered_total

### 4. CORD (11K receipts) — Download later
- **Source**: HuggingFace `naver-clova-ix/cord-v2`
- **Size**: 11K receipts
- **What**: Indonesian receipts with line-item annotations
- **Use**: Test receipt signing decisions

### 5. RealKIE (5 enterprise datasets) — Download later
- **Source**: HuggingFace `amazon-agi/RealKIE-FCC-Verified`
- **What**: SEC filings, NDAs, FCC invoices, contracts
- **Use**: Test enterprise signing decisions

### 6. BuDDIE (1,665 business docs) — Download later
- **Source**: J.P. Morgan BuDDIE dataset
- **What**: Business documents with annotations
- **Use**: Test business signing decisions

## Pipeline Architecture

```
Document arrives
      ↓
┌─────────────────┐
│ Nutrient DWS    │  Extract fields + confidence
│ (real API)      │  Returns: fields, bbox, confidence
└────────┬────────┘
         ↓
┌─────────────────┐
│ Doc Classifier   │  Predict: receipt/invoice/form/contract/identity
│ (trained)        │  Features: extracted fields + confidence
└────────┬────────┘
         ↓
┌─────────────────┐
│ Risk Assessor    │  Predict: safe/risky/fraudulent per doc type
│ (trained)        │  Features: field consistency + cross-doc checks
└────────┬────────┘
         ↓
┌─────────────────┐
│ Confidence       │  Compute calibrated signing confidence
│ Calibration      │  Isotonic + Platt + conformal
└────────┬────────┘
         ↓
┌─────────────────┐
│ Threshold        │  Per-doc-type optimal threshold
│ Optimizer        │  Cogym evolution on train set
└────────┬────────┘
         ↓
┌─────────────────┐
│ SignatureGate    │  Enforce: score >= threshold → SIGN
│ (server-side)    │  Otherwise → REVIEW (defer to human)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Foxit MCP        │  Reversible: upload + merge + compress
│ (real API)       │  Irreversible: eSign → human signer
└─────────────────┘
```

## Metrics

### Per Doc Type
- Accuracy (correct sign/refuse decisions)
- FPR (signed but should have refused)
- FNR (refused but should have signed)
- Utility (correct signs - penalties for errors)
- Calibration error (ECE, Brier)

### Overall
- Mean accuracy across all doc types
- Mean FPR across all doc types
- Risk-coverage curve
- ROC-AUC

## Cogym Optimization

### Pattern: HardWorlds + Evolution
1. Each doc type is a "hard world" with its own optimal threshold
2. Evolution loop: mutate threshold → benchmark → select best
3. BehaviorSignature: fingerprint each signer's profile
4. State transfer: test if optimized thresholds transfer to new docs

### Optimization Loop
```
for gen in range(n_generations):
    for each doc_type:
        mutate threshold (±0.05)
        benchmark on train set
        select best threshold
    test on held-out set
    report generalization gap
```

## Citations

1. HIRA (CIKM 2026) - Retrieval-augmented cascade
2. ConfBench (2026) - Calibration benchmark for IDP
3. Valid Per-Field (2026) - Selective risk control
4. EXTRACTCONF (2026) - Multi-signal confidence engine
5. DocHRL (2026) - Hierarchical RL for classification
6. CORD, FATURA, FUNSD, RealKIE, BuDDIE, IDNet datasets

## Expected Results

| Doc Type | Dataset | Expected Accuracy | Expected FPR |
|----------|---------|-------------------|--------------|
| Receipts | CORD | 85-90% | 5-10% |
| Invoices | FATURA | 85-90% | 5-10% |
| Forms | FUNSD | 80-85% | 5-10% |
| Enterprise | RealKIE | 80-85% | 5-10% |
| Business | BuDDIE | 80-85% | 5-10% |
| Identity | IDNet | N/A (always defer) | 0% |

## Timeline

1. **Day 1**: Download datasets, extract features
2. **Day 2**: Train classifiers, calibrate confidence
3. **Day 3**: Optimize thresholds, run benchmarks
4. **Day 4**: Generate plots, write paper draft
5. **Day 5**: Final review, submission prep
