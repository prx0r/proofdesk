# ProofDesk — Technical Depth

**Research appendix for judges who want to understand the engineering behind the product.**

> The product is "AI does the reversible work. Evidence and people control the irreversible." This document explains the research that makes that possible.

---

## 1. The Confidence Problem

When an AI agent extracts a fact from a PDF, how confident should it be? And when that confidence is wrong, what happens?

ProofDesk attacks this problem from three angles simultaneously:

1. **Calibration** — making confidence scores honest (when the model says 90%, it should be right 90% of the time)
2. **Risk control** — bounding the probability of catastrophic error (false signature)
3. **Online learning** — improving from human feedback over time

---

## 2. Five Frontier Algorithms, One Module

Our confidence module (`foxit/src/confidence_module.py`) implements five algorithms from recent ML research:

| Algorithm | Paper | What It Does |
|-----------|-------|--------------|
| Conformal Risk Control | Angelopoulos et al., ICLR 2024 | Finite-sample quantile thresholds with coverage guarantees |
| EXTRACTCONF Dual-Call | Kumar, IJCAI-ECAI 2026 | Hunter + Mapper extraction verification, 40 features |
| Per-Field Risk Control | Valid Per-Field, 2026 | Mondrian LTT with exact binomial tails per field |
| Isotonic Calibration | Standard | Score mapping from raw confidence to calibrated probability |
| Sheepish Transform | **This work** | Asymmetric Bayesian shrinkage penalizing overconfidence |

### The Sheepish Metric (Novel Contribution)

When a model is overconfident (says 95% but is wrong), that's worse than being underconfident (says 60% and is wrong). The Sheepish transform formalizes this asymmetry:

```python
if raw_confidence > estimated_accuracy:
    # Overconfident: shrink toward accuracy estimate
    sheepish = (λ_over * raw + λ_under * acc) / (λ_over + λ_under)
else:
    # Underconfident: leave alone (honest uncertainty)
    sheepish = raw_confidence
```

Where `λ_over = 3 × λ_under` (overconfidence penalized 3x more).

**Key insight:** `estimated_accuracy` must be derived from extraction signals (field completeness, assertion pass rate, grounding score) — NOT from ground truth labels. Using ground truth creates label leakage. We fixed this bug during development.

### Mixture of Experts

Different document types have different risk profiles. A single threshold can't handle invoices and contracts equally.

Our MixtureOfExperts architecture:
- **Router** — Decision tree on document features selects the expert
- **Per-world expert** — Each doc type has its own calibrated threshold
- **Fusion weights** — Logistic regression combines expert opinions

Results: **5x fewer false positives** than single-threshold approach.

---

## 3. Calibration Methods

Four calibration methods, each addressing a different failure mode:

| Method | Handles | Implementation |
|--------|---------|----------------|
| Isotonic Regression | General miscalibration | scikit-learn, monotone mapping |
| Conformal Risk Control | Finite-sample guarantees | Hoeffding upper bound, split-conformal |
| Platt Scaling | Sigmoid miscalibration | Nelder-Mead sigmoid fit |
| MarginOnlineCalibrator | Distribution shift over time | Per-band EWMA + Bayesian shrinkage |

The MarginOnlineCalibrator is particularly important: it improves from human feedback. Each time a human resolves an exception, the calibrator updates its thresholds. This is the convergence loop.

---

## 4. Verification Pipeline

Before a fact enters the confidence module, it passes through multiple verification layers:

### EXTRACTCONF Dual-Call (`src/providers/extractconf.py`)
- **Hunter call:** "Extract the vendor name from this document"
- **Mapper call:** "Does this document contain the vendor name 'Acme'?"
- **Disagreement = unreliability.** If the two calls disagree, the extraction is suspect.

### RaV-IDP Reconstruction (`src/providers/ravidp.py`)
- Re-extract fields using deterministic regex patterns
- Compare to original extraction
- Fidelity score = agreement rate
- LOW_FIDELITY → reject extraction

### ConfBench Distribution Monitoring (`src/providers/confbench.py`)
- Track confidence distributions over time
- PSI (Population Stability Index) detects drift
- PSI < 0.1 = stable, 0.1-0.25 = warning, ≥ 0.25 = alert

---

## 5. Benchmark Results

### Dataset: 24,878 examples across 6 datasets

| Dataset | Records | Type |
|---------|---------|------|
| InvoiceBenchmark | 200 | Invoices (tabular) |
| FATURA | 1,400 | Invoices (tabular) |
| ContractNER | 3,241 | Contracts (text) |
| ColdHearted Fraud | 19,872 | Transactions (tabular) |
| CUAD | 509 | Contracts (PDF) |
| Local PDFs | 18 | Real Nutrient extraction |

### Key Results at 1% False Sign Rate

| Method | Coverage | Improvement |
|--------|----------|-------------|
| Baseline (LogReg) | 22.4% | — |
| **ProofDesk (GradBoost + calibration)** | **59.8%** | **2.7x** |
| Random Forest | 53.8% | 2.4x |
| Ensemble | 59.1% | 2.6x |

