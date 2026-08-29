# ProofDesk × cogymkernel — Confidence Scoring Optimization Spec

## Overview

Use cogymkernel's deterministic evolution laboratory to optimize confidence
thresholds for document extraction and verification across 6 document types.
The benchmark results ARE the product — measurable, auditable, reproducible.

---

## Architecture

```
COGYMKERNEL
  ├─ worlds/proofdesk.py      ← defines the optimization surface
  ├─ evo/recipes.py            ← mutate thresholds → evaluate → select
  ├─ eval/gates.py             ← quality gates (accuracy floor, FP ceiling)
  ├─ kernel/runs.py            ← content-addressed RunReceipts
  └─ orchestration/            ← wire best config to agent

NUTRIENT APIs                  ← extraction (what we're optimizing)
FACTMINER                      ← verification (the verdict layer)
HERMES KANBAN                  ← task management (human review)
AUDIT TRAIL                    ← tamper-evident proof of every decision
```

---

## Worldpack Definition

```python
# worlds/proofdesk.py

PROOFDESK_WORLDPACK = {
    "name": "proofdesk-confidence",
    "version": "1.0",

    # Document types to optimize across
    "documents": {
        "invoice": {
            "source": "data/test_pdfs/invoice_*.pdf",
            "schema": SCHEMAS["invoice"],
            "ground_truth": GROUND_TRUTH["invoice"],
            "strengths": ["total_amount", "invoice_number"],
            "weaknesses": ["vendor_name"],
        },
        "contract": {
            "source": "/tmp/cuad/data/test.json",
            "schema": None,  # clause detection, not field extraction
            "ground_truth": CUAD_LABELS,
            "strengths": ["structured_fields"],
            "weaknesses": ["semantic_clauses"],
        },
        "receipt": {
            "source": "/tmp/ICDAR-2019-SROIE/data/img/",
            "schema": RECEIPT_SCHEMA,
            "ground_truth": "/tmp/ICDAR-2019-SROIE/data/key/",
            "strengths": ["total", "date"],
            "weaknesses": ["company", "address"],
        },
        "kyc_id": {
            "source": "data/test_pdfs/kyc_01_*.pdf",
            "schema": SCHEMAS["kyc_id"],
            "ground_truth": GROUND_TRUTH["kyc"],
            "strengths": ["full_name", "date_of_birth"],
            "weaknesses": ["address"],
        },
        "trade": {
            "source": "data/test_pdfs/trade_*.pdf",
            "schema": SCHEMAS["trade"],
            "ground_truth": GROUND_TRUTH["trade"],
            "strengths": ["invoice_number", "total_value"],
            "weaknesses": ["incoterm"],
        },
        "medical": {
            "source": "data/test_pdfs/redaction_*.pdf",
            "schema": SCHEMAS["medical"],
            "ground_truth": GROUND_TRUTH["medical"],
            "strengths": ["patient_name", "dob"],
            "weaknesses": ["ssn"],
        },
    },

    # Extraction methods to compare
    "methods": {
        "nutrient_extract": {
            "api": "/extraction/extract",
            "mode": "understand",
            "cost_per_call": 15,  # credits
            "latency_p50_ms": 4000,
        },
        "nutrient_parse": {
            "api": "/extraction/parse",
            "mode": "understand",
            "cost_per_call": 9,
            "latency_p50_ms": 3500,
        },
        "ocr_then_extract": {
            "api": "/processor/ocr → /extraction/extract",
            "cost_per_call": 24,  # OCR + extract
            "latency_p50_ms": 8000,
        },
    },

    # Verification methods
    "verifiers": {
        "det_c017": {"cost": 0, "latency_ms": 0, "requires_torch": False},
        "nli_c026": {"cost": 0, "latency_ms": 50, "requires_torch": True},
        "typed_dag": {"cost": "variable", "latency_ms": "variable", "requires_torch": False},
    },

    # Optimization surface (what cogymkernel mutates)
    "search_space": {
        "auto_approve_threshold": (0.85, 0.99),
        "human_review_threshold": (0.50, 0.84),
        "reject_threshold": (0.0, 0.49),
        "verifier_per_type": {
            "invoice": ["det_c017", "nli_c026"],
            "contract": ["typed_dag", "nli_c026"],
            "receipt": ["det_c017"],
            "kyc_id": ["det_c017", "nli_c026"],
            "trade": ["det_c017"],
            "medical": ["nli_c026"],
        },
        "cross_doc_verify": True,  # verify fields across related docs
    },

    # Quality gates (hard constraints, not objectives)
    "gates": {
        "min_accuracy": 0.80,          # overall extraction accuracy
        "min_auto_approve_accuracy": 0.95,  # if auto-approved, must be 95%+ correct
        "max_false_positive_rate": 0.05,    # max 5% of auto-approved are wrong
        "max_cost_per_doc": 0.05,           # max $0.05 per document
        "max_latency_p50": 10000,           # max 10s per document
    },

    # Objectives (lexicographic, not scalar)
    "objectives": [
        ("auto_approve_rate", "maximize"),      # efficiency
        ("accuracy", "maximize"),                # correctness
        ("cost_per_doc", "minimize"),            # economy
        ("latency_p50", "minimize"),             # speed
    ],
}
```

---

## Candidate Configuration

Each candidate is a specific threshold + method mapping:

