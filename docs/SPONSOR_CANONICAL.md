# Sponsor Canonical Reference — What Each Hackathon Wants

**Purpose:** Clear, single-source reference for what each sponsor demands and how ProofDesk uses them.

**Source:** Devpost hackathon page + sponsor-specific challenge descriptions.

---

## Quick Comparison

| | Nutrient DWS | Doctavian | Foxit |
|---|---|---|---|
| **Prize** | $1,500 | $1,000 | $1,000 |
| **Core question** | How do you trust extracted data? | How do you generate complex documents? | How do you handle the signing authority boundary? |
| **What they own** | Intake + human review surface | Approved data → final document | PDF prep + signature gate |
| **Key API** | Data Extraction API | Document Generate API | PDF Services + eSign API |
| **Must demonstrate** | Source-grounded extraction with confidence | Templates that branch/loop/calculate | Authority transition from AI to human |
| **Demo proof** | Click source → see evidence in Viewer | Different inputs → different documents | Premature sign blocked → resolve → sign |

---

## 1. Nutrient DWS — "Turn Documents Into Something People Actually Trust"

### What they want
> "The best document work isn't one magic call — it's a pipeline: pull the data out, judge how confident you are, bring a human in exactly where it matters, and keep a record of every step."

### The one rule
> "Your project must use Nutrient DWS — the API, an SDK, or the Viewer — for at least one core document operation, meaningfully (not a single throwaway call)."

### Bonus respect for
> "Pipelines that lean on what makes DWS different: deterministic, auditable output, with a human in the loop where a guess isn't acceptable."

### What Nutrient actually does
- **Data Extraction API** — Pull structured fields from PDFs with confidence scores, source coordinates (page + bbox), and match labels
- **DWS Viewer** — Embeddable document viewer for human review (click source chip → see evidence in context)
- **Processor API** — OCR, conversion, compression
- **Accessibility API** — PDF/UA compliance

### How ProofDesk uses it
```
Source PDFs → Nutrient Data Extraction API → Structured facts with:
  - value (raw + normalized)
  - confidence (0-1)
  - source page + bounding box
  - match label (id_match / fuzzy_match / not_found)
```

**Real API call:** `POST https://api.nutrient.io/extraction/extract`

**What we extract:** 11 procurement fields across 4 documents (vendor name, spend, dates, insurance, security)

### Acceptance gate
A judge must see:
1. A real extracted value
2. Click to jump to source evidence
3. A material mismatch routed to review
4. Human resolution
5. Downstream workflow unblocks

### What we need to build
- [x] Real Nutrient Data Extraction API call
- [x] Retain value + page/source location + confidence
- [x] Route low-confidence/conflicting facts to review
- [ ] **DWS Viewer embedded** — click source chip → see evidence in Viewer

### Our submission line
> "Nutrient DWS turns messy source documents into source-grounded structured evidence and provides the review surface where humans resolve facts the automation is not allowed to guess."

---

## 2. Doctavian — "Generate It Right. Sign It Tight."

### What they want
> "Bring us your messiest, most real-world data problem, and build an AI agent that turns it into a document that gets it right — repeatedly."

### The key requirement
> "Your agent needs to actually call Doctavian's generation API to shape a real document — not just talk about one."

### What Doctavian actually does
- **Document Generate API** — Turn template + structured data into finished PDF/DOCX/XLSX
- **Templates with logic** — Branching (if/else), loops (line items), calculations (totals) — not just mail-merge
- **Signatures** — Create and track legally binding envelopes end-to-end

### How ProofDesk uses it
```
Approved structured record → Doctavian Document Generate API → Final PDF

Template handles:
  - Branch: APPROVED vs CONDITIONALLY APPROVED vs REJECTED
  - Loop: Quote line items, obligations, conditions
  - Calculate: Totals, date gaps, risk counts
  - Conditional clauses: Insurance renewal obligations
```

**Real API call:** `POST https://demo.api.doctavian.com/v1/documents/document/generate`

**Auth required:** Bearer token (Google OAuth) + x-api-key + X-Subscription-Key

### Acceptance gate
A judge must see:
1. Different inputs produce visibly different documents
2. Template branching works (approved vs conditional)
3. Loops render correctly (line items)
4. Calculated values are correct (totals, date gaps)
5. Invalid data is caught (validation state)

### What we need to build
- [x] Real Doctavian API client with auth
- [x] DOCX template for Vendor Approval Memorandum
- [x] Wired into orchestrator (replace stub)
- [ ] **Real API generation working** — demo env has Google Drive permission issue

### Our submission line
> "Doctavian converts ProofDesk's approved structured record into the final conditional approval packet, including repeated line items, calculated values, and branch-specific clauses."

---

## 3. Foxit — "Your Agent Shouldn't Sign That"

### What they want
> "Build an agent that starts from a plain prompt and ends with a signed document."

### The key insight
> "We left signing out of the catalog on purpose. To send anything for signature, your agent has to call the Foxit eSign API directly, with its own credentials, and a person has to sign it. That handoff is the interesting part."

