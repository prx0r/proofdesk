# Peer assessment: ProofDesk for API + Cloud + AI Hackathon 2026

The core idea is strong enough to win a sponsor track. The current submission is not yet packaged strongly enough to make that obvious.

The best version of ProofDesk is **not** "a sophisticated confidence research project for PDFs." It is:

> **ProofDesk is an authority layer for document agents: AI can extract, prepare, merge, and generate documents, but irreversible actions remain blocked until the evidence, human approval, and exact artifact all agree.**

That story maps unusually well onto all three sponsors. Foxit explicitly frames its MCP tools as reversible document work while eSign is a separate irreversible handoff; Nutrient emphasizes deterministic, auditable document processing with confidence and human review; Doctavian wants its API to actually generate documents using conditional templates.

The hackathon itself judges **Progress, Concept, and Feasibility**. Your Concept score is already excellent. The main risks are Progress looking less real than it actually is because of contradictory documentation, and Feasibility getting undermined by integration shortcuts and prototype infrastructure.

---

## 1. The first thing I would fix: your project currently tells three different stories

The root README calls it **Sheepdog**. `HACKATHON_SUBMISSION.md` calls it **ProofDesk**. The Foxit submission package calls it **Sheepish**.

Kill this immediately.

Use:

**Product:** ProofDesk
**Core component:** SignatureGate
**Research/calibration technique:** Sheepish calibration, if you still want that name.

The repo currently also contains conflicting claims about sponsor status. Your README says:

* Nutrient: real
* Foxit PDF: real
* Foxit eSign: simulated
* Doctavian: API reachable but generation failing

Meanwhile the hackathon submission copy talks as though Foxit eSign is already an end-to-end real integration. Your North Star document is substantially more careful and admits that Doctavian cloud rendering and signature sending remain incomplete.

A judge will forgive an incomplete API integration much more readily than a submission whose claims appear inconsistent.

Create exactly one canonical matrix:

| Capability                          | Provider                | Status shown to judge     |
| ----------------------------------- | ----------------------- | ------------------------- |
| Evidence extraction                 | Nutrient DWS            | **LIVE**                  |
| Source page/bounding box/confidence | Nutrient DWS            | **LIVE**                  |
| Risk/authority decision             | ProofDesk               | **LIVE**                  |
| Conditional memo generation         | Doctavian               | **LIVE** once fixed       |
| PDF merge                           | Foxit MCP               | **LIVE**                  |
| PDF compression                     | Foxit MCP               | **LIVE**                  |
| Signature authorization             | ProofDesk SignatureGate | **LIVE**                  |
| Signing request                     | Foxit eSign             | **LIVE** once fixed       |
| Human signature                     | Foxit eSign             | **LIVE — show it happen** |
| Hash/Merkle audit                   | ProofDesk               | **LIVE**                  |

Do not use "sort of live," silent fallback, or simulated results in the prize demo.

---

## 2. Foxit judge assessment

### Current simulated score: **6.5–7/10**
### Potential after fixes: **9+/10**

This is probably your **highest-upside track** because the conceptual fit is so precise.

Foxit's challenge specifically revolves around an agent taking a plain-language instruction, using Foxit's MCP tools for document work, then handing the result into eSign, where a **real human must actually sign**. Foxit deliberately leaves signing outside the MCP tool catalog.

ProofDesk has a very good answer to the architectural question hidden inside that challenge:

> "Why shouldn't an agent with document tools automatically have signature authority?"

Your answer is **because tool capability is not authority**.

That is considerably more interesting than simply wiring `pdf_merge -> eSign`.

### What I would like as a Foxit judge

I want to see this happen:

**Agent:** "Prepare this $42,500 vendor agreement and send it to the CFO."

Then the agent autonomously calls Foxit MCP for everything it is allowed to do.

Then it attempts the irreversible operation.

Then:

**SIGNATURE DENIED — INSURANCE EVIDENCE EXPIRED**

That is your first wow moment.

Human checks the evidence, updates/approves it.

