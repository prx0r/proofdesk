#!/usr/bin/env python3
"""
A/B Test Harness — Nutrient DWS Extraction on all 6 use cases.

Tests real Nutrient API extraction against known ground truth,
then applies FactMiner 4-way verdict logic.
"""

import json
import os
import sys
import time
import requests

# Config
NUTRIENT_API_KEY = os.environ.get(
    "NUTRIENT_API_KEY", "pdf_live_hAAUR0ppmrzrIQcOqnPH29ea5z0uioX8pO9SGG6XYmk"
)
NUTRIENT_URL = "https://api.nutrient.io/extraction/extract"
PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "test_pdfs")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "benchmarks")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================
# SCHEMAS — one per use case
# ============================================================
SCHEMAS = {
    "procurement_request": {
        "type": "object",
        "properties": {
            "vendor_legal_name": {"type": "string", "description": "Legal name of vendor"},
            "requested_spend": {"type": "number", "description": "Total requested spend in USD"},
            "contract_start": {"type": "string", "description": "Contract start date"},
            "required_coverage_until": {"type": "string", "description": "Required insurance coverage end date"},
            "payment_terms": {"type": "string", "description": "Payment terms"},
        },
        "required": ["vendor_legal_name"],
    },
    "procurement_quote": {
        "type": "object",
        "properties": {
            "vendor_legal_name": {"type": "string", "description": "Vendor legal name"},
            "quote_total": {"type": "number", "description": "Total quote amount"},
            "platform_price": {"type": "number", "description": "Platform license price"},
            "support_price": {"type": "number", "description": "Support services price"},
            "payment_terms": {"type": "string", "description": "Payment terms"},
            "quote_valid_until": {"type": "string", "description": "Quote expiry date"},
        },
        "required": ["quote_total"],
    },
    "procurement_insurance": {
        "type": "object",
        "properties": {
            "insured_name": {"type": "string", "description": "Name of insured party"},
            "policy_type": {"type": "string", "description": "Type of insurance policy"},
            "policy_number": {"type": "string", "description": "Policy number"},
            "effective_date": {"type": "string", "description": "Policy start date"},
            "expiry_date": {"type": "string", "description": "Policy expiry date"},
            "coverage_limit": {"type": "number", "description": "Coverage limit in USD"},
        },
        "required": ["expiry_date"],
    },
    "procurement_security": {
        "type": "object",
        "properties": {
            "company_name": {"type": "string", "description": "Company name"},
            "data_retention_days": {"type": "number", "description": "Data retention in days"},
            "subprocessor_count": {"type": "number", "description": "Number of subprocessors"},
            "encryption_at_rest": {"type": "boolean", "description": "Encryption at rest enabled"},
            "soc2_type2": {"type": "boolean", "description": "SOC 2 Type II certified"},
        },
        "required": ["company_name"],
    },
    "kyc_id": {
        "type": "object",
        "properties": {
            "full_name": {"type": "string", "description": "Full legal name"},
            "date_of_birth": {"type": "string", "description": "Date of birth"},
            "license_number": {"type": "string", "description": "ID/license number"},
            "address": {"type": "string", "description": "Current address"},
            "expiry_date": {"type": "string", "description": "ID expiry date"},
        },
        "required": ["full_name"],
    },
    "kyc_address": {
        "type": "object",
        "properties": {
            "account_holder": {"type": "string", "description": "Account holder name"},
            "service_address": {"type": "string", "description": "Service/billing address"},
            "billing_period": {"type": "string", "description": "Billing period"},
            "amount_due": {"type": "number", "description": "Amount due"},
        },
        "required": ["service_address"],
    },
    "kyc_bank": {
        "type": "object",
        "properties": {
            "account_holder": {"type": "string", "description": "Account holder name"},
            "statement_period": {"type": "string", "description": "Statement period"},
            "opening_balance": {"type": "number", "description": "Opening balance"},
            "closing_balance": {"type": "number", "description": "Closing balance"},
            "account_type": {"type": "string", "description": "Account type"},
        },
        "required": ["account_holder"],
    },
    "invoice": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string", "description": "Invoice number"},
            "invoice_date": {"type": "string", "description": "Invoice date"},
            "due_date": {"type": "string", "description": "Payment due date"},
            "vendor_name": {"type": "string", "description": "Vendor company name"},
            "customer_name": {"type": "string", "description": "Customer company name"},
            "total_amount": {"type": "number", "description": "Total amount due"},
            "payment_terms": {"type": "string", "description": "Payment terms"},
            "origin_country": {"type": "string", "description": "Country of origin"},
        },
        "required": ["invoice_number", "total_amount"],
    },
    "trade_invoice": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string", "description": "Invoice number"},
            "shipper": {"type": "string", "description": "Shipper company"},
            "consignee": {"type": "string", "description": "Consignee company"},
            "origin": {"type": "string", "description": "Country of origin"},
            "incoterm": {"type": "string", "description": "Incoterm"},
            "quantity": {"type": "string", "description": "Quantity"},
            "total_value": {"type": "number", "description": "Total value in USD"},
        },
        "required": ["invoice_number"],
    },
    "trade_bol": {
        "type": "object",
        "properties": {
            "bl_number": {"type": "string", "description": "Bill of lading number"},
            "shipper": {"type": "string", "description": "Shipper"},
            "consignee": {"type": "string", "description": "Consignee"},
            "port_of_loading": {"type": "string", "description": "Port of loading"},
            "port_of_discharge": {"type": "string", "description": "Port of discharge"},
            "quantity": {"type": "string", "description": "Quantity"},
            "freight": {"type": "string", "description": "Freight terms"},
        },
        "required": ["bl_number"],
    },
    "trade_certificate": {
        "type": "object",
        "properties": {
            "certificate_number": {"type": "string", "description": "Certificate number"},
            "country_of_origin": {"type": "string", "description": "Country of origin"},
            "invoice_reference": {"type": "string", "description": "Invoice reference"},
            "hs_code": {"type": "string", "description": "HS code"},
            "quantity": {"type": "string", "description": "Quantity"},
        },
        "required": ["country_of_origin"],
    },
    "mortgage_appraisal": {
        "type": "object",
        "properties": {
            "property_address": {"type": "string", "description": "Property address"},
            "appraiser": {"type": "string", "description": "Appraiser name"},
            "property_type": {"type": "string", "description": "Property type"},
            "year_built": {"type": "number", "description": "Year built"},
            "square_footage": {"type": "number", "description": "Square footage"},
            "appraised_value": {"type": "number", "description": "Final appraised value"},
            "bedrooms": {"type": "number", "description": "Number of bedrooms"},
        },
        "required": ["appraised_value"],
    },
    "redaction_intake": {
        "type": "object",
        "properties": {
            "patient_name": {"type": "string", "description": "Patient full name"},
            "date_of_birth": {"type": "string", "description": "Patient date of birth"},
            "ssn": {"type": "string", "description": "Social security number"},
            "phone": {"type": "string", "description": "Phone number"},
            "email": {"type": "string", "description": "Email address"},
            "insurance_id": {"type": "string", "description": "Insurance ID"},
            "chief_complaint": {"type": "string", "description": "Chief complaint"},
        },
        "required": ["patient_name"],
    },
}

