# Doctavian Integration Spec — ProofDesk

**Status:** Canonical spec v1 · 2026-08-26
**Principle:** *ProofDesk decides what's true. Doctavian guarantees the output is structurally correct for that truth. Humans decide what binds.*

---

## 0. Role Division

| Concern | Owner | Never done by |
|---------|-------|---------------|
| What the facts are | Nutrient extraction | LLM free-write |
| Whether facts are consistent | ProofDesk deterministic checks | — |
| How risky signing is | `foxit/` confidence module (CRC + per-field budgets) | Fixed thresholds |
| What the final document contains/says | **Doctavian template logic** | LLM prose generation |
| Who authorizes signature | SignatureGate + human | Agent |
| Where the signature legally happens | **Doctavian Signatures API** | Agent self-sign |

Doctavian is used for **two stages**: GENERATE (documents from approved records) and SIGN (envelopes after the gate). Nothing else.

---

## 1. Data Contract: Approved Record → Template Payload

`StructuredRecord` (hash-frozen at approval) maps deterministically to a flat JSON payload. The confidence score comes from the foxit module; failed assertions become clause items.

```json
{
  "case_id": "case_abc123",
  "record_hash": "sha256:...",
  "generated_date": "2026-08-26",

  "vendor_name": "Northstar Data Systems Ltd.",
  "platform_price": "35,000",
  "support_price": "7,500",
  "quote_total": "42,500",
  "requested_spend": "42,500",
  "contract_start": "2026-10-01",
  "insurance_expiry": "2027-08-31",
  "required_coverage": "2027-10-01",
  "data_retention": "30",
  "subprocessors": "3",
  "encryption": "true",

  "signing_confidence": 0.62,
  "risk_band": "CONDITIONAL",

  "passed_checks": [
    {"predicate": "quote.total == platform_price + support_price", "detail": "35000 + 7500 = 42500"}
  ],
  "failed_checks": [
    {"predicate": "insurance.expiry >= required_coverage", "detail": "31-day gap", "rule": "coverage-v1"}
  ],
  "resolutions": [
    {"decision": "CONDITIONAL_ACCEPT", "reason": "Renewed cert required", "actor": "procurement_manager"}
  ],
  "has_conditions": true,
  "condition_count": 1
}
```

Rules:
- Payload built ONLY from the approved record — never re-derived, never mutated post-hash.
- `signing_confidence` = output of foxit module's calibrated score.
- `risk_band` ∈ {CLEARED, CONDITIONAL, ESCALATED} derived from CRC threshold for doc type.
- Every field the template references must exist (fill `"N/A"` explicitly) so template logic never sees undefined input.

## 2. Template Logic Spec (`vendor_approval_memo.docx`)

One template, three branches driven by `risk_band`, proving Doctavian's core value prop:

| Section | Element type | Logic |
|---------|-------------|-------|
| Header status | Field | `{{risk_band}}` + date |
| Vendor table | Static fields | Direct merge |
| Compliance table | Fields + calc | Coverage gap computed via expression |
| Checks section | Conditional paragraph | `{if passed_checks} ✓ rendered list {end}` |
| **Conditions section** | **Repeater loop** | `{for c in failed_checks}` → numbered obligation clause w/ rule id, detail, deadline = contract_start `{end}` — renders only when `has_conditions` |
| Resolution appendix | Repeater loop | Human decisions + actor + timestamp |
| Signature block | Conditional | Text differs per band: CLEARED → "Authorized for auto-signature"; CONDITIONAL → "Signature requires listed conditions"; ESCALATED → "Held for human review" |