Agent retries.

**SIGNATURE AUTHORIZED**

Foxit eSign sends the actual signing request.

A real human signs it.

That is an extremely clean challenge narrative.

### Critical Foxit implementation problems

**Problem #1: you're claiming MCP while a major path uses direct REST**

Your `foxit_pipeline.py` describes `FoxitPDFClient` as an HTTP client for "MCP-equivalent" functionality. That is not the same thing as actually exercising the Foxit MCP server.

For this track, don't make the judge infer equivalence. **Actually invoke the official MCP server in the demonstrated agent path.**

The direct REST adapter can remain in the repo as an alternate backend, but your challenge path should be:

```
Agent
  ↓ MCP
Foxit PDF tools
  ↓ resulting artifact
ProofDesk SignatureGate
  ↓ if ALLOW
Foxit eSign REST
  ↓
Human signer
```

**Problem #2: your merge path doesn't actually merge the memo**

In `foxit_pipeline.py`, when only one document ID is passed to `merge`, the implementation duplicates the document ID so Foxit receives two inputs. Fix the pipeline to explicitly create/upload two different artifacts.

**Problem #3: compression is chained to the wrong artifact**

The pipeline compresses the original uploaded `doc_id` rather than consuming the merged operation's result document ID.

**Problem #4: eSign code appears aligned to an older API path**

Align the code to the current API reference supplied for the event and write an integration test against it.

**Problem #5: fail closed**

The current Foxit pipeline catches merge/compress errors and continues. For ProofDesk that is philosophically backwards. Any error in artifact production must become `DOCUMENT_PREPARATION_FAILED`. The signature path should literally be unreachable.

---

## 3. Nutrient judge assessment

### Current simulated score: **8.5/10**
### Potential: **9.3–9.6/10**

This is currently your **most prize-ready integration**.

### The strongest Nutrient line

Don't say: "We use Nutrient to extract PDFs."

Say: **"Nutrient is ProofDesk's evidence sensor. Every value entering a legal decision retains its source page, coordinates, and extraction confidence, so the human can inspect the exact evidence that caused an agent to abstain."**

### Nutrient fix #1: never convert missing evidence into 90% confidence

Your extraction mapping does roughly this when citation metadata is absent:

```python
confidence = cite.get("confidence", 0.9) if cite else 0.9
```

The principle should be: **absence of confidence is absence of evidence, not evidence of confidence.**

### Nutrient fix #2: your parse path appears to ignore real PDF bytes

`extract_from_document()` correctly prefers `document.raw_bytes`. But `parse_document()` uses `document.raw_text.encode(...)`. Use the same source-byte helper in both methods.

### The giant Nutrient upgrade: put the source evidence on screen

Your review screen should show extracted facts alongside the source PDF with bounding box highlighting. Clicking a field should jump directly to the page/bounding box Nutrient returned.

---

## 4. Doctavian judge assessment

### Current simulated score: **5.5–6/10**
### Potential: **9/10**

This is your weakest track **today**, but not because the use case is weak.

### Make Doctavian visually indispensable

Build one demo record that changes three template branches. One template. Three risk states. Real Doctavian generation.

### Doctavian fallback needs to stop hiding failure

Return explicit provenance:

```json
{
  "provider": "doctavian",
  "mode": "live",
  "status": "failed",
  "error_code": "DELIVERY_PATH_RESOLUTION_FAILED",
  "fallback_used": true
}
```

---

## 5. Credential hygiene

Assume any credential ever committed publicly is compromised. **Rotate it. Remove the value from the current tree. Purge it from Git history if it was sensitive.**

---

## 6. Benchmark story

Do **not** put twelve metrics in the pitch. Use three:

| Question                                                   | Metric                                        |
| ---------------------------------------------------------- | --------------------------------------------- |
| Does the evidence pipeline work on real documents?         | Real API benchmark, N=___                     |
| Does calibrated abstention reduce bad automatic decisions? | FPR / false-sign rate at fixed coverage       |
| Is the audit mechanism valid?                              | 100% replay/hash verification across ___ runs |

