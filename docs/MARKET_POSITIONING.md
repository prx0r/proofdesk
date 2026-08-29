# ProofDesk — Market Positioning Report

## Executive Summary

ProofDesk is an evidence-gated document execution pipeline that extracts documents with source grounding, verifies facts with 4-way verdicts, routes uncertain cases to human review, and audit-trails every decision with hash-chained Merkle proofs.

It occupies a unique position in the document AI market: the intersection of extraction, verification, and auditability.

## The Market Gap

### What exists today:

| Layer | Players | What they do |
|-------|---------|--------------|
| **Extraction** | Nutrient DWS, Textract, Azure, LlamaIndex | Pull data from documents |
| **Verification** | VerifyDoc, FactMiner | Check if extraction is correct |
| **Audit** | SharePoint, DocuWare | Track who accessed files |
| **Signing** | DocuSign, Foxit eSign | Collect signatures |

### What's missing:

**No single system combines all four layers with real API integration.**

- Nutrient DWS extracts but doesn't verify or audit
- VerifyDoc verifies but doesn't extract or audit
- DocuSign signs but doesn't extract or verify
- SharePoint audits access but not extraction accuracy

**ProofDesk fills this gap.** It's the only system that:
1. Extracts with Nutrient DWS (source-grounded, confidence-scored)
2. Verifies with FactMiner (4-way verdict)
3. Routes to human review (calibrated confidence)
4. Audit-trails with hash chains (tamper-evident)
5. Signs with Foxit (real API)

## Market Position

```
                    EXTRACTION          VERIFICATION         AUDIT + SIGNING
                    ──────────          ────────────         ───────────────
Nutrient DWS        ████████████                                   (we use this)
VerifyDoc                          ████████████                     (trust layer)
ProofDesk           ████████████   ████████████   ████████████     (full pipeline)
```

**ProofDesk is the only system spanning all three layers.**

## The Three-Layer Thesis

### Layer 1: Extraction (Nutrient DWS)
- Pull data from documents
- Source grounding (page + bbox)
- Confidence scores
- Match labels (deterministic grounding)

### Layer 2: Verification (FactMiner)
- 4-way verdict: SUPPORTED/REFUTED/CONFLICTING/INSUFFICIENT
- Cross-document consistency checks
- Deterministic rules + LLM fallback

### Layer 3: Audit + Signing (Hash chain + Foxit)
- Hash-chained event ledger
- Merkle proofs for inclusion
- Content-addressed artifacts
- Self-hashing certificates
- Foxit PDF merge + eSign

**Each layer is independently valuable. Together, they're irreplaceable.**

## Competitive Advantages

### vs. Nutrient DWS alone
- Nutrient extracts but doesn't verify or audit
- ProofDesk adds verification, routing, and audit trail

### vs. VerifyDoc alone
- VerifyDoc calibrates but doesn't extract or audit
- ProofDesk adds Nutrient extraction, Foxit signing, hash-chain audit

### vs. DocuSign alone
- DocuSign signs but doesn't extract or verify
- ProofDesk adds source-grounded extraction and FactMiner verification

### vs. Custom LLM pipeline
- LLMs hallucinate without source grounding
- ProofDesk extracts deterministically with confidence scores
- LLMs can't audit their own decisions
- ProofDesk hash-chains every decision

## Target Customers

1. **Procurement teams** — $50k-500k vendor contracts need verification
2. **Compliance departments** — regulated workflows need audit trails
3. **Legal operations** — contract review needs source grounding
4. **Insurance** — claims processing needs cross-document verification
5. **Financial operations** — invoice processing needs accuracy guarantees

## The One-Liner

> "ProofDesk extracts documents with source grounding, verifies facts with 4-way verdicts, routes uncertain cases to human review, and audit-trails every decision with hash-chained Merkle proofs."

## Why Now

1. **Nutrient DWS** makes extraction accessible (free tier, real API)
2. **FactMiner** makes verification deterministic
3. **Hash chains + Merkle** make audit trails tamper-evident
4. **Foxit MCP** makes signing accessible
5. **Regulated workflows** demand all of the above

The convergence of these technologies makes ProofDesk possible for the first time.
