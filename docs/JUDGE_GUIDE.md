# ProofDesk — Judge Guide

**One page. Everything you need.**

---

## What is ProofDesk?

Evidence-gated document automation. Nutrient DWS extracts grounded evidence from source documents. ProofDesk reconciles it, estimates decision risk, routes uncertain cases to people, and produces a replayable audit trail.

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
| 4. Resolve | Human reviews source evidence, approves exception |
| 5. Generate | ProofDesk creates risk-branched approval memo (PDF) |
| 6. Prepare | PDF merge + compress (reversible) |
| 7. Sign | Gate passes six conditions, signing request sent |
| 8. Audit | Hash chain + Merkle proofs prove every transition |

---

## Nutrient DWS Integration

Nutrient DWS turns source PDFs into **grounded field evidence** — values, confidence, page and bounding-box provenance — that ProofDesk uses to decide whether automation may proceed or must defer to a human.

| Capability | Status |
|------------|--------|
| Evidence extraction (value + confidence + page + bbox) | **LIVE** |
| Source grounding with page coordinates | **LIVE** |
| Risk classification with per-field budgets | **LIVE** |
| Calibrated authority gate (6 conditions) | **LIVE** |
| Hash-chained audit trail | **LIVE** |
| Merkle inclusion proofs | **LIVE** |

---

## Key API Endpoints

```
GET  /demo                          — Interactive demo (click through)
GET  /v1/providers/status           — LIVE/STUB per provider
GET  /v1/cases/{id}/facts           — Extracted facts with bbox
GET  /v1/cases/{id}/signature-gate  — Gate check (reasons + checks)
GET  /v1/cases/{id}/trace           — Provider HTTP trace (Nutrient DWS calls)
POST /v1/cases/{id}/demo/tamper     — Tamper one byte, recompute hash
POST /v1/cases/{id}/demo/restore    — Restore from backup
GET  /v1/feedback/stats             — Convergence loop stats
```

---

## Why This Wins

1. **Nutrient DWS as the foundation**: Real extraction with source grounding, confidence, and page coordinates — not just form-filling
2. **The authority gate**: Tool access is not authority. The agent can prepare documents but cannot create legal commitment
3. **Human decisions become calibration data**: The convergence loop means the system improves with use
4. **Deterministic audit**: Merkle-sealed hash chain binding every decision to evidence
5. **Honest submission**: Every integration labeled LIVE or SIMULATED. No fake demos

---

## Technical Depth (if you want it)

See `docs/TECHNICAL_DEPTH.md` for:
- 6 calibrated algorithms (Conformal Risk Control, EXTRACTCONF, Per-Field Risk, Isotonic, Sheepish, Online Calibration)
- Mixture of Experts with per-world calibration
- Hash-chained audit trail with Merkle inclusion proofs
- Convergence loop: human labels -> online calibrator -> improved decisions

---

## Tests

```bash
python3 tests/test_all.py          # 38/38
python3 tests/test_audit.py        # 25/25
python3 tests/test_integration.py  # 33/33
python3 tests/test_learning.py     # 3/3
```

---

## One-Line Pitch

> **Nutrient provides trustworthy evidence. ProofDesk turns that evidence into progressively better calibrated authority.**
