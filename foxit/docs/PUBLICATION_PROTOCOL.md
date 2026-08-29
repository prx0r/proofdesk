# Experiment Suite — Publication-Ready Documentation

## Overview

Six experiments testing a risk-adaptive document signing system. Each experiment has:
- Research question
- Hypothesis
- Method (with frontier paper citation)
- Data collection protocol
- Logging protocol
- Reproducibility guide
- Expected results

---

## Data Collection Protocol

### Datasets

| Dataset | Source | Docs | Fraud Labels | Download |
|---------|--------|------|--------------|----------|
| InvoiceBenchmark | HuggingFace `jngb-labs/InvoiceBenchmark` | 200 | ✅ 40 fraudulent | `load_dataset()` |
| FATURA | HuggingFace `mathieu1256/FATURA2-invoices` | 10,000 | ❌ All safe | `load_dataset()` |
| ContractNER | HuggingFace `agilelab-org/ContractNER_Dataset` | 3,240 | ✅ 18 entity types | `load_dataset()` |
| CUAD | HuggingFace `theatticusproject/cuad` | 510 | ✅ 41 clause types | `load_dataset()` |
| INS-007 | HuggingFace `xpertsystems/ins007-sample` | 5,000 | ✅ 12 fraud types | `load_dataset()` |
| AIForge-Doc | HuggingFace `Scam-AI/AIForge-Doc-v1` | 4,061 | ✅ AI-forged docs | `load_dataset()` |
| 10K Fraud | Zenodo `aminmous/fraud-analysis` | 10,000+ | ✅ SEC AAER labels | Download |

### Preprocessing

1. **Download**: `load_dataset(name, token=HF_TOKEN)`
2. **Normalize**: Convert to unified schema (doc_id, text, labels, features)
3. **Split**: 60% train, 20% calibration, 20% test (stratified by risk level)
4. **Save**: Store as JSON with metadata

### Schema

```json
{
  "doc_id": "string",
  "dataset": "string",
  "risk_level": "low|medium|high",
  "doc_type": "invoice|contract|insurance|kyc|mortgage|securities",
  "text": "string",
  "labels": {
    "fraud": "boolean",
    "fraud_type": "string",
    "entities": "list"
  },
  "features": {
    "n_entities": "int",
    "avg_confidence": "float",
    "text_length": "int"
  }
}
```

---

## Experiment 1: Risk Classification

### Research Question
Can we correctly classify documents into Low/Medium/High risk levels?

### Hypothesis
A logistic regression classifier trained on document features achieves 90%+ accuracy on Low risk, 80%+ on Medium, 70%+ on High.

### Method
- **Classifier**: LogisticRegression (scikit-learn)
- **Features**: Entity count, confidence scores, text length, document type
- **Guarantee**: Conformal classification (Vovk et al.) for finite-sample coverage
- **Citation**: Vovk et al. (2005), Conformal Prediction

### Data Collection
1. Download all datasets
2. Label each document: Low/Medium/High risk
3. Extract features (entity count, confidence, text length)
4. Split: 60% train, 20% calibration, 20% test

### Logging
```json
{
  "experiment": "risk_classification",
  "method": "logistic_regression",
  "dataset": "combined",
  "n_docs": 22000,
  "accuracy_low": 0.92,
  "accuracy_medium": 0.85,
  "accuracy_high": 0.73,
  "confusion_matrix": [[...], [...], [...]],
  "timestamp": "2026-08-25T00:00:00Z"
}
```

### Reproducibility
```bash
python3 -m experiments.risk_classification --dataset all --seed 42
```

---

## Experiment 2: Threshold Optimization

### Research Question
What's the optimal signing threshold per document type?

### Hypothesis
Conformal Risk Control finds thresholds with finite-sample guarantees: P(risk > α) ≤ δ.

### Method
- **Algorithm**: Conformal Risk Control (Angelopoulos et al., ICLR 2024)
- **Parameters**: α = 0.1, δ = 0.05
- **Search**: Grid search over thresholds, select λ* = min{λ : upper_bound(R(λ)) ≤ α}
- **Citation**: Angelopoulos et al. (2024), "Conformal Risk Control"

### Data Collection
1. For each document type, collect calibration set
2. Compute nonconformity scores
3. Find conformal quantile
4. Validate on test set

### Logging
```json
{
  "experiment": "threshold_optimization",
  "method": "conformal_risk_control",
  "alpha": 0.1,
  "thresholds": {
    "invoice": 0.70,
    "contract": 0.85,
    "insurance": 0.90,
    "kyc": 0.95
  },
  "coverage_at_threshold": {
    "invoice": 0.85,
    "contract": 0.70,
    "insurance": 0.60,
    "kyc": 0.40
  }
}
```

---

## Experiment 3: False Sign Tradeoff

### Research Question
What does 0% false sign cost in coverage?

### Hypothesis
At 0% false sign, coverage drops to 60%. At 1%, coverage rises to 75%. At 5%, coverage reaches 90%.

