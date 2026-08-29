# Provider Benchmark Experiment — Formal Protocol

**Date:** 2026-08-26
**Status:** Ready for execution

---

## 1. Hypothesis

**H1:** Different document processing providers (Nutrient, Doctavian, Foxit) achieve different accuracy, confidence, and speed on the same documents.

**H2:** The optimal provider combination depends on the document type and use case.

**H3:** Provider interchangeability is possible without changing the core SignatureGate logic.

---

## 2. Methods

### 2.1 Dataset
- **Source:** 100 documents from `data/test_pdfs/` (18 PDFs) + generated documents
- **Types:** Invoices, contracts, KYC, insurance, procurement, trade
- **Ground truth:** Manual verification of key fields

### 2.2 Providers Tested

| Provider | API | Task |
|----------|-----|------|
| **Nutrient** | Data Extraction | Extract structured data from PDFs |
| **Doctavian** | Document Generation | Generate documents from templates |
| **Foxit PDF** | PDF Services | Merge, compress, convert |
| **Foxit eSign** | eSign API | Send for signature |

### 2.3 Metrics

| Metric | Definition | How to Measure |
|--------|------------|----------------|
| **Accuracy** | % of fields correctly extracted | Compare to ground truth |
| **Confidence** | Average confidence score | Nutrient/Doctavian output |
| **Speed** | Time per document | Wall clock time |
| **Cost** | API calls per document | Count endpoints called |
| **Reliability** | % of successful calls | Success rate |

### 2.4 Procedure

1. **Phase 1: Extraction Benchmark**
   - Run 100 documents through Nutrient
   - Run same 100 documents through Doctavian
   - Compare accuracy, confidence, speed

2. **Phase 2: Generation Benchmark**
   - Generate same document with Foxit DocGen
   - Generate same document with Doctavian
   - Compare quality, branching, calculations

3. **Phase 3: Combined Benchmark**
   - Test each provider combination
   - Measure end-to-end performance

---

## 3. Expected Results

| Provider | Best For | Worst For |
|----------|----------|-----------|
| **Nutrient** | Extraction accuracy | Generation |
| **Doctavian** | Template branching | Speed |
| **Foxit PDF** | PDF operations | Extraction |
| **Foxit eSign** | Signing workflow | Cost |

---

## 4. Analysis Plan

1. **Statistical tests:** Paired t-test for accuracy comparison
2. **Effect size:** Cohen's d for practical significance
3. **Confidence intervals:** 95% CI for all metrics
4. **Visualization:** Bar charts, box plots, radar charts

---

## 5. Limitations

1. **Small dataset:** 100 documents may not be representative
2. **Single environment:** Results may vary by deployment
3. **Cost not measured:** API pricing not included
4. **Reliability not measured:** Need longer running time

---

## 6. Expected Output

1. **Comparison table:** Provider vs Provider on each metric
2. **Radar chart:** Multi-dimensional comparison
3. **Provider selection guide:** Which provider for which use case
4. **Formal report:** With statistical tests and confidence intervals
