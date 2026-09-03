# ProofDesk — Canonical Hackathon Thesis & Build Specification
**Snapshot date:** 2026-08-24  
**Target:** DevNetwork [API + Cloud + AI] Hackathon 2026  
**Primary sponsor tracks:** Nutrient DWS + Foxit + Doctavian  
**Optional sponsor track:** Xano, only after the three-sponsor core is complete  
**Overall prize:** Yes.

## Executive decision

### Product
**ProofDesk — evidence-gated document execution for high-stakes business workflows.**

### One-line pitch
> ProofDesk lets an AI agent prepare complex business documents, but only lets verified, human-approved facts cross the boundary into the final signed document.

### Canonical demo
**Vendor / procurement onboarding using synthetic documents.**

Input bundle:
- vendor master agreement;
- pricing quote;
- certificate of insurance;
- security questionnaire;
- procurement request.

The agent must:
1. understand a plain-language task;
2. ingest source documents;
3. extract structured facts with source context and confidence;
4. reconcile facts across documents;
5. distinguish deterministic checks from uncertain judgments;
6. route exceptions to a human;
7. freeze an approved structured record;
8. generate a conditional/calculated document from that record;
9. perform reversible PDF preparation;
10. request a human signature;
11. preserve an audit trail proving why the irreversible action was allowed.

## Core thesis

Typical document agents collapse:
`read -> infer -> decide -> generate -> sign`

ProofDesk separates **authority tiers**:
- AI may propose.
- Deterministic systems verify mechanically verifiable claims.
- Humans resolve ambiguity and approve irreversible actions.
- Final documents are generated only from approved structured state.
- Signing is an authority transition, not another unrestricted agent tool.

**Product invariant:**  
> No irreversible action may depend on an unresolved or provenance-less fact.

---

# Sponsor architecture

```text
PLAIN-LANGUAGE TASK
        |
        v
SOURCE DOCUMENT BUNDLE
        |
        v
[NUTRIENT DWS]
extract + confidence + source context
Viewer for human review
        |
        v
[PROOFDESK EVIDENCE ENGINE]
normalize
cross-document reconcile
deterministic rules
exceptions / approvals
        |
        +---- unresolved ---> HUMAN REVIEW
        |                       |
        +-----------------------+
        |
        v
APPROVED STRUCTURED RECORD
        |
        v
[DOCTAVIAN]
branches + loops + calculations
        |
        v
[FOXIT MCP / PDF SERVICES]
reversible PDF preparation
        |
        v
[SIGNATURE GATE]
        |
        v
[FOXIT eSIGN API]
human signature
        |
        v
SIGNED ARTIFACT + AUDIT RECEIPT
```

Each sponsor owns a materially different stage. If one can be removed without changing the workflow, the integration is too shallow.

---

# 1. Nutrient DWS

## Official intent
Brief official excerpts from the Devpost challenge:
> "pull the data out, judge how confident you are, bring a human in exactly where it matters"

> "must use Nutrient DWS ... for at least one core document operation, meaningfully"

The challenge additionally rewards deterministic, auditable pipelines with human review where guessing is unacceptable.

## ProofDesk role
Nutrient owns **source truth intake and human evidence review**.

Required:
1. Real Nutrient Data Extraction API call.
2. Retain value + page/source location + confidence.
3. Never discard provenance after extraction.
4. Route low-confidence/conflicting material facts to review.
5. Embed DWS Viewer.
6. Clicking an exception opens its source context.
7. Human resolution becomes a new event; original extraction stays immutable.

## Why this fits
Nutrient's current extraction product emphasizes source-grounded output, coordinates, confidence, validation, exception routing, and review. ProofDesk uses those as its evidence substrate rather than as decoration.

## Submission line
**Nutrient DWS turns messy source documents into source-grounded structured evidence and provides the review surface where humans resolve facts the automation is not allowed to guess.**

## Acceptance gate
A judge must see a real extracted value, jump to source evidence, see a material mismatch routed to review, resolve it, and watch the downstream workflow unblock.

---

# 2. Foxit — Your Agent Shouldn't Sign That

## Official intent
> "starts from a plain prompt and ends with a signed document."

> "That handoff is the interesting part of this challenge"

The challenge deliberately separates reversible PDF/MCP work from direct eSign and human signature.

## ProofDesk role
Foxit owns the **reversible -> irreversible authority boundary**.

Required:
1. Start from a plain prompt.
2. After document generation, use Foxit PDF Services through MCP for meaningful reversible work, e.g.:
   - merge approval memo + evidence appendix;
   - compare revisions;
   - compress/convert final packet.
3. Signature is not exposed as an unrestricted tool.
4. Server-side `SignatureGate` checks:
   - zero unresolved blockers;
   - human approval present;
   - structured record hash matches approval;
   - artifact hash is frozen/current;
   - signer is supplied.
