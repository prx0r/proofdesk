"""Multi-use-case fixtures for ProofDesk.

Each fixture represents a different real-world scenario that exercises
different aspects of the pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class UseCase:
    id: str
    name: str
    description: str
    icon: str
    prompt: str
    documents: list[dict]
    domain_rules: list[dict]
    expected_assertions: list[dict]


USE_CASES: dict[str, UseCase] = {}


# ─── 1. PROCUREMENT (original) ───

USE_CASES["procurement"] = UseCase(
    id="procurement",
    name="Vendor Procurement Onboarding",
    description="Reconcile a vendor packet, detect insurance gaps, generate approval memo",
    icon="📋",
    prompt="Prepare Northstar Data Systems for a $42,500 annual software procurement. Reconcile the packet, create the approval memo, and send it for signature if it is safe.",
    documents=[
        {
            "doc_id": "doc_procurement_request",
            "filename": "procurement_request.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "PROCUREMENT REQUEST\n"
                "Legal Name: Northstar Data Systems Ltd.\n"
                "Requested Spend: $42,500\n"
                "Contract Start: 2026-10-01\n"
                "Required Coverage Until: 2027-10-01\n"
                "Purpose: Annual software platform license and support services.\n"
                "Requestor: Finance Department\n"
            ),
        },
        {
            "doc_id": "doc_vendor_quote",
            "filename": "vendor_quote.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "VENDOR QUOTE\n"
                "Legal Name: Northstar Data Systems Limited\n"
                "Platform License: $35,000\n"
                "Support Services: $7,500\n"
                "Quote Total: $42,500\n"
                "Valid Until: 2026-09-15\n"
            ),
        },
        {
            "doc_id": "doc_certificate_insurance",
            "filename": "certificate_of_insurance.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "CERTIFICATE OF INSURANCE\n"
                "Insured: Northstar Data Systems Ltd.\n"
                "Policy Type: Commercial General Liability\n"
                "Insurance Expiry: 2027-08-31\n"
                "Coverage: $5,000,000\n"
            ),
        },
        {
            "doc_id": "doc_security_questionnaire",
            "filename": "security_questionnaire.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "SECURITY QUESTIONNAIRE\n"
                "Data Retention Period: 30 days\n"
                "Subprocessors: 3\n"
                "Encryption at Rest: Yes\n"
                "SOC2 Compliance: Yes\n"
                "Penetration Test Date: 2026-01-15\n"
            ),
        },
    ],
    domain_rules=[
        {"field": "quote_arithmetic", "check": "quote.total == quote.platform_price + quote.support_price"},
        {"field": "entity_match", "check": "vendor.legal_name normalized across documents"},
        {"field": "coverage_date", "check": "insurance.expiry_date >= procurement.required_coverage_until"},
        {"field": "spend_match", "check": "procurement.requested_spend == quote.total"},
        {"field": "encryption", "check": "security.encryption_at_rest == true"},
    ],
    expected_assertions=[
        {"predicate": "quote.total == quote.platform_price + quote.support_price", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "vendor.legal_name matches across documents", "result": "PASS", "severity": "WARNING"},
        {"predicate": "insurance.expiry_date >= procurement.required_coverage_until", "result": "FAIL", "severity": "BLOCKER"},
        {"predicate": "procurement.requested_spend == quote.total", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "security.encryption_at_rest == true", "result": "PASS", "severity": "BLOCKER"},
    ],
)


# ─── 2. INSURANCE CLAIMS ───

USE_CASES["insurance"] = UseCase(
    id="insurance",
    name="Insurance Claim Adjudication",
    description="Process a property damage claim, verify coverage, detect fraud signals, route to adjuster",
    icon="🛡️",
    prompt="Process claim #CLM-2026-4812 for Meridian Properties LLC. Verify coverage, validate the damage amount against the policy, and route for adjuster review if the claim exceeds the deductible threshold.",
    documents=[
        {
            "doc_id": "doc_claim_form",
            "filename": "claim_form_4812.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "PROPERTY DAMAGE CLAIM FORM\n"
                "Claim Number: CLM-2026-4812\n"
                "Policyholder: Meridian Properties LLC\n"
                "Policy Number: GL-2026-00891\n"
                "Date of Loss: 2026-07-15\n"
                "Date Reported: 2026-07-18\n"
                "Claimed Amount: $67,500\n"
                "Damage Type: Water damage — burst pipe, 2nd floor\n"
                "Location: 1420 Industrial Blvd, Suite 200\n"
                "Description: Tenant reported ceiling collapse in server room. "
                "Equipment damage: 3 servers, networking rack, flooring. "
                "Business interruption: 5 days estimated.\n"
            ),
        },
        {
            "doc_id": "doc_policy",
            "filename": "policy_GL-2026-00891.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "COMMERCIAL PROPERTY INSURANCE POLICY\n"
                "Policyholder: Meridian Properties LLC\n"
                "Policy Number: GL-2026-00891\n"
                "Effective: 2026-01-01 to 2026-12-31\n"
                "Coverage Type: Special Form (Open Perils)\n"
                "Building Coverage: $2,500,000\n"
                "Business Personal Property: $500,000\n"
                "Business Income: 12 months actual loss sustained\n"
                "Deductible: $10,000 per occurrence\n"
                "Water Damage Sublimit: $50,000\n"
                "Equipment Breakdown: Excluded\n"
                "Flood: Excluded (separate policy required)\n"
            ),
        },
        {
            "doc_id": "doc_contractor_estimate",
            "filename": "contractor_estimate.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "RESTORATION ESTIMATE\n"
                "Contractor: BuildRight Restoration Inc.\n"
                "Claim: CLM-2026-4812\n"
                "Date: 2026-07-20\n\n"
                "Line Items:\n"
                "  Demolition & debris removal: $4,200\n"
                "  Structural drying (3 days): $3,600\n"
                "  Ceiling repair (drywall + paint): $8,400\n"
                "  Flooring replacement: $6,800\n"
                "  Server equipment restoration: $32,500\n"
                "  Networking rack replacement: $8,200\n"
                "  Electrical remediation: $3,800\n"
                "  Total: $67,500\n"
            ),
        },
    ],
    domain_rules=[
        {"field": "claim_amount_match", "check": "claim.claimed_amount == contractor.total"},
        {"field": "policy_active", "check": "claim.date_of_loss within policy.effective dates"},
        {"field": "deductible", "check": "claim.amount > policy.deductible (trigger review)"},
        {"field": "sublimit", "check": "water_damage_amount <= policy.water_sublimit"},
        {"field": "exclusions", "check": "damage_type not in policy.exclusions"},
        {"field": "reporting_timeliness", "check": "claim.reported within 30 days of loss"},
    ],
    expected_assertions=[
        {"predicate": "claim.claimed_amount == contractor.total", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "date_of_loss within policy effective dates", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "claimed_amount > deductible triggers adjuster review", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "water damage within $50k sublimit", "result": "FAIL", "severity": "BLOCKER"},
        {"predicate": "equipment breakdown not excluded from coverage", "result": "FAIL", "severity": "BLOCKER"},
        {"predicate": "claim reported within 30 days", "result": "PASS", "severity": "WARNING"},
    ],
)


# ─── 3. CONTRACT REVIEW ───

USE_CASES["contract"] = UseCase(
    id="contract",
    name="SaaS Contract Red Flag Review",
    description="Review a SaaS agreement for liability caps, auto-renewal traps, and data ownership issues",
    icon="📜",
    prompt="Review the SaaS Agreement between CloudVault Inc. and Pinnacle Financial Group. Identify red flags in liability, indemnification, data ownership, auto-renewal, and termination clauses. Generate a risk summary for legal review.",
    documents=[
        {
            "doc_id": "doc_saas_agreement",
            "filename": "saas_agreement_cloudvault.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "SAAS SERVICE AGREEMENT\n"
                "Provider: CloudVault Inc.\n"
                "Customer: Pinnacle Financial Group\n"
                "Effective Date: 2026-06-01\n"
                "Term: 24 months\n\n"
                "Section 4.1 — Liability Cap: Provider's total liability shall not exceed "
                "fees paid in the 12 months preceding the claim.\n\n"
                "Section 5.2 — Auto-Renewal: This Agreement auto-renews for successive "
                "12-month periods unless either party provides 60 days written notice.\n\n"
                "Section 8.3 — Data Ownership: All data uploaded by Customer remains Customer's "
                "property. Provider receives a worldwide, non-exclusive license to use anonymized "
                "data for product improvement.\n\n"
                "Section 9.1 — Indemnification: Customer shall indemnify Provider against all "
                "claims arising from Customer's use of the Service, including third-party IP claims.\n\n"
                "Section 11.4 — Termination for Convenience: Either party may terminate with "
                "90 days written notice. No refund of prepaid fees upon termination for convenience.\n\n"
                "Section 12.1 — SLA: Provider guarantees 99.9% uptime. Remedy: service credits "
                "up to 10% of monthly fees for downtime exceeding 0.1%.\n\n"
                "Section 15.2 — Governing Law: Laws of the State of Delaware.\n"
            ),
        },
    ],
    domain_rules=[
        {"field": "liability_cap", "check": "liability capped at 12-month fees"},
        {"field": "auto_renewal", "check": "auto-renewal with 60-day notice is short"},
        {"field": "data_license", "check": "anonymized data license for product improvement"},
        {"field": "indemnification", "check": "one-way indemnification (customer only)"},
        {"field": "termination", "check": "no refund on convenience termination"},
        {"field": "sla_remedy", "check": "10% cap on service credits is low"},
    ],
    expected_assertions=[
        {"predicate": "Liability cap at 12-month fees is industry standard", "result": "PASS", "severity": "INFO"},
        {"predicate": "Auto-renewal 60-day notice is aggressive (standard is 90-180)", "result": "FAIL", "severity": "WARNING"},
        {"predicate": "Anonymized data license may conflict with financial data regulations", "result": "FAIL", "severity": "BLOCKER"},
        {"predicate": "One-way indemnification favors provider", "result": "FAIL", "severity": "WARNING"},
        {"predicate": "No refund on convenience termination is unfavorable", "result": "FAIL", "severity": "WARNING"},
        {"predicate": "SLA remedy capped at 10% is below market standard (25-50%)", "result": "FAIL", "severity": "WARNING"},
    ],
)


# ─── 4. VENDOR COMPLIANCE (new: cross-document trade) ───

USE_CASES["trade"] = UseCase(
    id="trade",
    name="Trade Document Cross-Check",
    description="Catch mismatches between invoice, shipping doc, and certificate that would cost customs penalties",
    icon="🚢",
    prompt="Cross-check the trade document bundle for shipment SHP-2026-00341 between GlobalTech Manufacturing and Pacific Imports Ltd. Verify that the commercial invoice, bill of lading, and certificate of origin are consistent. Flag any discrepancies that could trigger customs holds.",
    documents=[
        {
            "doc_id": "doc_commercial_invoice",
            "filename": "commercial_invoice_SHP0341.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "COMMERCIAL INVOICE\n"
                "Invoice Number: INV-2026-7891\n"
                "Shipper: GlobalTech Manufacturing Co.\n"
                "Consignee: Pacific Imports Ltd.\n"
                "Port of Loading: Shanghai, China\n"
                "Port of Discharge: Long Beach, CA\n"
                "Description: Industrial servo motors (Model GT-SM-400)\n"
                "Quantity: 240 units\n"
                "Unit Price: $1,250.00\n"
                "Total Value: $300,000.00\n"
                "Currency: USD\n"
                "Country of Origin: China\n"
                "Incoterm: FOB Shanghai\n"
            ),
        },
        {
            "doc_id": "doc_bill_of_lading",
            "filename": "bill_of_lading_SHP0341.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "BILL OF LADING\n"
                "B/L Number: COSU6280034100\n"
                "Shipper: GlobalTech Manufacturing Co.\n"
                "Consignee: Pacific Imports Ltd.\n"
                "Vessel: MV PACIFIC STAR V.2608E\n"
                "Port of Loading: Shanghai, China\n"
                "Port of Discharge: Long Beach, CA\n"
                "Description of Goods: Servo motors, 240 cartons\n"
                "Gross Weight: 4,800 kg\n"
                "Measurement: 28.8 CBM\n"
                "Freight: Freight Prepaid\n"
            ),
        },
        {
            "doc_id": "doc_certificate_origin",
            "filename": "certificate_of_origin_SHP0341.pdf",
            "content_type": "application/pdf",
            "source_text": (
                "CERTIFICATE OF ORIGIN\n"
                "Invoice Number: INV-2026-7891\n"
                "Exporter: GlobalTech Manufacturing Co.\n"
                "Consignee: Pacific Imports Ltd.\n"
                "Country of Origin: China\n"
                "Description: Industrial servo motors, Model GT-SM-400\n"
                "Quantity: 240 units\n"
                "HS Code: 8501.53\n"
                "Issued by: China Council for the Promotion of International Trade\n"
                "Date: 2026-08-10\n"
            ),
        },
    ],
    domain_rules=[
        {"field": "invoice_matches_bl", "check": "invoice quantity/value matches bill of lading"},
        {"field": "origin_matches", "check": "country of origin consistent across all docs"},
        {"field": "hs_code_valid", "check": "HS code matches product description"},
        {"field": "parties_match", "check": "shipper/consignee names consistent"},
        {"field": "incoterm_consistent", "check": "freight terms match incoterm"},
    ],
    expected_assertions=[
        {"predicate": "Invoice quantity (240) matches B/L quantity (240 cartons)", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "Country of origin consistent across all 3 documents", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "HS code 8501.53 matches servo motor description", "result": "PASS", "severity": "BLOCKER"},
        {"predicate": "Shipper/consignee names consistent across documents", "result": "PASS", "severity": "WARNING"},
        {"predicate": "FOB Shanghai matches 'Freight Prepaid' (should be Freight Collect for FOB)", "result": "FAIL", "severity": "BLOCKER"},
    ],
)


def get_use_case(id: str) -> UseCase | None:
    return USE_CASES.get(id)


def list_use_cases() -> list[dict]:
    return [
        {"id": uc.id, "name": uc.name, "description": uc.description, "icon": uc.icon}
        for uc in USE_CASES.values()
    ]
