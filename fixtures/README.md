# Fixtures

Committed test fixtures for deterministic demos and CI. These files are
**always in Git** — the core demo and tests must never depend on
`data/test_pdfs/` (which is gitignored).

## demo/

The four canonical procurement documents used by:
- `tests/test_learning.py` (determinism + convergence tests)
- `/v1/cases/fixture` endpoint (API demo)
- `demo_2min.py` (CLI demo)
- `scripts/headless_inspect.py`
- `scripts/mcp_inspect.py`

| File | Purpose |
|------|---------|
| `procurement_request.pdf` | Spend request ($42,500) |
| `vendor_quote.pdf` | Vendor pricing breakdown |
| `insurance_certificate.pdf` | COI with expiry gap (the blocker) |
| `security_questionnaire.pdf` | Encryption + compliance attestation |

All files are ~1.3KB single-page PDFs generated deterministically.
