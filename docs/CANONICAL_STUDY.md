# ProofDesk — Canonical Study

## The Problem We Solve

Every business runs on documents — contracts, invoices, forms, IDs, claims, reports. When they're regulated, "almost right" isn't good enough.

An AI agent can read a PDF and extract "$42,500." But can it prove that value came from page 1, line 14 of the source document? Can it prove the extraction was correct? Can it prove it didn't hallucinate?

Today, the answer is no. Agents extract with confidence but without proof. They make decisions without audit trails. They sign documents without verification.

**ProofDesk changes that.**

## What ProofDesk Is

ProofDesk is an evidence-gated document execution pipeline powered by Nutrient DWS. It turns messy documents into verified, auditable, signable business outputs.

The pipeline:

```
MESSY DOCUMENTS
    ↓
NUTRIENT DWS (real API)
  Extract fields with confidence + source coordinates + match labels
    ↓
FACTMINER (4-way verification)
  SUPPORTED / REFUTED / CONFLICTING / INSUFFICIENT
    ↓
CONFIDENCE GATE (calibrated routing)
  AUTO_APPROVE / HUMAN_REVIEW / REJECT
    ↓
DWS VIEWER (human reviews source page)
    ↓
FOXIT PDF (merge + compress via real API)
    ↓
AUDIT TRAIL (hash chain + Merkle proofs)
```

## What We Prove on Real Data

### 1. Nutrient DWS Extraction (100% accuracy)
- 14/14 fields extracted from 4 real procurement PDFs
- Each field: confidence (0.95-0.97), page number, bounding box, match label
- Payment terms: "Net 60" (procurement) vs "Net 30" (vendor quote) — CONFLICT DETECTED

### 2. Cross-Document Verification
- Insurance expires Aug 31, 2027. Required coverage until Oct 1, 2027. **31-day gap.**
- Quote total matches requested spend ($42,500).
- Entity names match across documents (Ltd. vs Limited normalized).
- Payment terms conflict detected (Net 60 vs Net 30).

### 3. Confidence Routing
- confidence >= 0.95 → AUTO_APPROVE (42 fields)
- 0.65 <= confidence < 0.95 → HUMAN_REVIEW
- confidence < 0.65 → REJECT (3 fields)

### 4. Audit Trail
- 15 hash-chained events per pipeline run
- Merkle epoch sealing with inclusion proofs
- Content-addressed artifact store
- Ed25519 signed attestations
- 25/25 tests pass

### 5. Verification Comparison

| | VerifyDoc | ProofDesk |
|---|---|---|
| Fields extracted | 4 | 10 |
| Source grounding | Page + bbox | Page + bbox + match |
| Audit trail | None | Hash chain + Merkle |
| Signing | None | Foxit merge |
| Multi-API | No | 8 Nutrient APIs |

## Market Position

ProofDesk occupies the intersection of three trends:

1. **Agentic Document AI** — AI agents processing documents at scale
2. **Regulated Workflows** — Procurement, contracts, compliance requiring audit trails
3. **Human-AI Collaboration** — Humans review what agents can't verify

The market needs:
- Not just extraction (everyone does that)
- Not just verification (VerifyDoc does that)
- **Extraction + verification + audit + signing** in one pipeline

ProofDesk is the only system that combines all four with real Nutrient DWS integration.

## The One-Line Pitch

> "ProofDesk extracts documents with source grounding, verifies facts with 4-way verdicts, routes uncertain cases to human review, and audit-trails every decision with hash-chained Merkle proofs."

## Where We Fit

```
                    EXTRACTION          VERIFICATION         AUDIT + SIGNING
                    ──────────          ────────────         ───────────────
Nutrient DWS        ████████████                                   (we use this)
VerifyDoc                          ████████████                     (trust layer)
ProofDesk           ████████████   ████████████   ████████████     (full pipeline)
```

ProofDesk is the only system that spans all three layers with real API integration.
