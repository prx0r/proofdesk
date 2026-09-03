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

## NUTRIENT — [scroll to sponsor section]

Nutrient DWS is the extraction layer. Without it, ProofDesk has no facts to cross-check.

Nutrient gives us value plus confidence plus page-level grounding. That's what makes cross-document verification possible — we know exactly where each fact came from in the source document.

---

## DEMO — [click "Try the Live Demo" → /demo → click "Run Live Case"]

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

Nutrient turns PDFs into grounded evidence. ProofDesk turns grounded evidence into accountable authority.

*[End — pause 3 seconds]*
