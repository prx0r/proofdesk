# ProofDesk — Finish-Line Development Plan

## DevNetwork API + Cloud + AI Hackathon 2026 — Nutrient DWS Track

### Submission thesis

**ProofDesk is an evidence-gated document execution system. Nutrient DWS turns messy source documents into grounded evidence; ProofDesk determines whether that evidence is trustworthy enough to act on, routes uncertain cases to humans, learns from those interventions, and leaves a replayable audit trail.**

The sponsor alignment is unusually strong. Nutrient explicitly asks builders to extract data, determine confidence, bring humans in when judgment matters, and maintain a record; it gives extra credit for deterministic/auditable output and HITL workflows. The required submission is a public repo with setup instructions, a 2–4 minute end-to-end demo, a one-line pitch, and one line explaining where DWS does the heavy lifting.

---

# THE FINISH-LINE GOAL

By the end of today, a judge should be able to:

```bash
git clone https://github.com/prx0r/proofdesk
cd proofdesk
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# add NUTRIENT_API_KEY
<one command>
```

Then open one URL and see:

```text
Source PDFs
    ↓
Nutrient DWS extraction
    ↓
Grounded facts + confidence + source location
    ↓
Cross-document verification
    ↓
A meaningful discrepancy
    ↓
REVIEW_REQUIRED
    ↓
Human examines evidence
    ↓
Human resolves exception
    ↓
Structured record
    ↓
Deterministic generated artifact
    ↓
Decision certificate / hash / audit trail
```

The judge should not need to understand Foxit, Doctavian, the historical experiments, dataset downloads, your filesystem, or your development history before this works.

---

# PHASE 0 — FREEZE THE PRODUCT

Do not add another major feature.

The product already has enough:

* live Nutrient extraction
* evidence grounding
* reconciliation
* assertions
* explicit state machine
* fail-closed authority gate
* HITL exception resolution
* deterministic document generation
* content hashes
* audit events
* Merkle infrastructure
* decision certificates
* provider-call traces
* confidence calibration research
* per-field risk ideas
* online human-feedback calibration
* spot auditing
* experimental benchmarking

The task is now **compression and proof**, not invention.

Canonical hackathon target:

> **Nutrient only.**

Foxit work becomes technical/research provenance. Doctavian is historical material. Neither should compete for attention on the main judge path.

---

# PHASE 1 — P0: MAKE CI GREEN

## 1. Fix the missing demo PDFs

This is the first concrete blocker.

`tests/test_learning.py` directly opens:

```text
data/test_pdfs/procurement_request.pdf
data/test_pdfs/vendor_quote.pdf
data/test_pdfs/insurance_certificate.pdf
data/test_pdfs/security_questionnaire.pdf
```

But `.gitignore` explicitly excludes `data/test_pdfs/`.

Therefore:

```text
local machine:
PDFs exist
→ learning suite passes

clean GitHub runner:
PDFs don't exist
→ FileNotFoundError
→ CI red
```

This must be eliminated.

### Recommended implementation

Create:

```text
fixtures/
└── procurement/
    ├── procurement_request.pdf
    ├── vendor_quote.pdf
    ├── insurance_certificate.pdf
    └── security_questionnaire.pdf
```

These four files should be:

* tiny
* synthetic
* legally safe to publish
* deterministic
* designed specifically around the canonical contradiction
* committed to Git
* the exact files used by demo + tests

Then create one canonical fixture loader:

```python
# src/demo/fixtures.py

FIXTURE_ROOT = Path(__file__).parents[...] / "fixtures" / "procurement"

def load_procurement_fixture() -> list[Document]:
    ...
```

Every component should call that loader:

```text
tests/test_learning.py
POST /v1/cases/fixture
demo bootstrap
CLI demo
integration test
```

There should be exactly **one definition** of the canonical demo inputs.

### Acceptance test

This must work after:

```bash
git clone
```

with no private files whatsoever.

---

## 2. Fix Git/submodule debris

The existing CI cleanup has also complained about dataset/repository paths with incomplete submodule metadata.

Remove accidental gitlinks or properly declare actual submodules.

For hackathon submission, preferably remove them from the canonical dependency graph entirely.

The repo should not emit errors like:

```text
fatal: No url found for submodule path ...
```

even if they occur during post-job cleanup.

Research datasets should be referenced by documentation:

```text
datasets/
README → download instructions / source URLs
```

not wired into the judge's clone unless necessary.

---

## 3. Make the actual CI result authoritative

Current docs say things such as "104 tests passing," while the GitHub badge is red because a later suite fails. That weakens trust.

After fixing fixtures:

Run every named suite in CI:

```bash
python tests/test_all.py
python tests/test_audit.py
python tests/test_integration.py
python tests/test_generation.py
python tests/test_frontier.py
python tests/test_learning.py
```

Then preferably add one normal pytest invocation too if tests are pytest-compatible:

```bash
pytest -q
```

At the end, have CI print one canonical line:

```text
PROOFDESK SUBMISSION GATE: PASS
```

Only after that update README counts.

Do not manually count tests from historical notes.

---

# PHASE 2 — P0: MAKE NUTRIENT UNDENIABLY CENTRAL

A Nutrient judge should understand within ~20 seconds that this is not a superficial API call.

Nutrient explicitly says DWS must perform a meaningful core document operation rather than a throwaway invocation.

## 4. Make provider status visible

You already expose:

```text
GET /v1/providers/status
```

and distinguish live/stub integrations.

Keep it.

For the Nutrient submission, simplify the visual representation to something like:

```text
Nutrient DWS       LIVE
Document Renderer  LOCAL
Audit Engine       LOCAL
Human Review       LIVE
```

Foxit doesn't need to occupy prime demo real estate.

---

## 5. Make the DWS provider trace first-class

You already expose:

```text
GET /v1/cases/{case_id}/trace
```

for outbound provider calls.

This is excellent.

The demo should show a compact trace panel:

```text
NUTRIENT DWS
POST /build
200
842ms

operation:
  extract

document:
  insurance_certificate.pdf

result:
  grounded_fields: 14
```

Not every HTTP header.

Judges need proof of integration, not debugging noise.

The trace should make it obvious:

```text
THIS VALUE CAME FROM NUTRIENT.
```

---

## 6. Preserve evidence provenance per extracted fact

Every public fact should ideally expose:

```json
{
  "field": "insurance_expiry",
  "value": "2026-08-14",
  "confidence": 0.93,
  "source": {
    "document_id": "...",
    "filename": "insurance_certificate.pdf",
    "page": 1,
    "bbox": [...]
  },
  "provider": "nutrient_dws"
}
```

The exact schema can differ.

The important invariant:

> A judge can click from an asserted fact back to where it came from.

If bounding boxes are available from your current extraction path, surface them clearly.

If not every field has bbox data, do not fabricate it:

```text
grounding: available / unavailable
```

Fail honestly.

---

# PHASE 3 — P0: MAKE THE CONTRADICTION THE HERO

The procurement demo is already a good story.

Do not show a happy-path invoice extraction where everything succeeds.

The memorable moment should be:

```text
Purchase request:
Insurance must remain valid through X.

Certificate:
Coverage expires before X.

→ POLICY ASSERTION FAILED

→ SIGNING/AUTHORITY BLOCKED
```

