"""Document generator for SigningWorld.

Generates documents with known ground truth and Nutrient-style confidence
signals. Hard worlds where naive signing heuristics fail.
"""

from __future__ import annotations

import hashlib
import random
import numpy as np
from typing import Any

from .signing_world import (
    Document, DocField, Verdict,
    ConfidenceSignal, SigningWorld, SigningWorldManifest,
)


def _hash_id(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


# ─── Field generators by doc type ────────────────────────────────────

INVOICE_FIELDS = [
    ("vendor_name", ["Acme Corp", "Globex Inc", "Initech", "Umbrella LLC", "Stark Industries"]),
    ("invoice_date", ["2026-01-15", "2026-02-20", "2026-03-10", "2026-04-05"]),
    ("total_amount", ["$1,250.00", "$3,400.00", "$890.50", "$12,000.00", "$450.75"]),
    ("tax_amount", ["$100.00", "$272.00", "$71.24", "$960.00", "$36.06"]),
    ("po_number", ["PO-2026-001", "PO-2026-042", "PO-2026-103", "PO-2026-077"]),
    ("payment_terms", ["Net 30", "Net 15", "Net 60", "Due on Receipt"]),
    ("line_items", ["3 widgets @ $400", "1 service @ $3,400", "12 parts @ $74.21"]),
    ("currency", ["USD", "EUR", "GBP"]),
]

CONTRACT_FIELDS = [
    ("party_a", ["Northstar Data Systems", "Quantum Computing Corp", "Nexus Technologies"]),
    ("party_b", ["Widgets Inc", "Services LLC", "Parts Co"]),
    ("contract_value", ["$42,500", "$125,000", "$8,900", "$250,000"]),
    ("start_date", ["2026-01-01", "2026-06-01", "2026-09-01"]),
    ("end_date", ["2026-12-31", "2027-06-01", "2027-12-31"]),
    ("auto_renewal", ["Yes - 90 day notice", "No", "Yes - 30 day notice"]),
]

CLAIM_FIELDS = [
    ("claimant", ["John Smith", "Jane Doe", "ACME Insurance", "Global Claims Inc"]),
    ("incident_date", ["2026-03-15", "2026-05-22", "2026-07-01"]),
    ("claim_amount", ["$5,000", "$25,000", "$150,000", "$1,200"]),
    ("policy_number", ["POL-2025-1001", "POL-2025-2002", "POL-2025-3003"]),
    ("coverage_type", ["Liability", "Property", "Workers Comp", "Auto"]),
    ("deductible", ["$500", "$1,000", "$2,500"]),
    ("adjuster_notes", ["Standard claim", "Needs investigation", "Clear coverage"]),
]

FIELD_TEMPLATES = {
    "invoice": INVOICE_FIELDS,
    "contract": CONTRACT_FIELDS,
    "claim": CLAIM_FIELDS,
}


def _generate_fields(
    rng: random.Random,
    doc_type: str,
    corruption_rate: float,
) -> list[DocField]:
    templates = FIELD_TEMPLATES[doc_type]
    fields = []
    for name, values in templates:
        correct_val = rng.choice(values)
        corrupted = rng.random() < corruption_rate
        if corrupted:
            if "amount" in name or "value" in name:
                try:
                    amt = float(correct_val.replace("$", "").replace(",", ""))
                    corrupted_val = f"${amt * rng.uniform(1.5, 3.0):,.2f}"
                except ValueError:
                    corrupted_val = rng.choice(values)
            elif "date" in name:
                corrupted_val = "2099-12-31"
            else:
                corrupted_val = rng.choice(values)
            fields.append(DocField(name, corrupted_val, False))
        else:
            fields.append(DocField(name, correct_val, True))
    return fields


def _generate_signals(
    rng: random.Random,
    np_rng: np.random.RandomState,
    fields: list[DocField],
    verdict: Verdict,
    noise: float,
) -> ConfidenceSignal:
    accuracy = sum(f.correct for f in fields) / max(1, len(fields))

    # Core signals correlated with ground truth
    base_conf = accuracy * 0.7 + np_rng.normal(0, noise)
    nutrient_confidence = max(0.0, min(1.0, base_conf))

    # Match labels
    if verdict == Verdict.SAFE:
        match = rng.choice(["id_match", "id_match", "id_match", "fuzzy_match", "not_found"])
    elif verdict == Verdict.RISKY:
        match = rng.choice(["id_match", "fuzzy_match", "fuzzy_match", "not_found"])
    else:
        match = rng.choice(["fuzzy_match", "not_found", "not_found", "not_found"])
    match_score = {"id_match": 1.0, "fuzzy_match": 0.5, "not_found": 0.0}[match]

    grounding = max(0.0, min(1.0, accuracy * 0.8 + np_rng.normal(0, noise * 0.8)))
    margin = max(0.0, min(1.0, {
        Verdict.SAFE: 0.7,
        Verdict.RISKY: 0.4,
        Verdict.FRAUDULENT: 0.2,
    }[verdict] + np_rng.normal(0, noise)))

    consistency = max(0.0, min(1.0, {
        Verdict.SAFE: 0.85,
        Verdict.RISKY: 0.5,
        Verdict.FRAUDULENT: 0.3,
    }[verdict] + np_rng.normal(0, noise)))

    completeness = max(0.0, min(1.0, accuracy * 0.9 + np_rng.normal(0, noise * 0.3)))

    field_confs = [
        max(0.0, min(1.0, (1.0 if f.correct else 0.2) + np_rng.normal(0, noise)))
        for f in fields
    ]
    avg_fc = sum(field_confs) / len(field_confs) if field_confs else 0.0
    fc_var = sum((c - avg_fc) ** 2 for c in field_confs) / len(field_confs) if field_confs else 0.0

    return ConfidenceSignal(
        nutrient_confidence=nutrient_confidence,
        match_label=match,
        match_score=match_score,
        grounding_score=grounding,
        margin_score=margin,
        cross_doc_consistency=consistency,
        field_completeness=completeness,
        avg_field_confidence=avg_fc,
        confidence_variance=fc_var,
    )


# ─── Hard World Generators ───────────────────────────────────────────

def _gen_base_rate_shift(rng: random.Random, n: int, seed: int) -> tuple[list[Document], list[ConfidenceSignal]]:
    """High base rate of fraud — naive signer sees 'looks normal' and signs."""
    np_rng = np.random.RandomState(seed)
    docs, signals = [], []
    corruption_rate = rng.uniform(0.15, 0.4)
    for i in range(n):
        risk = rng.random()
        if risk > 0.7:
            verdict = Verdict.FRAUDULENT
            corr = corruption_rate * rng.uniform(2.0, 4.0)
        elif risk > 0.4:
            verdict = Verdict.RISKY
            corr = corruption_rate * rng.uniform(1.0, 2.0)
        else:
            verdict = Verdict.SAFE
            corr = corruption_rate * rng.uniform(0.0, 0.5)
        doc_type = rng.choice(["invoice", "contract", "claim"])
        fields = _generate_fields(rng, doc_type, min(corr, 0.8))
        doc = Document(
            doc_id=_hash_id(f"brs_{seed}_{i}"),
            doc_type=doc_type,
            fields=tuple(fields),
            verdict=verdict,
            difficulty=0.8,
            base_rate_risk=rng.uniform(0.3, 0.7),
            hard_world="base_rate_shift",
        )
        sig = _generate_signals(rng, np_rng, fields, verdict, 0.12)
        docs.append(doc)
        signals.append(sig)
    return docs, signals


def _gen_confounded_choice(rng: random.Random, n: int, seed: int) -> tuple[list[Document], list[ConfidenceSignal]]:
    """Correlated signals look normal but causal analysis reveals mismatch."""
    np_rng = np.random.RandomState(seed)
    docs, signals = [], []
    for i in range(n):
        verdict = rng.choices([Verdict.SAFE, Verdict.RISKY, Verdict.FRAUDULENT], weights=[0.3, 0.4, 0.3])[0]
        corr = rng.uniform(0.1, 0.3)
        doc_type = rng.choice(["invoice", "contract", "claim"])
        fields = _generate_fields(rng, doc_type, corr)
        doc = Document(
            doc_id=_hash_id(f"cc_{seed}_{i}"),
            doc_type=doc_type,
            fields=tuple(fields),
            verdict=verdict,
            difficulty=0.7,
            base_rate_risk=rng.uniform(0.1, 0.3),
            hard_world="confounded_choice",
        )
        sig = _generate_signals(rng, np_rng, fields, verdict, 0.12)
        docs.append(doc)
        signals.append(sig)
    return docs, signals


def _gen_regime_flip(rng: random.Random, n: int, seed: int) -> tuple[list[Document], list[ConfidenceSignal]]:
    """Past patterns that worked now indicate risk."""
    np_rng = np.random.RandomState(seed)
    docs, signals = [], []
    for i in range(n):
        verdict = rng.choices([Verdict.SAFE, Verdict.FRAUDULENT], weights=[0.4, 0.6])[0]
        corr = rng.uniform(0.05, 0.3)
        doc_type = rng.choice(["invoice", "contract", "claim"])
        fields = _generate_fields(rng, doc_type, corr)
        doc = Document(
            doc_id=_hash_id(f"rf_{seed}_{i}"),
            doc_type=doc_type,
            fields=tuple(fields),
            verdict=verdict,
            difficulty=0.85,
            base_rate_risk=rng.uniform(0.2, 0.5),
            hard_world="regime_flip",
        )
        sig = _generate_signals(rng, np_rng, fields, verdict, 0.12)
        docs.append(doc)
        signals.append(sig)
    return docs, signals


def _gen_costly_evidence(rng: random.Random, n: int, seed: int) -> tuple[list[Document], list[ConfidenceSignal]]:
    """Additional verification helps but costs more than improvement."""
    np_rng = np.random.RandomState(seed)
    docs, signals = [], []
    for i in range(n):
        verdict = rng.choices([Verdict.SAFE, Verdict.RISKY], weights=[0.6, 0.4])[0]
        corr = rng.uniform(0.0, 0.15)
        doc_type = rng.choice(["invoice", "contract", "claim"])
        fields = _generate_fields(rng, doc_type, corr)
        doc = Document(
            doc_id=_hash_id(f"ce_{seed}_{i}"),
            doc_type=doc_type,
            fields=tuple(fields),
            verdict=verdict,
            difficulty=0.5,
            base_rate_risk=rng.uniform(0.05, 0.2),
            hard_world="costly_evidence",
        )
        sig = _generate_signals(rng, np_rng, fields, verdict, 0.12)
        docs.append(doc)
        signals.append(sig)
    return docs, signals


def _gen_difficulty_weighted(rng: random.Random, n: int, seed: int) -> tuple[list[Document], list[ConfidenceSignal]]:
    """Simple heuristic looks right but analysis reveals different answer."""
    np_rng = np.random.RandomState(seed)
    docs, signals = [], []
    for i in range(n):
        verdict = rng.choices([Verdict.SAFE, Verdict.RISKY, Verdict.FRAUDULENT], weights=[0.5, 0.3, 0.2])[0]
        corr = rng.uniform(0.1, 0.3)
        doc_type = rng.choice(["invoice", "contract", "claim"])
        fields = _generate_fields(rng, doc_type, corr)
        doc = Document(
            doc_id=_hash_id(f"dwr_{seed}_{i}"),
            doc_type=doc_type,
            fields=tuple(fields),
            verdict=verdict,
            difficulty=0.65,
            base_rate_risk=rng.uniform(0.1, 0.3),
            hard_world="difficulty_weighted_rank",
        )
        sig = _generate_signals(rng, np_rng, fields, verdict, 0.12)
        docs.append(doc)
        signals.append(sig)
    return docs, signals


HARD_WORLD_GENERATORS = {
    "base_rate_shift": _gen_base_rate_shift,
    "confounded_choice": _gen_confounded_choice,
    "regime_flip": _gen_regime_flip,
    "costly_evidence": _gen_costly_evidence,
    "difficulty_weighted_rank": _gen_difficulty_weighted,
}


def generate_signing_world(
    hard_world: str,
    n_docs: int = 200,
    seed: int = 42,
    noise: float = 0.12,
) -> SigningWorld:
    """Generate a SigningWorld for one hard world family."""
    rng = random.Random(seed)
    gen = HARD_WORLD_GENERATORS[hard_world]
    docs, sigs = gen(rng, n_docs, seed)
    manifest = SigningWorldManifest(
        name=f"signing_{hard_world}",
        hard_world=hard_world,
        n_docs=n_docs,
        seed=seed,
    )
    return SigningWorld(manifest=manifest, documents=docs, signals=sigs)


def generate_all_worlds(
    n_per_world: int = 200,
    seed: int = 42,
) -> dict[str, SigningWorld]:
    """Generate one SigningWorld per hard world family."""
    worlds = {}
    for i, hw in enumerate(HARD_WORLD_GENERATORS):
        worlds[hw] = generate_signing_world(hw, n_per_world, seed + i * 1000)
    return worlds