# ============================================================
# GROUND TRUTH — what we expect to extract
# ============================================================
GROUND_TRUTH = {
    "procurement_01_request.pdf": {
        "vendor_legal_name": "Northstar Data Systems Ltd.",
        "requested_spend": 42500,
        "contract_start": "2026-10-01",
        "required_coverage_until": "2027-10-01",
        "payment_terms": "Net 60",
    },
    "procurement_02_quote.pdf": {
        "vendor_legal_name": "Northstar Data Systems Limited",
        "quote_total": 42500,
        "platform_price": 35000,
        "support_price": 7500,
        "payment_terms": "Net 30",
    },
    "procurement_03_insurance.pdf": {
        "insured_name": "Northstar Data Systems Ltd.",
        "policy_type": "Commercial General Liability",
        "expiry_date": "2027-08-31",
        "coverage_limit": 2000000,
    },
    "procurement_04_security.pdf": {
        "company_name": "Northstar Data Systems Ltd.",
        "data_retention_days": 30,
        "subprocessor_count": 3,
        "encryption_at_rest": True,
        "soc2_type2": True,
    },
    "kyc_01_drivers_license.pdf": {
        "full_name": "Sarah Chen",
        "date_of_birth": "1990-03-15",
        "license_number": "D1234567",
        "expiry_date": "2028-03-15",
    },
    "kyc_02_proof_of_address.pdf": {
        "account_holder": "Sarah M Chen",
        "service_address": "1847 Mission St, San Francisco, CA 94103",
        "amount_due": 142.37,
    },
    "kyc_03_bank_statement.pdf": {
        "account_holder": "Sarah Chen",
        "opening_balance": 12847.52,
        "closing_balance": 14203.18,
        "account_type": "Checking",
    },
    "invoice_01_vendor_invoice.pdf": {
        "invoice_number": "INV-2026-7891",
        "vendor_name": "GlobalTech Manufacturing Co.",
        "customer_name": "Pacific Imports Ltd.",
        "total_amount": 315700,
        "origin_country": "China",
    },
    "trade_01_invoice.pdf": {
        "invoice_number": "INV-2026-7891",
        "shipper": "GlobalTech Manufacturing Co.",
        "consignee": "Pacific Imports Ltd.",
        "origin": "China",
        "incoterm": "FOB Shanghai",
        "total_value": 300000,
    },
    "trade_02_bill_of_lading.pdf": {
        "bl_number": "COSU6280034100",
        "shipper": "GlobalTech Manufacturing Co.",
        "consignee": "Pacific Imports Ltd.",
        "freight": "Freight Prepaid",
    },
    "trade_03_certificate_origin.pdf": {
        "country_of_origin": "China",
        "invoice_reference": "INV-2026-7891",
        "hs_code": "8501.53",
    },
    "mortgage_01_appraisal.pdf": {
        "property_address": "742 Evergreen Terrace, Springfield, IL 62704",
        "property_type": "Single Family Residence",
        "year_built": 1998,
        "square_footage": 2340,
        "appraised_value": 387500,
        "bedrooms": 4,
    },
    "redaction_01_intake_form.pdf": {
        "patient_name": "Robert Johnson",
        "date_of_birth": "1975-06-22",
        "ssn": "123-45-6789",
        "phone": "(555) 234-5678",
        "email": "r.johnson@email.com",
        "insurance_id": "BC-9928371",
        "chief_complaint": "Lower back pain, 3 weeks duration",
    },
}

