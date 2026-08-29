"""Provider stubs — Nutrient DWS, Doctavian, Foxit.

In the real hackathon build, these call actual APIs.
For the prototype, they return deterministic structured outputs.
"""

from __future__ import annotations

import json
import time

from ..models.domain import (
    Document,
    ExtractedFact,
    GeneratedArtifact,
    _id,
    _hash,
)


# --- Nutrient DWS stub ---

# Extraction rules: doc_id pattern -> list of (field, raw, normalized, confidence)
EXTRACTION_RULES: dict[str, list[tuple]] = {
    # Procurement
    "procurement_request": [
        ("vendor.legal_name", "Northstar Data Systems Ltd.", "Northstar Data Systems Ltd", 0.98),
        ("procurement.requested_spend", "$42,500", "42500", 0.99),
        ("procurement.contract_start", "2026-10-01", "2026-10-01", 0.99),
        ("procurement.required_coverage_until", "2027-10-01", "2027-10-01", 0.98),
    ],
    "vendor_quote": [
        ("vendor.legal_name", "Northstar Data Systems Limited", "Northstar Data Systems Ltd", 0.97),
        ("quote.platform_price", "$35,000", "35000", 0.99),
        ("quote.support_price", "$7,500", "7500", 0.99),
        ("quote.total", "$42,500", "42500", 0.99),
    ],
    "certificate_insurance": [
        ("insurance.expiry_date", "2027-08-31", "2027-08-31", 0.99),
        ("insurance.policy_type", "Commercial General Liability", "Commercial General Liability", 0.98),
    ],
    "security_questionnaire": [
        ("security.data_retention_days", "30 days", "30", 0.97),
        ("security.subprocessors", "3", "3", 0.99),
        ("security.encryption_at_rest", "Yes", "true", 0.98),
    ],
    # Insurance
    "claim_form": [
        ("claim.claim_number", "CLM-2026-4812", "CLM-2026-4812", 0.99),
        ("claim.policyholder", "Meridian Properties LLC", "Meridian Properties LLC", 0.98),
        ("claim.policy_number", "GL-2026-00891", "GL-2026-00891", 0.99),
        ("claim.date_of_loss", "2027-07-15", "2026-07-15", 0.95),
        ("claim.date_reported", "2026-07-18", "2026-07-18", 0.98),
        ("claim.claimed_amount", "$67,500", "67500", 0.99),
        ("claim.damage_type", "Water damage — burst pipe, 2nd floor", "water damage", 0.97),
    ],
    "policy": [
        ("policy.policyholder", "Meridian Properties LLC", "Meridian Properties LLC", 0.99),
        ("policy.number", "GL-2026-00891", "GL-2026-00891", 0.99),
        ("policy.effective_start", "2026-01-01", "2026-01-01", 0.99),
        ("policy.effective_end", "2026-12-31", "2026-12-31", 0.99),
        ("policy.building_coverage", "$2,500,000", "2500000", 0.98),
        ("policy.deductible", "$10,000", "10000", 0.99),
        ("policy.water_sublimit", "$50,000", "50000", 0.99),
        ("policy.equipment_breakdown", "Excluded", "excluded", 0.98),
    ],
    "contractor_estimate": [
        ("contractor.name", "BuildRight Restoration Inc.", "BuildRight Restoration Inc.", 0.98),
        ("contractor.claim_reference", "CLM-2026-4812", "CLM-2026-4812", 0.99),
        ("contractor.total", "$67,500", "67500", 0.99),
    ],
    # Contract
    "saas_agreement": [
        ("contract.provider", "CloudVault Inc.", "CloudVault Inc.", 0.99),
        ("contract.customer", "Pinnacle Financial Group", "Pinnacle Financial Group", 0.99),
        ("contract.effective_date", "2026-06-01", "2026-06-01", 0.98),
        ("contract.term", "24 months", "24", 0.97),
        ("contract.liability_cap", "fees paid in 12 months preceding the claim", "12-month fees", 0.95),
        ("contract.auto_renewal_notice_days", "60 days", "60", 0.98),
        ("contract.data_license", "worldwide, non-exclusive license to use anonymized data for product improvement", "anonymized product improvement", 0.96),
        ("contract.indemnification", "Customer shall indemnify Provider against all claims", "one-way customer", 0.97),
        ("contract.termination_refund", "No refund of prepaid fees upon termination for convenience", "no refund", 0.98),
        ("contract.sla_uptime", "99.9%", "99.9", 0.99),
        ("contract.sla_remedy", "service credits up to 10% of monthly fees", "10% cap", 0.97),
    ],
    # Trade
    "commercial_invoice": [
        ("invoice.number", "INV-2026-7891", "INV-2026-7891", 0.99),
        ("invoice.shipper", "GlobalTech Manufacturing Co.", "GlobalTech Manufacturing", 0.98),
        ("invoice.consignee", "Pacific Imports Ltd.", "Pacific Imports", 0.98),
        ("invoice.quantity", "240 units", "240", 0.99),
        ("invoice.unit_price", "$1,250.00", "1250", 0.99),
        ("invoice.total_value", "$300,000.00", "300000", 0.99),
        ("invoice.origin", "China", "China", 0.99),
        ("invoice.incoterm", "FOB Shanghai", "FOB Shanghai", 0.98),
    ],
    "bill_of_lading": [
        ("bill_of_lading.number", "COSU6280034100", "COSU6280034100", 0.99),
        ("bill_of_lading.shipper", "GlobalTech Manufacturing Co.", "GlobalTech Manufacturing", 0.98),
        ("bill_of_lading.consignee", "Pacific Imports Ltd.", "Pacific Imports", 0.98),
        ("bill_of_lading.quantity", "240 cartons", "240", 0.98),
        ("bill_of_lading.origin", "Shanghai, China", "China", 0.97),
        ("bill_of_lading.freight", "Freight Prepaid", "prepaid", 0.99),
        ("bill_of_lading.weight", "4,800 kg", "4800", 0.97),
    ],
    "certificate_origin": [
        ("certificate.origin", "China", "China", 0.99),
        ("certificate.invoice_ref", "INV-2026-7891", "INV-2026-7891", 0.99),
        ("certificate.quantity", "240 units", "240", 0.98),
        ("certificate.hs_code", "8501.53", "8501.53", 0.99),
    ],
}


