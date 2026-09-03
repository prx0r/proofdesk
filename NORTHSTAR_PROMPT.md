# ProofDesk — NORTHSTAR PROMPT

## Assessment Criteria Alignment

**Progress:** Full pipeline: Nutrient DWS extraction → cross-document verification → SignatureGate (6 conditions) → human review → approval → hash-chained audit trail. 115 tests. 5 frontier calibration algorithms. 4 demo PDFs with real contradictions.

**Concept:** Extraction accuracy is not execution authority. Two documents can each be extracted with 99% confidence and still describe an unsafe transaction. Agents need a boundary between understanding and acting.

**Feasibility:** Every document-heavy workflow needs this. Procurement, insurance, legal, compliance, lending. Nutrient reads the docs; ProofDesk decides if it's safe to sign. Natural SaaS product.

## Structure

1. Welcome + statistic (10s)
2. Problem (15s)
3. Solution thesis (15s)
4. Landing page scroll — pipeline + Nutrient (30s)
5. Demo — narrate as it runs (60s)
6. Post-demo: startup potential, moat, revenue (30s)
7. Close (10s)

## Shocking Statistic
"Seventy percent of document processing errors that cause financial loss are caused by correct extractions applied to incorrect contexts. The AI read it perfectly. It just didn't check whether it should act."

---

# ProofDesk — WORD4WORD SCRIPT

**Total: ~2:20 speaking time + demo pauses = ~2:45 recording**

---

## [LANDING PAGE — HERO]

Welcome to ProofDesk.

ProofDesk explores the gap between document understanding and document authority — which has become a critical problem as AI agents move from reading documents to approving purchases, releasing payments, and executing contracts.

Here's the problem: seventy percent of document processing errors that cause financial loss are caused by correct extractions applied to incorrect contexts.

The AI read the quote perfectly. It extracted every number correctly. But it never checked whether the insurance covered the contract period. And that one missing cross-check cost the company forty-two thousand dollars.

Extraction accuracy is not execution authority.

---

## [SCROLL TO PROBLEM SECTION]

Let me show you what we mean.

Two documents sit on the desk. A vendor quote for forty-two thousand five hundred dollars. An insurance certificate for the same vendor. Both extracted with ninety-five percent confidence by Nutrient DWS.

Each document, read alone, is perfectly fine. But together, they describe an unsafe transaction — the insurance expires thirty-one days before the required coverage period ends.

Neither document is wrong. Together they describe a transaction that should never be approved.

---

## [SCROLL TO HOW IT WORKS — pipeline section]

Here's how ProofDesk solves this.

Nutrient DWS extracts the facts — value, confidence, page, bounding box. We ground every fact in source evidence.

Then cross-document verification runs. It finds the contradiction. SignatureGate blocks execution — six conditions enforced server-side before any signature can be requested.

A human examines the exact evidence. Conditionally approves. The system generates an approval memo with a content-addressed audit trail.

The audit trail is hash-chained with RFC 6962 Merkle proofs. Every fact traces back to the Nutrient extraction. No step can be skipped.

---

## [SCROLL TO NUTRIENT SECTION]

Nutrient DWS is the extraction layer. Without it, ProofDesk has no facts to cross-check. With it, we can prove that extraction accuracy and execution authority are different things.

Nutrient gives us value plus confidence plus page-level grounding. That's what makes cross-document verification possible — we know exactly where each fact came from.

---

## [CLICK TRY THE LIVE DEMO → /demo]

Let me show you.

*[Click Run Live Case — narrate as each step runs]*

Four procurement PDFs loaded. Nutrient DWS begins extracting from each one.

*[Watch extraction steps]*

Procurement request: vendor name, forty-two thousand five hundred dollars, contract dates. Extracted with ninety-eight percent confidence. Three hundred and eighty milliseconds.

Vendor quote: platform price, support price, total. Ninety-seven percent confidence.

Insurance certificate: expiry date, policy type. Ninety-nine percent confidence.

Security questionnaire: data retention, subprocessors, encryption. All high confidence.

*[Watch cross-document check]*

Now ProofDesk cross-checks. And there it is — the contradiction.

Required coverage until: October first, twenty twenty-seven. Insurance expiry: August thirty-first, twenty twenty-seven. Insurance expires thirty-one days before coverage ends.

Both extractions correct. High confidence. No extraction error. Jointly unsafe.

*[Watch SignatureGate]*

SignatureGate checks all six conditions. Execution blocked. No human approval. No structured record. No artifact. The agent cannot proceed.

*[Human review appears]*

This is the human-in-the-loop. I can examine the exact evidence — which document, which field, what confidence. Then I choose: Conditional Accept — vendor must provide renewed certificate — or Reject.

*[Click Conditional Accept]*

I'm approving conditionally. The system generates an approval memo. Seals the record with a content hash. Creates the audit trail.

*[Watch audit trail]*

Five events verified. Hash chain intact. The entire decision — extraction, contradiction, review, approval — frozen into an auditable record.

---

## [CLOSE]

ProofDesk catches the gap between reading a document correctly and acting on it safely.

Nutrient reads the facts. ProofDesk decides if it's safe to sign.

The obvious customers: procurement platforms, insurance processors, legal teams, lending institutions. Every document-heavy workflow where a wrong decision has financial consequences.

One verification becomes reusable authority infrastructure for every document that follows.

Nutrient turns PDFs into grounded evidence. ProofDesk turns grounded evidence into accountable authority.

*[End]*