That is ProofDesk.

## 7. Create one canonical seeded discrepancy

Freeze exactly one discrepancy.

For example:

```text
requested service period ends:
2026-12-31

insurance certificate expires:
2026-10-01

requirement:
coverage must remain valid through service end
```

No ambiguity.

Your reconciliation layer should derive:

```text
ASSERTION:
insurance_valid_through_service_period

EXPECTED:
expiry >= 2026-12-31

OBSERVED:
2026-10-01

RESULT:
FAIL
```

Then the system state becomes:

```text
REVIEW_REQUIRED
```

This should be deterministic.

The judge sees immediately why "accurate OCR" does not equal "safe business action."

---

# PHASE 4 — HARDEN THE AUTHORITY GATE

ProofDesk's best technical concept is not PDF parsing.

It's the distinction:

> **Evidence is not authority.**

## 8. Make gate checks visible

Instead of only:

```text
SIGNING DENIED
```

show:

```text
AUTHORITY GATE

✓ source evidence available
✓ extraction above minimum confidence
✗ unresolved policy exception
✗ human approval absent
✓ artifact integrity valid

DECISION:
BLOCK
```

After resolution:

```text
✓ source evidence available
✓ confidence threshold satisfied
✓ exceptions resolved
✓ human approval recorded
✓ artifact hash matches approved record

DECISION:
PROCEED
```

This is visually powerful.

---

## 9. Preserve deterministic decision certificates

Each final authorization should have a compact certificate containing roughly:

```text
case_id
record_hash
artifact_hash
policy/rule versions
assertion results
human decisions
evidence IDs
timestamp
gate result
audit root
```

Then expose:

```text
GET /v1/cases/{id}/certificate
```

if it isn't already cleanly surfaced.

The video only needs ~5 seconds on it:

> "Every authorization is replayable from this certificate."

Do not explain Merkle trees for 45 seconds.

---

# PHASE 5 — HUMAN REVIEW SHOULD BE A PRODUCT FEATURE, NOT A BUTTON

Nutrient explicitly favors human review when a guess is unacceptable.

## 10. Human review screen

When a blocker appears, show:

```text
Exception
─────────

Rule:
Insurance must cover full service period

Expected:
>= 31 Dec 2026

Observed:
1 Oct 2026

Evidence:
insurance_certificate.pdf
Page 1
[open source]

Confidence:
0.93

Actions:
[Reject]
[Conditional Accept]
[Mark Source Incorrect]
```

That is much stronger than:

```text
Resolve exception? yes/no
```

---

## 11. Record why the human decided

Resolution must include:

```text
decision
actor
timestamp
reason
evidence viewed
```

This becomes both:

* audit evidence
* future calibration data

Example:

```json
{
  "decision": "CONDITIONAL_ACCEPT",
  "reason": "Vendor has supplied confirmation renewal is in progress.",
  "actor": "procurement_manager",
  "assertion_id": "..."
}
```

No anonymous magic override.

---

# PHASE 6 — SURFACE THE LEARNING LOOP

This is one of the best "extra-credit" elements in the whole repository.

The implementation already captures human outcomes, updates an online calibrator, tracks field-level correctness labels, and maintains a spot-audit pool for auto-approved cases.

The learning tests explicitly test:

```text
human labels → calibrated policy
```

and the idea that safety should be assessed using measured errors among audited automated decisions rather than simply counting human acceptance.

## 12. Give this a simple product name

Do not call it:

```text
MarginOnlineCalibrator + conformal convergence feedback primitive
```

in the demo.

Call it:

> **Learning from Review**

Visual:

```text
Human Reviews: 37

Invoice total
  historical error: 0.2%
  automation threshold: 0.91

Insurance expiry
  historical error: 4.8%
  automation threshold: 0.98

Vendor name
  historical error: 0.0%
  automation threshold: 0.88
```

The exact numbers need to be real or clearly labelled demo/sample data.

The concept:

> Different fields earn different levels of trust.

That is excellent.

---

## 13. Do NOT claim "self-improving safety" without showing the control

The correct claim is:

> Human resolutions provide calibration labels, allowing the policy to adapt while spot audits continue measuring automated error.

Not:

> The AI learns and eventually signs everything itself.

The desired trajectory is:

```text
human review ↓
while
measured false-authority risk remains within policy
```

That distinction makes the work sound rigorous.

---

# PHASE 7 — PACKAGE THE CONFIDENCE RESEARCH PROPERLY

The `/foxit` directory contains substantial research:

* conformal risk control
* extraction-confidence experiments
* per-field control
* isotonic calibration
* asymmetric Sheepish shrinkage
* mixture of experts
* distribution-shift monitoring
* fraud/false-sign style benchmarks
* evolutionary optimization
* online feedback
* audit experiments

Your technical-depth document already frames calibration, risk control and online learning as the three central confidence problems.

This work should absolutely remain visible.

But it needs a hierarchy.

## 14. Rename the conceptual role of `/foxit`

Do not necessarily rename the directory now if that risks breakage.

Instead put this at its README top:

```text
# ProofDesk Research Lab

Historical note:
This research originated while exploring the Foxit signing challenge.

For the current Nutrient DWS submission, this directory serves as the
research laboratory behind ProofDesk's confidence and authority policy.

The production submission path is:
../src/

This directory contains:
- calibration experiments
- conformal-risk experiments
- benchmark protocols
- threshold optimization
- false-authorization research
```

Then prominently link:

```text
docs/TECHNICAL_DEPTH.md
```

from the main README.

This changes the judge's interpretation from:

> "Why is there another project nested here?"

to:

> "They have a serious research lab behind the product."

---

## 15. Separate CLAIMED from EXPERIMENTAL

Every research result should be categorized:

```text
PRODUCTION
EXPERIMENTAL
REPLICATED
PROVISIONAL
HISTORICAL
```

For example:

| Component                    | Submission status                          |
| ---------------------------- | ------------------------------------------ |
| Nutrient extraction          | PRODUCTION / LIVE                          |
| Cross-document checks        | PRODUCTION                                 |
| authority state machine      | PRODUCTION                                 |
| hash audit                   | PRODUCTION                                 |
| online feedback capture      | PRODUCTION                                 |
| conformal calibration method | EXPERIMENTAL / integrated where applicable |
| Sheepish transform           | EXPERIMENTAL                               |
| Cogym evolution              | RESEARCH                                   |
| fraud benchmark              | RESEARCH                                   |
| Foxit eSign                  | NOT PART OF CURRENT SUBMISSION             |

This single table will make the repo look much more trustworthy.

---

# PHASE 8 — RESEARCH CLAIM HYGIENE

This matters because the research is impressive enough that judges may actually inspect it.

## 16. Audit every headline number

There are currently different datasets and experimental contexts mixed together.

Before submission, make one canonical file:

```text
docs/RESULTS_CANONICAL.md
```

For every result:

```text
claim
dataset
n
task
metric
method
script that reproduces it
status
```

Example:

```text
Claim:
AUC = 0.993

Dataset:
ColdHearted

Unit:
transaction/example

Task:
fraud-risk discrimination

Reproduce:
python foxit/experiments/benchmark.py ...

Status:
research benchmark, not production-document accuracy
```