### What Foxit actually does
- **PDF Services API** — Merge, compress, convert, OCR, extract (40+ tools via MCP)
- **eSign API** — Create envelopes, send for signature, track status
- **MCP Server** — Open-source tool wrapping PDF Services for AI agents

### How ProofDesk uses it
```
Generated document → Foxit PDF Services (merge + compress) → Final PDF
                                                              ↓
                                          SignatureGate (6 checks)
                                                              ↓
                                          Foxit eSign API → Human signer
```

**Real API calls:**
- `POST https://na1.fusion.foxit.com/pdf-services/api/documents/enhance/pdf-combine` (merge)
- Foxit eSign API (signature request)

### The SignatureGate (6 checks before signing is allowed)
```python
def can_request_signature(case, artifact):
    return all([
        case.state == "PREPARED",           # Must be at PREPARED state
        case.blocking_exceptions == 0,       # No unresolved blockers
        case.human_approval is not None,     # Human must have approved
        case.structured_record is not None,  # Approved record must exist
        artifact.hash == case.approved_artifact_hash,  # Artifact must match approval
        case.signer is not None,             # Signer must be specified
    ])
```

### Acceptance gate
A judge must see:
1. Premature signature attempt fails
2. Reason for denial is clear (unresolved blocker)
3. Human resolves the blocker
4. Same path succeeds after resolution
5. Real Foxit eSign API call
6. Human performs signature

### What we need to build
- [x] Real Foxit PDF merge (working)
- [x] SignatureGate with 6 checks (working)
- [ ] **Real Foxit eSign API** — need eSign keys

### Our submission line
> "Foxit owns the authority boundary: PDF preparation is reversible AI work, but signing is an irreversible human commitment. ProofDesk's SignatureGate ensures no document reaches Foxit eSign without passing all six authorization checks."

---

## How They Fit Together

```text
STEP 1: INTAKE (Nutrient)
  User drops messy PDFs
  → Nutrient Data Extraction API
  → Structured facts with confidence + source coordinates
  → DWS Viewer for human review of uncertain facts

STEP 2: VERIFY (ProofDesk)
  Cross-document reconciliation
  → Quote arithmetic ✓
  → Entity name normalization ✓
  → Insurance coverage gap ✗ (31 days)
  → Route blocker to human

STEP 3: RESOLVE (Human)
  Human reviews source evidence
  → Conditional approval requiring renewed insurance
  → Resolution recorded as audit event

STEP 4: GENERATE (Doctavian)
  Approved structured record
  → Doctavian template branches: CONDITIONALLY APPROVED
  → Loop: line items, obligations
  → Calculate: totals, date gaps
  → Final Vendor Approval Memorandum

STEP 5: PREPARE (Foxit PDF)
  Generated document
  → Foxit PDF Services: merge + compress
  → Final PDF packet

STEP 6: SIGN (Foxit eSign)
  SignatureGate checks all 6 conditions
  → Foxit eSign API → Human signer
  → Signed artifact + audit receipt
```

---

## What We Claim vs What We Have

| Capability | Claimed | Working | Gap |
|-----------|---------|---------|-----|
| Nutrient extraction | Yes | Yes (real API) | None |
| Confidence scores | Yes | Yes (from Nutrient) | None |
| Source coordinates | Yes | Yes (page + bbox) | None |
| DWS Viewer | Yes | No | Need to wire iframe |
| Doctavian generation | Yes | Partial (local fallback) | Demo env Google Drive issue |
| Doctavian branching | Yes | Yes (local) | Need real API |
| Foxit PDF merge | Yes | Yes (real API) | None |
| Foxit eSign | Yes | No (stub) | Need eSign keys |
| Audit trail | Yes | Yes (hash chain + Merkle) | None |
| SignatureGate | Yes | Yes (6 checks) | None |

---

## What to Submit (per sponsor)

### Nutrient track
- Project name + one-line pitch
- Public repo with setup instructions
- 2-4 min demo video
- One line: "Nutrient DWS does the extraction with source-grounded citations and provides the Viewer for human review of uncertain facts."

### Doctavian track
- Project name + one-line pitch
- Public repo with setup instructions
- 2-4 min demo video
- One line: "Doctavian generates the final Vendor Approval Memorandum from approved structured data, with template branching for approval status and conditional clauses."

### Foxit track
- Project name + one-line pitch
- Public repo with setup instructions
- 2-4 min demo video
- One line: "Foxit PDF Services handles reversible PDF preparation, and Foxit eSign handles the irreversible signature — separated by ProofDesk's SignatureGate."

---

## Priority Order

1. **Nutrient** — Strongest story, real API works, highest prize ($1,500)
2. **Foxit** — PDF merge works, SignatureGate works, need eSign keys
3. **Doctavian** — Client built, demo env has permission issue, local fallback works

**Recommendation:** Submit to Nutrient track as primary. Mention Foxit and Doctavian as supporting integrations.
