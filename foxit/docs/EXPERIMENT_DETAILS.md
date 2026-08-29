# Experiment Suite — Frontier Methods + Datasets

## Experiment 1: Risk Classification

**Question:** Can we classify documents into Low/Medium/High risk?

**Method:** Logistic regression on document features + conformal classification guarantees.

**Datasets:**
| Risk | Dataset | Docs | Why |
|------|---------|------|-----|
| Low | InvoiceBenchmark | 200 | Real invoices, fraud labels |
| Low | FATURA | 10K | Multi-layout invoices |
| Medium | ContractNER | 3,240 | 18 entity types |
| Medium | CUAD | 510 | 41 clause types |
| High | INS-007 | 5,000 | 12 fraud types |
| High | AIForge-Doc | 4,061 | AI-forged docs |
| High | 10K Fraud | 10,000 | SEC AAER labels |

**Frontier method:** Conformal classification (Vovk et al.) — finite-sample coverage guarantees.

**Metric:** Accuracy per risk level, confusion matrix.

**Expected:** 90%+ Low, 80%+ Medium, 70%+ High.

---

## Experiment 2: Threshold Optimization

**Question:** What's the optimal signing threshold per document type?

**Method:** Conformal Risk Control (Angelopoulos et al., ICLR 2024) — find λ* such that P(risk > α) ≤ δ.

**Datasets:** Same as Experiment 1.

**Frontier method:** CRC with α = 0.1, δ = 0.05.

**Metric:** Optimal threshold per type, risk-coverage curve.

**Expected:** Different thresholds:
- Invoices: τ = 0.70
- Contracts: τ = 0.85
- KYC/Mortgage: τ = 0.95

---

## Experiment 3: False Sign Optimization

**Question:** Can we achieve 0% false sign rate?

**Method:** Conformal Risk Control with α = 0 (zero false sign guarantee).

**Datasets:** Same as Experiment 1.

**Frontier method:** CRC with α = 0, SCRC (Selective Conformal Risk Control).

**Metric:** Coverage at FPR = 0 (how many docs can we auto-sign with zero false signs?).

**Expected:**
- Low risk: 80%+ coverage at FPR = 0
- Medium risk: 50%+ coverage at FPR = 0
- High risk: 20%+ coverage at FPR = 0

---

## Experiment 4: Per-Type Analysis

**Question:** Which document types is the system good/bad at?

**Method:** Measure accuracy, FPR, coverage per document type.

**Datasets:** Same as Experiment 1.

**Metric:** Accuracy per type, FPR per type, which types need human review.

**Expected:** Show invoices easy, KYC hard.

---

## Experiment 5: Merkle Audit

**Question:** Can we prove every signing decision was calibrated?

**Method:** Hash-chain every signing decision with calibration metadata.

**Integration:** ProofDesk EventLedger (hash-chained audit trail).

**Metric:** Audit trail completeness, Merkle proof verification.

---

## Experiment 6: End-to-End

**Question:** Does the full system work?

**Method:** Run complete pipeline: classify → threshold → sign → audit.

**Datasets:** All combined.

**Metric:** End-to-end accuracy, total false signs, total coverage.

**Expected:** 0% false signs, 60%+ coverage, complete audit trail.

---

## Dataset Summary

| Experiment | Low Risk | Medium Risk | Hard Risk | Total |
|------------|----------|-------------|-----------|-------|
| 1. Classification | InvoiceBenchmark, FATURA | ContractNER, CUAD | INS-007, AIForge-Doc, 10K Fraud | 22K+ |
| 2. Threshold | Same | Same | Same | 22K+ |
| 3. False Sign | Same | Same | Same | 22K+ |
| 4. Per-Type | All | All | All | 22K+ |
| 5. Merkle | All | All | All | 22K+ |
| 6. End-to-End | All | All | All | 22K+ |

## Frontier Methods Summary

| Method | Paper | Use |
|--------|-------|-----|
| Conformal Risk Control | Angelopoulos et al., ICLR 2024 | Threshold optimization |
| Selective Conformal Risk Control | Xu et al., 2025 | Zero false sign |
| Auto-Adaptive CRC | Blot et al., 2024 | Adaptive thresholds |
| Conformal Abstention Policy | Tayebati et al., 2025 | Learned abstention |
| Cross-Validation CRC | Cohen et al., 2024 | Data-efficient calibration |
