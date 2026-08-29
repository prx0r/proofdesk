# ProofDesk — Northstar: Hackathon Winning Strategy

**Last updated:** 2026-08-25
**Status:** Strategy finalized, dev plan pending
**Deadline:** Sep 3, 2026 @ 10:00 AM PT

---

## Strategic Decision: ONE ENTRY, THREE STORIES

**Single monolith submission.** The same procurement workflow naturally hits all three sponsor narratives. Making three separate apps would be weaker — judges see spread-thin effort, waste time building three UIs, and the ProofDesk concept is literally one pipeline with authority tiers.

---

## Sponsor Story Map

```
MESSY PROCUREMENT PACKET
        ↓
NUTRIENT — "We can trust the AI's document reading"
  extract + source evidence + confidence
        ↓
PROOFDESK — "The AI found a real problem"
  detect discrepancies / policy violations
        ↓
HUMAN REVIEW — "A person decided, not the machine"
        ↓
DOCTAVIAN — "The final document is correct by construction"
  structured data → conditional document with branches/loops/calcs
        ↓
FOXIT MCP — "The agent prepared, but didn't overstep"
  reversible PDF work (merge/convert/compress)
        ↓
HUMAN AUTHORITY GATE — "Signing requires a person"
        ↓
FOXIT eSIGN — "Real signature, real commitment"
        ↓
AUDITABLE OUTPUT — "You can prove why this happened"
```

---

## What Each Sponsor Judge Sees

### Nutrient judge sees:
- Real DWS extraction with coordinates, confidence, source pages
- Cross-document discrepancy detection (payment terms mismatch)
- Click-to-source review in DWS Viewer
- Human exception routing
- Audit trail

### Doctavian judge sees:
- Approved structured record with jurisdiction, payment terms, risk tier, line items
- Template branching: IF high-risk → add compliance schedule
- Loop: FOR EACH line item → pricing row
- Calculation: totals, taxes
- Different inputs produce visibly different documents

### Foxit judge sees:
- Plain prompt entry
- Agent does reversible PDF work (merge, convert, compress) via MCP
- Clear authority boundary: "Ready to commit. Human signature required."
- Real eSign API call to real person
- Signed document returned
- Audit log distinguishes AI actions from human actions

### Overall judge sees:
- A functioning business product, not an experiment
- Solves expensive procurement problem
- Could become a company (horizontal trust control plane)
- Built substantially during the event

---

## The Canonical Discrepancy

```
PO:           Payment = Net 60
Vendor contract: Payment = Net 15
Company policy:  Contracts over $50k require Net 45+
```

This single discrepancy demonstrates all three sponsors:
- Nutrient: extracted the actual values with confidence
- Doctavian: generated corrected contract with proper Net 45 terms
- Foxit: authority boundary prevents agent from self-signing the corrected contract

---

## Acceptance Checklist (60 gates)

See:
- `docs/NUTRIENT_GATES.md` — 20 TRUE/FALSE gates
- `docs/DOCTAVIAN_GATES.md` — 20 TRUE/FALSE gates
- `docs/FOXIT_GATES.md` — 20 TRUE/FALSE gates

**Target:** 55/60 minimum. Items 1-9 of each track should all be TRUE first.

---

## Priority Order (DO NOT INVERT)

1. One immaculate procurement scenario that works end-to-end
2. Real Nutrient extraction with evidence/confidence
3. Visible human review gate
4. Real Doctavian conditional generation
5. Real Foxit MCP document preparation
6. Real Foxit eSign + human signature
7. Audit/provenance screen
8. 5-20 adversarial/edge-case fixtures
9. Frozen quantitative evaluation
10. Demo polish

---

## What NOT to Build

- Three separate apps
- Sophisticated multi-agent debate
- Free-form contract-writing LLM (Doctavian is about structured generation)
- Benchmark harness for OCR routing (distracted from the actual problem)
- Generic chat-with-PDF
- Custom OCR / viewer / e-sign engine
- Blockchain notarization
- Large RAG stack
- Real PII
- Broad legal/compliance certification
- Autonomous signing

---

## Sponsor API Keys Status

| Provider | Keys | Status |
|----------|------|--------|
| Nutrient DWS | In HANDOVER.md | Have keys, need to wire real calls |
| Doctavian | Need to register | Contact hello@doctavian.com |
| Foxit PDF + eSign | Need to register | Contact theodore_castro@foxitsoftware.com |
| SerpApi | In HANDOVER.md | Optional $3k track — easiest add |

---

## Reference Documents

- `PROOFDESK_CANONICAL.md` — Full hackathon spec (the source of truth)
- `HANDOVER.md` — Session log with real API keys
- `docs/NUTRIENT_GATES.md` — 20 acceptance gates
- `docs/DOCTAVIAN_GATES.md` — 20 acceptance gates
- `docs/FOXIT_GATES.md` — 20 acceptance gates
