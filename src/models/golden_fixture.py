"""Golden fixture — Northstar Data Systems procurement scenario.

This is the canonical synthetic test case from the ProofDesk spec.
"""

FIXTURE = {
    "case_id": "case_northstar_001",
    "prompt": (
        "Prepare Northstar Data Systems for a $42,500 annual software procurement. "
        "Reconcile the packet, create the approval memo, and send it for signature "
        "if it is safe."
    ),
    "documents": [
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
    "expected_extractions": [
        {
            "field": "vendor.legal_name",
            "doc_id": "doc_procurement_request",
            "value_raw": "Northstar Data Systems Ltd.",
            "value_normalized": "Northstar Data Systems Ltd",
            "page": 1,
            "confidence": 0.98,
        },
        {
            "field": "vendor.legal_name",
            "doc_id": "doc_vendor_quote",
            "value_raw": "Northstar Data Systems Limited",
            "value_normalized": "Northstar Data Systems Ltd",
            "page": 1,
            "confidence": 0.97,
        },
        {
            "field": "quote.platform_price",
            "doc_id": "doc_vendor_quote",
            "value_raw": "$35,000",
            "value_normalized": "35000",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "quote.support_price",
            "doc_id": "doc_vendor_quote",
            "value_raw": "$7,500",
            "value_normalized": "7500",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "quote.total",
            "doc_id": "doc_vendor_quote",
            "value_raw": "$42,500",
            "value_normalized": "42500",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "procurement.requested_spend",
            "doc_id": "doc_procurement_request",
            "value_raw": "$42,500",
            "value_normalized": "42500",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "insurance.expiry_date",
            "doc_id": "doc_certificate_insurance",
            "value_raw": "2027-08-31",
            "value_normalized": "2027-08-31",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "procurement.required_coverage_until",
            "doc_id": "doc_procurement_request",
            "value_raw": "2027-10-01",
            "value_normalized": "2027-10-01",
            "page": 1,
            "confidence": 0.98,
        },
        {
            "field": "security.data_retention_days",
            "doc_id": "doc_security_questionnaire",
            "value_raw": "30 days",
            "value_normalized": "30",
            "page": 1,
            "confidence": 0.97,
        },
        {
            "field": "security.subprocessors",
            "doc_id": "doc_security_questionnaire",
            "value_raw": "3",
            "value_normalized": "3",
            "page": 1,
            "confidence": 0.99,
        },
        {
            "field": "security.encryption_at_rest",
            "doc_id": "doc_security_questionnaire",
            "value_raw": "Yes",
            "value_normalized": "true",
            "page": 1,
            "confidence": 0.98,
        },
    ],
    "expected_assertions": [
        {
            "predicate": "quote.total == quote.platform_price + quote.support_price",
            "result": "PASS",
            "detail": "35000 + 7500 = 42500",
            "severity": "BLOCKER",
        },
        {
            "predicate": "vendor.legal_name matches across documents",
            "result": "PASS",
            "detail": "Normalized: 'Northstar Data Systems Ltd' matches in all docs",
            "severity": "WARNING",
        },
        {
            "predicate": "insurance.expiry_date >= procurement.required_coverage_until",
            "result": "FAIL",
            "detail": "2027-08-31 < 2027-10-01 — insurance expires 61 days before required coverage",
            "severity": "BLOCKER",
        },
        {
            "predicate": "procurement.requested_spend == quote.total",
            "result": "PASS",
            "detail": "42500 == 42500",
            "severity": "BLOCKER",
        },
        {
            "predicate": "security.encryption_at_rest == true",
            "result": "PASS",
            "detail": "Encryption at rest confirmed",
            "severity": "BLOCKER",
        },
    ],
}
