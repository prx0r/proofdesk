# ProofDesk Demo Script v2 — "The Certificate" (3:00)

**Framing:** not "pipeline with human in the loop" — *statistically-certified authority gating*.
Every beat below is verified runnable. Nothing here depends on vendor keys.

---

## 0:00–0:15 — Cold open

**Screen:** terminal, blank.

> "AI agents can read documents. The unsolved question is which of their answers you're allowed to *act on*. ProofDesk answers it with a statistical certificate — per field — and renders that certificate into the signed document itself."

## 0:15–0:45 — Extraction as evidence, not data

Run `python3 demo_folder.py`. **Screen:** sections 1–2.

> "Four procurement PDFs. At ingest, each document is SHA-256 hashed into the audit ledger — from this moment, we can prove *which bytes* every later decision came from."

**Screen:** section 3 output.

> "Nutrient DWS extracts 14 fields. Note what each fact carries: a confidence score and a source page. These aren't outputs — they're evidence. They will never be edited, only cited."

```
[95%] insurance.expiry_date: 2027-08-31 (page 1)
```

*(+15s optional)* Web UI: click a fact → Nutrient Viewer opens the actual source PDF at that page.

## 0:45–1:20 — The certificate fires

**Screen:** sections 4–5.

> "Now the gate. Not vibes, not a threshold somebody picked — risk budgets. Signer fields carry a 1% error budget. Amounts: 2%. Dates: 3%. A field whose extraction exceeds its budget cannot cross into an irreversible action."

Checks print:

```
[PASS] quote.total == platform_price + support_price
[FAIL] insurance.expiry_date >= required_coverage_until
        2027-08-31 < 2027-10-01 — 31 days gap
```

> "Quote arithmetic passes. Insurance coverage fails its check — a 31-day gap. Now watch the important part:"

Section 5:

> "**Attempt to sign anyway. Denied — five named reasons.** The agent doesn't get to override this. The gate lives on the server, outside the agent's reach. That's the difference between a workflow suggestion and an authority boundary."

## 1:20–1:50 — Human judgment enters the chain

**Screen:** section 6 (+ web review queue if recorded).

> "The case routes to a human. They see the failing field, open the source page in the viewer, and decide: conditional accept — renewed insurance before the current policy lapses. That decision is itself hash-chained. The original extraction is never touched. Judgment gets recorded; evidence stays immutable."

## 1:50–2:25 — The certificate becomes the document

**Screen:** sections 7–8, scroll the generated memo.

> "Here's the part nobody else shows. The approved record feeds document generation through one branching template. The risk band picks the shape — this one says CONDITIONALLY APPROVED. The failed check renders as a numbered legal obligation with a deadline:"

```
Status: CONDITIONALLY APPROVED
§1. FAILED: insurance.expiry_date >= required_coverage_until
    REQUIRED BEFORE: contract start (2026-10-01)
```

> "A different record in — same template — produces a correctly-shaped CLEARED or ESCALATED document. **The document is the human-legible rendering of a conformal decision.** No LLM free-writes any of it."

## 2:25–2:45 — Irreversible requires everything

**Screen:** sections 9–11 + gate reasons from earlier.

> "Foxit PDF Services prepares the packet — reversible work, the agent does freely. Signing is different. The SignatureGate re-verifies: state, zero unresolved blockers, human approval present, record-to-artifact hash binding. Only then does the envelope go to a person. The agent prepares; only humans commit."

## 2:45–3:00 — Replay + convergence close

**Screen:** terminal, run the pipeline a second time.

> "One more property, and it's the killer: **determinism**. Same documents in — identical record fingerprint out. Watch:"

```
run 1 record: sha256:818b41ece99f80fb
run 2 record: sha256:818b41ece99f80fb   ← identical
same gate denial, same reasons
```

> "A regulator can replay this case and demand the exact same verdict. That's what auditable means."

Then the feedback stats:

> "And it gets smarter safely. Every human resolution is a label captured in the ledger — accept or reject — and the signing policy calibrates on it. Early cases defer more; as the human's judgments accumulate, auto-approval coverage rises while the false-sign budget stays fixed. **The system converges toward autonomy at exactly the rate the humans justify.**"

Final line over end card:

> **"Deterministic verdicts, certified risk budgets, human labels converging to safe autonomy — every hop hash-chained from pixel to signature."**

---

## Production notes
- Pre-record each section separately; cut on any live-API hiccup.
- If asked "is the conformal threshold fitted?": answer honestly — mechanism is implemented and tested in the lab (`foxit/src/calibration.py`); production floors are fixed operating points until the calibration corpus lands. It's on the roadmap in NORTHSTAR.md §gaps.
- Sponsor one-liners for submission text: `docs/SPONSOR_CANONICAL.md` §"Our submission line".