---

## 7. Your actual application is better than the documentation makes it look

The API has genuinely useful machinery: arbitrary PDF upload, run pipeline, inspect extracted facts, inspect assertions, human resolution, approval, generation, PDF preparation, signature authorization, audit events, SignatureGate inspection, receipt generation, provider HTTP trace, Merkle inclusion proof, batch processing and resolution.

Put a "LIVE PROVIDER TRACE" drawer directly on the dashboard. That's how you eliminate "is this mocked?" from the judge's mind.

---

## 8. The demo I would build

### 0:00–0:15 — The premise
Show one agent command: "Prepare the Northstar vendor agreement for $42,500 and send it to our CFO for signature."

### 0:15–0:40 — Nutrient does the evidence work
Show extraction with source grounding. Click a field, viewer jumps to the highlighted source.

### 0:40–0:55 — The first wow moment
Agent attempts to proceed. BLOCKED — UNRESOLVED_EVIDENCE. No Foxit eSign call in provider trace.

### 0:55–1:20 — Human resolves evidence
Human opens source citation and approves updated certificate.

### 1:20–1:45 — Doctavian visibly transforms the record
Show before/after of conditional template rendering.

### 1:45–2:10 — Foxit MCP performs reversible work
Show tool trace: upload, merge, compress. Banner: REVERSIBLE WORK — AGENT AUTHORIZED.

### 2:10–2:35 — Gate + real signing
SignatureGate checks pass. Then signing request sent.

### 2:35–2:55 — Second wow moment: tamper with the packet
Change one field. DENY — ARTIFACT_HASH_MISMATCH.

### 2:55–3:10 — Finish with provenance
Zoom out to final timeline. Last line: "AI does the reversible work. Evidence and people control the irreversible."

---

## 9. Judge-specific track framing

| Judge         | What to tell them                                        | What to show                                                  |
| ------------- | -------------------------------------------------------- | ------------------------------------------------------------- |
| **Foxit**     | "MCP capability does not equal signature authority."     | MCP calls → blocked sign → approval → real eSign → human signature |
| **Nutrient**  | "Every business decision is anchored to source evidence."| Extraction → confidence → page/bbox → human reviews the exact source |
| **Doctavian** | "The approved machine record becomes the actual legal document." | Same template dynamically changes clauses/loops/status from live payload |

These aren't three separate products. They are three stages of the **same transaction**.

---

## 10. Repo surgery before submission

Prioritized:

1. Rotate and remove exposed credentials.
2. Get Doctavian generation returning an actual cloud-generated document.
3. Replace the Foxit "MCP-equivalent" demo path with the actual Foxit MCP server.
4. Fix merge chaining: real memo + evidence → merged result ID → compressed result ID.
5. Get current Foxit eSign API working and have a human actually sign the demo document.
6. Make all provider failures fail closed before signature.
7. Fix Nutrient's missing-confidence `0.9` default and the `raw_bytes` parse path.
8. Embed Nutrient Viewer/source highlighting into the review step.
9. Unify ProofDesk naming and create one canonical integration/status matrix.
10. Replace the dozens of headline metrics with three defensible benchmark results.
11. Add `.env.example`, root `LICENSE`, dependency lock, and CI.
12. Move experimental/research clutter below the judge path rather than deleting the work.

---

## 11. How I would restructure the repository

```
proofdesk/
├── README.md
├── LICENSE
├── .env.example
├── Makefile
├── uv.lock / requirements.lock
├── src/
├── tests/
├── demo/
│   ├── README.md
│   ├── run_live.py
│   ├── sample_docs/
│   └── expected/
├── docs/
│   ├── JUDGE_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── INTEGRATIONS.md
│   ├── BENCHMARKS.md
│   ├── SECURITY.md
│   └── RESEARCH.md
└── artifacts/
    └── example_run/
        ├── provider_trace.redacted.json
        ├── approval_memo.pdf
        ├── final_packet.pdf
        └── audit_receipt.json
```

