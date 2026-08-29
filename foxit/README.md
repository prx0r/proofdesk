# ProofDesk — Foxit Track

**Project:** Sheepish: Risk-Budgeted Document Signing with Conformal Guarantees
**Team:** Trades
**Tracks:** Foxit, Nutrient, Doctavian
**Deadline:** September 3, 2026

---

## One-Line Pitch

"SignatureGate catches errors at every stage — extraction, classification, signing — with auditable, deterministic decisions."

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (26/26 pass)
python -m pytest tests/test_real.py -v

# Run benchmark
python experiments/benchmark.py

# Start API server
python -m uvicorn src.api.app:app --port 3799
```

---

## What We Built

### Core: SignatureGate
A 5-condition gate that decides when an AI agent can sign a document:
1. No unresolved blockers
2. Human approval present
3. Artifact hash matches
4. Signer authorized
5. Score above threshold

### Key Features

| Feature | Status |
|---------|--------|
| Risk-Adaptive Thresholds | ✅ Working |
| Conformal Risk Control | ✅ Working |
| Sheepish Metric | ✅ Working |
| Merkle Audit Trail | ✅ Working |
| Convergence Loop | ✅ Working |
| MCP Server | ✅ Working |

---

## Experiments (Valid)

| Experiment | Data | Result | Proves |
|------------|------|--------|--------|
| E1: Nutrient Extraction | 468 real PDFs | 0.999 confidence | Extraction works |
| E6: 18-Document Demo | 18 real PDFs | 94.4% accuracy | Pipeline works |
| E12: CUAD Extraction | 468 real PDFs | 261.9 fields/contract | Extraction at scale |
| E14: Unit Tests | 26/26 | All pass | Engineering works |
| E13: Zugferd | 10 real PDFs | 90% accuracy | Format diversity |

### Fraud Detection

| Metric | Value |
|--------|-------|
| Dataset | ColdHearted (9,936 fraud + 9,936 safe) |
| AUC | 0.993 |
| Coverage at 0% FSR | 49.1% |
| Baseline comparison | 99% improvement over random |

---

## Provider Statements

### Foxit
"Foxit PDF Services handles reversible operations while SignatureGate owns the boundary between reversible and irreversible."

### Nutrient
"Nutrient DWS creates evidence with per-field confidence, preserved immutably in our hash-chained audit trail."

### Doctavian
"Template branches on risk band, loops obligations, and calculates totals through mdoc tags."

---

## What We DON'T Claim

- ❌ "98% accuracy" (inflated by class imbalance)
- ❌ "301K documents" (synthetic/fabricated)
- ❌ "System detects fraud" (no fraud labels in CUAD)
- ❌ "Confidence = accuracy" (different things)

---

## What We DO Claim

- ✅ "Nutrient extracts 261.9 fields per contract"
- ✅ "AUC=0.993 on real fraud data"
- ✅ "Merkle audit is tamper-evident"
- ✅ "Every decision auditable"

---

## Repository Structure

```
foxit/
├── src/
│   ├── confidence_module.py    # CRC, EXTRACTCONF, PerField, Isotonic, Sheepish
│   ├── calibration.py          # Isotonic, Platt, CRC, MARGIN
│   ├── metrics.py              # ECE, MCE, Brier, BAS, AURC
│   ├── sheepish.py             # Asymmetric shrinkage
│   ├── experts.py              # MixtureOfExperts, DocTypeRouter
│   ├── foxit_pipeline.py       # DynamicSignatureGate
│   ├── frontier_experiments.py # CRC, SCRC, EXTRACTCONF
│   ├── engine/                 # Orchestrator, reconciliation
│   ├── audit/                  # Merkle, hash chain, certificates
│   ├── models/                 # Domain models
│   ├── state/                  # State machine
│   └── api/                    # FastAPI endpoints
├── tests/
│   └── test_real.py            # 26/26 unit tests
├── experiments/                 # Benchmark scripts
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
├── archive/                    # Old experiments (kept for reference)
├── SUBMISSION_PACKAGE.md       # Hackathon submission
├── EXPERIMENTS_CANONICAL.md    # Experiment inventory
├── HANDOVER.md                 # Dev handover
└── README.md                   # This file
```

---

## License

MIT with commercial use restriction. See LICENSE file.
