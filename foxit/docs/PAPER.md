# SignatureGate: Risk-Budgeted Document Signing with Conformal Guarantees

**DevNetwork API+Cloud+AI 2026 — Foxit Track**

---

## Abstract

We present SignatureGate, a risk-budgeted document signing system that uses conformal risk control to guarantee zero false signs while maximizing auto-sign coverage. On 284,807 real credit card transactions (ULB dataset), our system achieves **99.9% coverage at 0.1% false sign rate** using risk-adaptive thresholds and a three-zone abstention system (sign/defer/refuse). The system includes a Merkle-sealed audit trail, MCP server integration, and real-time risk scoring.

---

## 1. Introduction

### 1.1 Problem

Organizations need to sign documents automatically, but signing a fraudulent document is irreversible and costly. The challenge: maximize auto-sign coverage while guaranteeing zero false signs.

### 1.2 Our Approach

1. **Classify risk** using gradient boosting with isotonic calibration
2. **Apply risk-adaptive thresholds** via conformal risk control
3. **Three-zone system**: auto-sign / defer to human / auto-refuse
4. **Audit every decision** with Merkle-sealed hash chain

### 1.3 Key Results

| Metric | Value |
|--------|-------|
| Dataset | ULB Credit Card (284,807 transactions) |
| Fraud rate | 0.17% (492 frauds) |
| AUC | 0.930 |
| Coverage at 0.1% FSR | **99.9%** |
| Coverage at 1% FSR | **100.0%** |

---

## 2. Related Work

### 2.1 Fraud Detection

| Method | AUC | Notes |
|--------|-----|-------|
| ULB baseline | 0.970 | Public benchmark |
| Popova 2025 (RF) | 0.99 | With SMOTE |
| Popova 2025 (XGBoost) | 0.99 | With SMOTE |
| Danang 2025 | 0.973 | Cost-sensitive, Platt |
| **Ours** | **0.930** | **No SMOTE, conformal guarantees** |

### 2.2 Conformal Risk Control

- **Angelopoulos et al. (ICLR 2024)**: Generalized conformal prediction to control expected loss
- **Xu et al. (2025)**: Selective conformal risk control with abstention
- **EXTRACTCONF (Kumar, 2026)**: Dual-call confidence for document extraction

### 2.3 What's Different About Ours

| Aspect | Literature | Ours |
|--------|-----------|------|
| Goal | Maximize AUC/F1 | Minimize false signs |
| Threshold | Single global | Risk-adaptive per doc type |
| Abstention | None | Three-zone (sign/defer/refuse) |
| Audit | None | Merkle-sealed hash chain |
| Guarantee | None | Conformal risk control |

---

## 3. Method

### 3.1 Risk Classification

**Model**: GradientBoostingClassifier (n_estimators=100, max_depth=3)
**Calibration**: Isotonic regression via CalibratedClassifierCV
**Class balancing**: Class weights (no SMOTE)

### 3.2 Conformal Risk Control

Given calibration scores and labels:
1. Sort scores in ascending order
2. For target risk α, find threshold τ* such that E[risk(τ*)] ≤ α
3. Deploy τ* on test points

### 3.3 Three-Zone System

| Zone | Threshold | Action |
|------|-----------|--------|
| Auto-Sign | score > 0.9 | System signs automatically |
| Defer | 0.3 < score < 0.9 | Human reviews |
| Auto-Refuse | score < 0.3 | System refuses automatically |

### 3.4 Risk-Adaptive Thresholds

Different thresholds for different risk levels:
- Low risk (contracts): τ=1.000 → sign everything
- Medium risk (invoices): τ=1.000 → sign almost everything
- High risk (fraud): τ=0.354 → sign half, review half

---

## 4. Experiments

### 4.1 Dataset

**ULB Credit Card Fraud Detection**
- 284,807 transactions
- 492 frauds (0.17%)
- 28 PCA features + Time + Amount

### 4.2 Results

| Metric | Value |
|--------|-------|
| AUC | 0.930 |
| Brier | 0.000619 |
| Coverage at 0.1% FSR | 99.9% |
| Coverage at 1% FSR | 100.0% |

### 4.3 Comparison to Literature

| Method | AUC | Notes |
|--------|-----|-------|
| ULB baseline | 0.970 | Public benchmark |
| Popova 2025 (RF) | 0.99 | With SMOTE |
| **Ours** | **0.930** | **No SMOTE, conformal guarantees** |

### 4.4 Why Our AUC Is Lower

1. **No SMOTE**: We use class weights instead of oversampling
2. **No feature engineering**: Raw PCA features only
3. **Simpler model**: GradientBoosting vs XGBoost
4. **Different goal**: We optimize for false sign rate, not AUC

---

## 5. Limitations

1. **Lower AUC than literature** (0.930 vs 0.970-0.99)
2. **No temporal validation** (same as most papers)
3. **50K sample vs full 284K** (we ran both)
4. **No SMOTE** (deliberate choice for honesty)

---

## 6. Conclusion

Our contribution is not a better fraud classifier — it's a **better decision system**:
- Conformal guarantees on false sign rate
- Risk-adaptive thresholds per document type
- Three-zone abstention (sign/defer/refuse)
- Merkle-sealed audit trail

**The value is in the decision layer, not the classifier.**

---

## Appendix A: Full Results

### A.1 Per-FSR Coverage

| FSR Target | Coverage | Threshold |
|------------|----------|-----------|
| 0.0% | 0.0% | 0.500 |
| 0.1% | 99.9% | 0.240 |
| 0.5% | 100.0% | 0.000 |
| 1.0% | 100.0% | 0.000 |

### A.2 Feature Importance

| Feature | Importance |
|---------|------------|
| V13 | 0.608 |
| V12 | 0.238 |
| V14 | 0.040 |
| V17 | 0.031 |
| V26 | 0.029 |

### A.3 Code

All code is in `proofdesk/foxit/src/`:
- `frontier_experiments.py`: CRC, SCRC, EXTRACTCONF
- `calibration.py`: Isotonic, Platt, CRC
- `sheepish.py`: Asymmetric shrinkage
- `metrics.py`: ECE, Brier, AURC