Acceptance test (mirrors Doctavian's Mission 1 gate): mutate fixture data → regenerate → branch content, condition count, and computed gap MUST change correctly without touching the template.

## 3. GENERATE Stage Workflow

```
approve_record(case)                       # record hash frozen
  ↓
build_payload(record, confidence_score)    # §1 contract
  ↓
POST /v1/documents/template/upload         # fresh each run (uploads are consumed)
  X-Storage-Type: document-template        # → TEMPLATE_URN
  ↓
POST /v1/documents/data/upload             # form-data .json file
  X-Storage-Type: document-data            # → DATA_URN (ephemeral)
  ↓
POST /v1/documents/document/generate       # path:"root", locale:"en", timezone IANA
  → DOC_URN (+ pages-generated consumption receipt)
  ↓
GET /v1/documents/document/{DOC_URN}/download   # URL-encoded URN
  → PDF bytes saved to /tmp/proofdesk/{artifact_id}.pdf
  ↓
audit_ledger.append(GENERATED, payload={
    provider: "doctavian",
    doc_urn, pages, template_id: "vendor_approval_memo@1.0",
    input_record_hash, pdf_sha256 })
  ↓
artifact.content_hash = sha256(pdf_bytes)  # artifact bound to real bytes
```

Audit event MUST capture: template id+version, record hash, Doctavian URN, page count, output PDF hash. This is the provenance chain judges (and Doctavian's own gates #14/#15) look for.

**Fallback:** if any Doctavian call fails, render locally with `_render_memo()` (same sections, same branch logic), mark `provider: "local_fallback"` in the audit event. Pipeline never hard-fails on vendor outage.

## 4. SIGN Stage Workflow (replaces stubbed Foxit eSign)

```
can_request_signature(case)                # existing 6-check gate — unchanged
  ↓ allowed only if: state==PREPARED, 0 unresolved blockers,
    human approval present, record/artifact hashes match
  ↓
POST /v1/signatures/document/upload        # the generated PDF
  X-Storage-Type: document-input           # → SIGN_DOC_URN
  ↓
POST /v1/signatures/envelope/create
  documents: [{referenceDocumentId:1, urn: SIGN_DOC_URN}]
  recipients: [{signer email, role:"signer", mandatory:true}]
  fields: [{type:"signature", page:1, positioned block, isRequired:true},
           {type:"name"}, {type:"date"}]
  envelope: subject references case_id + record_hash
  → ENVELOPE_ID
  ↓
GET /v1/signatures/envelope/{ENVELOPE_ID}/send     # draft → SENT, human gets email
  ↓
audit_ledger.append(SIGNATURE_REQUESTED, payload={
    provider: "doctavian_signatures", envelope_id,
    artifact_hash, approval_id: record_hash, signer })
  ↓ [human signs via email link]
GET /v1/signatures/envelope/{id}/get               # poll → status "Completed"
GET /v1/signatures/envelope/{id}/audit/get         # their audit trail
GET /v1/signatures/envelope/{id}/document/{doc}/download  # signed PDF
  ↓
audit_ledger.append(SIGNED, payload={envelope audit ref, signed_pdf_sha256})
transition SIGNED → ARCHIVED
```

Authority boundary preserved: the agent can CREATE and SEND an envelope only through the gate; it can never produce a signed document itself. Envelope creation is denied pre-gate exactly like the old eSign stub — premature attempt still demos as a denial.

## 5. Confidence Integration (foxit/ module → Doctavian)

```
foxit_module.score(record) → {confidence, band, per_field_risk}
```

- `band` selects template branch (§2).
- Per-field failures (signer >1% risk, amount >2%, date >3%) are appended to `failed_checks` with `rule: "confidence:<field>"` so they render as numbered conditions too.
- ESCALATED band short-circuits: generate still happens (document says HELD), but envelope stage is forbidden regardless of gate — belt and suspenders.

This makes one demo show: calibration math → visible document branching → gated human signature.

## 6. Non-Goals

- No LLM writes document text. Ever.
- No Doctavian Salesforce/OneDrive delivery (Storage only — demo env constraint documented).
- No envelope templates (Mission 3 pattern) unless multi-vendor reuse becomes a demo beat.
- No retry storms on 5xx: one retry, then local fallback.

## 7. Build Checkpoints

| CP | Deliverable | Pass criterion |
|----|------------|----------------|
| D1 | Payload builder + unit tests | Record → payload mapping deterministic, hash-stable |
| D2 | Template v2 with branches/loops/calc | Fixture mutation changes branch + condition count correctly |
| D3 | GENERATE wired (real API) | Real URN returned, PDF downloaded, bytes hashed into ledger |
| D4 | Envelope flow behind SignatureGate | Premature attempt denied; post-resolution envelope created+sent; status polled |
| D5 | Confidence wiring | Band from foxit module drives branch; per-field risks appear as clauses |
| D6 | Fallback verified | Kill network → local memo renders, pipeline reaches ARCHIVED, audit marks fallback |

## 8. Demo Beats (~75 seconds of the video)

1. Insurance gap detected → premature signature DENIED (gate reasons on screen)
2. Human resolves → conditional accept
3. Doctavian generates: conditions section shows the 31-day gap as §1 obligation *(their branching, our evidence)*
4. SignatureGate green → Doctavian envelope sent to CFO *(real sign, real email)*
5. Audit timeline: extraction → resolution → generation URN → envelope ID → signed hash

Submission line: *"Doctavian does two jobs: its template logic turns ProofDesk's approved, confidence-scored record into a correctly-shaped conditional approval packet — and its signature API carries that exact packet to a human signer, with every hop hash-chained in our audit ledger."*