# Map PDFs to their schemas
PDF_TO_SCHEMA = {
    "procurement_01_request.pdf": "procurement_request",
    "procurement_02_quote.pdf": "procurement_quote",
    "procurement_03_insurance.pdf": "procurement_insurance",
    "procurement_04_security.pdf": "procurement_security",
    "kyc_01_drivers_license.pdf": "kyc_id",
    "kyc_02_proof_of_address.pdf": "kyc_address",
    "kyc_03_bank_statement.pdf": "kyc_bank",
    "invoice_01_vendor_invoice.pdf": "invoice",
    "trade_01_invoice.pdf": "trade_invoice",
    "trade_02_bill_of_lading.pdf": "trade_bol",
    "trade_03_certificate_origin.pdf": "trade_certificate",
    "mortgage_01_appraisal.pdf": "mortgage_appraisal",
    "redaction_01_intake_form.pdf": "redaction_intake",
}


def extract_from_nutrient(pdf_path: str, schema: dict) -> dict:
    """Call real Nutrient DWS extraction API."""
    with open(pdf_path, "rb") as f:
        response = requests.post(
            NUTRIENT_URL,
            headers={"Authorization": f"Bearer {NUTRIENT_API_KEY}"},
            files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
            data={
                "instructions": json.dumps(
                    {
                        "schema": schema,
                        "parseConfig": {"mode": "understand"},
                        "instructions": "Extract all fields precisely. Dates in ISO format. Currency as numbers without symbols.",
                    }
                )
            },
            timeout=60,
        )
    if response.status_code != 200:
        return {"error": response.status_code, "text": response.text[:500]}
    return response.json()


