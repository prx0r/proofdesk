"""HarnessSpec — the evolvable unit is the whole verification config.

A HarnessSpec fully determines verification behavior. The benchmark
mutates specs; the loop evaluates them on the same frozen claims.
Quality gate = accuracy >= floor; optimization targets = cost, latency.

Adapted from cogymkernel's evolution lab pattern.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from .ids import content_id


@dataclass(frozen=True)
class HarnessSpec:
    """One complete verification strategy. This is what gets evolved."""

    name: str

    # --- Extraction config ---
    extraction_mode: str = "deterministic"  # deterministic | structured_api | hybrid
    confidence_threshold: float = 0.8       # min confidence to admit a fact
    entity_normalization: str = "aggressive"  # aggressive | moderate | strict

    # --- Check config ---
    checks_enabled: tuple = ("all",)        # ("all",) or specific check names
    check_severity_filter: str = "all"      # all | blocker | warning+
    parallel_checks: bool = True            # run checks concurrently
    early_stop_on_fail: bool = False        # stop after first failure

    # --- Source routing ---
    primary_source: str = "structured"      # structured | web_search | hybrid
    web_search_fallback: bool = True        # use web if structured fails
    max_search_queries: int = 3             # queries per fact
    search_depth: str = "fast"              # fast | standard | deep

    # --- Escalation ---
    escalate_to_llm: bool = False           # use LLM for ambiguous cases
    llm_confidence_threshold: float = 0.7   # below this, escalate
    adversarial_probe: bool = False         # counter-search on weak SUPPORTED

    # --- Budget ---
    max_retrieval_calls: int = 10           # max external API calls per episode
    max_latency_ms: float = 5000.0          # hard latency budget
    max_cost_usd: float = 0.05             # hard cost budget per episode

    # --- Quality gates ---
    accuracy_floor: float = 0.95            # minimum accuracy to pass gate
    false_positive_ceiling: float = 0.02    # max false positive rate
    defect_detection_floor: float = 0.8     # min defect detection rate

    # --- Domain-specific ---
    cross_validation: bool = False           # cross-validate extracted fields
    checks_per_fact: int = 1                # checks to run per extracted fact
    iterative_retrieval: bool = False       # FIRE-style iterative retrieval
    max_retrieval_rounds: int = 3           # max rounds for iterative retrieval
    typed_verification: bool = False        # different strategy per clause type
    clause_type_strategies: dict = field(default_factory=dict)  # type -> strategy
    evidence_binding: bool = False          # GAVEL-style evidence binding
    mechanized_scrutiny: bool = False       # mechanized citation validation
    kg_first: bool = False                  # KG-first approach
    cross_document_reconciliation: bool = False  # reconcile across docs
    coverage_matrix: bool = False           # build coverage matrix
    date_arithmetic: bool = False           # verify date relationships
    interpret_exclusions: bool = False      # interpret policy exclusions
    validate_against_web: bool = False      # validate fields against web

    @property
    def spec_id(self) -> str:
        return content_id("harness", {
            "name": self.name,
            "extraction_mode": self.extraction_mode,
            "checks_enabled": self.checks_enabled,
            "primary_source": self.primary_source,
            "escalate_to_llm": self.escalate_to_llm,
            "adversarial_probe": self.adversarial_probe,
        })

    def to_dict(self) -> dict:
        d = asdict(self)
        d["spec_id"] = self.spec_id
        return d


# --- Seed population: named strategies ---

STRATEGIES: dict[str, dict] = {
    "baseline": {
        "name": "baseline",
        "description": "Current ProofDesk pipeline — check everything, no escalation",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": False,
        "escalate_to_llm": False,
        "adversarial_probe": False,
    },
    "fast_fail": {
        "name": "fast_fail",
        "description": "Stop on first failure, skip remaining checks",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": False,
        "early_stop_on_fail": True,
        "primary_source": "structured",
        "web_search_fallback": False,
        "escalate_to_llm": False,
        "adversarial_probe": False,
    },
    "blockers_only": {
        "name": "blockers_only",
        "description": "Only run BLOCKER-severity checks, skip warnings",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "check_severity_filter": "blocker",
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": False,
        "escalate_to_llm": False,
        "adversarial_probe": False,
    },
    "web_enhanced": {
        "name": "web_enhanced",
        "description": "Structured checks + web search fallback for ambiguous facts",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": True,
        "max_search_queries": 2,
        "search_depth": "fast",
        "escalate_to_llm": False,
        "adversarial_probe": False,
    },
    "adversarial": {
        "name": "adversarial",
        "description": "Full checks + counter-search on weak SUPPORTED verdicts",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": True,
        "adversarial_probe": True,
        "max_search_queries": 3,
        "escalate_to_llm": False,
    },
    "llm_escalation": {
        "name": "llm_escalation",
        "description": "Deterministic first, escalate ambiguous cases to LLM judge",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": True,
        "escalate_to_llm": True,
        "llm_confidence_threshold": 0.7,
        "adversarial_probe": True,
    },
    "kitchen_sink": {
        "name": "kitchen_sink",
        "description": "Everything enabled — max accuracy, higher cost",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "parallel_checks": True,
        "primary_source": "hybrid",
        "web_search_fallback": True,
        "max_search_queries": 5,
        "search_depth": "standard",
        "escalate_to_llm": True,
        "llm_confidence_threshold": 0.6,
        "adversarial_probe": True,
    },
    "minimal": {
        "name": "minimal",
        "description": "Fewest checks, fastest, cheapest — tests the floor",
        "extraction_mode": "deterministic",
        "checks_enabled": ("quote_arithmetic", "spend_match"),
        "check_severity_filter": "blocker",
        "parallel_checks": True,
        "primary_source": "structured",
        "web_search_fallback": False,
        "escalate_to_llm": False,
        "adversarial_probe": False,
    },
}


def make_spec(name: str) -> HarnessSpec:
    """Create a HarnessSpec from a named strategy."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    # Filter out non-HarnessSpec fields like 'description'
    params = {k: v for k, v in STRATEGIES[name].items()
              if k in HarnessSpec.__dataclass_fields__}
    return HarnessSpec(**params)


def mutate_spec(spec: HarnessSpec, rng=None) -> HarnessSpec:
    """Randomly mutate one parameter of a spec."""
    import random
    rng = rng or random.Random()

    params = [
        "confidence_threshold", "check_severity_filter", "parallel_checks",
        "early_stop_on_fail", "primary_source", "web_search_fallback",
        "max_search_queries", "search_depth", "escalate_to_llm",
        "llm_confidence_threshold", "adversarial_probe", "max_retrieval_calls",
    ]

    param = rng.choice(params)
    current = getattr(spec, param)

    mutations = {
        "confidence_threshold": lambda: round(rng.uniform(0.5, 0.99), 2),
        "check_severity_filter": lambda: rng.choice(["all", "blocker", "warning+"]),
        "parallel_checks": lambda: not current,
        "early_stop_on_fail": lambda: not current,
        "primary_source": lambda: rng.choice(["structured", "web_search", "hybrid"]),
        "web_search_fallback": lambda: not current,
        "max_search_queries": lambda: rng.randint(1, 5),
        "search_depth": lambda: rng.choice(["fast", "standard", "deep"]),
        "escalate_to_llm": lambda: not current,
        "llm_confidence_threshold": lambda: round(rng.uniform(0.5, 0.9), 2),
        "adversarial_probe": lambda: not current,
        "max_retrieval_calls": lambda: rng.randint(3, 20),
    }

    new_val = mutations[param]()
    return HarnessSpec(**{**asdict(spec), param: new_val, "name": f"{spec.name}_mutant"})
