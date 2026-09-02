# ProofDesk — Your Agent Shouldn't Sign That

**DevNetwork API+Cloud+AI Hackathon 2026**

> Two documents are individually read correctly. Together they describe a transaction that should not happen. The AI refuses to act.

**Live Demo:** https://proofdesk-90q.pages.dev

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

## Why Nutrient DWS

Nutrient DWS performs the core document extraction and source grounding that turns uploaded PDFs into confidence-aware evidence. Every extracted field carries value, confidence, source page, and bounding box — not just text.

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

## The SignatureGate

6 conditions enforced server-side. The agent cannot negotiate.

| Check | What it verifies |
|-------|-----------------|
| State is PREPARED | Pipeline completed all prior stages |
| No unresolved blockers | All BLOCKER-severity assertions resolved |
| Human approval present | A human explicitly approved |
| Structured record exists | Approved record with content hash |
| Artifact hash verified | SHA-256 matches stored hash |
| Calibrated score ≥ threshold | Confidence meets risk threshold |

---

## Learning from Review

Human decisions become calibration data. Over time, ProofDesk learns where this organization can safely automate while maintaining spot audits on automated decisions.

---

## Tests

```bash
python3 tests/test_all.py         # 38/38
python3 tests/test_audit.py       # 25/25
python3 tests/test_integration.py # 33/33
python3 tests/test_frontier.py    # 16/16
python3 tests/test_learning.py    # 3/3
```

115 tests. All passing.

---

## Technical Depth

See `docs/TECHNICAL_DEPTH.md` for:
- 6 calibrated algorithms
- Conformal risk control
- Online human-feedback calibration
- Hash-chained audit with Merkle proofs

Research lab: `foxit/` (calibration experiments, benchmarks, threshold optimization)

---

## License

MIT