def compare_field(extracted, expected, field_name) -> dict:
    """Compare extracted value to ground truth. Returns verdict."""
    if extracted is None:
        return {"field": field_name, "verdict": "INSUFFICIENT", "extracted": None, "expected": expected}

    ext_str = str(extracted).strip().lower()
    exp_str = str(expected).strip().lower()

    # Exact match
    if ext_str == exp_str:
        return {"field": field_name, "verdict": "SUPPORTED", "extracted": extracted, "expected": expected}

    # Numeric near-match (within 1%)
    try:
        ext_num = float(ext_str.replace("$", "").replace(",", ""))
        exp_num = float(exp_str.replace("$", "").replace(",", ""))
        if abs(ext_num - exp_num) / max(abs(exp_num), 1) < 0.01:
            return {"field": field_name, "verdict": "SUPPORTED", "extracted": extracted, "expected": expected}
    except (ValueError, TypeError):
        pass

    # Substring match
    if exp_str in ext_str or ext_str in exp_str:
        return {"field": field_name, "verdict": "SUPPORTED", "extracted": extracted, "expected": expected}

    # Date partial match (year-month-day vs month/day/year etc)
    # Try normalized date comparison
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"]:
        try:
            from datetime import datetime
            ext_dt = datetime.strptime(extracted.split("T")[0], fmt)
            exp_dt = datetime.strptime(expected.split("T")[0], fmt)
            if ext_dt == exp_dt:
                return {"field": field_name, "verdict": "SUPPORTED", "extracted": extracted, "expected": expected}
        except (ValueError, TypeError):
            continue

    return {"field": field_name, "verdict": "REFUTED", "extracted": extracted, "expected": expected}


def apply_factminer_verdicts(comparisons: list) -> dict:
    """Apply FactMiner 4-way verdict logic to extraction results."""
    supported = [c for c in comparisons if c["verdict"] == "SUPPORTED"]
    refuted = [c for c in comparisons if c["verdict"] == "REFUTED"]
    insufficient = [c for c in comparisons if c["verdict"] == "INSUFFICIENT"]

    total = len(comparisons)
    if total == 0:
        return {"overall": "INSUFFICIENT", "confidence": 0.0}

    support_rate = len(supported) / total

    if support_rate >= 0.8 and len(refuted) == 0:
        overall = "SUPPORTED"
    elif len(refuted) > 0 and support_rate >= 0.5:
        overall = "CONFLICTING"
    elif len(refuted) > 0:
        overall = "REFUTED"
    else:
        overall = "INSUFFICIENT"

    return {
        "overall": overall,
        "support_rate": round(support_rate, 3),
        "supported": len(supported),
        "refuted": len(refuted),
        "insufficient": len(insufficient),
        "total": total,
    }


