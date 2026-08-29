"""Synthetic test data generator — creates thousands of document bundles
with known ground truth for benchmarking.

Each bundle has:
- A set of documents with extracted fields
- Injected defects (wrong dates, mismatched totals, missing fields)
- Known ground truth labels for every check
- Domain metadata
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass
class SyntheticField:
    name: str
    value: Any
    raw_value: str
    source_doc: str
    confidence: float
    is_defect: bool = False
    defect_type: str = ""


@dataclass
class SyntheticBundle:
    bundle_id: str
    domain: str
    documents: list[dict]
    fields: list[SyntheticField]
    ground_truth: dict  # check_name -> {"expected": bool, "severity": str}
    defect_count: int
    defect_types: list[str]


# --- Generators per domain ---

def _random_company() -> str:
    prefixes = ["Apex", "Vertex", "Nexus", "Pinnacle", "Summit", "Crest", "Core", "Edge", "Flux", "Glow"]
    suffixes = ["Corp", "Inc", "LLC", "Ltd", "Solutions", "Systems", "Group", "Partners"]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


def _random_date(year: int = 2026) -> date:
    start = date(year, 1, 1)
    return start + timedelta(days=random.randint(0, 364))


def _random_amount(min_val: float = 1000, max_val: float = 500000) -> float:
    return round(random.uniform(min_val, max_val), 2)


def generate_procurement_bundle(bundle_id: str, defect_rate: float = 0.3) -> SyntheticBundle:
    """Generate a procurement document bundle with optional defects."""
    rng = random.Random(bundle_id)
    company = _random_company()
    platform = rng.randint(10000, 200000)
    support = rng.randint(1000, 50000)
    total = platform + support
    spend = total
    insurance_expiry = _random_date()
    required_coverage = insurance_expiry + timedelta(days=rng.randint(-60, 60))

    defects = []
    fields = []

    # Normal fields
    fields.append(SyntheticField("vendor.legal_name", company, company, "doc_quote", 0.98))
    fields.append(SyntheticField("quote.platform_price", platform, f"${platform:,}", "doc_quote", 0.99))
    fields.append(SyntheticField("quote.support_price", support, f"${support:,}", "doc_quote", 0.99))
    fields.append(SyntheticField("quote.total", total, f"${total:,}", "doc_quote", 0.99))
    fields.append(SyntheticField("procurement.requested_spend", spend, f"${spend:,}", "doc_request", 0.99))
    fields.append(SyntheticField("insurance.expiry_date", str(insurance_expiry), str(insurance_expiry), "doc_insurance", 0.99))
    fields.append(SyntheticField("procurement.required_coverage_until", str(required_coverage), str(required_coverage), "doc_request", 0.98))
    fields.append(SyntheticField("security.encryption_at_rest", True, "Yes", "doc_security", 0.98))

    # Inject defects
    if rng.random() < defect_rate:
        # Defect 1: wrong total
        if rng.random() < 0.5:
            wrong_total = total + rng.randint(100, 5000)
            fields[3] = SyntheticField("quote.total", wrong_total, f"${wrong_total:,}", "doc_quote", 0.99, True, "wrong_total")
            defects.append("wrong_total")
        # Defect 2: insurance gap
        else:
            short_expiry = required_coverage - timedelta(days=rng.randint(1, 90))
            fields[6] = SyntheticField("insurance.expiry_date", str(short_expiry), str(short_expiry), "doc_insurance", 0.99, True, "insurance_gap")
            defects.append("insurance_gap")

    # Ground truth checks
    gt = {
        "quote_arithmetic": {"expected": "wrong_total" not in defects, "severity": "BLOCKER"},
        "entity_match": {"expected": True, "severity": "WARNING"},
        "coverage_date": {"expected": "insurance_gap" not in defects, "severity": "BLOCKER"},
        "spend_match": {"expected": "wrong_total" not in defects, "severity": "BLOCKER"},
        "encryption": {"expected": True, "severity": "BLOCKER"},
    }

    return SyntheticBundle(
        bundle_id=bundle_id,
        domain="procurement",
        documents=[
            {"doc_id": "vendor_quote", "filename": "quote.pdf", "raw_text": f"Quote from {company}"},
            {"doc_id": "procurement_request", "filename": "request.pdf", "raw_text": f"Procurement request for {company}"},
            {"doc_id": "certificate_insurance", "filename": "insurance.pdf", "raw_text": f"Insurance certificate"},
            {"doc_id": "security_questionnaire", "filename": "security.pdf", "raw_text": f"Security questionnaire"},
        ],
        fields=fields,
        ground_truth=gt,
        defect_count=len(defects),
        defect_types=defects,
    )


def generate_insurance_bundle(bundle_id: str, defect_rate: float = 0.3) -> SyntheticBundle:
    """Generate an insurance claim bundle."""
    rng = random.Random(bundle_id)
    claimed = _random_amount(5000, 200000)
    deductible = rng.choice([5000, 10000, 25000])
    sublimit = rng.choice([30000, 50000, 75000])
    water_damage = rng.random() < 0.4

    defects = []
    fields = []

    fields.append(SyntheticField("claim.claimed_amount", claimed, f"${claimed:,.0f}", "doc_claim", 0.99))
    fields.append(SyntheticField("contractor.total", claimed, f"${claimed:,.0f}", "doc_estimate", 0.99))
    fields.append(SyntheticField("policy.deductible", deductible, f"${deductible:,}", "doc_policy", 0.99))
    fields.append(SyntheticField("policy.water_sublimit", sublimit, f"${sublimit:,}", "doc_policy", 0.99))
    fields.append(SyntheticField("claim.damage_type", "water damage" if water_damage else "fire damage", "water damage" if water_damage else "fire damage", "doc_claim", 0.97))

    if rng.random() < defect_rate:
        # Contractor estimate doesn't match claimed amount
        wrong_amount = claimed + rng.randint(500, 10000)
        fields[1] = SyntheticField("contractor.total", wrong_amount, f"${wrong_amount:,.0f}", "doc_estimate", 0.99, True, "amount_mismatch")
        defects.append("amount_mismatch")

    if water_damage and claimed > sublimit:
        defects.append("sublimit_exceeded")

    gt = {
        "amount_match": {"expected": "amount_mismatch" not in defects, "severity": "BLOCKER"},
        "sublimit": {"expected": claimed <= sublimit if water_damage else True, "severity": "BLOCKER"},
        "deductible": {"expected": claimed > deductible, "severity": "BLOCKER"},
    }

    return SyntheticBundle(
        bundle_id=bundle_id,
        domain="insurance",
        documents=[
            {"doc_id": "claim_form", "filename": "claim.pdf", "raw_text": "Insurance claim form"},
            {"doc_id": "policy", "filename": "policy.pdf", "raw_text": "Insurance policy"},
            {"doc_id": "contractor_estimate", "filename": "estimate.pdf", "raw_text": "Contractor estimate"},
        ],
        fields=fields,
        ground_truth=gt,
        defect_count=len(defects),
        defect_types=defects,
    )


def generate_trade_bundle(bundle_id: str, defect_rate: float = 0.3) -> SyntheticBundle:
    """Generate a trade document bundle."""
    rng = random.Random(bundle_id)
    origin = rng.choice(["China", "Germany", "Japan", "Mexico", "India"])
    qty = rng.randint(50, 500)
    price = rng.randint(100, 5000)
    total = qty * price
    fob = rng.choice(["FOB", "CIF", "EXW"])
    freight_prepaid = rng.random() < 0.5

    defects = []
    fields = []

    fields.append(SyntheticField("invoice.quantity", qty, str(qty), "doc_invoice", 0.99))
    fields.append(SyntheticField("bl.quantity", qty, str(qty), "doc_bl", 0.98))
    fields.append(SyntheticField("invoice.origin", origin, origin, "doc_invoice", 0.99))
    fields.append(SyntheticField("bl.origin", origin, origin, "doc_bl", 0.97))
    fields.append(SyntheticField("certificate.origin", origin, origin, "doc_cert", 0.99))
    fields.append(SyntheticField("invoice.incoterm", fob, fob, "doc_invoice", 0.98))
    fields.append(SyntheticField("bl.freight", "Freight Prepaid" if freight_prepaid else "Freight Collect", "prepaid" if freight_prepaid else "collect", "doc_bl", 0.99))

    if rng.random() < defect_rate:
        # FOB + Freight Prepaid mismatch
        fields[5] = SyntheticField("invoice.incoterm", "FOB", "FOB", "doc_invoice", 0.98, True, "incoterm_mismatch")
        fields[6] = SyntheticField("bl.freight", "Freight Prepaid", "prepaid", "doc_bl", 0.99, True, "incoterm_mismatch")
        defects.append("incoterm_mismatch")

    gt = {
        "qty_match": {"expected": True, "severity": "BLOCKER"},
        "origin_match": {"expected": True, "severity": "BLOCKER"},
        "incoterm": {"expected": "incoterm_mismatch" not in defects, "severity": "BLOCKER"},
    }

    return SyntheticBundle(
        bundle_id=bundle_id,
        domain="trade",
        documents=[
            {"doc_id": "commercial_invoice", "filename": "invoice.pdf", "raw_text": "Commercial invoice"},
            {"doc_id": "bill_of_lading", "filename": "bl.pdf", "raw_text": "Bill of lading"},
            {"doc_id": "certificate_origin", "filename": "cert.pdf", "raw_text": "Certificate of origin"},
        ],
        fields=fields,
        ground_truth=gt,
        defect_count=len(defects),
        defect_types=defects,
    )


GENERATORS = {
    "procurement": generate_procurement_bundle,
    "insurance": generate_insurance_bundle,
    "trade": generate_trade_bundle,
}


def generate_bundles(domain: str, n: int, defect_rate: float = 0.3,
                     seed: int = 42) -> list[SyntheticBundle]:
    """Generate n bundles for a domain."""
    rng = random.Random(seed)
    gen = GENERATORS[domain]
    return [gen(f"{domain}_{i:05d}") for i in range(n)]


def generate_all_domains(n_per_domain: int = 1000, defect_rate: float = 0.3,
                         seed: int = 42) -> dict[str, list[SyntheticBundle]]:
    """Generate bundles for all domains."""
    return {
        domain: generate_bundles(domain, n_per_domain, defect_rate, seed + i)
        for i, domain in enumerate(GENERATORS)
    }