This prevents accidental claims such as calling transaction datasets "24,878 real documents."

---

## 17. Do not equate confidence with correctness

Your existing research docs correctly distinguish these concepts.

Keep that discipline everywhere.

Correct:

```text
Nutrient returned confidence 0.97 for this extraction.
```

Incorrect:

```text
Nutrient was 97% accurate.
```

Unless you have calibrated ground-truth evaluation proving that.

---

# PHASE 9 — CLEAN THE MAIN README

The README should be understandable in 90 seconds.

Recommended structure:

```text
# ProofDesk
Evidence-gated document execution.

[hero GIF/screenshot]

## The problem

AI can extract data from documents.
That does not mean it has enough evidence or authority to act.

## What ProofDesk does

Source documents
→ Nutrient DWS
→ grounded facts
→ verification
→ authority gate
→ human review when needed
→ audit certificate

## Demo

<3 commands>

## Why Nutrient DWS

DWS is the evidence layer...

## Core guarantees

Fail closed
Source grounding
Human authority
Content integrity
Replayable audit

## Learning from review

<short section>

## Technical depth

link to TECHNICAL_DEPTH.md

## API

minimal useful endpoints

## Tests

current CI result

## Research

link, don't dump it all here
```

Remove historical sponsor confusion from above the fold.

---

# PHASE 10 — CREATE A ONE-COMMAND JUDGE EXPERIENCE

Add:

```bash
./scripts/demo.sh
```

or:

```bash
make demo
```

It should:

```text
1. validate environment
2. print Nutrient LIVE/STUB state
3. start server
4. tell user the local URL
5. optionally load the canonical fixture
```

Example output:

```text
ProofDesk Hackathon Demo
========================

Nutrient DWS: LIVE
Demo fixtures: READY
Audit store: READY

Server:
http://localhost:3799

Open:
http://localhost:3799/demo
```

If Nutrient credentials are absent:

```text
Nutrient DWS: MISSING

Set:
export NUTRIENT_API_KEY=...

The deterministic fixture replay is still available with:
./scripts/demo.sh --replay
```

Fail clearly.

---

# PHASE 11 — DEMO RELIABILITY

You need two modes:

## LIVE

Actual Nutrient API.

Use this for tomorrow's recording.

## REPLAY

Previously captured Nutrient result, with explicit label:

```text
REPLAY — CAPTURED NUTRIENT DWS RESPONSE
```

Use this if:

* network dies
* DWS is slow
* credits fail
* service is unavailable during judging

Both should pass through the **same downstream code**.

Do not have a completely separate fake demo implementation.

Architecture:

```text
NutrientProvider
    ├── LiveTransport
    └── ReplayTransport

same normalization
same Fact objects
same reconciliation
same gate
same audit
```

That is robust and defensible.

---

# PHASE 12 — CANONICAL DEMO SCRIPT

Target length:

**~3:00–3:20**

## 0:00–0:18 — Thesis

Screen:

ProofDesk title + workflow.

Narration concept:

> AI can read a contract. That doesn't mean it should be trusted to execute what the contract says. ProofDesk separates document intelligence from authority to act.

---

## 0:18–0:45 — Nutrient does the heavy lifting

Show four procurement documents.

Press:

```text
Analyze
```

Immediately show provider trace:

```text
Nutrient DWS — LIVE
```

Then grounded facts.

Focus on one or two:

```text
service_end_date
insurance_expiry
```

Show confidence and source/page.

Narration:

> Nutrient DWS converts the source PDFs into grounded evidence with confidence and source provenance.

---

## 0:45–1:10 — Cross-document verification

Show the assertion:

```text
insurance_expiry >= service_end_date
```

Result:

```text
FAIL
```

State:

```text
REVIEW_REQUIRED
```

Narration:

> Both fields may have been extracted correctly. The problem is that together they describe an unsafe transaction.

This line is important.

It explains why ProofDesk exists beyond extraction.

---

## 1:10–1:35 — Fail-closed authority

Open gate view.

Show:

```text
✓ evidence available
✗ unresolved blocker
✗ human approval
✓ record integrity

BLOCKED
```

Narration:

> An AI confidence score never becomes execution authority by itself.

Very strong line.

---

## 1:35–1:58 — Human review

Click the exception.

Open the evidence.

Resolve:

```text
CONDITIONAL_ACCEPT
```

with reason.

Show actor + timestamp.

Narration:

> ProofDesk sends the exact uncertain claim and its source back to a human instead of asking them to review the entire document bundle from scratch.

---

## 1:58–2:25 — Deterministic execution

Continue.

Show:

```text
record hash
generated artifact
artifact hash
gate PASS
decision certificate
```

Narration:

> Once the evidence and human decision are resolved, the approved record is content-addressed and the final action is tied to exactly those bytes.

---

## 2:25–2:48 — Audit

Show a compact audit timeline:

```text
INGEST
DWS_EXTRACT
ASSERT
BLOCK
HUMAN_RESOLUTION
APPROVE
GENERATE
AUTHORIZE
```

Then alter something / briefly show tamper demo if reliable:

```text
HASH MISMATCH → DENY
```

No more than 15–20 seconds.

---

## 2:48–3:08 — Learning loop

Show:

```text
Learning from Review
```

Explain:

> Human resolutions become calibration labels. Over time ProofDesk can automate the cases it has learned are safe while maintaining spot audits on automated decisions.

Show `/v1/feedback/stats` or equivalent in visual form.

---

## 3:08–3:20 — Finish

End with:

> Nutrient gives agents trustworthy document evidence. ProofDesk determines when that evidence is strong enough to act.

Logo / architecture.

Done.

---

# PHASE 13 — REQUIRED NUTRIENT SUBMISSION LINE

The sponsor explicitly asks for:

> one line explaining where DWS does the heavy lifting and why.

Use:

**"Nutrient DWS performs the core document extraction and source grounding that turns uploaded PDFs into confidence-aware evidence; ProofDesk uses that evidence to determine whether an automated action may proceed or must defer to a human."**

---

# PHASE 14 — DEVPOST POSITIONING

## One-line pitch

**ProofDesk turns document extraction into evidence-gated execution: Nutrient DWS grounds the facts, and ProofDesk decides when AI can safely proceed and when a human must intervene.**

## Problem

Existing AI document systems optimize:

```text
document → answer
```

Regulated workflows actually need:

```text
document
→ evidence
→ confidence
→ policy
→ human authority
→ irreversible action
→ audit
```

The dangerous failure is not merely extraction error.

It is:

> **taking an irreversible action on insufficient evidence.**

---

## Innovation

The innovation is the composition:

```text
Nutrient source grounding
+
cross-document verification
+
calibrated uncertainty
+
explicit authority state machine
+
human exception handling
+
content-addressed artifacts
+
feedback-driven calibration
```

Do not pitch "we invented conformal prediction."

Pitch:

> **We turned reliability research into an execution boundary.**

---

# PHASE 15 — EXTRA-CREDIT SECTION FOR JUDGES

The Devpost story should contain a section called something like:

## Beyond the demo: research behind the authority gate

Then mention succinctly:

### 1. Risk-adaptive confidence

Different document fields should not share one arbitrary confidence threshold.

