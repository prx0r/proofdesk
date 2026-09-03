# ProofDesk — Your Agent Shouldn't Sign That

**Evidence-gated document automation for high-stakes business workflows.**

> Two documents are individually read correctly. Together they describe a transaction that should not happen. The AI refuses to act.

**Live Demo:** https://proofdesk-90q.pages.dev

## The Problem

AI agents can prepare documents, merge PDFs, and compress files. But should they be able to sign them? Signing is irreversible — it creates legal commitment. An agent that signs without proper verification is a liability.

## The Magic Transition

```
BEFORE
Two PDFs, each extracted correctly
Confidence: high
Naive automation: would proceed

PROOFDESK
Cross-document verification finds a contradiction
Insurance expires 31 days before the service period ends

AFTER
Authority gate: BLOCKED
Human reviews the exact evidence
Resolves the exception
Auditable authorization produced
```

That contrast is the product. High extraction confidence does not equal safe action.

## How It Works

1. **Extract** — Nutrient DWS extracts fields with confidence, page, and bounding box
2. **Verify** — Cross-document assertions catch inconsistencies
3. **Gate** — 6 conditions enforced server-side: state, blockers, approval, record, hash, calibrated score
4. **Human** — The exact failing claim and its source are sent to a human
5. **Execute** — Content-hashed artifact, hash-chained audit, Merkle proofs

## Sponsor Integration — Nutrient DWS

Nutrient is not a checkout button bolted on at the end. It provides the evidence layer throughout:

- **Extraction**: `POST /extraction/extract` → grounded fields with confidence
- **Source grounding**: page number + bounding box for every fact
- **Match labels**: id_match, fuzzy_match, not_found — deterministic grounding checks
- **Citations**: full provenance per extracted field

Without Nutrient DWS, there is no evidence. Without evidence, there is no authority decision.

## Results

| Metric | Value |
|--------|-------|
| Facts extracted | 13 (with page + bbox) |
| Assertions checked | 6 |
| Contradictions caught | 1 (insurance gap) |
| Authority gate | BLOCKED correctly |
| Tests passing | 115/115 |
| Audit trail | Hash-chained + Merkle-sealed |

## Why This Wins

1. **Obvious problem**: extraction looks fine, but the documents conflict
2. **Surprising action**: the AI refuses despite high confidence
3. **Sponsor causally necessary**: Nutrient provides the grounded evidence that makes the contradiction visible
4. **State-changing**: not a recommendation — a block, then an authorization
5. **Auditable**: every decision replayable from hash chain + Merkle proofs

## The One-Line Pitch

> **Nutrient DWS extracts grounded evidence. ProofDesk decides when AI can safely proceed and when a human must intervene.**

## Startup Extension

The same primitive generalizes: Nutrient provides grounded evidence, ProofDesk determines when that evidence is sufficient for irreversible action.

- **Accounts payable**: invoice → PO → receipt → payment auth
- **Insurance**: claim → policy → evidence → settlement
- **Lending**: application → income → valuation → underwrite
- **Compliance**: ID → KYC → risk → onboard

The reusable product is **evidence → policy → authority**, not procurement specifically.

## Reproduce

```bash
git clone https://github.com/prx0r/proofdesk
cd proofdesk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 tests/test_all.py          # 38/38
python3 tests/test_audit.py        # 25/25
python3 tests/test_integration.py  # 33/33
python3 tests/test_learning.py     # 3/3
uvicorn src.api.app:app --port 8080
# http://localhost:8080/demo
```
