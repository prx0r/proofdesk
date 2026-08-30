# ProofDesk — Judge Guide

**One page. Everything you need.**

---

## What is ProofDesk?

An authority gate for document agents. AI can prepare documents, merge PDFs, compress files. But signing creates legal commitment. ProofDesk decides when that's allowed.

> **Tool access is not authority.**

---

## Quick Start

```bash
cd proofdesk
pip install -r requirements.txt
cp .env.example .env
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080/demo
```

---

## What You'll See (8 stages)

| Stage | What Happens |
|-------|-------------|
| 1. Premise | Agent receives: "Prepare $42,500 vendor agreement, send to CFO" |
| 2. Evidence | Nutrient DWS extracts 13 facts with confidence + page + bbox |
| 3. Blocked | SignatureGate denies — insurance coverage mismatch |
| 4. Resolve | Human reviews evidence, approves exception |
| 5. Generate | ProofDesk creates risk-branched approval memo (PDF) |
| 6. Prepare | Foxit PDF Services merges + compresses (reversible) |
| 7. Sign | Gate passes → signing request sent |
| 8. Audit | Hash chain + Merkle proofs prove every transition |

---

## Three Sponsors, One Transaction

| Sponsor | What It Does | Status |
|---------|-------------|--------|
| **Nutrient DWS** | Evidence extraction with source grounding | LIVE |
| **Foxit PDF Services** | Merge + compress (reversible) | LIVE |
| **Foxit eSign** | Signing (irreversible) | SIMULATED |

---

## Key API Endpoints

```
GET  /demo                          — Interactive demo (click through)
GET  /v1/providers/status           — LIVE/STUB per provider
GET  /v1/cases/{id}/facts           — Extracted facts with bbox
GET  /v1/cases/{id}/signature-gate  — Gate check (reasons + checks)
GET  /v1/cases/{id}/trace           — Provider HTTP trace
POST /v1/cases/{id}/demo/tamper     — Tamper one byte, recompute hash
POST /v1/cases/{id}/demo/restore    — Restore from backup
```

---

## Why This Wins

1. **Concept:** "Tool access is not authority" — the best pitch in the hackathon
2. **Nutrient:** Real DWS extraction, source grounding, confidence-aware routing
3. **Foxit:** Real PDF merge/compress with task polling + SHA-256 verification
4. **Gate:** 6 conditions: state, blockers, approval, record, hash, calibrated score
5. **Honest:** Every integration labeled LIVE or SIMULATED

---

## Technical Depth (if you want it)

See `docs/TECHNICAL_DEPTH.md` for:
- 5 frontier algorithms (Conformal Risk Control, EXTRACTCONF, Per-Field Risk, Isotonic, Sheepish)
- Mixture of Experts with per-world calibration
- 24,878-document benchmark (59.8% auto-sign at 1% FSR)
- CogymKernel evolutionary optimization
- Hash-chained audit trail with Merkle inclusion proofs
- 14 papers cited, novel Sheepish metric

---

## Tests

```bash
python3 tests/test_all.py          # 38/38
python3 tests/test_audit.py        # 25/25
python3 tests/test_generation.py   # 8/8
python3 tests/test_integration.py  # 33/33
```

---

## One-Line Pitch

> **AI does the reversible work. Evidence and people control the irreversible.**