```python
@dataclass
class ProofDeskCandidate:
    # Thresholds (cogymkernel mutates these)
    auto_approve_threshold: float = 0.92
    human_review_threshold: float = 0.65
    reject_threshold: float = 0.30

    # Method selection per document type
    method_per_type: dict = field(default_factory=lambda: {
        "invoice": "nutrient_extract",
        "contract": "nutrient_extract",
        "receipt": "ocr_then_extract",
        "kyc_id": "nutrient_extract",
        "trade": "nutrient_extract",
        "medical": "nutrient_extract",
    })

    # Verifier selection per document type
    verifier_per_type: dict = field(default_factory=lambda: {
        "invoice": "det_c017",
        "contract": "typed_dag",
        "receipt": "det_c017",
        "kyc_id": "det_c017",
        "trade": "det_c017",
        "medical": "nli_c026",
    })

    # Whether to cross-verify related documents
    cross_doc_verify: bool = True
```

---

## Evaluation Flow

```
CANDIDATE (thresholds + methods)
    ↓
FOR EACH document in test set:
    ↓
    1. EXTRACT (Nutrient API with candidate's method)
    2. VERDICT (FactMiner with candidate's verifier)
    3. CLASSIFY:
       confidence >= auto_approve_threshold → AUTO-APPROVE
       confidence >= human_review_threshold  → HUMAN_REVIEW
       else                                 → REJECT
    4. COMPARE to ground truth
    5. RECORD: {extracted, verdict, decision, correct, cost, latency}
    ↓
AGGREGATE:
    accuracy = correct / total
    auto_approve_rate = auto_approved / total
    false_positive_rate = wrong_auto_approved / auto_approved
    cost_per_doc = total_credits / total_docs
    latency_p50 = median(latencies)
    ↓
GATE CHECK:
    accuracy >= min_accuracy?             → PASS/FAIL
    auto_approve_accuracy >= 0.95?        → PASS/FAIL
    false_positive_rate <= 0.05?          → PASS/FAIL
    cost_per_doc <= max_cost?             → PASS/FAIL
    latency_p50 <= max_latency?           → PASS/FAIL
    ↓
RECEIPT (content-addressed RunReceipt)
```

---

## cogymkernel Integration

### 1. Register ProofDesk as a world

```python
# cogym_kernel/worlds/proofdesk.py

from cogym_kernel.worlds.registry import register_world
from .spec import PROOFDESK_WORLDPACK

register_world("proofdesk", PROOFDESK_WORLDPACK)
```

### 2. Define the evolution recipe

```python
# cogym_kernel/evo/proofdesk_recipe.py

RECIPE = {
    "name": "proofdesk-threshold-evolution",
    "world": "proofdesk",
    "generations": 50,
    "population_size": 20,
    "mutation": {
        "type": "continuous",
        "fields": ["auto_approve_threshold", "human_review_threshold"],
        "range": 0.05,  # ±5% per mutation
    },
    "selection": {
        "type": "lexicographic",
        "objectives": ["auto_approve_rate", "accuracy", "cost_per_doc"],
    },
    "gates": "proofdesk_quality_gates",
}
```

### 3. Run evolution

```bash
cg run --world proofdesk --recipe proofdesk-threshold-evolution --seed 42
```

### 4. Get RunReceipt

```json
{
  "run_id": "blake3:9d455f9e90ff19c7...",
  "world": "proofdesk",
  "recipe": "proofdesk-threshold-evolution",
  "best_candidate": {
    "auto_approve_threshold": 0.91,
    "human_review_threshold": 0.62,
    "auto_approve_rate": 0.78,
    "accuracy": 0.94,
    "cost_per_doc": 0.018,
    "latency_p50_ms": 4200
  },
  "gate_results": {
    "min_accuracy": "PASS (0.94 >= 0.80)",
    "auto_approve_accuracy": "PASS (0.97 >= 0.95)",
    "false_positive_rate": "PASS (0.03 <= 0.05)",
    "cost_per_doc": "PASS ($0.018 <= $0.05)",
    "latency_p50": "PASS (4200ms <= 10000ms)"
  },
  "merkle_root": "sha256:abc123..."
}
```

---

## What Judges See

### The Demo (2-4 minutes)

**0:00-0:20** — "We benchmarked confidence scoring across 6 document types using cogymkernel optimization."

**0:20-0:50** — Show the optimization loop: candidates mutate → evaluate → select. Display the frontier of accuracy vs auto-approve rate.

**0:50-1:20** — Show results table:
```
Type        Accuracy  Auto-Approve  FP Rate  Cost
Invoice     96.8%     89%           3.2%     $0.015
Contract    84.2%     62%           4.1%     $0.012
Receipt     71.4%     31%           2.8%     $0.018
KYC         98.1%     94%           1.9%     $0.015
Trade       93.5%     78%           3.5%     $0.015
Medical     90.2%     71%           4.0%     $0.018
```

**1:20-1:50** — Show the agent processing a messy folder. Documents flow through extraction → verification → auto-approve or human review.

**1:50-2:20** — Show the audit trail. Every decision hash-chained. Merkle proof for any event. Signed attestations.

**2:20-2:40** — "The system knows what it knows, knows what it doesn't know, and can prove it."

### The One-Line Pitch

**"ProofDesk benchmarks confidence scoring across 6 document types — it knows when to trust itself and when to ask a human, with a tamper-evident audit trail proving every decision."**

---

## Files to Build

| File | What | Lines |
|------|------|-------|
| `src/benchmark/confidence_world.py` | ProofDesk worldpack for cogymkernel | ~150 |
| `src/benchmark/confidence_candidate.py` | Candidate configuration dataclass | ~50 |
| `src/benchmark/confidence_eval.py` | Evaluation loop (extract → verdict → classify → compare) | ~200 |
| `src/benchmark/confidence_gates.py` | Quality gates (accuracy, FP rate, cost, latency) | ~80 |
| `src/benchmark/confidence_report.py` | Generate benchmark report + RunReceipt | ~100 |
| `tests/test_confidence_benchmark.py` | Tests for the benchmark system | ~150 |
