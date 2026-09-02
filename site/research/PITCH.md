# ProofDesk — The Pitch

## What We Built

An evidence-gated document automation system. Nutrient DWS extracts grounded evidence from source documents. ProofDesk determines when that evidence is sufficient for an irreversible action — and when it must defer to a human.

## The Problem

The dangerous failure in document AI is not "can the model read this?" — it's **"is the evidence sufficient to authorize what happens next?"**

Two documents can be individually extracted with high confidence and still describe a transaction that should never be approved. Extraction accuracy is not execution authority.

Current document systems treat extraction as the hard problem. It's not. The hard problem is knowing when to stop.

## How It Works

### 1. Nutrient DWS extracts grounded evidence

Source PDFs go through Nutrient DWS. Every extracted field carries:
- **value** — what was found
- **confidence** — how sure the extractor is
- **page** — which page it came from
- **bounding box** — where on the page

This is not text extraction. It's source-grounded evidence with provenance.

### 2. Cross-document verification

Extracted facts are checked against each other:
- Does the quote total match the line items?
- Do entity names normalize across documents?
- Does the insurance coverage extend through the service period?

These are deterministic, rule-based checks. No LLM calls. The assertions are either PASS or FAIL.

### 3. Calibrated authority gate

The SignatureGate enforces 6 conditions server-side. The agent cannot negotiate:

| Check | What it verifies |
|-------|-----------------|
| State is PREPARED | Pipeline completed all prior stages |
| No unresolved blockers | All BLOCKER-severity assertions resolved |
| Human approval present | A human explicitly approved the record |
| Structured record exists | Approved record with content hash |
| Artifact hash verified | SHA-256 of final PDF matches stored hash |
| Calibrated score ≥ threshold | Confidence meets risk-appropriate threshold |

The threshold is not arbitrary. It's calibrated from the research.

### 4. Human reviews the exact evidence

When the gate blocks, the human doesn't re-read the entire document bundle. They see:
- The specific failing assertion
- The source document and page
- The extracted values that created the conflict
- The confidence scores

They resolve with a decision, reason, and actor. This becomes audit evidence AND calibration data.

### 5. Deterministic execution

Once resolved, every transition is hash-chained. The final artifact is content-addressed. Any post-approval modification is detected. The entire decision is replayable from the audit trail.

## The ML Research

The authority gate thresholds are not hand-tuned. They come from a research program in calibrated confidence:

### What the algorithms do

| Algorithm | What it solves | How |
|-----------|---------------|-----|
| Conformal-style risk calibration | "What threshold gives me ≤X% false authorization?" | Splits data into tune/certify/test, uses quantile of nonconformity scores |
| Sheepish transform | "Overconfident errors are more dangerous than cautious abstentions" | Asymmetric penalty — confidence that's too high gets penalized more than confidence that's too low |
| Per-field risk budgets | "A wrong signer name is worse than a wrong metadata field" | signer: 1% max error, amount: 2%, date: 3%, default: 10% |
| Online calibration | "Human decisions should improve future thresholds" | MarginOnlineCalibrator updates from human feedback labels |
| Dual-call verification | "Does a second extraction agree with the first?" | Hunter (field-guided) vs Mapper (document-guided) — disagreement is informative |

### The convergence loop

Every time a human resolves an exception, ProofDesk captures:
- What confidence level was the system at
- Did the human accept or reject
- What field was involved

This becomes calibration data. The online calibrator updates. Future decisions improve. The spot-audit pool measures actual error rate on auto-approved decisions.

The trajectory: **human review falls over time while measured false-authorization risk stays bounded.**

### What we measured

- **13 PDF fixtures** across 6 document types — all extracted correctly
- **Threshold calibration** — tuned on heterogeneous classification datasets, validated on held-out splits
- **Convergence** — feedback labels improve acceptance rate while maintaining error bounds
- **Tamper detection** — post-approval byte modification detected by hash mismatch

## The Core Thesis

> **Correct extraction does not equal sufficient authority.**

A document can be read with 99% confidence and still describe a transaction that should not happen. ProofDesk catches the gap between "we extracted it correctly" and "we should act on it."

Nutrient DWS provides the grounded evidence. ProofDesk decides when that evidence is strong enough to act.

## One-Line Pitch

**Nutrient DWS grounds the facts. ProofDesk decides when the evidence is sufficient to act.**

## The Demo Story (3 minutes)

**0:00–0:12** — "AI can read a contract. That doesn't mean it has authority to act on it."

**0:12–0:28** — Click Run Live. Show Nutrient DWS extracting with confidence and page provenance.

**0:28–0:50** — Stop on two dates. "The procurement requires insurance through October. The certificate expires in August. Both are high-confidence extractions. Together they are unsafe."

**0:50–1:10** — "This is the key difference. Confidence is evidence quality. It is not execution authority."

**1:10–1:35** — Human resolves the exception. "The human sees the exact evidence, not the entire bundle."

**1:35–1:55** — Approve + generate. Record hash, artifact hash. "Every transition is replayable."

**1:55–2:15** — Tamper test or audit chain. "Change one byte and the hash changes."

**2:15–2:35** — Research tab. "Human review becomes calibration data, not discarded manual work."

**2:35–2:50** — Close. "Nutrient turns PDFs into grounded evidence. ProofDesk turns grounded evidence into accountable authority."
