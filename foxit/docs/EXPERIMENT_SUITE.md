# Frontier-Level Experiment Suite: High-Risk Document Signing

## Core Thesis

**Classify risk → optimize threshold per doc type → enforce 0% false sign → audit everything.**

Each experiment builds on the previous. The goal: a signing system that never signs a risky document, with a Merkle audit trail proving every decision.

---

## Experiment 1: Risk Classification

**Question:** Can we correctly classify documents into risk levels?

**Method:** Train a classifier on document features → predict Low/Medium/High risk.

**Datasets:**
- Low: InvoiceBenchmark (200), FATURA (10K), SROIE (1K)
- Medium: ContractNER (3,240), CUAD (510)
- High: INS-007 (5K), AIForge-Doc (4K), 10K Fraud (10K)

**Metrics:**
- Classification accuracy per risk level
- Confusion matrix (which types get misclassified?)
- Per-document-type accuracy (which types are easy vs hard?)

**Frontier method:** Conformal classification (Vovk et al.) for finite-sample guarantees.

**Expected result:** 90%+ accuracy on Low, 80%+ on Medium, 70%+ on High.

---

## Experiment 2: Threshold Optimization

**Question:** What's the optimal signing threshold for each document type?

**Method:** For each document type, find threshold that maximizes utility subject to FPR ≤ α.

**Datasets:** Same as Experiment 1.

**Metrics:**
- Optimal threshold per document type
- Risk-coverage curve per type
- Utility at optimal threshold

**Frontier method:** Conformal Risk Control (Angelopoulos et al., ICLR 2024).

**Expected result:** Different thresholds for different types:
- Invoices: τ = 0.70 (sign freely)
- Contracts: τ = 0.85 (review required)
- KYC/Mortgage: τ = 0.95 (always review)

---

## Experiment 3: False Sign Optimization

**Question:** Can we achieve 0% false sign rate while maintaining coverage?

**Method:** Optimize threshold to maximize coverage subject to FPR = 0.

**Datasets:** Same as Experiment 1.

**Metrics:**
- Coverage at FPR = 0 (how many docs can we auto-sign with zero false signs?)
- Coverage at FPR = 0.01 (how many at 1% false sign rate?)
- Coverage at FPR = 0.05 (how many at 5% false sign rate?)

**Frontier method:** Conformal Risk Control with α = 0 (zero false sign guarantee).

**Expected result:**
- Low risk: 80%+ coverage at FPR = 0
- Medium risk: 50%+ coverage at FPR = 0
- High risk: 20%+ coverage at FPR = 0

---

## Experiment 4: Per-Document-Type Analysis

**Question:** Which document types is the system good/bad at?

**Method:** Measure accuracy, FPR, coverage per document type.

**Datasets:** Same as Experiment 1.

**Metrics:**
- Accuracy per document type
- FPR per document type
- Coverage per document type
- Which types need more human review?

**Expected result:** Show which types are easy (invoices) vs hard (KYC, mortgage).

---

## Experiment 5: Merkle Audit Integration

**Question:** Can we prove every signing decision was properly calibrated?

**Method:** Hash-chain every signing decision with calibration metadata.

**Integration:**
- Use ProofDesk's EventLedger (hash-chained audit trail)
- Store: document hash, risk level, threshold, calibration score, decision
- Merkle proof for each signing decision

**Metrics:**
- Audit trail completeness
- Merkle proof verification
- Tamper-evidence

---

## Experiment 6: End-to-End Pipeline

**Question:** Does the full system work on real documents?

**Method:** Run the complete pipeline: classify → threshold → sign → audit.

**Datasets:** All datasets combined.

**Metrics:**
- End-to-end accuracy
- Total false signs
- Total coverage
- Audit trail completeness

**Expected result:** 0% false signs, 60%+ coverage, complete audit trail.

---

## Dataset Selection (Per Experiment)

| Experiment | Easy | Medium | Hard | Total |
|------------|------|--------|------|-------|
| 1. Risk Classification | InvoiceBenchmark, FATURA | ContractNER, CUAD | INS-007, AIForge-Doc | 22K+ |
| 2. Threshold Optimization | InvoiceBenchmark, FATURA | ContractNER, CUAD | INS-007, AIForge-Doc | 22K+ |
| 3. False Sign Optimization | InvoiceBenchmark, FATURA | ContractNER, CUAD | INS-007, AIForge-Doc | 22K+ |
| 4. Per-Type Analysis | All | All | All | 22K+ |
| 5. Merkle Audit | All | All | All | 22K+ |
| 6. End-to-End | All | All | All | 22K+ |

---

## What We're Optimizing

| Force | Target | Method |
|-------|--------|--------|
| **0% false sign** | Zero risky docs signed | Conformal CRC with α = 0 |
| **Max coverage** | Sign as many safe docs as possible | Threshold optimization |
| **Per-type tuning** | Different thresholds per doc type | Cogym evolution |
| **Auditability** | Prove every decision was calibrated | Merkle hash chain |

---

## Expected Results

| Experiment | Key Finding |
|------------|-------------|
| 1. Risk Classification | 90%+ accuracy on Low, 80%+ on Medium, 70%+ on High |
| 2. Threshold Optimization | Different thresholds: 0.70 (Low), 0.85 (Medium), 0.95 (High) |
| 3. False Sign Optimization | 80%+ coverage at FPR = 0 for Low risk |
| 4. Per-Type Analysis | Invoices easy, KYC hard |
| 5. Merkle Audit | Complete audit trail for every decision |
| 6. End-to-End | 0% false signs, 60%+ coverage |

---

## Frontier Methods Used

| Method | Paper | Experiment |
|--------|-------|------------|
| Conformal Risk Control | Angelopoulos et al., ICLR 2024 | 2, 3 |
| Conformal Classification | Vovk et al. | 1 |
| Cogym Evolution | Our contribution | 2, 4 |
| Merkle Hash Chain | ProofDesk existing | 5 |

---

## Timeline

1. **Day 1:** Experiment 1 (Risk Classification)
2. **Day 2:** Experiment 2 (Threshold Optimization)
3. **Day 3:** Experiment 3 (False Sign Optimization)
4. **Day 4:** Experiments 4-5 (Per-Type + Merkle Audit)
5. **Day 5:** Experiment 6 (End-to-End) + Polish
