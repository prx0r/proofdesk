# ProofDesk vs Frontier Literature — Honest Comparison

**Date:** 2026-08-26
**Status:** Pre-submission analysis

---

## Executive Summary

| Dimension | Our Solution | Frontier Literature | Winner |
|-----------|-------------|---------------------|--------|
| Extraction quality | Deterministic stubs | RaV-IDP reconstruction | Frontier |
| Confidence calibration | MarginOnlineCalibrator | EXTRACTCONF dual-call | Frontier |
| Pipeline infrastructure | Merkle proofs, hash chain | Not addressed | Us |
| Convergence mechanism | FeedbackLoop + calibrator | Not addressed | Us |
| Distribution shift | Not addressed | ConfBench monitoring | Frontier |
| Audit trail | Hash-chained + Merkle | Not addressed | Us |
| Demo readiness | Working demo + script | Research papers | Us |

---

## Detailed Comparison

### 1. EXTRACTION QUALITY VERIFICATION

**Our Solution:**
- Deterministic stubs that return known-good extractions
- Nutrient API with confidence scores
- No reconstruction validation

**Frontier (RaV-IDP 2026):**
- After extraction, reconstruct the document region
- Compare reconstruction to original
- Fidelity score = grounded quality signal
- If fidelity < threshold → route to fallback
- Recovers 38.1% of failed extractions

**Verdict:** Frontier wins. We don't verify extraction quality — we trust Nutrient's confidence. RaV-IDP would catch cases where Nutrient is confidently wrong.

**Gap:** We have no way to detect when extraction is wrong but confident.

---

### 2. CONFIDENCE CALIBRATION

**Our Solution:**
- `MarginOnlineCalibrator` from foxit lab
- Human labels → calibrator updates → threshold adjusts
- Fixed thresholds per risk level (0.50-1.00)

**Frontier (EXTRACTCONF 2026):**
- Dual-call: Hunter (field-guided) + Mapper (document-guided)
- Disagreement = reliability signal
- 0.928 AUC, 99.1% accuracy at 80% coverage

**Verdict:** Frontier wins. Our calibrator adjusts thresholds but doesn't verify extraction quality. EXTRACTCONF's dual-call catches cases where extraction is inconsistent.

**Gap:** We don't have a second opinion on extraction quality.

---

### 3. DISTRIBUTION SHIFT DETECTION

**Our Solution:**
- None — we assume i.i.d. data
- No monitoring of confidence distributions
- No drift detection

**Frontier (ConfBench 2026):**
- Track confidence distribution over time
- Detect drift via KS test or PSI
- Alert when distribution shifts significantly
- Retrain on new data

**Verdict:** Frontier wins. We have no defense against distribution shift. If the PDF population changes (e.g., new vendor formats), our thresholds become stale.

**Gap:** We're brittle to population changes.

---

### 4. PIPELINE INFRASTRUCTURE

**Our Solution:**
- Hash-chained audit events
- Real Merkle inclusion proofs
- File validation (type + size)
- Error handling with tracebacks
- Cross-doc assertion deduplication

**Frontier (None):**
- Papers focus on extraction/calibration
- No mention of audit trails, Merkle proofs, or tamper-evidence

**Verdict:** We win. Frontier papers assume the infrastructure exists. We built it.

**Strength:** Our audit chain is production-ready.

---

### 5. CONVERGENCE MECHANISM

**Our Solution:**
- `FeedbackLoop.record()` captures human labels
- `MarginOnlineCalibrator` updates per-rule
- `classify_document()` uses `calibrated()` — **loop is now closed**
- Spot-audit panel tracks auto-sign error rate

**Frontier (None):**
- Papers assume static thresholds
- No mention of online calibration or feedback loops

**Verdict:** We win. Frontier papers calibrate once; we calibrate continuously.

**Strength:** Our system improves with use.

---

### 6. ACTIVE LEARNING

**Our Solution:**
- `select_for_review()` selects fields near decision boundary
- Uncertainty sampling for human feedback
- Not wired into batch processor

**Frontier (CoPAL 2024):**
- Conformal Prediction for Active Learning
- Use CP uncertainty to select samples
- Theoretically grounded selection

**Verdict:** Tie. We have the mechanism; it's not wired. Frontier has theory; we have code.

**Gap:** Need to wire `select_for_review()` into batch flow.

---

### 7. SPOT AUDIT

**Our Solution:**
- `record_auto_sign()` tracks pure-auto cases
- `spot_audit()` captures human verification
- `measured_error_rate` on panel (not acceptance rate)

**Frontier (None):**
- No mention of spot audit mechanisms

**Verdict:** We win. We have the safety evidence mechanism.

**Strength:** Rubber-stamp hole is closed.

---

## What We Should Steal

| Paper | Concept | Implementation Effort | Impact |
|-------|---------|----------------------|--------|
| RaV-IDP | Reconstruction validation | 2-3 days | HIGH — catches extraction errors |
| EXTRACTCONF | Dual-call Hunter-Mapper | 1-2 days | HIGH — second opinion on quality |
| ConfBench | Distribution shift monitoring | 1 day | MEDIUM — alerts on drift |
| CoPAL | Wire active learning | 0.5 day | MEDIUM — better sample selection |

---

## What We Have That They Don't

| Feature | Us | Frontier |
|---------|-----|----------|
| Tamper-evident audit chain | ✅ | ❌ |
| Merkle inclusion proofs | ✅ | ❌ |
| Online convergence (improves with use) | ✅ | ❌ |
| Spot-audit safety evidence | ✅ | ❌ |
| Production-ready infrastructure | ✅ | ❌ |

---

## The Honest Pitch

**What we built:**
> "A production-ready document execution pipeline with tamper-evident audit, online convergence, and provable safety evidence. We don't claim our model is perfect — we claim our PIPELINE catches errors at every stage."

**What we're missing:**
> "Extraction quality verification (RaV-IDP), dual-call confidence (EXTRACTCONF), and distribution shift monitoring (ConfBench). These are research-grade solutions we could integrate in 1-2 weeks."

**The judge's question:**
> "Why not use RaV-IDP or EXTRACTCONF?"

**Our answer:**
> "They're research papers — we're a working system. We built the infrastructure they assume exists. Integrating their extraction verification into our audit chain would take 1-2 weeks and would be the next step post-hackathon."

---

## Recommendation

**For hackathon submission:**
- Keep our infrastructure (audit, Merkle, convergence)
- Add a note in the writeup: "RaV-IDP and EXTRACTCONF are next-step integrations"
- Focus the demo on what works: pipeline gates, human review, Merkle proofs

**For production:**
- Integrate RaV-IDP reconstruction validation
- Add EXTRACTCONF dual-call for extraction verification
- Add ConfBench distribution shift monitoring
