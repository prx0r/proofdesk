# Real Nutrient DWS Extraction Accuracy — 4 Procurement Documents

**Date:** 2026-08-25
**API:** Nutrient DWS /extraction/extract (understand mode)
**Documents:** 4 real procurement PDFs (procurement_request, vendor_quote, insurance_certificate, security_questionnaire)

## Results

| Field | Accuracy | Confidence | Notes |
|-------|----------|------------|-------|
| vendor.legal_name | 100% (4/4) | 95% | Correct across all 4 docs |
| procurement.requested_spend | 100% (1/1) | 97% | Exact numeric match |
| procurement.contract_start | 100% (1/1) | 95% | ISO date format |
| procurement.required_coverage_until | 100% (1/1) | 95% | ISO date format |
| quote.total | 100% (1/1) | 97% | Exact numeric match |
| quote.platform_price | 100% (1/1) | 97% | Exact numeric match |
| quote.support_price | 100% (1/1) | 97% | Exact numeric match |
| insurance.expiry_date | 100% (1/1) | 95% | ISO date format |
| security.data_retention_days | 100% (1/1) | 97% | Exact numeric match |
| security.subprocessors | 100% (1/1) | 97% | Exact numeric match |
| security.encryption_at_rest | 0% (0/1) | 97% | Nutrient returns "true" (string), we compare to True (bool) — normalization issue |

**OVERALL: 92.9% (13/14 fields correct)**

## Key Findings

1. **Nutrient DWS is excellent on clean PDFs** — 92.9% accuracy with 95-97% confidence
2. **The one "failure" is our normalization** — Nutrient returns `"true"` (string), we compare to `True` (Python bool). Fix: normalize to lowercase string before comparison.
3. **All procurement fields extracted correctly** — vendor name, spend, dates, quote items
4. **Confidence scores are consistent** — 95% for text fields, 97% for numeric fields
5. **Bounding boxes provided** — every fact has page number and coordinates for source-jump

## Comparison to Previous Benchmarks

| Dataset | Accuracy | Notes |
|---------|----------|-------|
| Our 4 procurement PDFs (real) | 92.9% | Clean PDFs, Nutrient understand mode |
| SROIE receipts (real images) | 60% | Noisy receipt images, harder |
| SROIE receipts (previous) | 53% | Nutrient on 10 receipts |

**Key insight:** Nutrient excels on clean PDFs (93%) but struggles on noisy receipt images (53%). The procurement use case is the sweet spot.
