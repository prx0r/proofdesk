# ProofDesk — Canonical Study

## The Problem

Foxit asks: **"When should an agent sign a document, or defer to human?"**

> "We left signing out of the catalog on purpose. To send anything for signature, your agent has to call the Foxit eSign API directly. That handoff is the interesting part."
> — Foxit Hackathon Challenge

## The Answer

**SignatureGate + Domain Rules**

The agent should SIGN when:
- Document type is safe (procurement, invoice, quote)
- No red flags (vendor mismatch, high amount)
- Confidence above threshold

The agent should REVIEW when:
- Document type needs human eyes (KYC, mortgage, medical)
- Confidence below threshold
- Red flags detected

## Benchmark: 18 Real Documents

Tested on real PDFs with real Nutrient DWS extraction and real Foxit API.

### Results

| Method | Accuracy | Signed | Reviewed | FP | FN |
|--------|----------|--------|----------|----|----|
| **Ours (domain rules)** | **88.9%** | 12 | 6 | **1** | **1** |
| Always Sign | 66.7% | 18 | 0 | 6 | 0 |
| Always Review | 33.3% | 0 | 18 | 0 | 12 |
| Naive (conf>0.5) | 61.1% | 17 | 1 | 6 | 1 |
| Conservative (conf>0.95) | 33.3% | 0 | 18 | 0 | 12 |
| SafeCommit | 61.1% | 17 | 1 | 6 | 1 |

### Key Finding

**Our method has the fewest errors (2 total) while still signing 12/18 documents.**

- Always Sign: 6 false positives (signs risky docs)
- Always Review: 12 false negatives (reviews safe docs)
- Our method: 1 FP + 1 FN = 2 total errors

## How It Works

### Data Accuracy vs Signing Confidence

| Signal | Source | Meaning | Range |
|--------|--------|---------|-------|
| Data accuracy | Nutrient DWS | "Did extraction work?" | Always ~0.95 |
| Signing confidence | Our method | "Should we sign?" | 0.29 - 0.95 |

**Key insight: High data accuracy ≠ safe to sign.**

A KYC document can be extracted perfectly (0.95 data accuracy) but still needs human review (0.29 signing confidence).

### The Pipeline

```
Document arrives
      ↓
Nutrient DWS extracts → data accuracy ~0.95
      ↓
Domain rules compute → signing confidence (varies)
      ↓
If signing confidence ≥ threshold → SIGN
If signing confidence < threshold → REVIEW
      ↓
SignatureGate enforces
      ↓
Foxit MCP: upload + merge + compress (reversible)
      ↓
Foxit eSign: send to human (irreversible)
```

### Domain Rules

| Document Type | Signing Confidence | Decision |
|---------------|-------------------|----------|
| Procurement | 0.95 | SIGN |
| Invoice | 0.95 | SIGN |
| Quote | 0.95 | SIGN |
| KYC | 0.29 | REVIEW |
| Mortgage | 0.38 | REVIEW |
| Medical | 0.29 | REVIEW |

## Frontier Alignment

Our approach aligns with 2026 frontier research:

| Paper | Finding | Our Implementation |
|-------|---------|-------------------|
| "Act or Escalate?" | τ* = 1 - (cost_defer/cost_wrong) | Domain rules enforce threshold |
| "SafeCommit" | Commit only when safe in ALL worlds | SignatureGate checks all conditions |
| "AgentAbstain" | Best agents 59.5% at knowing when NOT to act | Our method: 88.9% |
| "Informed Abstention" | Precondition-aware pause, runtime enforcement | SignatureGate is runtime enforcement |
| "HALO" | Evidence-based confidence, not self-reported | Cross-document verification |

## What We Built

### Core: SignatureGate
Server-side gate that decides when the agent defers to human before signing.

### Foxit Integration
- Real PDF upload, merge, compress (MCP tools)
- Real eSign via FreeSign (Foxit eSign needs separate creds)
- Reversible → irreversible handoff

### Benchmark
- 18 real PDFs from proofdesk/data/test_pdfs/
- Real Nutrient DWS extraction
- 6 methods compared
- Our method wins: 88.9% accuracy, 2 total errors

## Files

```
foxit/
├── demo_mvp.py           # Full demo
├── batch_test.py         # Batch processing
├── test_foxit.py         # API smoke test
├── validate_rubrics.py   # Rubric checker
├── src/
│   ├── foxit_pipeline.py # SignatureGate + Foxit integration
│   ├── foxit.py          # Real Foxit API client
│   └── state/machine.py  # 15-state machine
├── rubrics/foxit.json    # 11 criteria (11/11 PASS)
└── BUILD_NOTES.md        # Architecture decisions
```

## One-Line Pitch

**Your Agent Shouldn't Sign That** — ProofDesk separates reversible PDF work from irreversible signature through a server-side authority gate with domain-specific rules.