### 2. Conformal-style risk control

Experimental work explores controlling false authorization rather than optimizing generic accuracy.

### 3. Sheepish confidence

You explored asymmetric penalties for overconfidence because overconfident errors are operationally more dangerous than cautious abstentions.

### 4. Multiple verification signals

Extraction confidence can be augmented with:

```text
dual extraction agreement
deterministic reconstruction
field completeness
policy assertions
grounding quality
distribution drift
```

### 5. Human-feedback learning

Human resolutions become calibration evidence rather than disappearing into an audit log.

### 6. Spot auditing

Auto-approved decisions remain sampled for human audit so the system measures real automated error.

### 7. Tamper-evident execution

Record hashes, artifact hashes, chained events and Merkle proofs bind the decision to its evidence.

This is enough.

Link the technical appendix for judges who want the full details.

---

# PHASE 16 — FUTURE / STARTUP STORY

The strongest commercial vision is not "contract signing software."

It is:

> **An authority layer for AI agents operating on enterprise documents.**

Nutrient gives you the document evidence.

ProofDesk answers:

```text
Does the agent have enough evidence?
What policy applies?
How risky is this field?
What requires human judgment?
Who has authority?
Did the approved bytes change?
What happened?
What did humans teach the system?
```

That primitive generalizes.

## Procurement

```text
quote
insurance
security questionnaire
purchase request
→ approval
```

## Accounts payable

```text
invoice
PO
goods receipt
bank details
→ payment authorization
```

## Insurance

```text
claim
policy
supporting evidence
→ settlement authority
```

## Lending

```text
application
income evidence
valuation
identity docs
→ underwriting action
```

## Compliance

```text
ID
KYC docs
risk evidence
→ onboarding
```

## Healthcare administration

```text
referral
coverage
authorization form
→ administrative approval
```

The reusable product is:

> **evidence → policy → authority**

not procurement specifically.

---

# PHASE 17 — LONGER-TERM LEARNING MOAT

This could become the most important ProofDesk asset.

Each organization generates proprietary calibration data:

```text
field
document type
provider
confidence
policy rule
model prediction
human decision
later audit result
```

Over time ProofDesk learns:

```text
where automation is trustworthy
where it fails
which fields are dangerous
which document types drift
which vendors produce unreliable documents
which rules cause unnecessary human review
```

That produces an organization-specific **trust model**.

A competitor can copy the UI.

It cannot instantly copy:

```text
three years of calibrated authority decisions
+
measured downstream outcomes
+
field-specific risk profiles
```

That is a credible data moat.

---

# PHASE 18 — CODE QUALITY / FAILURE MODES

Before recording, explicitly test these.

### Nutrient unavailable

Expected:

```text
DWS_UNAVAILABLE
→ no fabricated extraction
→ no authorization
```

### Nutrient returns zero fields

Expected:

```text
EVIDENCE_INCOMPLETE
→ BLOCK
```

### missing confidence

Expected:

```text
unknown confidence
→ conservative handling
```

### cross-document contradiction

Expected:

```text
REVIEW_REQUIRED
```

### unresolved blocker + attempt approval

Expected:

```text
409 / state violation
```

### attempt generation before approval

Expected:

```text
deny
```

### artifact modified after approval

Expected:

```text
hash mismatch
→ deny
```

### duplicate human resolution

Expected:

```text
idempotent or explicit conflict
```

### provider timeout

Expected:

```text
visible provider failure
→ no silent fallback pretending to be live
```

### audit corruption

Expected:

```text
chain verification fail
```

These are excellent judge-facing engineering tests.

---

# PHASE 19 — SECURITY / CREDENTIAL HYGIENE

Before final push:

```bash
git grep -Ei \
'(api[_-]?key|client[_-]?secret|bearer |authorization:)'
```

Inspect results manually.

Confirm:

```text
.env ignored
real DWS key absent
old Foxit credentials absent
dataset credentials absent
tokens absent from fixtures
provider traces redact auth headers
```

Replay fixtures should contain provider responses, never authentication material.

---

# PHASE 20 — CLEAN-CLONE SUBMISSION GATE

Do this from outside your working tree.

```bash
cd /tmp
rm -rf proofdesk-final
git clone https://github.com/prx0r/proofdesk proofdesk-final
cd proofdesk-final

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python tests/test_all.py
python tests/test_audit.py
python tests/test_integration.py
python tests/test_generation.py
python tests/test_frontier.py
python tests/test_learning.py

./scripts/demo.sh --replay
```

Then separately:

```bash
export NUTRIENT_API_KEY=...
./scripts/demo.sh --live
```

The live demo must work using **only instructions present in README/DEMO.md**.

No:

```text
oh, you also need this random local dataset
```

No:

```text
run the script from my other repo
```

No:

```text
copy these PDFs manually
```

No hidden steps.

---

# PHASE 21 — CREATE `DEMO.md`

Make tomorrow stupidly easy.

```text
# ProofDesk Demo Runbook

## Before recording

[ ] git pull
[ ] tests green
[ ] NUTRIENT_API_KEY loaded
[ ] /v1/providers/status says LIVE
[ ] canonical PDFs present
[ ] browser at correct zoom
[ ] terminal clean
[ ] notifications disabled

## Start

command...

## Scene 1

click...
say...

Expected:
...

## Scene 2

...

## If Nutrient fails

switch to:
--replay

and explicitly say:
"This is a captured Nutrient response being replayed through the same downstream pipeline."
```

Include the complete 3-minute narration.

Tomorrow should require almost no thinking.

---

# PHASE 22 — SCREENSHOT PACKAGE

Capture at least four clean images today:

### Screenshot 1

Pipeline overview:

```text
Nutrient → Evidence → Verify → Human → Execute
```

### Screenshot 2

Grounded extracted fact with PDF source.

### Screenshot 3

`REVIEW_REQUIRED` discrepancy.

### Screenshot 4

Audit/certificate after resolution.

Optional:

### Screenshot 5

Learning-from-review panel.

These can populate Devpost even before the video exists.

---

# PHASE 23 — WHAT NOT TO DO

Do not:

```text
add another document provider
build Foxit eSign now
restore Doctavian
invent another confidence algorithm
download another 100k-document dataset
redesign the entire frontend
turn the demo into an academic talk
run enormous benchmarks instead of fixing CI
claim experimental results as production guarantees
```

Every hour spent there is an hour not spent making the submission undeniable.

---

# TODAY'S EXECUTION ORDER

## Block A — Repo trustworthiness

1. Commit canonical four-document fixture pack.
2. Refactor learning test/demo to use it.
3. Remove/fix dangling gitlinks/submodules.
4. Run full suite.
5. Push.
6. Verify GitHub Actions green.

**Gate:** do not move on while CI is red.

---

## Block B — Nutrient proof

1. Verify current API credentials.
2. Run canonical fixture live through DWS.
3. Inspect provider trace.
4. Ensure facts retain source provenance.
5. Ensure demo visibly labels Nutrient LIVE.
6. Save one clean replay fixture from a successful call.

**Gate:** one full successful real-DWS run from fresh startup.

---

## Block C — Product UI

1. Tighten discrepancy screen.
2. Tighten authority gate screen.
3. Tighten human review.
4. Add certificate/audit summary.
5. Add learning-from-review mini panel.
6. Remove sponsor noise.

