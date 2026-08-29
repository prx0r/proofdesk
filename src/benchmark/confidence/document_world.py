"""DocumentWorld — synthetic documents with known ground truth for signing decisions.

Hard world families where naive sign-refuse heuristics fail:
  1. base_rate_shift — looks good but fraud rate is high
  2. confounded_choice — signals suggest approval, analysis says refuse
  3. regime_flip — past patterns now indicate risk
  4. costly_evidence — verification costs more than improvement
  5. difficulty_weighted_rank — simple heuristic wrong, analysis right
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocumentVerdict(Enum):
    SAFE = "safe"
    RISKY = "risky"
    FRAUDULENT = "fraudulent"


class HardWorld(Enum):
    BASE_RATE_SHIFT = "base_rate_shift"
    CONFOUNDED_CHOICE = "confounded_choice"
    REGIME_FLIP = "regime_flip"
    COSTLY_EVIDENCE = "costly_evidence"
    DIFFICULTY_WEIGHTED_RANK = "difficulty_weighted_rank"


@dataclass
class DocumentField:
    name: str
    value: str
    ground_truth_correct: bool
    source_page: int = 0
    bbox: dict = field(default_factory=lambda: {"x": 0, "y": 0, "w": 100, "h": 20})


@dataclass
class SigningDocument:
    doc_id: str
    doc_type: str  # invoice, contract, claim, procurement
    fields: list[DocumentField]
    verdict: DocumentVerdict
    hard_world: HardWorld
    difficulty: float  # 0-1, how hard is this for a naive signer
    base_rate_risk: float  # prior probability of fraud in this category
    metadata: dict = field(default_factory=dict)

    @property
    def should_sign(self) -> bool:
        return self.verdict == DocumentVerdict.SAFE

    @property
    def field_accuracy(self) -> float:
        if not self.fields:
            return 0.0
        return sum(1 for f in self.fields if f.ground_truth_correct) / len(self.fields)


def _hash_id(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


# --- Document generators per hard world ---

def _gen_invoice_fields(rng: random.Random, n_fields: int = 8,
                        corruption_rate: float = 0.0) -> list[DocumentField]:
    """Generate invoice fields, some corrupted."""
    templates = [
        ("vendor_name", ["Acme Corp", "Globex Inc", "Initech", "Umbrella LLC", "Stark Industries"]),
        ("invoice_date", ["2026-01-15", "2026-02-20", "2026-03-10", "2026-04-05"]),
        ("total_amount", ["$1,250.00", "$3,400.00", "$890.50", "$12,000.00", "$450.75"]),
        ("tax_amount", ["$100.00", "$272.00", "$71.24", "$960.00", "$36.06"]),
        ("po_number", ["PO-2026-001", "PO-2026-042", "PO-2026-103", "PO-2026-077"]),
        ("payment_terms", ["Net 30", "Net 15", "Net 60", "Due on Receipt"]),
        ("line_items", ["3 widgets @ $400", "1 service @ $3,400", "12 parts @ $74.21"]),
        ("currency", ["USD", "EUR", "GBP"]),
    ]
    fields = []
    for name, values in templates[:n_fields]:
        correct_val = rng.choice(values)
        is_corrupted = rng.random() < corruption_rate
        if is_corrupted:
            # Corrupt: shift amount, change date, swap vendor
            if "amount" in name:
                amt = float(correct_val.replace("$", "").replace(",", ""))
                corrupted = f"${amt * rng.uniform(1.5, 3.0):,.2f}"
                fields.append(DocumentField(name, corrupted, False))
            elif "date" in name:
                fields.append(DocumentField(name, "2099-12-31", False))
            else:
                fields.append(DocumentField(name, rng.choice(values), False))
        else:
            fields.append(DocumentField(name, correct_val, True))
    return fields


def _gen_contract_fields(rng: random.Random, n_fields: int = 6,
                         corruption_rate: float = 0.0) -> list[DocumentField]:
    templates = [
        ("party_a", ["Northstar Data Systems", "Quantum Computing Corp", "Nexus Technologies"]),
        ("party_b", ["Widgets Inc", "Services LLC", "Parts Co"]),
        ("contract_value", ["$42,500", "$125,000", "$8,900", "$250,000"]),
        ("start_date", ["2026-01-01", "2026-06-01", "2026-09-01"]),
        ("end_date", ["2026-12-31", "2027-06-01", "2027-12-31"]),
        ("auto_renewal", ["Yes - 90 day notice", "No", "Yes - 30 day notice"]),
    ]
    fields = []
    for name, values in templates[:n_fields]:
        correct_val = rng.choice(values)
        is_corrupted = rng.random() < corruption_rate
        if is_corrupted:
            if "value" in name:
                amt = float(correct_val.replace("$", "").replace(",", ""))
                fields.append(DocumentField(name, f"${amt * rng.uniform(0.1, 0.5):,.0f}", False))
            elif "date" in name:
                fields.append(DocumentField(name, "2025-01-01", False))
            else:
                fields.append(DocumentField(name, rng.choice(values), False))
        else:
            fields.append(DocumentField(name, correct_val, True))
    return fields


def _gen_claim_fields(rng: random.Random, n_fields: int = 7,
                      corruption_rate: float = 0.0) -> list[DocumentField]:
    templates = [
        ("claimant", ["John Smith", "Jane Doe", "ACME Insurance", "Global Claims Inc"]),
        ("incident_date", ["2026-03-15", "2026-05-22", "2026-07-01"]),
        ("claim_amount", ["$5,000", "$25,000", "$150,000", "$1,200"]),
        ("policy_number", ["POL-2025-1001", "POL-2025-2002", "POL-2025-3003"]),
        ("coverage_type", ["Liability", "Property", "Workers Comp", "Auto"]),
        ("deductible", ["$500", "$1,000", "$2,500"]),
        ("adjuster_notes", ["Standard claim", "Needs investigation", "Clear coverage"]),
    ]
    fields = []
    for name, values in templates[:n_fields]:
        correct_val = rng.choice(values)
        is_corrupted = rng.random() < corruption_rate
        if is_corrupted:
            if "amount" in name:
                amt = float(correct_val.replace("$", "").replace(",", ""))
                fields.append(DocumentField(name, f"${amt * rng.uniform(3.0, 10.0):,.0f}", False))
            else:
                fields.append(DocumentField(name, rng.choice(values), False))
        else:
            fields.append(DocumentField(name, correct_val, True))
    return fields


DOC_GENERATORS = {
    "invoice": _gen_invoice_fields,
    "contract": _gen_contract_fields,
    "claim": _gen_claim_fields,
}


def generate_world(
    n_docs: int = 1000,
    hard_world: HardWorld | None = None,
    corruption_rate: float = 0.15,
    seed: int = 42,
    doc_types: list[str] | None = None,
) -> list[SigningDocument]:
    """Generate a world of documents with known ground truth.

    If hard_world is None, generates across all 5 families.
    """
    rng = random.Random(seed)
    if doc_types is None:
        doc_types = ["invoice", "contract", "claim"]

    worlds = [hw for hw in HardWorld] if hard_world is None else [hard_world]
    docs_per_world = n_docs // len(worlds)
    docs = []

    for hw in worlds:
        for i in range(docs_per_world):
            doc_type = rng.choice(doc_types)
            gen = DOC_GENERATORS[doc_type]

            if hw == HardWorld.BASE_RATE_SHIFT:
                # High base rate of fraud — naive signer sees "looks normal" and signs
                actual_risk = rng.random()
                if actual_risk > 0.7:
                    verdict = DocumentVerdict.FRAUDULENT
                    corr = corruption_rate * rng.uniform(2.0, 4.0)
                elif actual_risk > 0.4:
                    verdict = DocumentVerdict.RISKY
                    corr = corruption_rate * rng.uniform(1.0, 2.0)
                else:
                    verdict = DocumentVerdict.SAFE
                    corr = corruption_rate * rng.uniform(0.0, 0.5)
                difficulty = 0.8  # hard because base rate is deceptive

            elif hw == HardWorld.CONFOUNDED_CHOICE:
                # Correlated signals (vendor name, date format) look normal
                # but causal analysis reveals mismatch
                verdict = rng.choices([DocumentVerdict.SAFE, DocumentVerdict.RISKY, DocumentVerdict.FRAUDULENT],
                                     weights=[0.3, 0.4, 0.3])[0]
                corr = corruption_rate * rng.uniform(0.5, 1.5)
                difficulty = 0.7

            elif hw == HardWorld.REGIME_FLIP:
                # Patterns that worked before now indicate risk
                # e.g., vendor that was safe is now compromised
                verdict = rng.choices([DocumentVerdict.SAFE, DocumentVerdict.FRAUDULENT],
                                     weights=[0.4, 0.6])[0]
                corr = corruption_rate * rng.uniform(0.3, 2.0)
                difficulty = 0.85

            elif hw == HardWorld.COSTLY_EVIDENCE:
                # Additional verification helps but costs more than the improvement
                verdict = rng.choices([DocumentVerdict.SAFE, DocumentVerdict.RISKY],
                                     weights=[0.6, 0.4])[0]
                corr = corruption_rate * rng.uniform(0.0, 0.3)
                difficulty = 0.5

            elif hw == HardWorld.DIFFICULTY_WEIGHTED_RANK:
                # Simple heuristic looks right but careful analysis reveals different answer
                verdict = rng.choices([DocumentVerdict.SAFE, DocumentVerdict.RISKY, DocumentVerdict.FRAUDULENT],
                                     weights=[0.5, 0.3, 0.2])[0]
                corr = corruption_rate * rng.uniform(0.5, 2.0)
                difficulty = 0.65

            fields = gen(rng, corruption_rate=min(corr, 0.8))

            doc = SigningDocument(
                doc_id=_hash_id(f"{hw.value}_{doc_type}_{i}_{seed}"),
                doc_type=doc_type,
                fields=fields,
                verdict=verdict,
                hard_world=hw,
                difficulty=difficulty,
                base_rate_risk=rng.uniform(0.1, 0.5),
                metadata={"world_index": i, "corruption_rate": corr},
            )
            docs.append(doc)

    return docs


def get_oracle_decision(doc: SigningDocument) -> bool:
    """The ground truth: should this document be signed?"""
    return doc.should_sign


def get_naive_decision(doc: SigningDocument) -> bool:
    """A naive heuristic: sign if >50% fields are correct."""
    return doc.field_accuracy > 0.5