def nutrient_extract(document: Document) -> list[ExtractedFact]:
    """Simulate Nutrient DWS extraction with source-grounded confidence."""
    import re
    facts = []

    # Find matching extraction rules (flexible matching: strip numbers/underscores)
    extractions = []
    normalized_doc_id = re.sub(r'[_0-9]', '', document.doc_id.lower())
    for pattern, rules in EXTRACTION_RULES.items():
        normalized_pattern = re.sub(r'[_0-9]', '', pattern.lower())
        if normalized_pattern in normalized_doc_id or normalized_doc_id in normalized_pattern:
            extractions = rules
            break

    for field_name, raw, normalized, conf in extractions:
        facts.append(ExtractedFact(
            case_id=document.case_id,
            doc_id=document.doc_id,
            field_name=field_name,
            value_raw=raw,
            value_normalized=normalized,
            source_page=1,
            extractor="nutrient_dws",
            confidence=conf,
            content_hash=_hash({"field": field_name, "value": normalized}),
        ))

    return facts


# --- Doctavian stub ---

def doctavian_generate(record_data: dict, template_id: str = "approval_memo", confidence: dict | None = None) -> tuple[GeneratedArtifact, str]:
    """Simulate Doctavian document generation from structured record.

    Uses the canonical payload builder so fallback output matches the real
    Doctavian branch logic (risk_band, numbered conditions).
    """
    from ..providers.doctavian import build_generation_payload

    lines = []
    lines.append("=" * 60)
    lines.append("VENDOR APPROVAL & RISK MEMORANDUM")
    lines.append("=" * 60)
    lines.append("")

    data = build_generation_payload(record_data, confidence=confidence)
    band_text = {
        "CLEARED": "APPROVED",
        "CONDITIONAL": "CONDITIONALLY APPROVED",
        "ESCALATED": "REJECTED — REQUIRES RESOLUTION",
    }.get(data["risk_band"], data["risk_band"])
    facts = {f["field"]: f["value_normalized"] for f in record_data.get("facts", [])}
    assertions = record_data.get("assertions", [])
    resolutions = record_data.get("resolutions", [])

    approval_status = band_text

    lines.append(f"Status: {approval_status}")
    lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Vendor info
    lines.append("VENDOR INFORMATION")
    lines.append("-" * 40)
    lines.append(f"Legal Name: {facts.get('vendor.legal_name', 'N/A')}")
    lines.append(f"Platform License: ${facts.get('quote.platform_price', 'N/A')}")
    lines.append(f"Support Services: ${facts.get('quote.support_price', 'N/A')}")
    lines.append(f"Quote Total: ${facts.get('quote.total', 'N/A')}")
    lines.append(f"Requested Spend: ${facts.get('procurement.requested_spend', 'N/A')}")
    lines.append("")

    # Compliance summary
    lines.append("COMPLIANCE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Insurance Expiry: {facts.get('insurance.expiry_date', 'N/A')}")
    lines.append(f"Required Coverage Until: {facts.get('procurement.required_coverage_until', 'N/A')}")
    lines.append(f"Data Retention: {facts.get('security.data_retention_days', 'N/A')} days")
    lines.append(f"Subprocessors: {facts.get('security.subprocessors', 'N/A')}")
    lines.append(f"Encryption at Rest: {facts.get('security.encryption_at_rest', 'N/A')}")
    lines.append("")

    # Assertions
    lines.append("DETERMINISTIC CHECKS")
    lines.append("-" * 40)
    for a in assertions:
        status = "✓" if a["result"] == "PASS" else "✗" if a["result"] == "FAIL" else "?"
        lines.append(f"  [{status}] {a['predicate']}")
        lines.append(f"      {a['detail']}")
    lines.append("")

    # Resolutions
    if resolutions:
        lines.append("EXCEPTION RESOLUTIONS")
        lines.append("-" * 40)
        for r in resolutions:
            lines.append(f"  Decision: {r['decision']}")
            lines.append(f"  Reason: {r['reason']}")
            lines.append(f"  Actor: {r['actor_id']}")
            lines.append("")

    # Conditional clauses
    if approval_status == "CONDITIONALLY APPROVED":
        lines.append(f"CONDITIONS ({data.get('condition_count', 1)})")
        lines.append("-" * 40)
        for i, c in enumerate(data.get("failed_checks", []), 1):
            lines.append(f"  §{i}. FAILED: {c['predicate']}")
            lines.append(f"     Detail: {c['detail']}   [rule: {c.get('rule', '')}]")
            lines.append(f"     OBLIGATION: resolved before contract start "
                         f"({facts.get('procurement.contract_start', 'contract start')}).")
        lines.append("")

    lines.append("EVIDENCE APPENDIX")
    lines.append("-" * 40)
    lines.append("  All facts are source-grounded via Nutrient DWS extraction.")
    lines.append("  Each fact retains its original value, source document, page,")
    lines.append("  and confidence score for full auditability.")
    lines.append("")
    lines.append("=" * 60)

    content = "\n".join(lines)

    artifact = GeneratedArtifact(
        case_id=record_data.get("case_id", ""),
        record_id=record_data.get("record_id", ""),
        record_hash=record_data.get("content_hash", ""),
        template_id=template_id,
        template_version="1.0",
        content_hash=_hash(content),
        provider_job_id=_id("job_"),
    )
    artifact.output_path = f"/tmp/proofdesk/{artifact.artifact_id}.txt"
    return artifact, content


# --- Foxit stub ---

def foxit_pdf_prepare(artifact: GeneratedArtifact, content: str) -> dict:
    """Simulate Foxit PDF preparation."""
    return {
        "operation": "merge_and_compress",
        "input_artifact": artifact.artifact_id,
        "output_pdf": f"/tmp/proofdesk/{artifact.artifact_id}.pdf",
        "pages": content.count("\n") + 1,
        "size_bytes": len(content.encode()),
        "provider": "foxit_pdf_services",
        "status": "prepared",
    }


def foxit_esign_request(artifact_id: str, signer: str) -> dict:
    """Simulate Foxit eSign request."""
    return {
        "provider": "foxit_esign",
        "request_id": _id("esign_"),
        "folder_id": _id("folder_"),
        "artifact_id": artifact_id,
        "signer": signer,
        "status": "SENT",
        "message": f"Signature request sent to {signer}",
    }