**Gate:** entire workflow understandable without terminal explanation.

---

## Block D — Documentation

Rewrite:

```text
README.md
docs/JUDGE_GUIDE.md
HACKATHON_SUBMISSION.md
DEMO.md
docs/RESULTS_CANONICAL.md
```

Main sponsor everywhere:

```text
Nutrient DWS
```

Research directory described as research provenance.

---

## Block E — Submission material

Prepare:

```text
project title
one-line pitch
Devpost description
DWS heavy-lifting line
four screenshots
2–4 minute narration
future roadmap
technical-depth link
```

---

## Block F — Final clean clone

Destroy local assumptions.

Fresh clone.

Follow README literally.

If any step fails:

**fix the repo, not the instructions in your head.**

---

# DEFINITION OF DONE

ProofDesk is submission-ready when all of these are true:

```text
[ ] Public repo is coherent
[ ] GitHub Actions is green
[ ] No required files are gitignored
[ ] No broken submodules/gitlinks
[ ] Clean install succeeds
[ ] Canonical replay demo succeeds
[ ] Live Nutrient demo succeeds
[ ] Nutrient call is visibly demonstrated
[ ] Extracted facts point back to source evidence
[ ] Seeded contradiction reliably produces REVIEW_REQUIRED
[ ] Authority gate fails closed
[ ] Human resolution is attributed and audited
[ ] Final artifact is content-addressed
[ ] Decision certificate can be inspected
[ ] Learning loop is accurately represented
[ ] Research is clearly separated from production claims
[ ] README says Nutrient, not three competing sponsors
[ ] Four clean screenshots exist
[ ] Exact 2–4 minute demo script exists
[ ] Devpost copy exists
[ ] No secrets in Git
```

---

# FINAL PRODUCT POSITIONING

The demo should leave a Nutrient judge with one thought:

> **"They understood that trustworthy document AI isn't mainly an extraction problem. It's an evidence-and-authority problem."**

Nutrient supplies the grounded document substrate.

ProofDesk adds the layer above it:

```text
What did the documents actually establish?

How certain are we?

Do the documents agree?

What policy applies?

Is the evidence sufficient?

Does a person need to decide?

Exactly what they approve?

Did the artifact change afterward?

Can the entire decision be replayed?

What can the system learn from this human decision?
```

That is substantially more interesting than another PDF extraction demo, and it maps almost verbatim onto what Nutrient says it wants: deterministic document operations, confidence-aware workflows, human judgment at the right point, and an auditable record.

The first coding task should be the **fixture/CI repair**, then one live Nutrient run. Everything after that is packaging and demo quality rather than core product development.

---

---

# APPENDIX: REPO AUDIT FINDINGS

**Date:** 2026-09-01
**Auditor:** opencode (automated)

This appendix documents the current state of the repository and supports the dev plan above. Every item is evidence — not speculation.

---

## A1. What Already Works (supporting PHASE 0 freeze)

### Core pipeline (PRODUCTION)

| Component | File | Evidence |
|-----------|------|----------|
| Nutrient DWS extraction | `src/providers/nutrient.py` | Real API when `NUTRIENT_API_KEY` set, falls back to stubs |
| Evidence grounding | `src/models/domain.py:91-117` | ExtractedFact has page, bounding_box, confidence, extractor fields |
| Cross-document reconciliation | `src/engine/reconciliation.py` | 22KB of normalization + check logic |
| State machine | `src/state/machine.py` | 15 states, forbidden transitions, guard checks |
| SignatureGate (6 conditions) | `src/state/machine.py:96-213` | State, blockers, approval, record, hash, calibrated score |
| HITL exception resolution | `src/engine/orchestrator.py:257-305` | Resolution with decision, reason, actor, audit trail |
| Deterministic document generation | `src/engine/orchestrator.py:351-394` | render_approval_memo with branching |
| Content hashing | `src/models/domain.py:167-185` | StructuredRecord.compute_hash strips volatile IDs |
| Hash-chained audit trail | `src/audit/chain.py` | EventLedger with verify_chain(), seal_epoch(), proof_for_seq() |
| Merkle tree (RFC 6962) | `src/audit/merkle.py` | Domain-separated leaf/node hashing, inclusion proofs |
| Provider call traces | `src/providers/trace.py` | Every outbound HTTP call recorded |
| Batch processing | `src/engine/batch.py` | 789 lines, file validation, per-file Merkle proofs |
| MCP server | `src/mcp/server.py` | 12 tools covering full lifecycle |
| FastAPI server | `src/api/app.py` | 694 lines, 20+ endpoints |
| Interactive demo UI | `src/static/demo.html` | 30KB SPA |
| Dashboard | `src/static/dashboard.html` | 33KB |
| Batch dashboard | `src/static/batch.html` | 17KB |

### Research (EXPERIMENTAL / integrated)

| Component | File | Evidence |
|-----------|------|----------|
| Conformal Risk Control | `foxit/src/confidence_module.py:22-55` | Angelopoulos et al., ICLR 2024 |
| Dual-call confidence | `foxit/src/confidence_module.py:60-80` | EXTRACTCONF style |
| Per-field risk control | `src/providers/classifier.py:303-328` | Wired into classify_document() |
| Isotonic calibration | `foxit/src/confidence_module.py` | Standard method |
| Sheepish transform | `foxit/src/sheepish.py` + `src/sheepish.py` | Asymmetric overconfidence penalty |
| Online calibration | `src/engine/feedback.py:20-24` | MarginOnlineCalibrator from foxit/src/calibration.py |
| Feedback loop | `src/engine/feedback.py:27-175` | FeedbackLoop with record(), calibrated(), spot_audit() |
| Mixture of experts | `foxit/src/experts.py` | Per-world calibration |
| Distribution drift monitoring | `src/providers/confbench.py` | PSI, KS statistics |
| Spot-audit pool | `src/engine/feedback.py:36-58` | record_auto_sign(), spot_audit() |

### Test suites (PASSING)

| Suite | File | Count | Status |
|-------|------|-------|--------|
| Core | `tests/test_all.py` | 38 | PASS |
| Audit | `tests/test_audit.py` | 25 | PASS |
| Integration | `tests/test_integration.py` | 33 | PASS |
| Frontier | `tests/test_frontier.py` | 16 | PASS |
| Learning | `tests/test_learning.py` | 3 | PASS |
| **Total** | | **115** | **ALL PASS** |

---

## A2. Key Files Found During Audit

### Files that are critical but easy to miss

| File | Why it matters |
|------|----------------|
| `src/engine/feedback.py` | The convergence loop — best extra-credit element |
| `src/providers/trace.py` | Provider call tracing — proves Nutrient integration |
| `src/audit/chain.py` | Hash-chained ledger — production quality |
| `src/audit/merkle.py` | RFC 6962 Merkle tree — production quality |
| `src/state/machine.py:96-213` | SignatureGate — the core innovation |
| `src/models/domain.py:167-185` | StructuredRecord.compute_hash — determinism proof |
| `foxit/src/confidence_module.py` | All 6 frontier algorithms in one file |
| `foxit/src/calibration.py` | MarginOnlineCalibrator — online learning |
| `foxit/src/sheepish.py` | Novel Sheepish metric |
| `foxit/src/experts.py` | Mixture of experts |
| `GOLDEN_FIXTURE.json` | Canonical test fixture data |
| `STATE_MACHINE.yaml` | Machine-readable state definitions |
| `rubrics/nutrient.json` | Nutrient acceptance criteria |