### Method
- **Algorithm**: CRC with α ∈ {0, 0.01, 0.05}
- **Metric**: Coverage at each α
- **Citation**: Angelopoulos et al. (2024), SCRC (Xu et al., 2025)

### Data Collection
1. For each α, find threshold via CRC
2. Measure coverage on test set
3. Plot risk-coverage curve

### Logging
```json
{
  "experiment": "false_sign_tradeoff",
  "tradeoff": {
    "0%": {"coverage": 0.60, "threshold": 0.95},
    "1%": {"coverage": 0.75, "threshold": 0.90},
    "5%": {"coverage": 0.90, "threshold": 0.80}
  }
}
```

---

## Experiment 4: Per-Type Analysis

### Research Question
Which document types is the system good/bad at?

### Hypothesis
Invoices are easy (90%+ accuracy), KYC is hard (70%+ accuracy).

### Method
- **Metric**: Accuracy, FPR, coverage per document type
- **Visualization**: Heatmap of performance by type

### Data Collection
1. For each document type, measure accuracy, FPR, coverage
2. Identify which types need more human review

### Logging
```json
{
  "experiment": "per_type_analysis",
  "results": {
    "invoice": {"accuracy": 0.95, "fpr": 0.02, "coverage": 0.85},
    "contract": {"accuracy": 0.85, "fpr": 0.05, "coverage": 0.70},
    "insurance": {"accuracy": 0.80, "fpr": 0.08, "coverage": 0.60},
    "kyc": {"accuracy": 0.70, "fpr": 0.12, "coverage": 0.40}
  }
}
```

---

## Experiment 5: Merkle Audit

### Research Question
Can we prove every signing decision was calibrated?

### Method
- **Integration**: ProofDesk EventLedger (hash-chained audit trail)
- **Storage**: document hash, risk level, threshold, calibration score, decision
- **Verification**: Merkle proof for each signing decision

### Data Collection
1. Hash-chain every signing decision
2. Store calibration metadata
3. Generate Merkle proofs

### Logging
```json
{
  "experiment": "merkle_audit",
  "n_decisions": 1000,
  "chain_valid": true,
  "merkle_root": "abc123...",
  "proof_verification": "passed"
}
```

---

## Experiment 6: End-to-End

### Research Question
Does the full system work on real documents?

### Method
- **Pipeline**: classify → threshold → sign → audit
- **Metric**: End-to-end accuracy, total false signs, total coverage

### Data Collection
1. Run complete pipeline on all datasets
2. Measure accuracy, FPR, coverage
3. Verify audit trail completeness

### Logging
```json
{
  "experiment": "end_to_end",
  "accuracy": 0.92,
  "fpr": 0.02,
  "coverage": 0.75,
  "false_signs": 0,
  "audit_complete": true
}
```

---

## Reproducibility Guide

### For a New Agent

1. **Clone repo**: `git clone <repo>`
2. **Install deps**: `pip install -r requirements.txt`
3. **Download datasets**: `python3 scripts/download_datasets.py`
4. **Run experiments**: `python3 -m experiments.run_all`
5. **Check results**: `cat results/experiment_*.json`

### Key Files

| File | Purpose |
|------|---------|
| `experiments/run_all.py` | Run all experiments |
| `experiments/risk_classification.py` | Experiment 1 |
| `experiments/threshold_optimization.py` | Experiment 2 |
| `experiments/false_sign_tradeoff.py` | Experiment 3 |
| `experiments/per_type_analysis.py` | Experiment 4 |
| `experiments/merkle_audit.py` | Experiment 5 |
| `experiments/end_to_end.py` | Experiment 6 |
| `scripts/download_datasets.py` | Download all datasets |
| `scripts/preprocess.py` | Preprocess data |
| `scripts/plot_results.py` | Generate figures |

### Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Publication-Ready Figures

| Figure | Content | File |
|--------|---------|------|
| Fig 1 | Risk classification accuracy | `figures/risk_classification.png` |
| Fig 2 | Threshold optimization | `figures/threshold_optimization.png` |
| Fig 3 | False sign tradeoff curve | `figures/false_sign_tradeoff.png` |
| Fig 4 | Per-type analysis heatmap | `figures/per_type_analysis.png` |
| Fig 5 | Merkle audit verification | `figures/merkle_audit.png` |
| Fig 6 | End-to-end pipeline | `figures/end_to_end.png` |

---

## Paper Structure

1. **Introduction** — Problem, motivation, contributions
2. **Related Work** — Conformal prediction, selective prediction, document understanding
3. **Method** — Risk classification, threshold optimization, false sign tradeoff
4. **Experiments** — 6 experiments with full results
5. **Discussion** — Limitations, future work
6. **Conclusion** — Key findings

### Citations

1. Angelopoulos et al. (2024). Conformal Risk Control. ICLR 2024.
2. Vovk et al. (2005). Conformal Prediction.
3. Xu et al. (2025). Selective Conformal Risk Control.
4. Blot et al. (2024). Auto-Adaptive CRC.
5. Tayebati et al. (2025). Conformal Abstention Policy.
6. Cohen et al. (2024). Cross-Validation CRC.
