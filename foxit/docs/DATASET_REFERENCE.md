# Canonical Frontier Dataset Reference

## Purpose
Map every document type → risk level → available dataset. Used for benchmarking signing confidence systems.

---

## Risk Level Classification

| Risk Level | Threshold | Description | Action |
|------------|-----------|-------------|--------|
| **Low** | τ = 0.70 | Simple, structured, low-stakes | SIGN if verified |
| **Medium** | τ = 0.85 | Complex, semi-structured, moderate stakes | REVIEW required |
| **High** | τ = 0.95 | Legal, financial, identity, high-stakes | ALWAYS REVIEW |

---

## Dataset Registry

### LOW RISK (τ = 0.70) — Safe to Sign

| Document Type | Dataset | Size | Source | Fraud Labels |
|---------------|---------|------|--------|--------------|
| Invoices | InvoiceBenchmark | 200 | HuggingFace | ✅ 40 fraudulent |
| Invoices | FATURA | 10,000 | HuggingFace | ❌ All safe |
| Receipts | CORD v2 | 11,000 | HuggingFace | ❌ All safe |
| Receipts | SROIE | 1,000 | HuggingFace | ❌ All safe |
| Receipts | WildReceipt | 4,000 | HuggingFace | ❌ All safe |
| Purchase Orders | — | — | Need dataset | — |
| Vendor Quotes | — | — | Need dataset | — |

### MEDIUM RISK (τ = 0.85) — Review Required

| Document Type | Dataset | Size | Source | Fraud Labels |
|---------------|---------|------|--------|--------------|
| Contracts | CUAD | 510 | HuggingFace | ✅ 41 clause types |
| Contracts | ContractNER | 3,240 | HuggingFace | ✅ 18 entity types |
| Contracts | LegalBench | Various | HuggingFace | ✅ Multiple tasks |
| Bank Statements | — | — | Need dataset | — |
| Tax Forms | — | — | Need dataset | — |
| Employment Contracts | — | — | Need dataset | — |

### HIGH RISK (τ = 0.95) — Always Review

| Document Type | Dataset | Size | Source | Fraud Labels |
|---------------|---------|------|--------|--------------|
| Insurance Claims | Fraud Simulator | 5,000 | HuggingFace | ✅ Fraud labels |
| Insurance Claims | INS-007 | 5,000 | HuggingFace | ✅ 99 features |
| Insurance Claims | Vehicle Claims | 1,000 | Kaggle | ✅ Fraud labels |
| Mortgage Apps | HMDA | 5GB+ | Kaggle/FHFA | ✅ Denial reasons |
| Mortgage Appraisals | UAD PUF | Large | FHFA | ✅ Appraisal data |
| KYC Documents | — | — | Need dataset | — |
| Driver Licenses | — | — | Need dataset | — |
| Passports | — | — | Need dataset | — |
| Medical Forms | — | — | Need dataset | — |

---

## Available Datasets (Downloaded/Accessible)

### 1. InvoiceBenchmark (200 invoices)
- **Source**: HuggingFace `jngb-labs/InvoiceBenchmark`
- **Type**: Invoices (Low risk)
- **Labels**: ✅ 160 safe, 40 fraudulent (correct vs incorrect totals)
- **Status**: ✅ Downloaded, tested

### 2. FATURA (10K invoices)
- **Source**: HuggingFace `mathieu1256/FATURA2-invoices`
- **Type**: Invoices (Low risk)
- **Labels**: ❌ All safe
- **Status**: ✅ Downloaded

### 3. FUNSD (199 forms)
- **Source**: HuggingFace `nielsr/funsd-layoutlmv3`
- **Type**: Forms (Medium risk)
- **Labels**: ❌ All need review
- **Status**: ✅ Downloaded

### 4. CUAD (510 contracts)
- **Source**: HuggingFace `theatticusproject/cuad`
- **Type**: Contracts (High risk)
- **Labels**: ✅ 41 clause types, 13K+ annotations
- **Status**: ⏳ Need to download

### 5. ContractNER (3,240 contract chunks)
- **Source**: HuggingFace `agilelab-org/ContractNER_Dataset`
- **Type**: Contracts (High risk)
- **Labels**: ✅ 18 entity types
- **Status**: ✅ Downloaded

### 6. Fraud Simulator (5,000 claims)
- **Source**: HuggingFace `bdr-ai-org/fraud-simulator-dataset`
- **Type**: Insurance claims (High risk)
- **Labels**: ✅ Fraud labels, 12 fraud types
- **Status**: ⏳ Gated, need access

### 7. INS-007 (5,000 claims)
- **Source**: HuggingFace `xpertsystems/ins007-sample`
- **Type**: Insurance claims (High risk)
- **Labels**: ✅ 99 features, fraud rings
- **Status**: ⏳ Sample available

### 8. HMDA (5GB+ mortgage data)
- **Source**: Kaggle/FHFA
- **Type**: Mortgage (High risk)
- **Labels**: ✅ Denial reasons, loan outcomes
- **Status**: ⏳ Large, need to download subset

---

## What We're Missing (Priority Order)

| Priority | Document Type | Why | Dataset Needed |
|----------|---------------|-----|----------------|
| **1** | Contracts | High-risk signing decisions | CUAD (have it, need to download) |
| **2** | Insurance Claims | Fraud detection critical | Fraud Simulator (gated) |
| **3** | Mortgage Docs | High-stakes lending | HMDA (large, need subset) |
| **4** | KYC Documents | Identity verification | Need to find |
| **5** | Rental/Leases | Real estate transactions | Need to find |

---

## Dataset Coverage Matrix

| Document Type | Low Risk | Medium Risk | High Risk | Total |
|---------------|----------|-------------|-----------|-------|
| Invoices | ✅ 10,200 | — | — | 10,200 |
| Receipts | ✅ 15,000 | — | — | 15,000 |
| Forms | — | ✅ 199 | — | 199 |
| Contracts | — | ✅ 3,750 | ✅ 510 | 4,260 |
| Insurance | — | — | ✅ 10,000 | 10,000 |
| Mortgage | — | — | ⏳ Large | — |
| KYC | — | — | ❌ Missing | 0 |
| **Total** | **25,200** | **3,949** | **10,510** | **39,659** |

---

## Key Insight

**We have good coverage for Low and Medium risk. We're missing High risk documents (KYC, medical, some contracts).**

The frontier uses:
- HIRA: 30K documents (retrieval cascade)
- ConfBench: 1.3K variants (calibration)
- EXTRACTCONF: DocILE + CORD (dual-call design)

**Our gap**: We need high-risk documents (contracts, insurance, mortgage) to properly test the signing decision system.

---

## Next Steps

1. Download CUAD (510 contracts) — already accessible
2. Download INS-007 sample (5,000 insurance claims)
3. Download HMDA subset (mortgage data)
4. Find KYC/identity document dataset
5. Build benchmark across all risk levels