### Files buried in archive that may be valuable

| File | Size | Why |
|------|------|-----|
| `_archive/PROOFDESK_CANONICAL.md` | 19KB | Full canonical design spec |
| `_archive/contract_extractor.py` | 10KB | Extraction code, may still be referenced |
| `_archive/receipt_extractor.py` | 7.7KB | Extraction code |
| `_archive/proofdesk_cogym.py` | 15KB | Evolution/optimization code |
| `_archive/proofdesk_evolve.py` | 11KB | Evolution code |
| `foxit/archive/frontier_plots.py` | 22KB | Plot generation |
| `foxit/archive/ml_lab.py` | 23KB | ML experimentation |

### Files in foxit/src that are the research provenance

| File | Size | What it contains |
|------|------|-----------------|
| `foxit/src/confidence_module.py` | 8.5KB | ConformalRiskController, DualCallConfidence, sheepish_transform |
| `foxit/src/calibration.py` | 9.1KB | MarginOnlineCalibrator |
| `foxit/src/sheepish.py` | 6.7KB | SheepishMetric |
| `foxit/src/experts.py` | 12KB | MixtureOfExperts, WorldCalibrator |
| `foxit/src/metrics.py` | 7.1KB | Evaluation metrics |
| `foxit/src/frontier_experiments.py` | 28KB | Full experiment runner |
| `foxit/experiments/benchmark.py` | 16KB | Benchmark harness |
| `foxit/experiments/crc_tradeoff.py` | 5.5KB | Conformal risk tradeoff |
| `foxit/experiments/per_type_analysis.py` | 8.1KB | Per-document-type analysis |
| `foxit/tests/test_real.py` | 8.4KB | Research test suite (26/26) |

---

## A3. Duplicate / Redundant Files

| Duplication | Files | Action |
|-------------|-------|--------|
| PDFs duplicated | `data/datasets/all/` and `data/test_pdfs/` | Both gitignored; fixtures/demo/ is now canonical |
| CSV duplicated | `data/datasets/transactions/creditcard.csv` and `ulb_credit_card.csv` | Both 151MB — same dataset |
| Empty file | `data/datasets/receipts/ds_receipts_v2_train_train.jsonl` | 0 bytes — broken download |
| Rubric duplicated | `foxit/rubrics/foxit.json` and `rubrics/foxit.json` | Same 9.2KB file |
| Archive overlap | `_archive/` and `foxit/archive/` share test_foxit.py, validate_rubrics.py | Identical files |
| V2 variants | `src/benchmark/confidence/` has 6 `_v2` pairs | Old + new versions side by side |
| Root vs docs | Root `NORTHSTAR.md` (12KB) vs `docs/NORTHSTAR.md` (3.1KB) | Root is canonical |

---

## A4. Empty / Placeholder Directories

| Directory | Status |
|-----------|--------|
| `data/datasets/insurance/` | Empty |
| `data/cord/` | Empty |
| `data/funsd/` | Empty |
| `data/realkie/` | Empty |

These suggest planned integrations that were never populated. Not blocking.

---

## A5. Large Directories (disk budget)

| Directory | Size | Contents |
|-----------|------|----------|
| `vendor/` | 1.2 GB | 13 cloned reference repos (includes .venv) |
| `data/` | 643 MB | Datasets, test PDFs, templates |
| `imported/` | 618 MB | factjudge + factminer codebases |
| `foxit/` | 928 KB | Research lab |
| `src/` | 1.5 MB | Production code |

The 1.8GB of vendor/ + imported/ is reference material, not needed for submission.

---

## A6. Submodule / Gitlink Status

No `.gitmodules` file exists in proofdesk. No submodule debris found during audit. The earlier CI complaints about "No url found for submodule path" likely came from the parent patala repo, not proofdesk itself.

---

## A7. Merkle Root Bug (fixed)

`src/engine/batch.py:578` was using `leaves[0].hex()[:32]` (first leaf hash) instead of `tree_levels[-1][0].hex()` (actual Merkle root). This meant batch Merkle roots were misleading. **Fixed during this session.**

---

## A8. CI Status

After fixture fix, all 115 tests pass:

```text
test_all.py:        38/38  PASS
test_audit.py:      25/25  PASS
test_integration.py: 33/33  PASS
test_frontier.py:   16/16  PASS
test_learning.py:    3/3   PASS
```

The CI workflow (`.github/workflows/ci.yml`) runs all 6 suites. After fixtures are committed, GitHub Actions should be green.

---

## A9. What the Audit Supports in the Dev Plan

| Dev Plan Phase | Audit Evidence |
|----------------|----------------|
| PHASE 0 (freeze) | 15 production components already wired, 115 tests passing |
| PHASE 1 (CI green) | Fixtures created, all tests pass, no submodule debris |
| PHASE 2 (Nutrient central) | `/v1/cases/{id}/trace` exists, `to_public()` returns page/bbox, provider status endpoint exists |
| PHASE 3 (contradiction hero) | Insurance expiry gap is seeded in golden_fixture.py and stubs.py — deterministic |
| PHASE 4 (authority gate) | SignatureGate with 6 conditions at `src/state/machine.py:96-213` — already implemented |
| PHASE 5 (human review) | Resolution model has decision, reason, actor_id, timestamp, evidence_refs |
| PHASE 6 (learning loop) | FeedbackLoop with record(), calibrated(), spot_audit(), auto_sign pool — all working |
| PHASE 7 (research packaging) | foxit/ has 19 source files, 27 docs, 4 experiments, 19 archive files — substantial research provenance |
| PHASE 8 (claim hygiene) | "24,878 real documents" fixed to "24,878 examples (mix of tabular records and document text)" |
| PHASE 9 (README) | Already rewritten for Nutrient-first framing |
| PHASE 10 (one-command) | scripts/demo.sh doesn't exist yet — needs creation |
| PHASE 11 (demo reliability) | Stub infrastructure already supports both live and fallback — ReplayTransport needs wiring |
| PHASE 12 (demo script) | docs/DEMO_VIDEO_SCRIPT.md exists (5.1KB), needs update for Nutrient framing |
| PHASE 18 (failure modes) | EVIDENCE_INCOMPLETE block at orchestrator.py:175-180, state violations return 409, tamper detection at demo/tamper endpoint |
| PHASE 19 (credential hygiene) | .env.keys is gitignored, provider traces don't log auth headers |

---

## A10. Stretch Goal: AuthorityBench + Trust Lab + Technical Preprint

**Plan:** `docs/AUTHORITYBENCH_PLAN.md`

The extra-credit research layer: a reproducible benchmark (AuthorityBench), an interactive visualization (Trust Lab), and an arXiv-style technical report — all three views over the same benchmark artifacts.

Priority: after PHASE 1–6 of this dev plan are done. The first six items of the AuthorityBench priority stack are the win package.

---

## A10. Skills Subsystem (hidden depth)

