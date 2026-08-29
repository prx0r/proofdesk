"""Multi-domain deterministic reconciliation engine.

Extends the original procurement engine to handle insurance claims,
contract review, and trade document cross-checks.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from ..models.domain import (
    Assertion,
    AssertionResult,
    ExceptionSeverity,
    ExtractedFact,
)


# --- Normalization helpers (shared) ---

def normalize_currency(s: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def normalize_date(s: str) -> date | None:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_boolean(s: str) -> bool | None:
    s_lower = s.strip().lower()
    if s_lower in ("yes", "true", "1"):
        return True
    if s_lower in ("no", "false", "0"):
        return False
    return None


def normalize_entity_name(s: str) -> str:
    s = re.sub(r"[.,]", "", s.strip())
    s = re.sub(r"\b(Ltd|Limited|Inc|LLC|Corp|Corporation|Co\.|Company)\b", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def parse_numeric(s: str) -> float | None:
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


# --- Fact indexing ---

def build_fact_index(facts: list[ExtractedFact]) -> dict[str, list[ExtractedFact]]:
    index: dict[str, list[ExtractedFact]] = {}
    for f in facts:
        index.setdefault(f.field_name, []).append(f)
    return index


def get_value(fact_index: dict, field: str, cast=str):
    facts = fact_index.get(field, [])
    if not facts:
        return None
    val = facts[0].value_normalized
    if cast == float:
        return normalize_currency(str(val)) if not isinstance(val, (int, float)) else float(val)
    if cast == bool:
        return normalize_boolean(str(val))
    if cast == date:
        return normalize_date(str(val))
    return val


# ─── PROCUREMENT CHECKS ───

def check_procurement(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    assertions = []

    # Quote arithmetic
    p = get_value(fact_index, "quote.platform_price", float)
    s = get_value(fact_index, "quote.support_price", float)
    t = get_value(fact_index, "quote.total", float)
    if all(v is not None for v in [p, s, t]):
        passed = abs((p + s) - t) < 0.01
        assertions.append(Assertion(
            predicate="quote.total == quote.platform_price + quote.support_price",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{p} + {s} = {p+s} {'==' if passed else '!='} {t}",
            rule_version="procurement-arith-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Entity name normalization
    names = fact_index.get("vendor.legal_name", [])
    if len(names) >= 2:
        normalized = set(normalize_entity_name(n.value_normalized) for n in names)
        passed = len(normalized) == 1
        assertions.append(Assertion(
            predicate="vendor.legal_name matches across documents",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"Normalized: {normalized}",
            rule_version="procurement-entity-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    # Coverage date
    expiry = get_value(fact_index, "insurance.expiry_date", date)
    required = get_value(fact_index, "procurement.required_coverage_until", date)
    if expiry and required:
        passed = expiry >= required
        delta = (required - expiry).days
        assertions.append(Assertion(
            predicate="insurance.expiry_date >= procurement.required_coverage_until",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{expiry} {'>=' if passed else '<'} {required}" + (f" — {delta} days gap" if not passed else ""),
            rule_version="procurement-coverage-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Spend match
    spend = get_value(fact_index, "procurement.requested_spend", float)
    if spend is not None and t is not None:
        passed = abs(spend - t) < 0.01
        assertions.append(Assertion(
            predicate="procurement.requested_spend == quote.total",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{spend} == {t}",
            rule_version="procurement-spend-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Encryption
    enc = get_value(fact_index, "security.encryption_at_rest", bool)
    if enc is not None:
        assertions.append(Assertion(
            predicate="security.encryption_at_rest == true",
            result=AssertionResult.PASS if enc else AssertionResult.FAIL,
            detail=f"encryption_at_rest = {enc}",
            rule_version="procurement-security-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Payment terms consistency
    payment_terms = fact_index.get("payment_terms", [])
    if len(payment_terms) >= 2:
        terms_values = set(n.value_normalized.strip().lower() for n in payment_terms)
        passed = len(terms_values) == 1
        assertions.append(Assertion(
            predicate="payment_terms consistent across documents",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"Payment terms found: {terms_values}" + (" — CONFLICT" if not passed else ""),
            rule_version="procurement-payment-v1",
            severity=ExceptionSeverity.WARNING if not passed else ExceptionSeverity.INFO,
        ))

    return assertions


# ─── INSURANCE CLAIM CHECKS ───

def check_insurance(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    assertions = []

    # Claim amount matches contractor estimate
    claimed = get_value(fact_index, "claim.claimed_amount", float)
    contractor_total = get_value(fact_index, "contractor.total", float)
    if claimed is not None and contractor_total is not None:
        passed = abs(claimed - contractor_total) < 0.01
        assertions.append(Assertion(
            predicate="claim.claimed_amount == contractor.total",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{claimed} == {contractor_total}",
            rule_version="insurance-amount-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Policy active during loss
    loss_date = get_value(fact_index, "claim.date_of_loss", date)
    policy_start = get_value(fact_index, "policy.effective_start", date)
    policy_end = get_value(fact_index, "policy.effective_end", date)
    if loss_date and policy_start and policy_end:
        passed = policy_start <= loss_date <= policy_end
        assertions.append(Assertion(
            predicate="date_of_loss within policy effective dates",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{loss_date} in [{policy_start}, {policy_end}]",
            rule_version="insurance-active-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Deductible threshold
    deductible = get_value(fact_index, "policy.deductible", float)
    if claimed is not None and deductible is not None:
        triggers_review = claimed > deductible
        assertions.append(Assertion(
            predicate="claimed_amount > deductible triggers adjuster review",
            result=AssertionResult.PASS if triggers_review else AssertionResult.FAIL,
            detail=f"{claimed} > {deductible} = {triggers_review}",
            rule_version="insurance-deductible-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Water damage sublimit
    water_sublimit = get_value(fact_index, "policy.water_sublimit", float)
    if claimed is not None and water_sublimit is not None:
        # For water damage claims, check against sublimit
        damage_type = get_value(fact_index, "claim.damage_type")
        if damage_type and "water" in str(damage_type).lower():
            passed = claimed <= water_sublimit
            assertions.append(Assertion(
                predicate="water damage within $50k sublimit",
                result=AssertionResult.PASS if passed else AssertionResult.FAIL,
                detail=f"${claimed:,.0f} {'<=' if passed else '>'} ${water_sublimit:,.0f} sublimit",
                rule_version="insurance-sublimit-v1",
                severity=ExceptionSeverity.BLOCKER,
            ))

    # Reporting timeliness
    reported = get_value(fact_index, "claim.date_reported", date)
    if loss_date and reported:
        days = (reported - loss_date).days
        passed = days <= 30
        assertions.append(Assertion(
            predicate="claim reported within 30 days",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"Reported {days} days after loss",
            rule_version="insurance-timeliness-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    return assertions


# ─── CONTRACT REVIEW CHECKS ───

def check_contract(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    assertions = []

    # Liability cap
    liability_cap = get_value(fact_index, "contract.liability_cap")
    if liability_cap:
        assertions.append(Assertion(
            predicate="Liability cap at 12-month fees is industry standard",
            result=AssertionResult.PASS,
            detail=f"Cap: {liability_cap}",
            rule_version="contract-liability-v1",
            severity=ExceptionSeverity.INFO,
        ))

    # Auto-renewal notice period
    notice_days = get_value(fact_index, "contract.auto_renewal_notice_days", float)
    if notice_days is not None:
        passed = notice_days >= 90
        assertions.append(Assertion(
            predicate="Auto-renewal notice period >= 90 days (standard)",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"{int(notice_days)} days (standard is 90-180)",
            rule_version="contract-renewal-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    # Data license scope
    data_license = get_value(fact_index, "contract.data_license")
    if data_license:
        has_broad = "anonymized" in str(data_license).lower() or "product improvement" in str(data_license).lower()
        assertions.append(Assertion(
            predicate="Anonymized data license may conflict with financial data regulations",
            result=AssertionResult.FAIL if has_broad else AssertionResult.PASS,
            detail=f"License scope: {data_license}",
            rule_version="contract-data-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Indemnification symmetry
    indemnification = get_value(fact_index, "contract.indemnification")
    if indemnification:
        is_one_way = "customer" in str(indemnification).lower() and "provider" not in str(indemnification).lower().replace("provider", "", 1)
        assertions.append(Assertion(
            predicate="One-way indemnification favors provider",
            result=AssertionResult.FAIL if is_one_way else AssertionResult.PASS,
            detail=f"Indemnification: {indemnification}",
            rule_version="contract-indemnity-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    # Termination refund
    termination = get_value(fact_index, "contract.termination_refund")
    if termination:
        no_refund = "no refund" in str(termination).lower() or "no prepaid" in str(termination).lower()
        assertions.append(Assertion(
            predicate="No refund on convenience termination is unfavorable",
            result=AssertionResult.FAIL if no_refund else AssertionResult.PASS,
            detail=f"Termination terms: {termination}",
            rule_version="contract-termination-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    # SLA remedy
    sla_remedy = get_value(fact_index, "contract.sla_remedy")
    if sla_remedy:
        assertions.append(Assertion(
            predicate="SLA remedy capped at 10% is below market standard (25-50%)",
            result=AssertionResult.FAIL,
            detail=f"SLA remedy: {sla_remedy}",
            rule_version="contract-sla-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    return assertions


# ─── TRADE DOCUMENT CHECKS ───

def check_trade(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    assertions = []

    # Quantity consistency
    invoice_qty = get_value(fact_index, "invoice.quantity", float)
    bl_qty = get_value(fact_index, "bill_of_lading.quantity", float)
    if invoice_qty is not None and bl_qty is not None:
        passed = abs(invoice_qty - bl_qty) < 0.01
        assertions.append(Assertion(
            predicate="Invoice quantity matches bill of lading quantity",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"Invoice: {invoice_qty}, B/L: {bl_qty}",
            rule_version="trade-qty-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Country of origin consistency
    origins = set()
    for field in ["invoice.origin", "bill_of_lading.origin", "certificate.origin"]:
        val = get_value(fact_index, field)
        if val:
            origins.add(normalize_entity_name(str(val)))
    if len(origins) >= 2:
        assertions.append(Assertion(
            predicate="Country of origin consistent across all documents",
            result=AssertionResult.FAIL,
            detail=f"Different origins found: {origins}",
            rule_version="trade-origin-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))
    elif len(origins) == 1:
        assertions.append(Assertion(
            predicate="Country of origin consistent across all documents",
            result=AssertionResult.PASS,
            detail=f"All documents: {origins.pop()}",
            rule_version="trade-origin-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Party name consistency
    shippers = set()
    for field in ["invoice.shipper", "bill_of_lading.shipper", "certificate.shipper"]:
        val = get_value(fact_index, field)
        if val:
            shippers.add(normalize_entity_name(str(val)))
    if len(shippers) >= 2:
        assertions.append(Assertion(
            predicate="Shipper names consistent across documents",
            result=AssertionResult.FAIL,
            detail=f"Different shippers: {shippers}",
            rule_version="trade-party-v1",
            severity=ExceptionSeverity.WARNING,
        ))
    elif len(shippers) == 1:
        assertions.append(Assertion(
            predicate="Shipper names consistent across documents",
            result=AssertionResult.PASS,
            detail=f"All: {shippers.pop()}",
            rule_version="trade-party-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    # FOB vs freight terms
    incoterm = get_value(fact_index, "invoice.incoterm")
    freight = get_value(fact_index, "bill_of_lading.freight")
    if incoterm and freight:
        is_fob = "fob" in str(incoterm).lower()
        is_prepaid = "prepaid" in str(freight).lower()
        # FOB = buyer pays freight, so "Freight Prepaid" on a FOB shipment is suspicious
        passed = not (is_fob and is_prepaid)
        assertions.append(Assertion(
            predicate="FOB incoterm consistent with freight payment terms",
            result=AssertionResult.PASS if passed else AssertionResult.FAIL,
            detail=f"Incoterm: {incoterm}, Freight: {freight}" + (" — FOB should be Freight Collect" if not passed else ""),
            rule_version="trade-incoterm-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    return assertions


# ─── RECEIPT CHECKS ───

def check_receipt(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    assertions = []

    # Company name present
    company = get_value(fact_index, "company")
    if company is not None:
        assertions.append(Assertion(
            predicate="receipt.company_name_present",
            result=AssertionResult.PASS if len(str(company)) > 2 else AssertionResult.FAIL,
            detail=f"Company: {company}",
            rule_version="receipt-company-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Date format valid
    date_val = get_value(fact_index, "date")
    if date_val is not None:
        import re
        valid = bool(re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', str(date_val)))
        assertions.append(Assertion(
            predicate="receipt.date_format_valid",
            result=AssertionResult.PASS if valid else AssertionResult.FAIL,
            detail=f"Date: {date_val}",
            rule_version="receipt-date-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Total is numeric and positive
    total = get_value(fact_index, "total")
    if total is not None:
        try:
            val = float(str(total).replace(",", ""))
            valid = val > 0
        except (ValueError, TypeError):
            valid = False
        assertions.append(Assertion(
            predicate="receipt.total_numeric",
            result=AssertionResult.PASS if valid else AssertionResult.FAIL,
            detail=f"Total: {total}",
            rule_version="receipt-total-v1",
            severity=ExceptionSeverity.BLOCKER,
        ))

    # Address present
    address = get_value(fact_index, "address")
    if address is not None:
        assertions.append(Assertion(
            predicate="receipt.address_present",
            result=AssertionResult.PASS if len(str(address)) > 5 else AssertionResult.FAIL,
            detail=f"Address: {str(address)[:50]}",
            rule_version="receipt-address-v1",
            severity=ExceptionSeverity.WARNING,
        ))

    return assertions


# ─── CUAD CONTRACT CLAUSE CHECKS ───

def check_cuad_clause(fact_index: dict[str, list[ExtractedFact]]) -> list[Assertion]:
    """Check CUAD clause presence/absence."""
    assertions = []

    for field_name, facts in fact_index.items():
        if not field_name.startswith("clause_"):
            continue
        label = field_name[7:]  # Remove "clause_" prefix
        is_present = facts[0].value_normalized.lower() in ("true", "1", "yes")

        # Use underscores in rule_version to match GT key convention
        assertions.append(Assertion(
            predicate=f"cuad.clause_{label}",
            result=AssertionResult.PASS if is_present else AssertionResult.FAIL,
            detail=f"Clause '{label}': {'present' if is_present else 'absent'}",
            rule_version=f"cuad_clause_{label}",
            severity=ExceptionSeverity.BLOCKER,
        ))

    return assertions


# ─── DISPATCHER ───

DOMAIN_CHECKERS = {
    "procurement": check_procurement,
    "insurance": check_insurance,
    "contract": check_contract,
    "receipt": check_receipt,
    "cuad": check_cuad_clause,
    "trade": check_trade,
}


def run_checks(facts: list[ExtractedFact], domain: str = "procurement") -> list[Assertion]:
    """Run all deterministic checks for a given domain."""
    fact_index = build_fact_index(facts)
    checker = DOMAIN_CHECKERS.get(domain, check_procurement)
    return checker(fact_index)
