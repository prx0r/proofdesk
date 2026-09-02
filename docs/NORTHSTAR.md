# ProofDesk — Northstar: Hackathon Strategy

**Last updated:** 2026-09-01
**Deadline:** Sep 3, 2026 @ 10:00 AM PT

---

## Primary Submission: Nutrient DWS

ProofDesk is an evidence-gated document automation system. Nutrient DWS extracts grounded evidence from source documents. ProofDesk reconciles it, estimates decision risk, routes uncertain cases to people, and produces a replayable audit trail.

---

## The Nutrient Story

```
PDF → NUTRIENT DWS → Grounded Evidence → Verify → Classify → Route → Human → Audit
         │                │                │        │         │       │       │
         │                │                │        │         │       │       └─ Hash chain + Merkle
         │                │                │        │         │       └─ Binary feedback
         │                │                │        │         └─ AUTO/DEFER/BLOCK
         │                │                │        └─ Calibrated thresholds
         │                │                └─ Cross-document checks
         │                └─ value + confidence + page + bbox
         └─ Real API: document understanding
```

### What the Nutrient judge sees

- Real DWS extraction with value, confidence, page, and bounding-box provenance
- Cross-document discrepancy detection (e.g., insurance coverage gap)
- Source-grounded evidence review
- Human exception routing with audit trail
- The SignatureGate: 6 conditions enforced server-side before any signing

### Why this is a strong Nutrient submission

Nutrient's own judging thesis: "pull the data out, judge confidence, bring a human in where it matters, keep a record."

That is exactly what ProofDesk does. The research makes it stronger — calibrated confidence thresholds, convergence loop from human feedback, spot-audit pool measuring actual error on auto-sign decisions.

---

## What Each Endpoint Proves

| Endpoint | What it shows |
|----------|---------------|
| `/v1/cases/{id}/facts` | Extracted fields with confidence, page, bbox |
| `/v1/cases/{id}/trace` | Every outbound Nutrient DWS call |
| `/v1/cases/{id}/signature-gate` | 6-condition gate check |
| `/v1/cases/{id}/events` | Hash-chained audit trail |
| `/v1/feedback/stats` | Convergence loop: human labels -> calibration |

---

## Priority Order

1. One immaculate procurement scenario that works end-to-end
2. Real Nutrient extraction with evidence/confidence
3. Visible human review gate
4. Audit/provenance screen
5. Convergence loop demo (brief)
6. Demo polish

---

## What NOT to Build

- Three separate apps
- Sophisticated multi-agent debate
- Free-form contract-writing LLM
- Generic chat-with-PDF
- Custom OCR / viewer / e-sign engine
- Blockchain notarization
- Large RAG stack
- Real PII
- Broad legal/compliance certification
- Autonomous signing

---

## Reference Documents

- `docs/JUDGE_GUIDE.md` — One-page judge guide
- `docs/TECHNICAL_DEPTH.md` — Full research appendix
- `HACKATHON_SUBMISSION.md` — Submission narrative
- `fixtures/demo/` — 4 canonical demo PDFs (committed to Git)
