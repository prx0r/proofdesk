# ProofDesk — Recording Cheatsheet

**Site:** https://proofdesk-site.pages.dev
**Length:** 3:10–3:30
**Style:** screencast, live product, no slides

---

## BEFORE YOU RECORD

1. Open https://proofdesk-site.pages.dev in Chrome
2. Set browser zoom to 100%
3. Close all other tabs
4. Disable notifications
5. Run the demo once to warm up the API cache
6. Run it again — this is the take

---

## THE NARRATION (read from this)

### 0:00–0:15 — HOOK
**Screen:** Hero text "Extraction accuracy is not execution authority"
**Say:**
> "This is ProofDesk. Modern document AI is getting very good at reading PDFs. But in regulated work, the harder question is not 'did we extract this correctly?' It is 'do we have enough evidence to let an AI act?'"

**Action:** Slow scroll down to the contradiction section.

---

### 0:15–0:35 — THE DANGEROUS CASE
**Screen:** The two contradiction cards (coverage until 2027-10-01 vs expires 2027-08-31)
**Say:**
> "Here is the failure mode. The procurement request requires insurance coverage through October first. The certificate expires August thirty-first. Both fields can be extracted correctly, with high confidence, and yet together they describe a transaction that should not be approved."

> "That gap between extraction accuracy and action safety is what ProofDesk is built around."

**Action:** Optionally click the two source PDFs links so the judge sees real documents, then come back.

---

### 0:35–1:10 — RUN THE LIVE PIPELINE
**Screen:** Click "Run Live →" button. Watch the steps animate in.
**Say:**
> "I'll run the real workflow now. Nutrient DWS does the core document work here: it turns the source PDFs into structured evidence — values, confidence, source page and bounding-box grounding."

As provider trace appears:
> "You can see the Nutrient call in the provider trace. ProofDesk then normalizes those facts and runs deterministic cross-document assertions over the entire bundle."

As the failing assertion appears:
> "The important part is that this is not an extraction failure. It is a relationship failure between individually plausible facts."

---

### 1:10–1:38 — AUTHORITY GATE
**Screen:** Hold on the red BLOCKED verdict.
**Say:**
> "Now we reach the authority boundary. A confidence score never becomes execution authority by itself."

> "The server-side gate checks the pipeline state, unresolved blockers, explicit human approval, the structured record, artifact integrity, and the calibrated threshold. Right now the blocker is unresolved, there is no human approval, and no approved record exists — so the agent cannot proceed."

**PAUSE half a second on the red result.**

> "High confidence. Still blocked."

**That's the money line. Don't rush it.**

---

### 1:38–2:10 — HUMAN REVIEW → ARTIFACT
**Screen:** Click "resolve exception →"
**Say:**
> "A human now reviews the exact evidence that caused the exception — not the entire document bundle. In this case the renewal is confirmed as in progress, so the reviewer conditionally accepts the exception."

As approval/generation runs:
> "ProofDesk re-evaluates the case, creates a structured approved record, generates the artifact, and binds the result to its content hashes."

When receipt appears:
> "Every transition is recorded in the audit trail, and the resulting record and artifact are tamper-evident."

---

### 2:10–2:38 — RESEARCH
**Screen:** Scroll to Research section. Show the graphs first.
**Say:**
> "We also did not want the authority threshold to be a magic number. Behind the product is a research program around what I call the evidence-to-authority gap: when should an automated system act, abstain, or escalate?"

> "The benchmark work covers calibrated abstention, per-field risk budgets, online human-feedback calibration, risk-versus-coverage analysis, and real Nutrient extraction runs across multiple document types."

If 13-PDF results visible:
> "We also tested the Nutrient extraction path across thirteen real PDFs spanning procurement, KYC, invoices, trade, mortgage and medical documents."

**Don't recite every algorithm.**

---

### 2:38–2:58 — LEARNING FROM HUMANS
**Screen:** Show convergence/feedback area.
**Say:**
> "Human review is not just a fallback. Each intervention becomes calibration data. Over time the system learns which fields and situations this organization can safely automate, while continuing to spot-audit automatic decisions."

---

### 2:58–3:20 — CLOSE
**Screen:** Scroll back to the pipeline graphic or hero.
**Say:**
> "The product primitive is simple: evidence, policy, authority."

> "Nutrient gives agents trustworthy, source-grounded document evidence. ProofDesk determines when that evidence is strong enough to act — and when the only correct action is to stop and ask a person."

> "Today the demo is procurement. The same authority layer applies to insurance, contracts, trade, lending, compliance and other regulated document workflows."

**End immediately. No 'thanks for watching'.**

---

## KEY RULES

- Say **"Nutrient DWS"** at least twice
- The two memorable sentences:
  - **"Extraction accuracy is not execution authority."**
  - **"High confidence. Still blocked."**
- Don't lead with algorithms or test counts
- Show sponsor tech (Nutrient) doing extraction BEFORE explaining research
- End immediately after the close line
