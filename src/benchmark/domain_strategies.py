"""Domain-specific harness strategies based on frontier research.

Each harness encodes what the literature says works best for that document type.
The benchmark evolves which combination of strategies performs best.
"""

from __future__ import annotations

from .harness import HarnessSpec


# === RECEIPT EXTRACTION (SROIE/CORD) ===
# Literature: LayoutLMv3 SOTA at 97% F1, but requires training.
# Zero-shot: LLM-TKIE at 83.9% F1, Donut at 98% with spatial prompts.
# Our baseline: 92.5% with simple text search.
# Strategy: structured field matching + date/amount normalization + cross-field validation.

RECEIPT_STRATEGIES = {
    "receipt_text_search": {
        "name": "receipt_text_search",
        "description": "Current approach: simple text search for known field patterns",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "confidence_threshold": 0.8,
    },
    "receipt_structured_api": {
        "name": "receipt_structured_api",
        "description": "Use Nutrient DWS extract endpoint with receipt schema",
        "extraction_mode": "structured_api",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "confidence_threshold": 0.85,
        "max_retrieval_calls": 1,
    },
    "receipt_cross_validate": {
        "name": "receipt_cross_validate",
        "description": "Extract + cross-validate: line items sum to total, date within range",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "cross_validation": True,
        "checks_per_fact": 2,
    },
    "receipt_llm_fallback": {
        "name": "receipt_llm_fallback",
        "description": "Deterministic first, LLM for ambiguous fields (dates, amounts)",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "escalate_to_llm": True,
        "llm_confidence_threshold": 0.7,
    },
}


# === CONTRACT REVIEW (CUAD) ===
# Literature: DeBERTa fine-tuned at 87.8%, Legal-BERT at 92.3% span F1.
# Iterative retrieval improves exact match 68.7% -> 74.4%.
# CLAUSE benchmark: 7500 perturbed contracts, typed hallucination profiles.
# Our baseline: 78.4% with simple text search.
# Strategy: clause-aware extraction + cross-reference following + typed verification.

CONTRACT_STRATEGIES = {
    "contract_text_search": {
        "name": "contract_text_search",
        "description": "Current: simple substring match for clause detection",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "confidence_threshold": 0.8,
    },
    "contract_iterative_retrieval": {
        "name": "contract_iterative_retrieval",
        "description": "Iterative retrieval: LLM directs each retrieval step (FIRE-style)",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "hybrid",
        "web_search_fallback": True,
        "max_search_queries": 5,
        "search_depth": "standard",
        "iterative_retrieval": True,
        "max_retrieval_rounds": 3,
    },
    "contract_typed_verification": {
        "name": "contract_typed_verification",
        "description": "Different verification per clause type (LegalHalluLens-style)",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "typed_verification": True,
        "clause_type_strategies": {
            "numeric": "exact_match",
            "temporal": "date_parsing",
            "obligation": "semantic_nli",
            "factual": "web_search",
        },
    },
    "contract_evidence_contract": {
        "name": "contract_evidence_contract",
        "description": "GAVEL-style: every claim bound to explicit evidence spans",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "evidence_binding": True,
        "mechanized_scrutiny": True,
    },
    "contract_hybrid_kg": {
        "name": "contract_hybrid_kg",
        "description": "KG-first for structured clauses, web fallback for ambiguous ones",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "hybrid",
        "web_search_fallback": True,
        "kg_first": True,
        "max_search_queries": 3,
    },
}


# === TRADE DOCUMENTS ===
# Literature: less specific SOTA, but cross-document consistency is well-studied.
# Our baseline: 100% on synthetic, untested on real.
# Strategy: field normalization + cross-document reconciliation + HS code validation.

TRADE_STRATEGIES = {
    "trade_text_search": {
        "name": "trade_text_search",
        "description": "Current: simple field matching across documents",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
    },
    "trade_cross_doc_reconcile": {
        "name": "trade_cross_doc_reconcile",
        "description": "Extract from all docs, reconcile across invoice/BOL/cert",
        "extraction_mode": "structured_api",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "cross_document_reconciliation": True,
        "entity_normalization": "moderate",
    },
    "trade_web_validate": {
        "name": "trade_web_validate",
        "description": "Validate HS codes, company names, and addresses against web",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "hybrid",
        "web_search_fallback": True,
        "validate_against_web": True,
    },
}


# === INSURANCE CLAIMS ===
# Literature: less specific, but policy-vs-claim verification is well-studied.
# Our baseline: 100% on synthetic, untested on real.
# Strategy: policy term extraction + coverage matrix + date arithmetic.

INSURANCE_STRATEGIES = {
    "insurance_text_search": {
        "name": "insurance_text_search",
        "description": "Current: simple field matching for amounts and dates",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
    },
    "insurance_coverage_matrix": {
        "name": "insurance_coverage_matrix",
        "description": "Build coverage matrix: claim type x policy terms x limits",
        "extraction_mode": "structured_api",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "coverage_matrix": True,
        "date_arithmetic": True,
    },
    "insurance_llm_interpret": {
        "name": "insurance_llm_interpret",
        "description": "LLM interprets ambiguous policy language + exclusion clauses",
        "extraction_mode": "deterministic",
        "checks_enabled": ("all",),
        "primary_source": "structured",
        "escalate_to_llm": True,
        "llm_confidence_threshold": 0.6,
        "interpret_exclusions": True,
    },
}


# === ALL STRATEGIES ===

ALL_STRATEGIES = {
    **RECEIPT_STRATEGIES,
    **CONTRACT_STRATEGIES,
    **TRADE_STRATEGIES,
    **INSURANCE_STRATEGIES,
}


def get_strategies_for_domain(domain: str) -> dict:
    """Get all strategies applicable to a domain."""
    prefix = domain.lower()
    return {k: v for k, v in ALL_STRATEGIES.items() if k.startswith(prefix)}
