# AGENTS.md — ProofDesk Hackathon Project

**Last updated:** 2026-09-01
**Status:** Nutrient DWS submission — see `docs/DEV_PLAN.md` for canonical dev plan
**Deadline:** Sep 3, 2026 10:00 AM PT

---

## Project Overview

ProofDesk is an **evidence-gated document execution system** for the DevNetwork API+Cloud+AI Hackathon 2026 (Nutrient DWS track). Nutrient DWS extracts grounded evidence from source documents. ProofDesk reconciles it, estimates decision risk, routes uncertain cases to people, and produces a replayable audit trail.

**Core thesis:** "Nutrient provides trustworthy evidence. ProofDesk turns that evidence into progressively better calibrated authority."

**Canonical dev plan:** `docs/DEV_PLAN.md` (2101 lines, 23 phases + audit appendix)

---

## Quick Start

```bash
cd /home/box/Documents/patala/proofdesk

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.keys .env

# 3. Run tests
python3 tests/test_all.py

# 4. Start demo
python3 demo_2min.py

# 5. Start server
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

---

## Where Everything Is

### Core Code

| File | Purpose |
|------|---------|
| `src/api/app.py` | FastAPI server (start here) |
| `src/engine/batch.py` | Batch processor (main logic) |
| `src/engine/orchestrator.py` | Single-file pipeline |
| `src/engine/reconciliation.py` | Cross-document checks |
| `src/engine/feedback.py` | Convergence loop |
| `src/engine/cost_analysis.py` | ROI tracking |
| `src/engine/evaluation.py` | Binary rubric evaluation |
| `src/providers/nutrient.py` | Nutrient DWS API (REAL) |
| `src/providers/doctavian.py` | Doctavian API (REAL) |
| `src/providers/classifier.py` | Risk classification |
| `src/providers/extractconf.py` | EXTRACTCONF verification |
| `src/providers/ravidp.py` | RaV-IDP validation |
| `src/providers/confbench.py` | Distribution monitoring |
| `src/audit/chain.py` | Hash-chained ledger |
| `src/audit/merkle.py` | Merkle tree |

### Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_all.py` | 38 core tests | ✅ All passing |
| `tests/test_audit.py` | 25 audit tests | ✅ All passing |
| `tests/test_doctavian.py` | 3 Doctavian tests | ✅ All passing |
| `tests/test_frontier.py` | 16 frontier tests | ✅ All passing |
| `tests/test_learning.py` | 3 convergence tests | ✅ All passing |

### Data

| Directory | Contents |
|-----------|----------|
| `fixtures/demo/` | 4 canonical demo PDFs (committed to Git) |
| `data/test_pdfs/` | 18 test PDFs (gitignored, for local dev) |
| `data/datasets/pdfs/` | 509 CUAD contracts (gitignored) |
| `data/templates/` | Doctavian DOCX template |

### Scripts

| Script | Purpose |
|--------|---------|
| `demo_2min.py` | 2-minute demo presentation |
| `run_benchmark.py` | Full benchmark on CUAD dataset |
| `generate_visuals.py` | Generate charts for presentation |
| `pitch_script.py` | Pitch script for judges |

---

## How It Works

### Pipeline

```
PDF → Nutrient Extract → Verify → Classify → Route → Human → Audit
  │        │              │        │         │       │       │
  │        │              │        │         │       │       └─ Hash chain + Merkle
  │        │              │        │         │       └─ Binary feedback
  │        │              │        │         └─ AUTO/DEFER/BLOCK
  │        │              │        └─ 5 frontier algorithms
  │        │              └─ Cross-document checks
  │        └─ Real API: value + confidence + page + bbox
  └─ 509 CUAD contracts
```

### Classification Decision

```python
if has_unresolved_blockers:
    decision = "BLOCKED"
elif per_field_violations:
    decision = "DEFER_TO_HUMAN"
elif calibrated_confidence >= threshold:
    decision = "AUTO_SIGN"
else:
    decision = "DEFER_TO_HUMAN"
```

---

## Key Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Documents processed | 20 CUAD contracts | Real Nutrient API |
| Accuracy | 95% (19/20) | Binary rubric |
| False Positive Rate | 5% (1/20) | Measured |
| Auto-sign rate | 10% (2/20) | High confidence |
| Deferred to human | 80% (16/20) | Correct |
| Blocked | 10% (2/20) | High-risk |
| Cost savings | $19,437 | Fraud prevention |
| ROI | 3,239% | Cost analysis |

---

## Sponsor Integration

| Provider | What It Does | Status |
|----------|--------------|--------|
| **Nutrient DWS** | Extracts facts with source grounding | ✅ Real API |
| **Doctavian** | Template branching, loops, calculations | ⚠️ API works, generation fails |
| **Foxit PDF** | Merge/compress documents | ✅ Real API |
| **Foxit eSign** | Signing authority boundary | ❌ Simulated |

---

## API Keys

Stored in `.env.keys` (DO NOT COMMIT):

- **Nutrient DWS:** see `.env.keys`
- **Doctavian:** API key + Bearer token (expired, needs refresh)
- **Foxit PDF:** Client ID + Client Secret

---

## Run Commands

### Tests
```bash
python3 tests/test_all.py         # 38/38
python3 tests/test_audit.py       # 25/25
python3 tests/test_doctavian.py   # 3/3
python3 tests/test_frontier.py    # 16/16
python3 tests/test_learning.py    # 3/3
```

### Demo
```bash
python3 demo_2min.py              # 2-minute demo
python3 run_benchmark.py          # Full benchmark
python3 generate_visuals.py       # Generate charts
python3 pitch_script.py           # Show pitch
```

### Server
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

---

## Known Issues

| Issue | Status | Fix |
|-------|--------|-----|
| Doctavian generation fails | OAuth scope issue | Refresh token via portal |
| Foxit eSign simulated | No real keys | Register at developer portal |
| Nutrient Viewer not tested | Integrated but untested | Test with real API |
| Human ground truth heuristic | Using heuristic | Need human labels |

---

## Files to Read First

1. `docs/DEV_PLAN.md` — Canonical dev plan (23 phases + audit appendix)
2. `docs/AUTHORITYBENCH_PLAN.md` — Stretch goal: benchmark + Trust Lab + paper
3. `README.md` — Project overview (Nutrient-first)
4. `src/engine/orchestrator.py` — Pipeline orchestration
5. `src/state/machine.py` — SignatureGate (6 conditions)
6. `src/engine/feedback.py` — Convergence loop
6. `tests/test_all.py` — How tests work

---

## Handover Checklist

- [ ] All tests passing (85/85)
- [ ] Demo script working
- [ ] Benchmark script working
- [ ] Visualizations generated
- [ ] Pitch script ready
- [ ] API keys configured
- [ ] README comprehensive
- [ ] .gitignore updated
- [ ] No secrets in repo
