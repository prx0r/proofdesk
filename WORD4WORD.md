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

Every step is recorded in a tamper-evident audit trail. Hash-chained events. Change one fact and the chain breaks. Every decision is replayable.

---

## RESEARCH — [scroll to "The Research"]

We studied when automation should stop.

The core question: how does the system know when it's safe to auto-sign versus when a human needs to look? Five algorithms answer that.

First, risk calibration. You pick a false-sign rate — say one percent. The math certifies the threshold that keeps you there. Not a guess. A guarantee.

Second, asymmetric penalty. Signing when you shouldn't is worse than deferring when you didn't need to. So the system penalizes overconfidence more than caution.

Third, per-field risk budgets. A wrong signer name is worse than wrong date metadata. Each field type gets its own threshold.

Fourth, the system learns from human decisions. Every time a human reviews a case, that feedback improves the next decision. The review rate drops over time. The error rate stays bounded.

Fifth, double-check extraction. Ask the document parser twice — once guided by fields, once guided by the full document. If they agree, confidence goes up.

We validated this across five datasets. At a one percent error rate, the system auto-signs sixty percent of documents without human review. That's two point seven times better than a standard logistic regression baseline.

---

## MOAT — [scroll to "The Moat"]

What's hard to replicate.

Every fact knows where it came from — not just what it says, but which page, which bounding box. That's Nutrient's source grounding.

The contradictions are between documents, not within them. A per-document system misses this entirely.

The gate is server-side. Six conditions. The agent cannot negotiate, cannot override, cannot route around it.

And the system gets better with every human review. That calibration data compounds. A competitor can copy the UI. They can't copy three years of learned authority decisions.

---

## NUTRIENT — [scroll to sponsor section]

Nutrient DWS is the extraction layer. Without it, ProofDesk has no facts to cross-check.

Nutrient gives us the value, the confidence, and exactly where in the source document each fact came from. That's what makes the whole system possible — we know the facts are grounded, not hallucinated.

---

## RESULTS — [scroll to "Results"]

What we built and what we measured.

One hundred and fifteen tests. All passing. Twelve document types. Six authority conditions.

Ninety-five percent accuracy on contract processing. Eighty percent correctly sent to human review. Ten percent auto-signed with high confidence. Zero unsafe actions.

The system caught a thirty-one day insurance gap that a per-document system would have missed.

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
