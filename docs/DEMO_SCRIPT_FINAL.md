# ProofDesk — Demo Script (Visual, 3 minutes)

## Opening (0:00-0:15)

[SCREEN: Dark background, ProofDesk logo]

"Every business signs documents without verifying the facts across them.
An AI agent might hallucinate values, and nobody can prove what happened.

ProofDesk changes that."

---

## Act 1: The Messy Folder (0:15-0:45)

[SCREEN: File upload zone with 18 PDFs]

"Drop in 18 mixed procurement documents."

[ANIMATION: Files fly in, agent classifies each]

"The agent classifies 9 document types automatically:
procurement, invoice, KYC, trade, mortgage, medical..."

[SCREEN: Extraction results with confidence badges]

"Nutrient DWS extracts 45 fields with real confidence scores.
Every field traces back to a specific page and bounding box."

---

## Act 2: The Discrepancy (0:45-1:15)

[SCREEN: Cross-document comparison]

"But here's what matters — cross-document verification."

[ANIMATION: Side-by-side comparison]

"Insurance expires August 31, 2027.
Required coverage until October 1, 2027.
That's a 31-day gap where the company is uninsured."

[SCREEN: FactMiner verdict]

"FactMiner verdict: REFUTED.
The insurance does NOT cover the full contract period."

---

## Act 3: Human Routing (1:15-1:45)

[SCREEN: Confidence routing stats]

"The system knows when it's uncertain."

[ANIMATION: Fields route to different buckets]

"42 fields auto-approved (confidence >= 0.95).
3 fields rejected (confidence < 0.65).
0 fields need human review on clean documents."

[SCREEN: DWS Viewer with source document]

"When confidence drops, the agent routes to a human via DWS Viewer.
Click the source chip — jump to the exact page and bounding box."

---

## Act 4: Audit Trail (1:45-2:15)

[SCREEN: Hash chain visualization]

"Every decision is audit-trailed with hash-chained events.
Each event stores the hash of the previous event.
Tamper with any event — the chain breaks."

[SCREEN: Merkle proof]

"Seal events into Merkle epochs.
Prove any event was included without re-running the entire chain."

[SCREEN: Signed certificate]

"Every generated document carries a self-hashing certificate.
The certificate hash is computed from its contents — tamper-evident by construction."

---

## Act 5: Comparison (2:15-2:30)

[SCREEN: Side-by-side table]

"We compared ProofDesk to VerifyDoc — a leading document trust layer."

| | VerifyDoc | ProofDesk |
|---|---|---|
| Fields extracted | 4 | 10 |
| Source grounding | Page + bbox | Page + bbox + match |
| Audit trail | None | Hash chain + Merkle |
| Signing | None | Foxit merge |

"VerifyDoc excels at calibration. ProofDesk excels at audit trail.
Together, they form the strongest document verification stack."

---

## Close (2:30-2:45)

[SCREEN: ProofDesk logo + tagline]

"AI does the reversible work.
Evidence and people control the irreversible."

"ProofDesk — Evidence-Gated Document Execution"

---

## Key Visual Moments

1. **File upload** — 18 PDFs flying into the agent
2. **Extraction** — confidence badges on each field
3. **Insurance gap** — side-by-side date comparison
4. **DWS Viewer** — source-jump to exact page
5. **Hash chain** — animated chain links breaking on tamper
6. **Merkle proof** — tree visualization with inclusion path
7. **Certificate** — self-hashing stamp