---

## 12. JUDGE_GUIDE.md

```text
WHAT TO RUN
make demo-live

WHAT TO WATCH
1. Nutrient extracts grounded evidence.
2. ProofDesk blocks an unsafe signature.
3. Human resolves the exception.
4. Doctavian generates the approval memo.
5. Foxit MCP prepares the packet.
6. ProofDesk verifies the exact artifact.
7. Foxit eSign sends it to the human signer.
8. Audit trail proves every transition.

WHERE EACH SPONSOR DOES REAL WORK

Nutrient
POST /extraction/extract
Produces values + confidence + page/bbox.

Doctavian
POST /documents/document/generate
Produces the branch-aware approval memorandum.

Foxit
MCP: pdf_merge + pdf_compress
eSign REST: create/send signing packet.
```

---

## 13. Canonical Devpost positioning

# ProofDesk — Evidence-Gated Execution for Document Agents

**AI can prepare the document. ProofDesk decides whether the evidence justifies executing it.**

Modern agents can extract data, generate agreements, merge PDFs, and initiate business workflows. The missing primitive is authority: the ability to distinguish reversible document work from an irreversible legal commitment.

ProofDesk inserts a server-side SignatureGate between those two worlds.

## Sponsor integrations

**Nutrient DWS — Evidence layer**
Nutrient performs the document extraction that drives the workflow. ProofDesk preserves the extracted values together with confidence, source page, and coordinates so uncertain decisions can be escalated to a human against the original evidence.

**Doctavian — Document generation layer**
Doctavian transforms the approved structured record into the final approval memorandum. One reusable template branches on risk state, loops over unresolved conditions, and renders the specific obligations that apply to each case.

**Foxit — Execution layer**
Foxit MCP performs reversible PDF operations on the final evidence packet. ProofDesk then enforces its SignatureGate before directly invoking Foxit eSign. A real human remains the final signer.

## The key idea

**Tool access is not authority.**

An agent may be allowed to prepare a document without being allowed to create a legal commitment from it.

ProofDesk makes that boundary explicit, deterministic, inspectable, and auditable.

**AI does the reversible work. Evidence and people control the irreversible.**

---

## 14. The three sponsor one-liners

**Foxit:** "Foxit MCP performs ProofDesk's reversible PDF work; a server-side SignatureGate then prevents Foxit eSign from being invoked until the evidence, human approval, signer, and exact artifact all pass."

**Nutrient:** "Nutrient DWS is ProofDesk's evidence layer: extracted values retain confidence and source location, and those signals determine what may proceed automatically versus what a human must inspect."

**Doctavian:** "Doctavian turns ProofDesk's approved structured record into the legal artifact itself, using one dynamic template to branch risk language and repeat case-specific conditions before signature."

---

## 15. What I would cut from the video

Do **not** spend precious demo time teaching isotonic regression, conformal prediction theory, Mixture of Experts, RFC 6962, every benchmark, all five confidence algorithms, or projected convergence.

The product demo should be understandable to someone with no statistics background:

**bad evidence → agent cannot sign**
**human resolves evidence → exact approved artifact can be sent for signature**
**tamper with artifact → blocked again**

Then, when a technical judge opens the repo and sees calibration, audit proofs, benchmarks, feedback loops, and replayability underneath it, the depth becomes a bonus rather than cognitive overhead.

---

## My ranking of what matters before September 3

**1. Foxit eSign actually completed by a human.**
**2. Doctavian real output.**
**3. One visual Nutrient evidence-review interaction.**
**4. Fix the Foxit artifact chain.**
**5. Canonicalize the repo and claims.**

If those five happen, I would stop adding features.

The important thing is that **you already have the difficult idea and most of the difficult infrastructure**. The remaining work is chiefly converting it from a research-heavy prototype with several integration paths into one indisputable transaction that a judge can watch succeed from prompt → evidence → block → human review → generated document → prepared packet → actual signature → audit receipt.