5. Only then call Foxit eSign directly.
6. Human performs signature.
7. Signature status becomes an audit event.

## Design argument
**Signing is not a document transformation. It is an authority transition.**

Reversible work can be inspected, retried, or discarded. Signature creates commitment. ProofDesk treats those as different capabilities.

## Acceptance gate
Demo a premature signature attempt that fails, resolve the blocker, then show the same path becoming authorized and reaching Foxit eSign with a human signer.

---

# 3. Doctavian — Generate It Right. Sign It Tight.

## Official intent
> "turns it into a document that gets it right — repeatedly."

> "actually call Doctavian's generation API to shape a real document"

## ProofDesk role
Doctavian owns **approved structured state -> final complex document**.

Canonical output: **Vendor Approval & Risk Memorandum**.

The template must prove structured complexity:
- branch: approve / conditional approve / reject;
- loop: quote line items or obligations;
- calculation: totals / derived dates / risk count;
- optional exception-resolution appendix;
- threshold-dependent clause;
- evidence/resolution references.

Do not let an LLM free-write the final document and use Doctavian merely as a renderer.

Correct:
`source evidence -> approved typed record -> Doctavian template logic -> generated artifact`

## Submission line
**Doctavian converts ProofDesk's approved structured record into the final conditional approval packet, including repeated line items, calculated values, and branch-specific clauses.**

## Acceptance gate
Modify fixture data and regenerate. Loops, totals, conditional clauses, and exception appendix must change correctly.

---

# 4. Xano — optional

Official excerpt:
> "must use Xano as the backend in a meaningful way."

Do not begin with Xano. Add it only after the three-sponsor pipeline works.

If added, Xano must own:
- users/organizations;
- cases;
- workflow state;
- transition guards;
- approvals;
- audit events;
- webhook status updates;
- provider job metadata.

Then ProofDesk is legitimately an AI-native procurement portal. A demo database row is not enough.

---

# 5. Overall DevNetwork criteria

Published overall judging criteria:

### Progress
> "How much progress did you make?"

ProofDesk answer: show the full live path, not slides:
`prompt -> extraction -> review -> generation -> PDF prep -> signature`

### Concept
> "Does it solve a real problem?"

ProofDesk answer: businesses cannot safely allow uncertain model output to silently become signed commitments. ProofDesk inserts evidence and authority gates.

### Feasibility
> "Could this become a startup or company?"

ProofDesk answer: procurement is the demo vertical; the product can generalize to contract ops, insurance, financial back office, compliance review, and document approval.

Do not claim regulatory certification. Claim governed, auditable workflow infrastructure.

---

# 6. Canonical synthetic fixture

Prompt:
`Prepare Northstar Data Systems for a $42,500 annual software procurement. Reconcile the packet, create the approval memo, and send it for signature if it is safe.`

Source facts:
- procurement request legal name: Northstar Data Systems Ltd.
- requested spend: $42,500
- contract start: 2026-10-01
- insurance required through: 2027-10-01
- quote legal name: Northstar Data Systems Limited
- quote: Platform $35,000 + Support $7,500
- quote total: $42,500
- insurance expiry: 2027-08-31
- security questionnaire: retention 30 days, 3 subprocessors, encryption at rest yes

Seeded discrepancy:
**insurance expires before the required coverage date.**

Expected behavior:
- normalize `Ltd.` vs `Limited` while retaining raw values;
- verify quote arithmetic deterministically;
- detect insurance-date mismatch deterministically;
- route only the material mismatch to review;
- block generation/signature until resolution;
- human chooses conditional approval requiring renewed insurance;
- Doctavian automatically includes that obligation.

This one discrepancy demonstrates all three sponsor narratives.

---

# 7. Evidence model

Extracted facts are immutable.

```json
{
  "fact_id": "fact_...",
  "field": "insurance.expiry_date",
  "value_raw": "August 31, 2027",
  "value_normalized": "2027-08-31",
  "source_document_id": "doc_03",
  "page": 1,
  "bounding_box": [0.12, 0.31, 0.42, 0.36],
  "extractor": "nutrient_dws",
  "confidence": 0.97,
  "content_hash": "sha256:..."
}
```

Derived checks are separate:

```json
{
  "assertion_id": "assert_...",
  "predicate": "insurance.expiry_date >= procurement.required_coverage_until",
  "inputs": ["fact_expiry", "fact_required_until"],
  "result": false,
  "method": "deterministic",
  "rule_version": "coverage-v1"
}
```

Human resolutions are separate:

```json
{
  "resolution_id": "resolution_...",
  "assertion_id": "assert_...",
  "decision": "CONDITIONAL_ACCEPT",
  "reason": "Renewed certificate required before current policy expires.",
  "actor_id": "user_..."
}
```

