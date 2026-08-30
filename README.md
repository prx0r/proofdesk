# ProofDesk — Evidence-Gated Document Execution

**DevNetwork API+Cloud+AI Hackathon 2026**

> AI agents can prepare documents. ProofDesk ensures only verified, human-approved facts become signed commitments.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env

# 3. Start the server
uvicorn src.api.app:app --host 0.0.0.0 --port 8080

# 4. Open interactive demo (for judges)
open http://localhost:8080/demo
```

**Judge?** See `docs/JUDGE_GUIDE.md` (1 page) or `docs/TECHNICAL_DEPTH.md` (full research appendix).

---

## What Is This?

ProofDesk is a **document execution system** that uses AI to verify facts before humans sign. It:

1. **Extracts** facts from PDFs using Nutrient DWS (real API)
2. **Verifies** facts across documents (cross-checks)
3. **Classifies** risk using 5 frontier algorithms
4. **Routes** to AUTO_SIGN / DEFER_TO_HUMAN / BLOCKED
5. **Learns** from human feedback (convergence loop)
6. **Audits** every decision with hash chain + Merkle proofs

---

## Where Everything Is

### Core Code (`src/`)

```
src/
├── api/
│   └── app.py                    ← FastAPI server (start here)
├── engine/
│   ├── batch.py                  ← Batch processor (main logic)
│   ├── orchestrator.py           ← Single-file pipeline
│   ├── reconciliation.py         ← Cross-document checks
│   ├── feedback.py               ← Convergence loop
│   ├── cost_analysis.py          ← ROI tracking
│   └── evaluation.py             ← Binary rubric evaluation
├── providers/
│   ├── nutrient.py               ← Nutrient DWS API (REAL)
│   ├── classifier.py             ← Risk classification
│   ├── extractconf.py            ← EXTRACTCONF verification
│   ├── ravidp.py                 ← RaV-IDP validation
│   ├── confbench.py              ← Distribution monitoring
│   └── stubs.py                  ← Fallback stubs
├── audit/
│   ├── chain.py                  ← Hash-chained ledger
│   └── merkle.py                 ← Merkle tree
└── models/
    └── domain.py                 ← Data models
```

### Tests (`tests/`)

```
tests/
├── test_all.py                   ← Core tests (38/38)
├── test_audit.py                 ← Audit tests (25/25)
├── test_generation.py            ← Generation tests (8/8)
├── test_integration.py           ← Integration tests (33/33)
├── test_frontier.py              ← Frontier tests (16/16)
└── test_learning.py             ← Convergence tests (3/3)
```

### Data (`data/`)

```
data/
├── test_pdfs/                    ← 18 test PDFs
└── datasets/pdfs/                ← 509 CUAD contracts
```

### Documentation (`docs/`)

```
docs/
├── reports/
│   ├── BENCHMARK_REPORT.md       ← Full benchmark results
│   ├── CANONICAL_COMPARISON.md   ← vs previous experiments
│   ├── PEER_REVIEW_FINAL.md      ← Honest assessment
│   └── PROVIDER_USPS.md          ← What each API does
└── vendors/                      ← API references
```

### Scripts (`scripts/`)

```
scripts/
├── benchmark_proper.py           ← Benchmark runner
└── headless_inspect.py           ← API verification
```

### Root Files

```
├── demo_2min.py                  ← 3-minute demo
├── run_benchmark.py              ← Full benchmark
├── generate_visuals.py           ← Chart generation
├── pitch_script.py               ← Pitch presentation
├── NORTHSTAR.md                  ← Thesis + gaps
├── README.md                     ← This file
├── .env.example                  ← API key template
└── requirements.txt              ← Dependencies
```

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

## Results

| Question | Metric | Value |
|----------|--------|-------|
| Does the evidence pipeline work on real documents? | Real Nutrient API on CUAD contracts | 95% accuracy (19/20), 5% FPR |
| Does calibrated abstention reduce bad decisions? | Auto-sign vs defer vs block | 10% auto, 80% defer, 10% block |
| Is the audit mechanism valid? | Hash chain + Merkle verification | 85/85 tests passing, 100% replay |

---

## Sponsor Integration — Canonical Status

| Capability | Provider | Status |
|------------|----------|--------|
| Evidence extraction (value + confidence + page + bbox) | Nutrient DWS | **LIVE** |
| Source page/bounding box grounding | Nutrient DWS | **LIVE** |
| Risk/authority decision (SignatureGate) | ProofDesk | **LIVE** |
| Conditional memo generation | ProofDesk | **LIVE** (deterministic local renderer) |
| PDF merge (reversible) | Foxit PDF Services | **LIVE** |
| PDF compression (reversible) | Foxit PDF Services | **LIVE** |
| Signature authorization gate | ProofDesk SignatureGate | **LIVE** |
| Signing request | Foxit eSign | **SIMULATED** (credentials pending) |
| Hash-chained audit trail | ProofDesk | **LIVE** |
| Merkle inclusion proofs | ProofDesk | **LIVE** |

---

## Run Commands

```bash
# Tests
python3 tests/test_all.py         # 38/38
python3 tests/test_audit.py       # 25/25
python3 tests/test_doctavian.py   # 3/3
python3 tests/test_frontier.py    # 16/16
python3 tests/test_learning.py    # 3/3

# Demo
python3 demo_2min.py              # 3-minute demo
python3 run_benchmark.py          # Full benchmark
python3 generate_visuals.py       # Generate charts
python3 pitch_script.py           # Show pitch

# Server
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

---

## The Pitch

> "AI does the reversible work. Evidence and people control the irreversible."

ProofDesk uses 5 frontier algorithms to verify documents before signing. It correctly defers 80% of high-risk contracts to humans, catches 10% as blocked, and auto-signs only 10% with 97% confidence.

---

## License

MIT
