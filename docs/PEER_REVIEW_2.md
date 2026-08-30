# Peer Review 2 — ProofDesk Post-Push Assessment

**Commit:** 87131c2
**Date:** 2026-08-31

## Assessment

| Dimension | Previous | Now | After P0 fixes |
|-----------|----------|-----|----------------|
| Product concept | 9.5 | **9.5** | 9.5 |
| Packaging | 5.5 | **8.5** | 9.3 |
| Demo UX | 6.5 | **8.0 visual / 5.5 technical** | 9.5 |
| Technical correctness | 7.0 | **6.5–7.0** | 9.0 |
| Nutrient fit | 8.5 | **8.2** | 9.3 |
| Doctavian fit | 5.5 | **6.5** | 9.0 |
| Foxit fit | 6.5 | **5.5** | 9.3 |
| Overall win potential | strong | **very strong but exposed** | **legitimate contender** |

## P0 Issues

### 1. Foxit pipeline still wrong
- `foxit_pdf_prepare` receives `GeneratedArtifact`, not `case.documents`
- Falls back to hard-coded `data/test_pdfs/procurement_request.pdf`
- Compression applies to source, not merge result
- No task polling — async operations never resolve to final PDF

### 2. reportlab not in requirements.txt
- Memo upload silently fails on clean install
- Demo shows green ticks for operations that didn't happen

### 3. Web demo lies about what happened
- Never calls `/signature-request` or `/sign`
- Hard-coded green ticks not derived from API responses
- No `response.ok` checks

### 4. SignatureGate doesn't enforce calibrated score
- Doesn't check confidence vs threshold
- Doesn't check per-field risk budgets
- Submission claims calibrated gate, code doesn't implement it

### 5. ARTIFACT_HASH_MISMATCH is fake
- Checks artifact references record, not artifact bytes
- No SHA-256 of actual final PDF
- Tamper demo doesn't actually tamper

### 6. Nutrient None confidence crashes downstream
- `f.get("confidence", 0.5)` returns `None` when key exists with None value
- TypeError on arithmetic

### 7. Doctavian failure control flow broken
- Failure object treated as generated document
- Doesn't fall through to local renderer

### 8. No tests cover behavioral changes

### 9. Dependencies missing from requirements.txt

### 10. Foxit eSign credentials still missing
- Challenge explicitly requires real human signing

## Dev Order

1. Fix Nutrient None confidence crash
2. Fix page vs source_page in demos
3. Make Foxit prep receive real case.documents
4. Add Foxit task polling → merge resultDocumentId → compress → download
5. SHA-256 actual final PDF bytes, store in gate check
6. Move calibrated confidence/threshold into can_request_signature()
7. Make /demo consume real API responses
8. Fix Doctavian failed-generation control flow
9. Add 10 integration tests
10. Add python-multipart + reportlab to requirements.txt

## What's Good

1. Eight-stage demo narrative — essentially perfect
2. Canonical sponsor matrix — good, tighten status taxonomy
3. Fail-closed philosophy — correct direction
4. Removal of $19K ROI nonsense
5. Product story: "AI does the reversible work. Evidence and people control the irreversible."