Never rewrite evidence to make the case look clean.

---

# 8. State machine

```text
RECEIVED
 -> INGESTED
 -> EXTRACTED
 -> RECONCILED
 -> CHECKED
    -> REVIEW_REQUIRED -> RESOLVED
 -> APPROVABLE
 -> APPROVED
 -> GENERATED
 -> PREPARED
 -> SIGNATURE_AUTHORIZED
 -> SIGNATURE_REQUESTED
 -> SIGNED
 -> ARCHIVED
```

Forbidden:
- REVIEW_REQUIRED -> GENERATED
- CHECKED -> SIGNATURE_REQUESTED
- GENERATED -> SIGNATURE_REQUESTED without approval bound to the exact record/artifact hash

Any source or approved-state mutation creates a new revision and invalidates downstream approval.

---

# 9. SignatureGate

```python
def can_request_signature(case, artifact):
    return all([
        case.state == "PREPARED",
        case.blocking_exceptions == 0,
        case.human_approval is not None,
        case.human_approval.structured_record_hash == case.structured_record_hash,
        artifact.hash == case.approved_artifact_hash,
        artifact.is_latest_revision,
        case.signer is not None,
    ])
```

Denials are structured:
```json
{
  "allowed": false,
  "reasons": [
    {"code": "UNRESOLVED_BLOCKER", "assertion_id": "assert_insurance_expiry"}
  ]
}
```

The demo should intentionally hit this denial once.

---

# 10. UI

Keep four screens.

## A — Case / prompt
Plain prompt + source upload + `Run ProofDesk`.

## B — Evidence board
Columns:
- source facts;
- deterministic checks;
- exceptions.

Every fact shows value, confidence, source chip, status.
Click source chip -> Nutrient Viewer at source context.

## C — Human decision
Only unresolved exceptions.
Show requirement, source value, rule result, evidence.
Actions: reject / conditional accept / corrected with evidence.

## D — Execution timeline
```text
Nutrient extraction        ✓
Cross-document checks      ✓
Human resolution           ✓
Structured record approved ✓
Doctavian generation       ✓
Foxit PDF preparation      ✓
Signature gate             ✓
Foxit eSign sent           ✓
Human signed               ✓
```

Each row expands to its receipt.

---

# 11. API

```text
POST /v1/cases
POST /v1/cases/{id}/documents
POST /v1/cases/{id}/run
GET  /v1/cases/{id}
GET  /v1/cases/{id}/facts
GET  /v1/cases/{id}/assertions

POST /v1/assertions/{id}/resolve
POST /v1/cases/{id}/approve

POST /v1/cases/{id}/generate
POST /v1/cases/{id}/prepare
POST /v1/cases/{id}/signature-request

GET  /v1/cases/{id}/events
GET  /v1/cases/{id}/receipt
```

The LLM may orchestrate reversible work; backend policy owns state truth.

---

# 12. Minimum data model

- `cases`
- `documents`
- `facts`
- `assertions`
- `resolutions`
- `structured_records`
- `generated_artifacts`
- `signature_requests`
- append-only `events`

Generated artifact receipt includes:
- Doctavian template ID/version;
- approved input hash;
- provider job ID;
- output artifact hash.

Signature receipt includes:
- exact artifact hash;
- approval ID;
- signer;
- Foxit request ID/status.

---

# 13. Build checkpoints

## CP0 — Freeze thesis
Commit this spec + sponsor matrix + source snapshot + state machine.

Pass: contributor can explain each sponsor's unique role in one sentence.

## CP1 — Golden fixture
Create deterministic synthetic source docs plus expected extraction/check/output fixtures.

Pass: tests know the truth before provider integration.

## CP2 — Nutrient extraction
Real DWS call; retain source context and confidence.

Pass: fixture facts trace to source.

## CP3 — Deterministic evidence engine
Implement:
- type normalization;
- legal-name normalization;
- quote arithmetic;
- coverage-date comparison;
- required fields;
- exception severity.

Pass: pure unit tests, no LLM required.

## CP4 — Nutrient Viewer review
Review queue, Viewer, source jump, resolution event.

Pass: blocker stops workflow; human resolution unblocks it.

## CP5 — Approved record/hash
Canonical JSON, revision, hash, explicit approval.

Pass: any fact change invalidates approval.

## CP6 — Doctavian real generation
Real API; nontrivial loop + branch + calculation.

Pass: changing fixture deterministically changes document structure.

## CP7 — Foxit reversible PDF work
Register MCP; perform meaningful operation on real generated artifact.

Pass: real provider operation visible in timeline.

## CP8 — SignatureGate + Foxit eSign
Direct eSign call behind server-side policy.

