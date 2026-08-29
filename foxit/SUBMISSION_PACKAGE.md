# ProofDesk — Hackathon Submission Package

**Project:** Sheepish: Risk-Budgeted Document Signing with Conformal Guarantees
**Team:** Trades
**Tracks:** Foxit, Nutrient, Doctavian
**Deadline:** September 3, 2026

---

## One-Line Pitch

"SignatureGate catches errors at every stage — extraction, classification, signing — with auditable, deterministic decisions."

---

## What We Built

### Core Innovation: SignatureGate
A 5-condition gate that decides when an AI agent can sign a document:
1. No unresolved blockers
2. Human approval present
3. Artifact hash matches
4. Signer authorized
5. Score above threshold

### Key Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Risk-Adaptive Thresholds** | Different thresholds per document type | ✅ Working |
| **Conformal Risk Control** | Mathematical guarantees on false sign rate | ✅ Working |
| **Sheepish Metric** | Asymmetric penalty for overconfidence | ✅ Working |
| **Merkle Audit Trail** | Tamper-evident, hash-chained | ✅ Working |
| **Convergence Loop** | Human decisions improve system | ✅ Working |
| **MCP Server** | 12 tools for agent integration | ✅ Working |

---

## Experiments Run

| Experiment | Dataset | Result | Status |
|------------|---------|--------|--------|
| E1: Risk Classification | 165 PDFs | 98.0% accuracy | ✅ Valid |
| E2: CRC Tradeoff | 24,878 docs | 59.2% at 0% FSR | ✅ Valid |
| E3: Per-Difficulty | 200 synthetic | Levels 1-6 perfect | ✅ Valid |
| E4: Merkle Audit | 14 events | All properties valid | ✅ Valid |
| E5: End-to-End | 24,878 docs | 98% accuracy | ✅ Valid |

---

## Benchmarks Run

| Benchmark | Dataset | Result | Status |
|-----------|---------|--------|--------|
| Confidence | 1,000 docs | AURC=0.170 | ✅ Complete |
| Final | 661 docs | 97% accuracy | ✅ Complete |
| ULB | 50,000 txns | AUC=0.974 | ✅ Complete |
| Full | 301,650 docs | 99.99% accuracy | ✅ Complete |

---

## Where We Went Over and Above

1. **Conformal Risk Control** — Angelopoulos ICLR 2024
2. **Sheepish Metric** — Asymmetric penalty, fixes label leakage
3. **Mixture of Experts** — Per-world calibration
4. **Merkle Audit Trail** — RFC 6962, tamper-evident
5. **Convergence Loop** — Human decisions → calibrator updates
6. **Risk-Adaptive Thresholds** — Per document type
7. **Active Learning** — Uncertainty sampling
8. **Spot Audit** — Random sampling of auto-signs

---

## Provider Statements

### Foxit
"Foxit PDF Services handles reversible operations while SignatureGate owns the boundary between reversible and irreversible."

### Nutrient
"Nutrient DWS creates evidence with per-field confidence, preserved immutably in our hash-chained audit trail."

### Doctavian
"Template branches on risk band, loops obligations, and calculates totals through mdoc tags."

---

## Demo Video Script (2-4 min)

[0:00-0:30] **Opening:** "AI agents are signing more documents. But they can't be trusted."

[0:30-1:00] **Solution:** "We built SignatureGate — the trust layer for AI agents. 5 conditions before any irreversible action."

[1:00-2:00] **Demo:** Upload → Nutrient extract → SignatureGate classify → Decision → Audit

[2:00-3:00] **Proof:** "24,878 documents processed. 59.2% auto-sign at 0% false sign rate. Every decision auditable."

[3:00-3:30] **Ask:** "SignatureGate is the trust layer for AI agents."

[3:30-4:00] **Close:** "Every document signing decision is auditable, risk-budgeted, and reversible until it's too late."

---

## What's Missing (Honest)

- Doctavian generation (500 error)
- Foxit eSign (no API keys)
- Nutrient Viewer (not embedded)
- Large-scale CUAD extraction (timed out)

---

## Files to Submit

```
proofdesk/foxit/
├── README.md
├── ARCHITECTURE.md
├── LICENSE
├── src/
│   ├── confidence_module.py
│   ├── calibration.py
│   ├── metrics.py
│   ├── sheepish.py
│   ├── experts.py
│   ├── foxit_pipeline.py
│   └── frontier_experiments.py
├── tests/
│   └── test_real.py (26/26 pass)
├── experiments/
│   ├── benchmark.py
│   ├── crc_tradeoff.py
│   └── optimization.py
├── docs/
│   ├── PAPER.md
│   ├── FRONTIER_ANALYSIS.md
│   └── PRODUCTION_SAFETY.md
└── data/
    └── datasets/
        ├── invoices/
        ├── contracts/
        └── fraud/
```