def run_ab_test():
    """Run extraction on all PDFs and compare to ground truth."""
    results = []
    summary = {"use_cases": {}, "total_fields": 0, "total_supported": 0, "total_refuted": 0, "total_insufficient": 0}

    print(f"{'='*70}")
    print(f"  NUTRIENT DWS A/B TEST — All 6 Use Cases")
    print(f"{'='*70}\n")

    for pdf_name, schema_name in PDF_TO_SCHEMA.items():
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        if not os.path.exists(pdf_path):
            print(f"  SKIP: {pdf_name} (not found)")
            continue

        schema = SCHEMAS[schema_name]
        truth = GROUND_TRUTH.get(pdf_name, {})

        print(f"  Testing: {pdf_name}")
        print(f"  Schema:  {schema_name}")

        # Extract
        start = time.time()
        response = extract_from_nutrient(pdf_path, schema)
        elapsed = time.time() - start

        if "error" in response:
            print(f"  ERROR: {response['error']} — {response['text'][:100]}")
            results.append({"pdf": pdf_name, "error": response["error"], "latency": elapsed})
            continue

        extracted = response.get("output", {}).get("data", {})
        metadata = response.get("output", {}).get("metadata", {})
        usage = response.get("usage", {}).get("data_extraction_credits", {})

        # Compare
        comparisons = []
        for field_name, expected_value in truth.items():
            extracted_value = extracted.get(field_name)
            citation = metadata.get(field_name, {})
            comp = compare_field(extracted_value, expected_value, field_name)
            comp["confidence"] = citation.get("confidence", None)
            comp["page"] = citation.get("pageNumber", None)
            comparisons.append(comp)

        # FactMiner verdict
        verdict = apply_factminer_verdicts(comparisons)

        # Report
        for c in comparisons:
            icon = "✓" if c["verdict"] == "SUPPORTED" else "✗" if c["verdict"] == "REFUTED" else "?"
            conf = f" (conf={c['confidence']:.2f})" if c.get("confidence") else ""
            print(f"    [{icon}] {c['field']}: {c['verdict']}{conf}")
            if c["verdict"] == "REFUTED":
                print(f"         extracted: {c['extracted']}")
                print(f"         expected:  {c['expected']}")

        print(f"  Result: {verdict['overall']} ({verdict['support_rate']:.0%} support, {elapsed:.1f}s)")
        print(f"  Credits: {usage.get('cost', '?')}")
        print()

        # Accumulate
        use_case = pdf_name.split("_")[0]
        if use_case not in summary["use_cases"]:
            summary["use_cases"][use_case] = {"supported": 0, "refuted": 0, "insufficient": 0, "total": 0}
        summary["use_cases"][use_case]["supported"] += verdict["supported"]
        summary["use_cases"][use_case]["refuted"] += verdict["refuted"]
        summary["use_cases"][use_case]["insufficient"] += verdict["insufficient"]
        summary["use_cases"][use_case]["total"] += verdict["total"]
        summary["total_fields"] += verdict["total"]
        summary["total_supported"] += verdict["supported"]
        summary["total_refuted"] += verdict["refuted"]
        summary["total_insufficient"] += verdict["insufficient"]

        results.append(
            {
                "pdf": pdf_name,
                "schema": schema_name,
                "extracted": extracted,
                "comparisons": comparisons,
                "verdict": verdict,
                "latency": elapsed,
                "credits": usage.get("cost", 0),
            }
        )

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}\n")

    print(f"  {'Use Case':<20} {'Supported':>10} {'Refuted':>10} {'Insufficient':>12} {'Total':>8} {'Accuracy':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*12} {'-'*8} {'-'*10}")

    for uc, data in sorted(summary["use_cases"].items()):
        acc = data["supported"] / data["total"] if data["total"] > 0 else 0
        print(
            f"  {uc:<20} {data['supported']:>10} {data['refuted']:>10} {data['insufficient']:>12} {data['total']:>8} {acc:>9.1%}"
        )

    total_acc = summary["total_supported"] / summary["total_fields"] if summary["total_fields"] > 0 else 0
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*12} {'-'*8} {'-'*10}")
    print(
        f"  {'TOTAL':<20} {summary['total_supported']:>10} {summary['total_refuted']:>10} {summary['total_insufficient']:>12} {summary['total_fields']:>8} {total_acc:>9.1%}"
    )

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nutrient_api_key": NUTRIENT_API_KEY[:20] + "...",
        "results": results,
        "summary": summary,
    }
    out_path = os.path.join(RESULTS_DIR, f"nutrient_ab_test_{time.strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {out_path}")

    return summary


if __name__ == "__main__":
    run_ab_test()
