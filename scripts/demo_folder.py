#!/usr/bin/env python3
"""ProofDesk Demo — drop in procurement docs, agent processes with REAL Nutrient API.

Run:
    NUTRIENT_API_KEY="pdf_live_..." python3 demo_folder.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from src.providers.nutrient import extract_from_document_sync
from src.providers.doctavian import DoctavianClient
from src.models.domain import Document, Case, CaseState, ResolutionDecision
from src.engine.orchestrator import run_pipeline, resolve_exception, approve_record, generate_document, prepare_pdf, request_signature, sign_document
from src.state.machine import can_request_signature
from src.audit.chain import EventLedger

# ============================================================
# Config
# ============================================================

PDF_DIR = os.path.join(os.path.dirname(__file__), "data", "test_pdfs")
API_KEY = os.environ.get("NUTRIENT_API_KEY", "")

if not API_KEY:
    print("ERROR: Set NUTRIENT_API_KEY environment variable")
    sys.exit(1)

# ============================================================
# Main Demo
# ============================================================

def divider(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    divider("PROOFDESK — Evidence-Gated Document Execution")
    print("  Real Nutrient DWS API | Real Doctavian API | Real Foxit PDF Services")
    print("  AI prepares. Humans decide. Audit proves it.\n")

    # Check Doctavian status
    doctavian = DoctavianClient()
    if doctavian.is_configured:
        print("  Doctavian: CONFIGURED (will attempt real API, fallback to local)")
    else:
        print("  Doctavian: NOT CONFIGURED (using local generation)")
    print()

    # 1. Discover procurement documents only
    divider("1. DISCOVER PROCUREMENT DOCUMENTS")
    procurement_pdfs = [
        "procurement_request.pdf",
        "vendor_quote.pdf",
        "insurance_certificate.pdf",
        "security_questionnaire.pdf",
    ]
    available = [f for f in procurement_pdfs if os.path.exists(os.path.join(PDF_DIR, f))]
    print(f"  Folder: {PDF_DIR}")
    print(f"  Procurement docs: {len(available)}/4")
    for f in available:
        print(f"    - {f}")

    # 2. Create case and load procurement PDFs
    divider("2. LOAD PROCUREMENT DOCUMENTS")
    case = Case(prompt="Prepare Northstar Data Systems for $42,500 procurement.")
    for pdf_name in available:
        path = os.path.join(PDF_DIR, pdf_name)
        with open(path, "rb") as f:
            raw = f.read()
        case.documents.append(Document(
            doc_id=pdf_name.replace(".pdf", ""),
            case_id=case.case_id,
            filename=pdf_name,
            content_type="application/pdf",
            raw_bytes=raw,
            raw_text=raw.decode("latin-1", errors="replace"),
        ))
    print(f"  Loaded {len(case.documents)} documents ({sum(len(d.raw_bytes) for d in case.documents)} bytes total)")

    # 3. Extract with Nutrient DWS (REAL API)
    divider("3. EXTRACT — Nutrient DWS (REAL API)")
    start = time.time()
    run_pipeline(case)
    extract_time = (time.time() - start) * 1000
    print(f"  Extracted {len(case.facts)} facts in {extract_time:.0f}ms")
    print(f"\n  Facts:")
    for f in case.facts:
        print(f"    [{f.confidence:.0%}] {f.field_name}: {f.value_normalized} (page {f.source_page})")

    # 4. Deterministic checks
    divider("4. VERIFICATION — Deterministic Checks")
    print(f"  {len(case.assertions)} checks:")
    for a in case.assertions:
        icon = "PASS" if a.result.value == "PASS" else "FAIL"
        print(f"    [{icon}] {a.predicate}")
        if a.result.value == "FAIL":
            print(f"         {a.detail}")

    # 5. Premature signature attempt
    divider("5. SIGNATURE GATE — Premature Attempt")
    gate = can_request_signature(case)
    print(f"  Allowed: {gate['allowed']}")
    if not gate["allowed"]:
        print(f"  Denied for {len(gate['reasons'])} reasons:")
        for r in gate["reasons"]:
            print(f"    - {r['code']}: {r.get('detail', '')}")

    # 6. Human resolution
    divider("6. HUMAN RESOLUTION")
    failing = [a for a in case.assertions if a.result.value == "FAIL"]
    if failing:
        print(f"  Resolving: {failing[0].predicate}")
        print(f"  Detail: {failing[0].detail}")
        resolve_exception(case, failing[0].assertion_id,
                         ResolutionDecision.CONDITIONAL_ACCEPT,
                         "Renewed insurance certificate required before current policy expires.",
                         "procurement_manager")
        print(f"  Decision: CONDITIONAL_ACCEPT")
        print(f"  State: {case.state.value}")

    # 7. Approve
    divider("7. APPROVE STRUCTURED RECORD")
    approve_record(case, "procurement_manager")
    print(f"  Record hash: {case.structured_record.content_hash}")
    print(f"  Revision: {case.structured_record.revision}")

    # 8. Generate document
    divider("8. GENERATE DOCUMENT")
    generate_document(case)
    print(f"  Artifact: {case.generated_artifact.artifact_id}")
    content = case._generated_content.get(case.generated_artifact.artifact_id, "")
    print(f"  Content: {len(content)} chars")
    # Show first 3 lines
    for line in content.split("\n")[:3]:
        if line.strip():
            print(f"    {line.strip()}")

    # 9. Prepare PDF (Foxit)
    divider("9. PREPARE PDF — Foxit PDF Services (REAL API)")
    prepare_pdf(case)
    print(f"  PDF prepared via Foxit merge")

    # 10. Request signature
    divider("10. REQUEST SIGNATURE")
    request_signature(case, "cfo@northstar.com")
    print(f"  Signer: {case.signature_request.signer}")
    print(f"  Foxit request: {case.signature_request.foxit_request_id}")

    # 11. Sign
    divider("11. SIGN")
    sign_document(case)
    print(f"  Status: {case.signature_request.status}")
    print(f"  Signed at: {case.signature_request.signed_at}")

    # 12. Audit trail
    divider("12. AUDIT TRAIL")
    print(f"  Events: {len(case.audit_events)}")
    for e in case.audit_events:
        print(f"    {e.event_type:25s} {e.from_state:25s} -> {e.to_state:25s} [{e.actor}]")

    # Summary
    divider("DEMO COMPLETE")
    print(f"\n  State: {case.state.value}")
    print(f"  Facts: {len(case.facts)}")
    print(f"  Assertions: {len(case.assertions)}")
    print(f"  Resolutions: {len(case.resolutions)}")
    print(f"  Audit events: {len(case.audit_events)}")
    print(f"  Record hash: {case.structured_record.content_hash}")
    print(f"  Artifact hash: {case.generated_artifact.content_hash}")
    print(f"  Signed by: {case.signature_request.signer}")
    print(f"\n  Real APIs used:")
    print(f"    Nutrient DWS: {len(case.facts)} facts extracted from {len(case.documents)} PDFs")
    print(f"    Foxit PDF: document merged (REAL API)")
    print(f"    Foxit eSign: signature requested")


if __name__ == "__main__":
    main()
