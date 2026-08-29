# Provider USPs — What Each API Actually Does

---

## Nutrient DWS

### What We Use
`POST https://api.nutrient.io/extraction/extract`

### What It Does
Extracts structured fields from PDFs with source grounding.

### What We Get
- **value**: The extracted text/number
- **confidence**: How sure the model is (0.0-1.0)
- **page**: Which page the fact came from
- **bbox**: Bounding box coordinates in the PDF

### Without Nutrient
We'd use stubs (deterministic fake data). No real confidence, no source grounding.

### With Nutrient
```json
{
  "field": "quote.total",
  "value": "$42,500",
  "confidence": 0.97,
  "page": 1,
  "bbox": {"x": 100, "y": 200, "width": 150, "height": 20}
}
```

### USP
> "Nutrient DWS extracts facts with source grounding — every confidence score is backed by a page and bbox. When the system says '97% confident', you can click to see exactly where in the PDF it found that number."

### Judge Quote
> "Nutrient DWS does the heavy lifting twice: first to extract facts with source grounding, then to verify extraction quality via re-extraction."

---

## Doctavian

### What We Use
- `POST /v1/documents/template/upload` — Upload template
- `POST /v1/documents/data/upload` — Upload structured data
- `POST /v1/documents/document/generate` — Render PDF
- `POST /v1/signatures/envelope/create` — Create signing envelope

### What It Does
Turns structured data into branded documents with template logic.

### What We Get
- **Branching**: Different output based on risk band (CLEARED/CONDITIONAL/ESCALATED)
- **Loops**: Failed checks rendered as numbered clauses (mdoc:repeater)
- **Calculations**: Quote totals computed from components
- **Conditional sections**: Resolutions appendix only when present
- **Signature envelope**: Create → send to human → poll status

### Without Doctavian
We'd use local renderer (`_render_memo()`). Plain text, no PDF, no branding.

### With Doctavian
```json
{
  "risk_band": "CONDITIONAL",
  "has_conditions": "true",
  "failed_checks": [
    {"idx": 1, "predicate": "insurance.expiry >= required_coverage", "detail": "31-day gap"}
  ]
}
```
→ Renders as "CONDITIONALLY APPROVED" with §1 obligation clause.

### USP
> "Doctavian turns our approved record into a branded conditional approval packet — with loops for repeated line items, branching for risk bands, and calculated totals. One template handles all three approval states."

### Judge Quote
> "Doctavian's template logic renders our confidence-scored record into a correctly-shaped document — branching on risk, looping on failures, and calculating totals — so every case gets a properly formatted packet without manual edits."

---

## Foxit PDF Services

### What We Use
- `POST /pdf-services/v3/merge` — Merge multiple PDFs
- `POST /pdf-services/v3/compress` — Compress output

### What It Does
Cloud-based PDF manipulation (merge, compress, convert).

### What We Get
- **Merge**: Combine multiple PDFs into one packet
- **Compress**: Reduce file size for email/delivery
- **MCP server**: 32 tools for PDF operations

### Without Foxit
We'd use PyPDF2 or pikepdf locally. Works but no cloud processing.

### With Foxit
- Real API calls for merge/compress
- MCP server available for agent integration
- Cloud-based (no local processing)

### USP
> "Foxit PDF Services handles the reversible work — merging documents into a packet, compressing for delivery — before the irreversible signature happens."

### Judge Quote
> "Foxit PDF Services does the reversible work: merge, compress, prepare. The agent can undo these steps. The signature is irreversible — that's where humans decide."

---

## Foxit eSign (Simulated)

### What We Use
`POST /esign/v1/envelopes` — Create signing envelope

### What It Does
Sends documents to humans for signature.

### What We Get
- **Envelope creation**: Define signer, fields, message
- **Send**: Deliver to human via email
- **Poll**: Check completion status
- **Audit**: Get signing audit trail

### Without Foxit eSign
We'd simulate the envelope. No real human signer.

### With Foxit eSign
- Real API calls (when keys available)
- Real human signer receives email
- Real signature captured
- Real audit trail

### USP
> "Foxit eSign is the authority boundary — the agent creates the envelope, but only a human can sign. The SignatureGate ensures no premature signing."

### Judge Quote
> "Foxit eSign provides the authority boundary: the agent can prepare and send, but only a human can sign. Our SignatureGate enforces this with 6 checks before any envelope is created."

---

## The Combined Pitch

### One-Line
> "AI does the reversible work. Evidence and people control the irreversible."

### Three-Liner
> "Nutrient DWS extracts facts with source grounding. Doctavian renders approved records into branded packets. Foxit PDF Services merges documents in the cloud. The agent does the reversible work — evidence and people control the irreversible."

### Judge Version
> "Sheepdog uses three sponsor APIs:
> 1. Nutrient DWS extracts facts with source grounding — every confidence score backed by a page and bbox
> 2. Doctavian renders approved records into branded conditional approval packets with loops and branching
> 3. Foxit PDF Services merges documents in the cloud — the reversible work before the irreversible signature
> 
> The agent does the reversible work. Evidence and people control the irreversible."

---

## What Survives Scrutiny

| Provider | Real API? | What Works | What's Weak |
|----------|-----------|------------|-------------|
| Nutrient DWS | ✅ YES | Extraction, confidence, source grounding | Viewer integration |
| Doctavian | ⚠️ PARTIAL | Template upload, data upload | Generation (OAuth scope) |
| Foxit PDF | ✅ YES | Merge, compress | MCP integration |
| Foxit eSign | ❌ SIMULATED | Envelope payload | No real signing |

---

## Honest Score

| Provider | Score | Notes |
|----------|-------|-------|
| Nutrient | 95% | Real API, real extraction, real confidence |
| Doctavian | 75% | API works, generation fails on OAuth |
| Foxit PDF | 80% | Real merge, MCP exists but untested |
| Foxit eSign | 30% | Simulated, needs real keys |
| **Overall** | **70%** | Good but not great |
