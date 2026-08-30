# ProofDesk — Your Agent Shouldn't Sign That

**Evidence-gated document execution for high-stakes business workflows.**

> AI agents can prepare documents. ProofDesk ensures only verified, human-approved facts become signed commitments.

## The Problem

AI agents can prepare documents, merge PDFs, and compress files. But should they be able to sign them? Signing is irreversible — it creates legal commitment. An agent that signs without proper verification is a liability.

## Our Solution

ProofDesk inserts a **calibrated authority gate** between reversible PDF work and irreversible signature:

1. **Extract** — Nutrient DWS extracts fields with confidence signals and source grounding
2. **Reconcile** — Cross-document verification catches inconsistencies
3. **Classify** — Risk-adaptive classification with per-field confidence scores
4. **Decide** — SignatureGate enforces: no blockers, human approval, hash integrity, calibrated score ≥ threshold
5. **Prepare** — Foxit PDF Services: merge source documents + approval memo, compress (reversible)
6. **Gate** — SHA-256 of final artifact verified against stored hash — any tamper detected
7. **Sign** — Human signer completes the irreversible commitment
8. **Audit** — Every step recorded with hash-chained audit trail + Merkle inclusion proofs

## Key Innovation: The Authority Gate

SignatureGate is a server-side, non-negotiable boundary between reversible and irreversible operations. It enforces six conditions before allowing any signing request:

| Check | What it verifies |
|-------|-----------------|
| State is PREPARED | Pipeline completed all prior stages |
| No unresolved blockers | All BLOCKER-severity assertions resolved by humans |
| Human approval present | A human explicitly approved the record |
| Structured record exists | Approved record with content hash |
| Artifact hash verified | SHA-256 of final PDF matches stored hash |
| Calibrated score ≥ threshold | Confidence meets risk-appropriate threshold |

The agent can prepare everything. It cannot sign.

## Live Integration Status

| Capability | Provider | Status |
|------------|----------|--------|
| Evidence extraction (value + confidence + page + bbox) | Nutrient DWS | **LIVE** |
| Source grounding with page coordinates | Nutrient DWS | **LIVE** |
| Risk classification with per-field budgets | ProofDesk | **LIVE** |
| Calibrated authority gate (6 conditions) | ProofDesk | **LIVE** |
| Document generation (risk-branched memo) | ProofDesk | **LIVE** |
| PDF merge (reversible) | Foxit PDF Services | **LIVE** |
| PDF compression (reversible) | Foxit PDF Services | **LIVE** |
| SHA-256 artifact integrity | ProofDesk | **LIVE** |
| Hash-chained audit trail | ProofDesk | **LIVE** |
| Merkle inclusion proofs | ProofDesk | **LIVE** |
| Signing request | Foxit eSign | **SIMULATED** (credentials pending) |

## Results

| Question | Metric | Value |
|----------|--------|-------|
| Does the evidence pipeline work on real documents? | Real Nutrient API on CUAD contracts | 95% accuracy (19/20), 5% FPR |
| Does calibrated abstention reduce bad decisions? | Auto-sign vs defer vs block | 10% auto, 80% defer, 10% block |
| Is the audit mechanism valid? | Hash chain + Merkle verification | 85+ tests passing, 100% replay |

## Quick Start

```bash
cd proofdesk
pip install -r requirements.txt
cp .env.example .env   # fill in your API keys

# Open interactive demo (for judges)
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080/demo

# Run 3-minute CLI demo
python3 demo_2min.py

# Run with real Nutrient API
export NUTRIENT_API_KEY="pdf_live_..."
python3 demo_2min.py

# Run tests
python3 tests/test_all.py
python3 tests/test_integration.py
```

## Architecture

```
proofdesk/
├── src/
│   ├── api/app.py              ← FastAPI server
│   ├── engine/orchestrator.py  ← Pipeline orchestration
│   ├── providers/
│   │   ├── nutrient.py         ← Nutrient DWS (REAL API)
│   │   ├── classifier.py       ← Risk classification + DecisionCertificate
│   │   └── stubs.py            ← Deterministic stubs
│   ├── state/machine.py        ← SignatureGate (6 conditions)
│   └── audit/                  ← Hash chain + Merkle proofs
├── tests/
│   ├── test_all.py             ← 38 core tests
│   ├── test_audit.py           ← 25 audit tests
│   ├── test_integration.py     ← 26 integration tests
│   └── ...
└── .github/workflows/ci.yml   ← CI on every push
```

## One-Line Pitch

Your Agent Shouldn't Sign That — ProofDesk separates reversible PDF work from irreversible signature through a server-side authority gate with calibrated risk thresholds.

## Why This Wins

1. **Addresses the core challenge**: Tool access is not authority. The agent can prepare documents but cannot create legal commitment.
2. **Real Nutrient integration**: Evidence extraction with source grounding, confidence, and page coordinates — not just form-filling.
3. **Real Foxit integration**: PDF Services merge + compress with task polling and resultDocumentId chaining.
4. **Calibrated gate**: Per-field risk budgets, calibrated confidence vs threshold, SHA-256 artifact verification.
5. **Honest submission**: Every integration is either LIVE or labeled SIMULATED. No fake demos.