Pass: premature sign rejected; approved sign allowed; human signer involved.

## CP9 — Replayable receipt
Event timeline, hashes, source refs, provider IDs, resolutions, signature state.

Pass: reviewer can reconstruct why signature was permitted.

## CP10 — <4 minute end-to-end demo
One resettable golden run.

## CP11 — Xano only after CP10
If time remains, make Xano the actual workflow backend.

## CP12 — submission polish
README, diagrams, screenshots, video, setup, tests, known limitations.

---

# 14. Test plan

Unit:
- currency/date parsing;
- normalized entity matching;
- quote arithmetic;
- state transition guards;
- hash stability;
- SignatureGate.

Failure injection:
- missing confidence;
- provider timeout;
- missing source;
- Doctavian failed generation;
- Foxit PDF failure;
- eSign retry;
- source changes after approval;
- artifact hash changes;
- duplicate webhook.

Golden E2E:
1. extract;
2. detect one blocker;
3. premature signature rejected;
4. human conditionally accepts;
5. approve record;
6. generate document;
7. prepare PDF;
8. signature authorized/requested.

---

# 15. What NOT to build

Do not spend hackathon time on:
- generic chat-with-PDF;
- custom OCR;
- custom viewer;
- custom e-sign;
- custom document-generation engine;
- blockchain notarization;
- multi-agent debate;
- large RAG stack;
- real PII;
- broad legal/compliance certification;
- ten workflow verticals;
- autonomous signing;
- opaque "AI confidence 94/100";
- giant dashboard.

The sponsor APIs already supply document primitives.

ProofDesk's original value is:
**evidence model + reconciliation + authority state machine + human escalation + cross-provider receipt.**

---

# 16. Why procurement is the canonical demo

A one-document contract demo has too little structure.

Procurement naturally has:
- heterogeneous sources;
- identity reconciliation;
- line items;
- arithmetic;
- dates;
- business thresholds;
- conditional approval;
- human exceptions;
- generated memo;
- signature.

It proves all integrations in one story.

---

# 17. Demo script (~3 minutes)

**0:00–0:20**  
"Agents can read and draft documents. The dangerous part is letting uncertain model output become a signed commitment."

Enter the procurement prompt.

**0:20–0:55 — Nutrient**  
Show extraction. Click insurance expiry and jump to source evidence.

**0:55–1:20 — Evidence gate**  
Quote arithmetic ✓. Entity normalization ✓. Insurance coverage ✕.  
Attempt irreversible progression: blocked.

**1:20–1:45 — Human**  
Review source. Select conditional approval requiring renewed insurance.

**1:45–2:15 — Doctavian**  
Generate approval memo. Show line-item loop, total, conditional insurance clause, resolution appendix.

**2:15–2:40 — Foxit**  
Use Foxit MCP/PDF Services to merge/prepare final package. SignatureGate green. Direct eSign request goes to human signer.

**2:40–3:00 — Receipt**  
Show source -> fact -> failed rule -> resolution -> approved hash -> generated hash -> signature authorization.

Close:
**"AI does the reversible work. Evidence and people control the irreversible work."**

---

# 18. Startup thesis

The hackathon product is procurement.
The company thesis is a provider-neutral trust control plane for AI-operated document workflows.

Reusable primitives:
- EvidenceFact
- Assertion
- ReviewTask
- HumanResolution
- Approval
- Artifact
- AuthorityGate
- Receipt

Potential future verticals:
- procurement;
- contracts;
- insurance;
- financial operations;
- document/compliance review.

The moat is not PDF manipulation. It is reusable evidence/authority semantics and receipts across document providers.

---

# 19. Final coding-agent priority

1. golden fixture;
2. real Nutrient source grounding;
3. deterministic mismatch;
4. human review gate;
5. immutable approved record/hash;
6. real Doctavian complex generation;
7. real Foxit reversible operation;
8. Foxit eSign behind SignatureGate;
9. audit receipt;
10. polish three-minute demo;
11. only then consider Xano.

When forced to choose between another feature and making a transition indisputably work, make the transition work.

---

# 20. Source snapshot

Official hackathon/sponsor page:
https://api-cloud-ai-hackathon-2026.devpost.com/

Nutrient:
https://www.nutrient.io/api/
https://www.nutrient.io/api/data-extraction-api/
https://www.nutrient.io/api/viewer-api/

Foxit:
https://developer-api.foxit.com/pdf-services/
https://developer-api.foxit.com/esign/
https://docs.developer-api.foxit.com/

Doctavian:
The current sponsor requirements are on the official Devpost challenge page. Obtain hackathon credentials/docs from Doctavian as instructed there.

Xano:
https://docs.xano.com/

Before submission, re-open Devpost and diff sponsor wording against this snapshot.