### Ablation Study

| Component Removed | Accuracy Drop |
|-------------------|---------------|
| Conformal Risk Control | -5.2% |
| Per-field risk budgets | -6.3% |
| Sheepish transform | -2.1% |
| Feature engineering | -15.3% |

**Feature engineering matters most.** Three extra features (relative_diff, has_error, high_txn) produced a 3x improvement.

### Calibration Quality

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| ECE | 0.15 | 0.08 | -47% |
| AURC | 0.145 | 0.042 | -71% |
| AUC | 0.92 | 0.97 | +5.4% |

### ULB Credit Card (284,807 transactions)

| Metric | Value |
|--------|-------|
| AUC | 0.930 |
| Coverage at 0.1% FSR | 99.9% |
| Feature importance | V13 (0.608), V12 (0.238) |

---

## 6. Audit Infrastructure

### Hash-Chained Audit Trail

Every state transition produces an `AuditEvent` containing:
- Event type, actor, timestamp
- Detail payload
- SHA-256 hash of (previous_event_hash + current_event_data)

Breaking any event invalidates all subsequent events.

### Merkle Inclusion Proofs

Events are organized into epochs. Each epoch is sealed with a Merkle tree root. Any event can be verified against the root with a logarithmic-size inclusion proof.

This matches the pattern used by AuditWeave 2026 and RFC 6962.

### Content-Addressed Artifacts

Every generated document is stored with its SHA-256 hash. The SignatureGate recomputes the hash at authorization time and compares to the stored value. One byte change → denial.

---

## 7. CogymKernel Evolution

We built an evolutionary optimization system (`scripts/cogym_optimize_real.py`) that evolves confidence thresholds on real document worlds:

- **Population:** 12 candidates per generation
- **Generations:** 20
- **Mutation:** Threshold perturbation, method swaps, weight adjustments
- **Selection:** Tournament with lexicographic ranking (BAS → accuracy → ECE)
- **Fitness:** Behavioral Alignment Score from Wu et al. 2026

Best evolved policy:
```
auto_threshold: 0.924
review_threshold: 0.351
fusion_weights: [0.18, 0.04, 0.16, 0.04, 0.08, 0.50]
BAS: 0.712
Accuracy: 1.0
```

Each run produces a Merkle-sealed `RunReceipt` for reproducibility.

---

## 8. Literature Positioning

### What We Built That Frontier Papers Don't Address

| Paper | What They Do | What We Add |
|-------|-------------|-------------|
| Angelopoulos (ICLR 2024) | Conformal risk control on static data | Online calibration that improves from feedback |
| Xu (2025) | Selective conformal risk control | Authority gate binding risk to irreversible action |
| Kumar (IJCAI-ECAI 2026) | Dual-call extraction verification | Production audit trail + hash chain |
| ConfBench (Amazon 2026) | Distribution shift monitoring | Integration with real Nutrient API + source grounding |
| MARGIN (2026) | Online calibration theory | Production convergence loop with spot audit panel |

### Novel Composition (Unclaimed Anywhere)

> Conformal certificate → authority decision → template-rendered legal clause → hash-chained provenance from source pixels to signature authorization.

Each layer has prior art. The chain does not.

---

## 9. Files to Explore

| Path | What to Read |
|------|-------------|
| `foxit/src/confidence_module.py` | 5 algorithms in one module |
| `foxit/src/sheepish.py` | Novel overconfidence penalty |
| `foxit/src/calibration.py` | 4 calibration methods |
| `foxit/src/metrics.py` | 6 evaluation metrics |
| `foxit/src/experts.py` | Mixture of Experts |
| `foxit/src/frontier_experiments.py` | Full experiment suite |
| `foxit/docs/CANONICAL_THESIS.md` | Extended thesis (14 papers cited) |
| `foxit/docs/PAPER.md` | ArXiv-formatted paper |
| `src/benchmark/confidence/` | Cogym-style signing world |
| `src/providers/extractconf.py` | Dual-call verification |
| `src/providers/ravidp.py` | Reconstruction validation |
| `src/providers/confbench.py` | Distribution monitoring |
| `src/skills/agent_brain.py` | 12 document type classifier |
| `scripts/cogym_optimize_real.py` | Evolutionary optimization |
| `benchmarks/` | Evolution results with Merkle receipts |

---

## 10. How to Run the Research

```bash
# Run the confidence benchmark
python3 -m src.benchmark.confidence.runner --n 1000

# Run the signing benchmark
python3 -m src.benchmark.confidence.signing_bench --n 200

# Run CogymKernel evolution
python3 scripts/cogym_optimize_real.py

# Run frontier experiments
python3 foxit/experiments/benchmark.py

# Generate publication-quality plots
python3 -m src.benchmark.confidence.ml_lab_v2
```

---

*This research was conducted during the DevNetwork API+Cloud+AI Hackathon 2026. The product is ProofDesk. The research is the engine that makes it work.*