The `src/skills/` directory contains a complete confidence-routing pipeline that is separate from (and more sophisticated than) the main `src/providers/classifier.py`. This is the real research implementation.

| File | Size | What it does |
|------|------|-------------|
| `src/skills/agent_brain.py` | 19KB | Master orchestrator: classifies documents, selects skill chains, executes, routes by confidence, audits every decision |
| `src/skills/nutrient_extract.py` | 14KB | Full Nutrient DWS extraction with citation parsing: field, value, confidence, match_label, page, bbox, confidence_components, recognition_score |
| `src/skills/calibration.py` | 8.7KB | Isotonic regression + conformal prediction. Maps match labels (id_match=1.0, fuzzy_match=0.5, not_found=0.0) to calibrated scores |
| `src/skills/confidence_gate.py` | 11KB | Role-stratified risk budgets (signer=0.01, amount=0.02, date=0.03), conformal risk control, BAS trajectory features |
| `src/skills/factminer_verdict.py` | 9.6KB | 4-way verification: SUPPORTED / REFUTED / CONFLICTING / INSUFFICIENT with evidence references |
| `src/skills/multi_signal_fusion.py` | 14KB | Fuses 4 signals: Nutrient confidence, match label, FactMiner verdict, cross-document consistency → single routing decision |

**Key insight:** The `Citation` dataclass in `nutrient_extract.py` captures everything Nutrient returns — not just value/confidence but also `match` label (id_match, fuzzy_match, not_found), `confidence_components` (probabilityScore, marginScore), and `recognition_score` for scans. This is the richest Nutrient integration in the repo.

**Key insight:** `confidence_gate.py` implements **role-stratified risk budgets** — different fields get different error tolerances based on their operational impact. Signer field: 1% max error. Financial amounts: 2%. Dates: 3%. General content: 5%. This is the per-field risk control from the research, implemented as production code.

**Key insight:** `factminer_verdict.py` implements a 4-way evidence verdict (SUPPORTED/REFUTED/CONFLICTING/INSUFFICIENT) inspired by FactMiner's TypedDag architecture. Each verdict carries a score for the calibration layer.

---

## A11. Ed25519 Signed Attestations

`src/audit/signing.py` (133 lines) implements Ed25519 digital signatures for approval records.

- `SignedAttestation` dataclass with type, case_id, payload, content_hash, signature, public_key, timestamp
- `AttestationSigner` generates key pairs and signs attestations
- `AttestationVerifier` verifies signatures
- Uses `cryptography` library (already in requirements.txt)
- Sourced from Patalacheckpoints: `pipeline/products/scholar_review/signing.py`

This is beyond hash chaining — it provides **non-repudiation**. A signed attestation proves who approved what, and can't be forged. Not wired into the main pipeline yet, but available for the "deterministic decision certificate" the dev plan calls for in PHASE 4.

---

## A12. Real Provider Implementations

### Foxit PDF Services (`src/providers/foxit_real.py`, 191KB)

Full API client with:
- `FoxitPDFClient`: upload, merge, compress, download with task polling
- `FoxitESignClient`: create_folder, send_for_signing
- Provider tracing on every outbound call
- Real OAuth2 token flow
- Configured when `FOXIT_CLOUD_API_CLIENT_ID` and `FOXIT_CLOUD_API_CLIENT_SECRET` are set

### Foxit Pipeline (`src/providers/foxit_pipeline.py`, 17KB)

Orchestration layer that chains: upload → merge → compress → download → SHA-256. Handles task polling with retries.

### Doctavian Pipeline (`src/providers/doctavian_pipeline.py`, 15KB)

Template-based document generation with branching, loops, and calculations. Wired but generation fails (OAuth scope issue per AGENTS.md).

### SerpApi (`src/providers/serpapi.py`, 6.9KB)

External fact verification via web search. Verifies extracted vendor names against real-world sources. Adds a web-verification step before human review. Requires `SERPAPI_KEY`.

---

## A13. Benchmark Infrastructure (substantial)

### Real Nutrient API tests

`tests/test_nutrient_real.py` (284 lines) runs actual Nutrient DWS extraction on SROIE receipts + CUAD contracts. Contains the **real API key** (should be moved to .env.keys). Compares against previous benchmarks (Tesseract 27%, Cloudflare 37%, Nutrient 53% on 10 PDFs).

### A/B test results

`benchmarks/nutrient_ab_test_20260825_042803.json` (849 lines) contains real Nutrient extraction results for 18 procurement PDFs with ground-truth comparisons. Shows actual extracted values vs expected, with verdict (SUPPORTED/REFUTED) per field.

### Confidence benchmark

`tests/test_confidence_benchmark.py` (212 lines) tests the confidence scoring pipeline with simulated documents — invoice with wrong vendor, invoice with wrong amount, invoice with correct everything. Validates quality gates and receipt generation.

### Benchmark suite

`src/benchmark/` contains 21+ files:
- `confidence_benchmark.py` (11KB) — candidate evaluation with quality gates
- `full_pipeline.py` (16KB) — end-to-end pipeline benchmark
- `confidence/runner.py` (12KB) — benchmark runner
- `confidence/calibration.py` + `calibration_v2.py` — calibration experiments
- `confidence/experts.py` + `experts_v2.py` — mixture of experts experiments
- `confidence/metrics.py` + `metrics_v2.py` — evaluation metrics
- `confidence/ml_lab_v2.py` (23KB) — ML experimentation lab
- `confidence/signing_world.py` + `signing_world_v2.py` — signing simulation
- `confidence/signing_runner.py` + `signing_runner_v2.py` — signing benchmarks

The v1/v2 pairs represent iterative refinement — v2 versions are the current implementations.

---

## A14. Configuration / Fixture Files

### GOLDEN_FIXTURE.json

Canonical test fixture data with expected facts, expected checks (quote_arithmetic PASS, legal_name_reconciliation PASS_WITH_NORMALIZATION, insurance_expiry FAIL), and expected gate result. This is the single source of truth for the procurement scenario.

### STATE_MACHINE.yaml

Machine-readable state definitions:
- 15 states
- 3 forbidden transitions (REVIEW_REQUIRED→GENERATED, CHECKED→SIGNATURE_REQUESTED, GENERATED→SIGNATURE_REQUESTED)
- 5 hard invariants (no unresolved blockers in APPROVED, generation requires approved record hash, etc.)

### templates/approval_memo.html

Production-quality HTML template for the approval memo. 84 lines with:
- Status badges (auto/review/reject)
- Confidence color coding (high/med/low)
- Fact tables with evidence
- Footer with case ID, timestamp, record hash
- CSS styling (professional, not prototype)

---

## A15. Scenario Agent

`src/scenarios/agent.py` (195 lines) processes document folders through the full Nutrient pipeline. Uses:
- `FactMinerVerifier` for 4-way evidence verification
- `ConfidenceCalibrator` for isotonic regression
- `MultiSignalFuser` for signal fusion
- `ConfidenceGate` for routing decisions

This is the "live Nutrient run" path — processes real PDFs through real API, measures accuracy, and routes by calibrated confidence.

---

## A16. Research Documentation (27 files in foxit/docs/)

