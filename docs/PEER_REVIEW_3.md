# Peer Review 3 — Post-Doctavian-Drop Assessment

**Commit:** fa61e1c
**Date:** 2026-08-31

## Assessment

| Area | 87131c2 | fa61e1c | After fixes |
|------|---------|---------|-------------|
| Concept | 9.5 | **9.5** | 9.6 |
| Repo clarity | 8.5 | **8.3** | 9.4 |
| Core correctness | 6.5 | **8.0** | 9.3 |
| Demo credibility | 5.5 | **7.8** | 9.5 |
| Nutrient track | 8.2 | **8.8** | 9.5 |
| Foxit track | 5.5 | **6.0** | 9.3 |
| Technical depth | 9.5 | **9.5** | 9.5 |

## P0 Issues

### 1. Calibrated SignatureGate not wired in production pipeline
- `confidence_adapter.score_case()` returns `{confidence, band, field_risks}` but NO `threshold`
- `field_risks` don't contain `within_budget`
- Gate receives `threshold=None` → runs `partial_calibration_data` without blocking
- **Fix:** Replace confidence_adapter with canonical DecisionCertificate from classifier.py

### 2. confidence_adapter.py has 3 correctness bugs
- `field_accuracy = hunter` recreates label leakage
- Grounding calculation inverted (10% → 100%)
- `f.confidence < threshold` crashes on None

### 3. Extraction failure can become APPROVABLE
- Empty facts → empty assertions → 0 blockers → APPROVABLE
- **Fix:** Missing required evidence must be a blocker

### 4. Local generation writes .txt, not .pdf
- Foxit upload only picks up `.pdf` files
- Approval memo never enters the Foxit packet
- **Fix:** Use reportlab to generate actual PDF

### 5. SHA-256 is metadata, not a guard
- Gate appends hash to checks but never recomputes and compares
- **Fix:** Recompute hash at gate time, compare to stored hash

### 6. Foxit download failure is fail-open
- `except Exception: pass` → status="prepared" even with no hash
- **Fix:** Raise on download failure

### 7. Foxit eSign removed from canonical path
- `request_signature()` unconditionally uses stub
- FoxitESignClient exists but nothing calls it
- **Fix:** Restore conditional eSign path

### 8. "FreeSign" is fabricated
- No FreeSign integration exists
- Stub creates random IDs and says "SENT"
- **Fix:** Label as "SIMULATED" not "FreeSign"

### 9. Stub identifies as real Foxit
- `"provider": "foxit_pdf_services"` in stub output
- **Fix:** Add `mode: "live"/"stub"` to all provider results

### 10. Calling REST "MCP" is incorrect
- Foxit direct REST ≠ Foxit MCP server
- **Fix:** Either wire MCP or rename to "Foxit PDF Services API"

### 11. Tests overstate coverage
- TEST-002 doesn't call parse_document
- TEST-003 tests stub not real
- TEST-007 doesn't induce failure
- No mock-based integration tests

### 12. No CI
- GitHub reports no status checks

### 13. Doctavian still in repo tree
- `src/providers/doctavian.py` still exists
- README still references Doctavian

### 14. README stale
- Lists test_doctavian.py, old Doctavian client, 85/85 count

### 15. HACKATHON_SUBMISSION.md stale
- Claims Foxit eSign integration that doesn't exist in canonical path

## Dev Order

1. Replace confidence_adapter with canonical DecisionCertificate
2. Missing extraction → blocking state
3. Local generation creates PDF not .txt
4. Verify generated memo in Foxit merge input
5. Foxit download/hash failure fatal
6. Store final PDF path + SHA-256, recompute in gate
7. Bind SignatureRequest to final prepared PDF hash
8. Real tamper demo
9. Explicit live/stub provenance
10. Wire MCP or rename to PDF Services
11. Mock-based integration tests + CI
12. Clean Doctavian from tree + fix README/HACKATHON_SUBMISSION
