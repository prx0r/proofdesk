# ProofDesk

**Your agent shouldn't sign that.**

[![Hackathon](https://img.shields.io/badge/DevNetwork_API%2BCloud%2BAI_Hackathon-2026-blue)](https://api-cloud-ai-hackathon-2026.devpost.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-115_passing-brightgreen)](#tests)

> Two documents are individually read correctly. Together they describe a transaction that should not happen. The AI refuses to act.

**[Demo Video](ProofDesk-Demo.mp4)** | **[Live Demo](https://proofdesk-90q.pages.dev)** | **[API](#quick-start)**

---

## The Problem

AI can extract data from documents. That does not mean it has enough evidence or authority to act. The dangerous failure is not extraction error — it is **taking an irreversible action on insufficient evidence.**

## What ProofDesk Does

Nutrient DWS turns source PDFs into grounded evidence — values, confidence, page and bounding-box provenance. ProofDesk uses that evidence to determine whether automation may proceed or must defer to a human.

```
Source PDFs
  → Nutrient DWS extraction (value + confidence + page + bbox)
  → Cross-document verification
  → A contradiction is found
  → Authority gate: BLOCKED
  → Human examines the exact evidence
  → Human resolves the exception
  → Authorized artifact with hash chain + Merkle proofs
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    SOURCE PDFs                            │
│         (insurance, procurement, quotes, questionnaires)  │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                 NUTRIENT DWS                             │
│  Extraction: value + confidence + page + bbox            │
│  Grounded evidence, not just text                        │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│              CROSS-DOCUMENT VERIFICATION                 │
│  Reconciliation • Contradiction detection                │
│  6 calibrated algorithms • Conformal risk control        │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                 SIGNATUREGATE                            │
│  6 server-side enforced conditions                       │
│  The agent cannot negotiate                              │
└──────────────────────────┬───────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      AUTO_SIGN       DEFER_TO_HUMAN    BLOCKED
                                     (contradictions)
          │                │                │
          └────────────────┼────────────────┘
                           ▼
              ┌────────────────────────┐
              │    AUDIT TRAIL         │
              │  Hash chain + Merkle   │
              │  Tamper-evident        │
              │  Replayable            │
              └────────────────────────┘
```

---

## The SignatureGate

**6 conditions enforced server-side. The agent cannot negotiate.**

| Check | What It Verifies |
|-------|-----------------|
| State is `PREPARED` | Pipeline completed all prior stages |
| No unresolved blockers | All BLOCKER-severity assertions resolved |
| Human approval present | A human explicitly approved |
| Structured record exists | Approved record with content hash |
| Artifact hash verified | SHA-256 matches stored hash |
| Calibrated score ≥ threshold | Confidence meets risk threshold |

---

## Core Guarantees

| Guarantee | How |
|-----------|-----|
| **Fail closed** | No evidence = no authorization |
| **Source grounding** | Every fact traced to page + bbox |
| **Human authority** | Agent cannot sign without human approval |
| **Content integrity** | SHA-256 of artifacts, tamper detection |
| **Replayable audit** | Hash-chained events + Merkle proofs |

---

## Quick Start

```bash
git clone https://github.com/prx0r/proofdesk
cd proofdesk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
# http://localhost:8080/demo
```

---

## Learning from Review

Human decisions become calibration data. Over time, ProofDesk learns where this organization can safely automate while maintaining spot audits on automated decisions.

### Technical Depth

- **6 calibrated algorithms** — from basic confidence thresholds to conformal risk control
- **Conformal risk control** — mathematically guaranteed error rates
- **Online human-feedback calibration** — improves with every human decision
- **Hash-chained audit** — tamper-evident, replayable, Merkle-proved

See `docs/TECHNICAL_DEPTH.md` for full details.

---

## Tests

```bash
python3 tests/test_all.py         # 38/38
python3 tests/test_audit.py       # 25/25
python3 tests/test_integration.py # 33/33
python3 tests/test_frontier.py    # 16/16
python3 tests/test_learning.py    # 3/3
```

**115 tests. All passing.**

---

## Sponsor Integrations

| Provider | What It Does | Status |
|----------|--------------|--------|
| **Nutrient DWS** | Extracts facts with source grounding (value + confidence + page + bbox) | Live API |
| **Foxit PDF** | Merge/compress documents | Live API |
| **Foxit eSign** | Signing authority boundary | Simulated |
| **Doctavian** | Template branching, loops, calculations | Integrated |

---

## Tech Stack

- **Language:** Python 3
- **API Framework:** FastAPI + Uvicorn
- **Document Extraction:** Nutrient DWS
- **PDF Operations:** Foxit PDF Services
- **Audit:** SHA-256 hash chain + Merkle proofs
- **Confidence:** Conformal prediction + online calibration
- **Testing:** 115 tests across 5 suites
- **Deployment:** Cloudflare Pages

---

## License

MIT

---

**DevNetwork API + Cloud + AI Hackathon 2026**