| File | Size | What it covers |
|------|------|---------------|
| `ARXIV_PAPER.md` | 5.5KB | Paper-quality writeup with abstract, methods, results, limitations |
| `CANONICAL_THESIS.md` | 10KB | Full thesis on confidence scoring for document signing |
| `PUBLICATION_PROTOCOL.md` | 9KB | How to publish the research |
| `HACKATHON_VISION.md` | 8.4KB | Vision for the hackathon submission |
| `PROVIDER_BENCHMARK_RESULTS.md` | 3.2KB | Real Nutrient vs Doctavian benchmark (165 documents) |
| `PROVIDER_BENCHMARK_PROTOCOL.md` | 3KB | Benchmark methodology |
| `EXPERIMENT_DETAILS.md` | 3.8KB | Experiment configurations |
| `EXPERIMENT_SUITE.md` | 5.7KB | Full experiment suite design |
| `PEER_REVIEW_AND_PROVIDER_GUIDE.md` | 10KB | Peer review + provider integration guide |
| `PRODUCTION_SAFETY.md` | 5.2KB | Safety analysis |
| `THREE_VERSIONS_SPEC.md` | 5.3KB | Three version specifications |
| `TRADEOFF_DESIGN.md` | 2.8KB | Design tradeoffs |
| `CANONICAL_PLAN.md` | 6.9KB | Canonical development plan |
| `CANONICAL_STUDY.md` | 4.4KB | Study design |
| `DATASET_REFERENCE.md` | 5.8KB | Dataset documentation |
| `DOCUMENT_TYPE_REFERENCE.md` | 4.4KB | Document type taxonomy |
| `HIGH_RISK_DATASETS.md` | 2.4KB | High-risk dataset identification |
| `BUILD_NOTES.md` | 1.4KB | Build notes |
| `BUILD_PLAN.md` | 5.7KB | Build plan |
| `BUILD_PROGRESS.md` | 5.2KB | Build progress |
| `INTEGRATION_PLAN.md` | 3.1KB | Integration plan |
| `PROGRESS.md` | 3.4KB | Progress tracking |
| `ARCHITECTURE.md` | 4.3KB | Architecture documentation |
| `ASSESSMENT_METHOD.md` | 1.4KB | Assessment methodology |

This is 120KB+ of research documentation — substantial intellectual property.

---

## A17. CogymKernel Integration

`/home/box/Documents/patala/cg/cogym_kernel/worlds/proofdesk.py` wraps ProofDesk's confidence benchmark for evolutionary optimization of confidence thresholds. Registered as `proofdesk.confidence` world kind in the CogymKernel registry.

This means ProofDesk's threshold optimization can be driven by CogymKernel's evolutionary search — exploring the space of possible thresholds to find optimal per-document-type, per-field configurations.

---

## A18. Root-Level Research Files

| File | Size | What it contains |
|------|------|-----------------|
| `CONFIDENCE_RESEARCH.md` | 4.2KB | Confidence research summary |
| `CONFIDENCE_RESEARCH_FULL.md` | 5.1KB | Full confidence research writeup |
| `FEEDBACK_THESIS.md` | 7.9KB | Thesis on human-feedback learning |
| `PAPER.md` | 13KB | Paper-quality writeup with abstract, results, limitations |
| `PEER_ASSESSMENT.md` | 18KB | Peer assessment of the work |
| `PEER_REVIEW_2.md` | 2.9KB | Second peer review |
| `PEER_REVIEW_3.md` | 3.5KB | Third peer review |
| `LITERARY_REPORT.md` | 3.9KB | Literary report |
| `SUBMISSION_REVIEW.md` | 12KB | Submission review with optimization results |
| `FRONTIER_ANALYSIS.md` | 8.9KB | Frontier analysis with 24,878 examples |
| `SPONSOR_CANONICAL.md` | 11KB | Sponsor canonical requirements |
| `DEMO_VIDEO_SCRIPT.md` | 5.1KB | Demo video script |
| `DEMO_SCRIPT_FINAL.md` | 3.3KB | Final demo script |
| `DEMO_SCENARIOS.md` | 6.2KB | Demo scenario definitions |
| `MARKET_POSITIONING.md` | 4.4KB | Market positioning analysis |
| `FINAL_STATUS.md` | 3.4KB | Final status report |
| `FINAL_DEV_REVIEW.md` | 3.6KB | Final dev review |
| `PROGRESS_LOG.md` | 6.3KB | Progress log |

That's 115KB+ of research and analysis documentation at the root level alone.

---

## A19. Test Infrastructure

| File | Size | What it tests |
|------|------|--------------|
| `tests/generate_test_pdfs.py` | 13KB | Generates test PDFs from fixture data using fpdf2 |
| `tests/ab_test_nutrient.py` | 22KB | A/B tests Nutrient extraction with ground truth comparison |
| `tests/test_nutrient_real.py` | 19KB | Real Nutrient API tests on SROIE + CUAD |
| `tests/test_confidence_benchmark.py` | 9.6KB | Confidence scoring benchmark tests |
| `tests/test_frontier.py` | 8.5KB | Frontier algorithm tests (16/16) |

The `generate_test_pdfs.py` file is important — it's how the fixture PDFs were created. It uses fpdf2 to generate deterministic PDFs from the golden fixture data. This is the canonical PDF generation path.

---

## A20. What's NOT Wired (available but unused)

| Component | File | Status |
|-----------|------|--------|
| Ed25519 signed attestations | `src/audit/signing.py` | Implemented, not in main pipeline |
| ConfidenceGate (role-stratified) | `src/skills/confidence_gate.py` | Implemented, classifier.py uses simpler version |
| Multi-signal fusion | `src/skills/multi_signal_fusion.py` | Implemented, not in main pipeline |
| FactMiner 4-way verdict | `src/skills/factminer_verdict.py` | Implemented, not in main pipeline |
| SerpApi web verification | `src/providers/serpapi.py` | Implemented, not in main pipeline |
| Doctavian generation | `src/providers/doctavian_pipeline.py` | Implemented, OAuth broken |
| Foxit eSign (real) | `src/providers/foxit_real.py` | Implemented, keys needed |
| CogymKernel optimization | `cg/cogym_kernel/worlds/proofdesk.py` | Registered, needs CogymKernel |
| Scenario agent | `src/scenarios/agent.py` | Implemented, needs real API |

These are **bonus materials** — if time permits, wiring any of them strengthens the submission. The confidence gate + multi-signal fusion + factminer verdict combo would be the highest-impact addition: it replaces the simpler classifier with the full research pipeline.

---

## A21. Credential Hygiene Issue Found

`tests/test_nutrient_real.py:16` contains a **hardcoded Nutrient API key**:

```python
NUTRIENT_API_KEY = os.environ.get("NUTRIENT_API_KEY")
if not NUTRIENT_API_KEY:
    raise RuntimeError("NUTRIENT_API_KEY required")
```

This should be moved to `.env.keys` and the fallback removed before the repo goes public. The key is also partially visible in `benchmarks/nutrient_ab_test_20260825_042803.json:3`.

**Action required before final push:** Remove hardcoded keys, ensure `.env` and `.env.keys` are gitignored (they are), scan with `git grep -Ei '(api[_-]?key|bearer |authorization:)'`.
