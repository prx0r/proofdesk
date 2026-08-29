# Canonical Document Type Classification Reference

## Purpose
Map document types to signing decisions. Based on frontier classification systems (Talonic 529-type ontology, MMM-Bench 5-level taxonomy, UiPath formats).

## Classification Hierarchy

### Level 1: Document Format
| Format | Examples | Signing Risk |
|--------|----------|--------------|
| Structured | Forms, questionnaires, tax forms | Low (deterministic) |
| Semi-structured | Invoices, receipts, POs, bank statements | Medium (variable) |
| Unstructured | Contracts, leases, agreements | High (complex) |

### Level 2: Business Domain
| Domain | Document Types | Signing Decision |
|--------|---------------|------------------|
| **Procurement** | Purchase orders, vendor quotes, invoices | SIGN (low risk) |
| **Finance** | Bank statements, loan applications | REVIEW (medium risk) |
| **Legal** | Contracts, NDAs, leases, agreements | REVIEW (high risk) |
| **Insurance** | Claims, policies, certificates | REVIEW (high risk) |
| **HR** | Employment contracts, onboarding forms | REVIEW (medium risk) |
| **Healthcare** | Patient forms, consent documents | ALWAYS REVIEW |
| **Identity** | Passports, licenses, KYC documents | ALWAYS REVIEW |
| **Real Estate** | Deeds, titles, appraisals | REVIEW (high risk) |

### Level 3: Risk Classification

| Risk Level | Threshold | Documents | Action |
|------------|-----------|-----------|--------|
| **Low** | τ = 0.70 | Invoices, receipts, POs, quotes | SIGN if verified |
| **Medium** | τ = 0.85 | Contracts, bank statements | REVIEW required |
| **High** | τ = 0.95 | KYC, mortgage, medical, legal | ALWAYS REVIEW |

## Document Type → Signing Decision Matrix

| Document Type | Format | Domain | Risk | Threshold | Action |
|---------------|--------|--------|------|-----------|--------|
| Invoice | Semi-structured | Procurement | Low | 0.70 | SIGN |
| Purchase Order | Semi-structured | Procurement | Low | 0.70 | SIGN |
| Vendor Quote | Semi-structured | Procurement | Low | 0.70 | SIGN |
| Receipt | Semi-structured | Finance | Low | 0.70 | SIGN |
| Bank Statement | Semi-structured | Finance | Medium | 0.85 | REVIEW |
| Contract | Unstructured | Legal | High | 0.95 | REVIEW |
| NDA | Unstructured | Legal | High | 0.95 | REVIEW |
| Lease Agreement | Unstructured | Real Estate | High | 0.95 | REVIEW |
| Insurance Policy | Semi-structured | Insurance | High | 0.95 | REVIEW |
| Insurance Claim | Semi-structured | Insurance | High | 0.95 | REVIEW |
| Employment Contract | Unstructured | HR | Medium | 0.85 | REVIEW |
| KYC Document | Semi-structured | Identity | High | 0.95 | ALWAYS REVIEW |
| Driver License | Semi-structured | Identity | High | 0.95 | ALWAYS REVIEW |
| Passport | Semi-structured | Identity | High | 0.95 | ALWAYS REVIEW |
| Mortgage Application | Semi-structured | Real Estate | High | 0.95 | ALWAYS REVIEW |
| Appraisal Report | Semi-structured | Real Estate | High | 0.95 | ALWAYS REVIEW |
| Medical Form | Semi-structured | Healthcare | High | 0.95 | ALWAYS REVIEW |
| Tax Form | Semi-structured | Finance | Medium | 0.85 | REVIEW |
| Bill of Lading | Semi-structured | Logistics | Medium | 0.85 | REVIEW |
| Certificate of Origin | Semi-structured | Trade | Low | 0.70 | SIGN |

## Dataset Coverage

| Dataset | Document Types | Risk Level | Coverage |
|---------|---------------|------------|----------|
| InvoiceBenchmark | Invoices | Low | ✅ |
| FATURA | Invoices | Low | ✅ |
| FUNSD | Forms | Medium | ✅ |
| CORD | Receipts | Low | ⏳ (gated) |
| CUAD | Contracts | High | ✅ |
| ContractNER | Contracts | High | ✅ |
| RealKIE | Enterprise docs | Medium-High | ⏳ (gated) |
| BuDDIE | Business docs | Medium | ⏳ (need access) |

## What We're Missing

| Document Type | Dataset | Risk | Priority |
|---------------|---------|------|----------|
| Contracts | CUAD (510 contracts) | High | High |
| NDAs | ContractNER | High | High |
| Leases | Need to find | High | High |
| Insurance Claims | Need to find | High | Medium |
| Mortgage Docs | Need to find | High | Medium |
| KYC Documents | Need to find | High | Low |

## Key Insight

**The harder the document, the higher the threshold.**

- Easy docs (invoices): τ = 0.70, sign freely
- Medium docs (contracts): τ = 0.85, review required
- Hard docs (KYC, mortgage): τ = 0.95, always review

This is the core of the Foxit challenge: "When should an agent sign?"
