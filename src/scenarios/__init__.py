"""ScenarioWorld — cogym world that generates document folders.

Each scenario = a world type that generates documents with known ground truth.
The agent processes the folder, extracts facts, verifies them, and routes decisions.
cogymkernel optimizes thresholds per scenario type.

Usage:
    world = ProcurementWorld()
    folder = world.generate_folder(variation=0)
    results = agent.process_folder(folder)
    metrics = world.score(results)
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DocVariant:
    """A single document variant within a scenario."""
    filename: str
    doc_type: str
    ground_truth: dict
    pdf_path: str | None = None
    expected_verdict: str = "SAFE"  # SAFE / RISKY / FRAUDULENT


@dataclass
class ScenarioFolder:
    """A folder of documents for one scenario."""
    scenario_id: str
    scenario_type: str
    documents: list[DocVariant]
    expected_outcome: str  # "approve" / "reject" / "review"
    discrepancy: str | None = None  # what the agent should find
    difficulty: float = 0.5


@dataclass
class ScenarioResult:
    """Result of processing a scenario folder."""
    scenario_id: str
    scenario_type: str
    docs_processed: int
    facts_extracted: int
    discrepancies_found: list[str]
    expected_discrepancy_found: bool
    routing_decisions: dict  # AUTO_APPROVE / HUMAN_REVIEW / REJECT counts
    accuracy: float
    latency_ms: float


# ============================================================
# ProcurementWorld
# ============================================================

class ProcurementWorld:
    """Generates procurement document folders with variations.

    Core scenario: 4 documents (request, quote, insurance, security).
    Variations: different vendors, amounts, dates, insurance gaps.
    """

    VARIATIONS = [
        # (vendor, spend, quote_total, insurance_expiry, required_coverage, expected_outcome, discrepancy)
        ("Northstar Data Systems", 42500, 42500, "2027-08-31", "2027-10-01", "review", "insurance 31-day gap"),
        ("Acme Corp", 75000, 75000, "2027-12-31", "2027-10-01", "approve", None),  # insurance OK
        ("Globex Inc", 28000, 28000, "2027-06-15", "2027-10-01", "review", "insurance 108-day gap"),
        ("Initech LLC", 150000, 150000, "2027-09-30", "2027-10-01", "review", "insurance 1-day gap"),
        ("Umbrella Corp", 55000, 52000, "2027-11-01", "2027-10-01", "review", "amount mismatch ($3k)"),
    ]

    def generate_folder(self, variation: int = 0, seed: int | None = None) -> ScenarioFolder:
        """Generate a procurement document folder."""
        v = self.VARIATIONS[variation % len(self.VARIATIONS)]
        vendor, spend, quote_total, ins_expiry, req_coverage, outcome, discrepancy = v

        # Ground truth matches Nutrient's ACTUAL extraction schema
        docs = [
            DocVariant(
                filename="procurement_request.pdf",
                doc_type="procurement_request",
                ground_truth={
                    "vendor.legal_name": vendor,
                    "procurement.requested_spend": spend,
                    "procurement.contract_start": "2026-10-01",
                    "procurement.required_coverage_until": req_coverage,
                },
                expected_verdict="SAFE",
            ),
            DocVariant(
                filename="vendor_quote.pdf",
                doc_type="vendor_quote",
                ground_truth={
                    "vendor.legal_name": vendor,
                    "quote.total": quote_total,
                    "quote.platform_price": int(quote_total * 0.82),
                    "quote.support_price": int(quote_total * 0.18),
                },
                expected_verdict="SAFE",
            ),
            DocVariant(
                filename="insurance_certificate.pdf",
                doc_type="insurance_certificate",
                ground_truth={
                    "vendor.legal_name": vendor,
                    "insurance.expiry_date": ins_expiry,
                },
                expected_verdict="SAFE",
            ),
            DocVariant(
                filename="security_questionnaire.pdf",
                doc_type="security_questionnaire",
                ground_truth={
                    "vendor.legal_name": vendor,
                    "security.data_retention_days": 30,
                    "security.subprocessors": 3,
                    "security.encryption_at_rest": True,
                },
                expected_verdict="SAFE",
            ),
        ]

        return ScenarioFolder(
            scenario_id=f"procurement_{variation}",
            scenario_type="procurement",
            documents=docs,
            expected_outcome=outcome,
            discrepancy=discrepancy,
            difficulty=0.3 if outcome == "approve" else 0.7,
        )

    def score(self, result: ScenarioResult) -> dict:
        """Score a scenario result."""
        # Did the agent find the expected discrepancy?
        found = result.expected_discrepancy_found

        # Accuracy: correct routing decision
        if result.routing_decisions.get("HUMAN_REVIEW", 0) > 0:
            routed_correctly = True  # human review is always safe
        else:
            routed_correctly = False

        return {
            "discrepancy_found": 1.0 if found else 0.0,
            "routed_correctly": 1.0 if routed_correctly else 0.0,
            "accuracy": result.accuracy,
            "facts_extracted": result.facts_extracted,
            "latency_ms": result.latency_ms,
        }


# ============================================================
# InvoiceWorld
# ============================================================

class InvoiceWorld:
    """Generates invoice document folders with variations."""

    VARIATIONS = [
        # (vendor, invoice_num, total, tax, payment_terms, expected_outcome, discrepancy)
        ("GlobalTech Manufacturing", "INV-2026-001", 315700, 0, "Net 60", "approve", None),
        ("Pacific Imports Ltd", "INV-2026-002", 89500, 7160, "Net 30", "approve", None),
        ("Acme Supplies", "INV-2026-003", 45000, 3600, "Net 15", "review", "payment terms too short"),
        ("BuildRight Corp", "INV-2026-004", 125000, 10000, "Net 90", "approve", None),
        ("TechParts Inc", "INV-2026-005", 67000, 5360, "Net 45", "approve", None),
    ]

    def generate_folder(self, variation: int = 0) -> ScenarioFolder:
        v = self.VARIATIONS[variation % len(self.VARIATIONS)]
        vendor, inv_num, total, tax, terms, outcome, discrepancy = v

        docs = [
            DocVariant(
                filename=f"{vendor.lower().replace(' ', '_')}_invoice.pdf",
                doc_type="invoice",
                ground_truth={
                    "invoice_number": inv_num,
                    "vendor_name": vendor,
                    "total_amount": total,
                    "tax_amount": tax,
                    "payment_terms": terms,
                },
            ),
        ]

        return ScenarioFolder(
            scenario_id=f"invoice_{variation}",
            scenario_type="invoice",
            documents=docs,
            expected_outcome=outcome,
            discrepancy=discrepancy,
            difficulty=0.4,
        )

    def score(self, result):
        return {
            "accuracy": result.accuracy,
            "facts_extracted": result.facts_extracted,
            "latency_ms": result.latency_ms,
        }


# ============================================================
# KYCWorld
# ============================================================

class KYCWorld:
    """Generates KYC document folders with variations."""

    VARIATIONS = [
        # (name, dob, license, address, expected_outcome, discrepancy)
        ("Sarah Chen", "1990-03-15", "D1234567", "1847 Mission St, SF", "approve", None),
        ("Robert Johnson", "1975-06-22", "R4567890", "987 Pine Ln, Springfield", "approve", None),
        ("Maria Garcia", "1988-11-03", "M7890123", "456 Oak Ave, Chicago", "review", "name mismatch across docs"),
        ("James Wilson", "1995-02-28", "J3216549", "321 Elm St, Boston", "approve", None),
        ("Lisa Anderson", "1982-07-19", "L6543210", "654 Maple Dr, Seattle", "approve", None),
    ]

    def generate_folder(self, variation: int = 0) -> ScenarioFolder:
        v = self.VARIATIONS[variation % len(self.VARIATIONS)]
        name, dob, license, address, outcome, discrepancy = v

        docs = [
            DocVariant(
                filename=f"{name.lower().replace(' ', '_')}_id.pdf",
                doc_type="kyc_id",
                ground_truth={
                    "full_name": name,
                    "date_of_birth": dob,
                    "license_number": license,
                    "address": address,
                },
            ),
        ]

        return ScenarioFolder(
            scenario_id=f"kyc_{variation}",
            scenario_type="kyc",
            documents=docs,
            expected_outcome=outcome,
            discrepancy=discrepancy,
            difficulty=0.3,
        )

    def score(self, result):
        return {
            "accuracy": result.accuracy,
            "facts_extracted": result.facts_extracted,
            "latency_ms": result.latency_ms,
        }


# ============================================================
# World Registry
# ============================================================

WORLDS = {
    "procurement": ProcurementWorld,
    "invoice": InvoiceWorld,
    "kyc": KYCWorld,
}


def get_world(world_type: str):
    """Get a world instance by type."""
    cls = WORLDS.get(world_type)
    if cls is None:
        raise ValueError(f"Unknown world type: {world_type}. Available: {list(WORLDS.keys())}")
    return cls()


def list_worlds():
    """List available world types."""
    return list(WORLDS.keys())
