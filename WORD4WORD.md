# ProofDesk — WORD4WORD SCRIPT

**How to read:** Bold text = what you say out loud. [Brackets] = what you do on screen.
Speak slowly. Pause at each section break. Let the demo breathe.

---

## OPENING — [hero visible]

Welcome to ProofDesk.

ProofDesk explores the gap between document understanding and document authority.

This matters because AI agents are moving from reading documents to approving purchases, releasing payments, and executing contracts. And the problem is: extraction accuracy is not execution authority.

Seventy percent of document processing errors that cause financial loss come from correct extractions applied to incorrect contexts. The AI read the quote perfectly. It just never checked whether the insurance covered the contract period.

---

## PROBLEM — [scroll to "The Problem"]

Two documents sit on the desk. A vendor quote for forty-two thousand five hundred dollars. An insurance certificate for the same vendor.

Both extracted with ninety-five percent confidence by Nutrient DWS. Each document, read alone, is perfectly fine.

But together, they describe an unsafe transaction — the insurance expires thirty-one days before the required coverage period ends.

Neither document is wrong. Together they describe something that should never be approved.

---

## SOLUTION — [scroll to "How It Works"]

Here's how ProofDesk solves this.

Nutrient DWS extracts the facts — value, confidence, page, bounding box. Every fact grounded in source evidence.

Cross-document verification runs. Finds the contradiction. SignatureGate blocks — six conditions enforced server-side before any signature can be requested.

A human examines the exact evidence. Conditionally approves. The system generates an approval memo with a content-addressed audit trail.

The audit trail is hash-chained with RFC 6962 Merkle proofs. Every fact traces back to the Nutrient extraction. No step can be skipped.

---

## RESEARCH — [scroll to "The Research"]

Behind the authority gate is a research program in calibrated confidence. Not ad-hoc thresholds — published algorithms applied to document automation.

We studied when automation should stop.

Five algorithms. Conformal-style risk calibration gives you a bounded false authorization rate — you pick the risk, the math certifies the threshold. The sheepish transform penalizes overconfidence more than caution — because a wrong signature is worse than a deferred review. Per-field risk budgets mean a wrong signer name gets a tighter threshold than wrong metadata. Online calibration means human decisions improve future thresholds — the system learns. And dual-call verification asks a second extraction to confirm the first.

The convergence loop is the key insight. Each time a human resolves an exception, ProofDesk captures the confidence level, the accept or reject decision, and the field involved. That becomes calibration data. The online calibrator updates. Future decisions improve. Human review falls over time while measured false-authorization risk stays bounded.

We validated this on five datasets — transaction records, contract text, invoices, contract clauses. At a one percent false-sign rate, the system achieves fifty-nine point eight percent auto-sign coverage. Two point seven times over baseline logistic regression.

---

## MOAT — [scroll to "The Moat"]

What's hard to replicate.

Nutrient source grounding — every fact carries value, confidence, page provenance, and bounding box. Not just text extraction. Evidence with location.

Cross-document verification — deterministic checks catch contradictions that per-document extraction misses. The conflict is between documents, not within them.

Calibrated authority gate — six conditions enforced server-side. Thresholds calibrated from research, not hand-tuned. The agent cannot negotiate.

Human-feedback convergence — human decisions become calibration data. The system learns where this organization can safely automate. Competitors can copy the UI. They can't copy three years of calibrated authority decisions.

And tamper-evident execution — hash-chained audit trail with Merkle proofs. Every decision replayable. Content-addressed artifacts. Change one byte and the hash changes.

---

## NUTRIENT — [scroll to sponsor section]

Nutrient DWS is the extraction layer. Without it, ProofDesk has no facts to cross-check.

Nutrient gives us value plus confidence plus page-level grounding. That's what makes cross-document verification possible — we know exactly where each fact came from in the source document.

Nutrient performs the core document extraction and source grounding that turns uploaded PDFs into confidence-aware evidence. ProofDesk uses that evidence to determine whether an automated action may proceed or must defer to a human.

---

## RESULTS — [scroll to "Results"]

What we measured.

One hundred and fifteen tests passing. Thirteen PDF fixtures tested. Twelve document types supported. Six authority conditions enforced.

Fifteen extracted fields per document bundle. Six cross-document verification checks. A thirty-one day coverage gap detected. Zero unsafe actions.

Ninety-five percent accuracy on CUAD contracts. Five percent false positive rate. Eighty percent correctly deferred to human review. Ten percent auto-signed with high confidence.

---

## DEMO — [click "Run Live Demo" → /demo → click "Run Live Case"]

Let me show you live.

*[Four PDFs load — narration starts]*

Four procurement PDFs. Nutrient DWS begins extracting from each one.

*[Watch extraction steps appear one by one]*

Procurement request: vendor name, spend amount, contract dates. Ninety-eight percent confidence. Three hundred and eighty milliseconds.

Vendor quote: platform price, support price, total. Ninety-seven percent.

Insurance certificate: expiry date, policy type. Ninety-nine percent.

Security questionnaire: data retention, subprocessors, encryption. All high.

*[Cross-document check runs]*

Now ProofDesk cross-checks. And there it is.

Required coverage until: October twenty-twenty-seven. Insurance expiry: August twenty-twenty-seven. Insurance expires thirty-one days before coverage ends.

Both extractions correct. High confidence. No extraction error. Jointly unsafe.

*[SignatureGate blocks]*

SignatureGate checks six conditions. Execution blocked. No human approval. No structured record. No artifact. The agent cannot proceed.

*[Human review appears]*

This is the human-in-the-loop. I examine the exact evidence — which document, which field, what confidence.

I choose: Conditional Accept — vendor must provide renewed certificate before execution.

*[Click Conditional Accept]*

Record sealed. Approval memo generated. Audit trail created — five events, hash chain verified.

---

## CLOSE — [stay on audit trail]

Nutrient reads the documents. ProofDesk decides if it's safe to sign.

The obvious customers: procurement platforms, insurance processors, legal teams, lending institutions. Every document-heavy workflow where a wrong decision has financial consequences.

Here's the question I want you to think about: would you rather have an AI agent that extracts correctly and acts blindly, or one that extracts correctly and knows when to stop?

The answer is obvious. And that's exactly why this matters.

An agent that can read a document is useful. An agent that knows whether it has enough evidence to act on that document is trustworthy. ProofDesk makes the difference between extraction and authority.

Nutrient turns PDFs into grounded evidence. ProofDesk turns grounded evidence into accountable authority. One document at a time. Every fact traceable. Every decision auditable. Every signature justified.

*[End — pause 3 seconds]*
