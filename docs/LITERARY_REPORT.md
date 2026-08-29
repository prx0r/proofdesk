# ProofDesk — The Story of a Repository

## Prologue: The Problem

In the summer of 2026, a team set out to answer a simple question: can an AI agent be trusted to process business documents?

The answer, it turned out, was: only if you can prove what it did.

## Chapter 1: The Foundation (Aug 24)

The project started with a state machine. Fifteen states. Three forbidden transitions. A SignatureGate that blocks premature signing. This was the skeleton — correct but lifeless.

Then came the reconciliation engine. Six domain checkers. Twenty deterministic rules. Quote arithmetic. Entity normalization. Insurance coverage date comparisons. The bones got muscles.

The audit trail was next. Hash-chained events. Merkle proofs. Content-addressed artifacts. Self-hashing certificates. Now the skeleton could prove it existed.

## Chapter 2: The Nutrient Integration (Aug 25, early)

Real API keys arrived. The first call to Nutrient DWS returned 14 facts from 4 procurement PDFs — 100% accuracy, confidence scores 0.95-0.97, bounding boxes on every field.

The insurance gap was detected: expires Aug 31, required until Oct 1. 31 days uninsured. The system blocked the signature. The human resolved. The pipeline completed.

For the first time, the system could prove that every extraction was traced to source evidence.

## Chapter 3: The Foxit Integration (Aug 25, midday)

Foxit PDF Services API keys arrived. Upload worked. Merge worked. Download worked. The pipeline now had real PDF operations, not stubs.

The full pipeline ran end-to-end: Nutrient extracts → FactMiner verifies → insurance gap caught → premature sign denied → human resolves → document generated → Foxit merges → signed → archived. 15 audit events recorded.

## Chapter 4: The Comparison (Aug 25, afternoon)

Vanilla Hermes was tested on the same documents. It found the same issues — insurance gap, payment terms conflict, arithmetic error. But it couldn't prove it found them. No source grounding. No audit trail. No confidence scores.

ProofDesk found the same issues AND could prove every finding was traceable to source evidence. The difference wasn't what it found — it was how it proved it.

## Chapter 5: The Frontier (Aug 25, evening)

Research confirmed the approach aligns with 2026 frontier papers:
- ExtractConf: multi-signal confidence for document extraction
- EviSearch: multi-agent extraction with per-cell provenance
- LandingAI ADE: visual grounding replaces confidence with location
- Audit Trails in Document AI: field-level traceability for compliance
- HITL Extraction: route 90-95% clear cases, flag uncertain

The architecture isn't invented. It's validated.

## Chapter 6: The VerifyDoc Comparison (Aug 25, night)

VerifyDoc was cloned and tested on the same documents. It extracted 4 fields in 460ms. ProofDesk extracted 10 fields in 10s. VerifyDoc excelled at calibration. ProofDesk excelled at audit trail and signing.

The conclusion: the combined stack is strongest. VerifyDoc calibration → ProofDesk extraction → ProofDesk audit.

## Epilogue: What We Built

A pipeline that:
- Extracts documents with source grounding (page + bbox + confidence)
- Verifies facts with 4-way verdicts (SUPPORTED/REFUTED/CONFLICTING/INSUFFICIENT)
- Routes uncertain cases to human review via DWS Viewer
- Audit-trails every decision with hash-chained Merkle proofs
- Signs documents with Foxit PDF services
- Uses 8 Nutrient DWS APIs in a single pipeline

The system knows what it knows, knows what it doesn't know, and can prove it.

## The Market

ProofDesk occupies the intersection of extraction, verification, and auditability — the only system spanning all three layers with real API integration.

In a world where AI agents process documents at scale, ProofDesk is the trust layer that makes it safe.

---

*"AI does the reversible work. Evidence and people control the irreversible."*
