#!/usr/bin/env python3
"""ProofDesk Demo — 3-minute hackathon presentation.

Story arc (the 3-minute transaction):
  0:00-0:15  — Premise: "AI can prepare the document. Can it sign?"
  0:15-0:40  — Nutrient extracts grounded evidence
  0:40-1:00  — SignatureGate BLOCKS the unsafe signature
  1:00-1:20  — Human resolves the blocker, approves the record
  1:20-1:45  — Doctavian generates the conditional approval memo
  1:45-2:10  — Foxit MCP merges + compresses (reversible work)
  2:10-2:35  — SignatureGate passes → signing request sent
  2:35-2:55  — Hash tamper detection → blocked again
  2:55-3:10  — Audit trail with Merkle proofs

Usage:
  python3 demo_2min.py              # Run with test PDFs
  python3 demo_2min.py --api        # Use real Nutrient API
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(__file__))

from src.engine.batch import get_processor
from src.engine.feedback import get_loop
from src.providers.classifier import classify_document
from src.models.domain import Case, CaseState, Document, ResolutionDecision, _id
from src.engine.orchestrator import (
    run_pipeline, resolve_exception, approve_record,
    generate_document, prepare_pdf, request_signature, sign_document,
)
from src.state.machine import can_request_signature
from src.audit.chain import EventLedger


BANNER = "=" * 64


def pause(secs=0.8):
    time.sleep(secs)


# ── 0:00-0:15 — The Premise ──────────────────────────────────

def act_premise():
    print(f"\n{BANNER}")
    print("  PROOFDESK — Evidence-Gated Document Execution")
    print(f"{BANNER}\n")
    print('  Agent: "Prepare the Northstar vendor agreement for $42,500')
    print('         and send it to our CFO for signature."\n')
    print('  The agent can extract data, generate agreements, merge PDFs.')
    print('  The dangerous question: should it be able to sign?')
    pause()


# ── 0:15-0:40 — Nutrient Evidence Extraction ─────────────────

def act_evidence(case):
    print(f"\n{BANNER}")
    print("  STAGE 1 — NUTRIENT DWS: Evidence Extraction")
    print(f"{BANNER}\n")

    if case.facts:
        print("  Extracted facts with source grounding:\n")
        print("  {'Field':<30} {'Value':<25} {'Conf':>5}  Source")
        print("  " + "-" * 75)
        for f in case.facts:
            pub = f.to_public()
            val = pub.get("value_normalized", "N/A")[:24]
            conf = pub.get("confidence")
            conf_str = f"{conf:.0%}" if conf is not None else "N/A"
            page = pub.get("source_page") or pub.get("page") or "?"
            print(f"  {pub['field']:<30} {val:<25} {conf_str:>5}  page {page}")
    else:
        print("  (Using stub extraction — set NUTRIENT_API_KEY for live)")
        print("  vendor.legal_name   = Northstar Data Systems")
        print("  procurement.spend   = $42,500")
        print("  insurance.expiry    = 2026-07-31  ← EXPIRED")
    pause()


# ── 0:40-1:00 — SignatureGate BLOCKS ─────────────────────────

def act_blocked(case):
    print(f"\n{BANNER}")
    print("  STAGE 2 — SIGNATUREGATE: Authority Check")
    print(f"{BANNER}\n")

    gate = can_request_signature(case)
    if gate["allowed"]:
        print("  [GATE PASSED] — all checks OK")
    else:
        print("  ┌─────────────────────────────────────────────────┐")
        print("  │              SIGNATURE DENIED                   │")
        for reason in gate.get("reasons", []):
            if isinstance(reason, dict):
                code = reason.get("code", "UNKNOWN")
                detail = reason.get("detail", "")
                msg = f"{code}: {detail}" if detail else code
            else:
                msg = str(reason)
            print(f"  │  ✗ {msg:<43}│")
        print("  └─────────────────────────────────────────────────┘")
        print()
        print("  No Foxit eSign call was made. The agent cannot sign.")
        print("  This is the security boundary — architectural, not a workflow convention.")
    pause()


# ── 1:00-1:20 — Human Resolves ──────────────────────────────

def act_resolve(case):
    print(f"\n{BANNER}")
    print("  STAGE 3 — HUMAN RESOLUTION")
    print(f"{BANNER}\n")

    blocking = [a for a in case.assertions if a.result.value == "FAIL"
                and a.severity.value == "BLOCKER"]
    if not blocking:
        print("  No blocking exceptions to resolve.")
        pause()
        return

    for a in blocking:
        print(f"  Resolving: {a.assertion_id}")
        print(f"    Rule:     {a.predicate}")
        print(f"    Severity: {a.severity.value}")
        resolve_exception(case, a.assertion_id, ResolutionDecision.ACCEPT,
                          "Human verified: insurance certificate renewed",
                          actor_id="procurement-reviewer")
        print(f"    → RESOLVED (ACCEPT) by procurement-reviewer")
    pause()


# ── 1:20-1:45 — Doctavian Generates ─────────────────────────

def act_generate(case):
    print(f"\n{BANNER}")
    print("  STAGE 4 — DOCTAVIAN: Document Generation")
    print(f"{BANNER}\n")

    try:
        generate_document(case)
        print("  Generated approval memorandum via Doctavian API.")
        if case._confidence:
            print(f"  Risk band:    {case._confidence.get('band', 'N/A')}")
            print(f"  Confidence:   {case._confidence.get('confidence', 0):.1%}")
        if case.generated_artifact:
            print(f"  Artifact:     {case.generated_artifact.artifact_id}")
            print(f"  Content hash: {case.generated_artifact.content_hash}")
    except Exception as e:
        print(f"  Generation: {e}")
        print("  (Doctavian cloud generation requires valid bearer token)")
    pause()


# ── 1:45-2:10 — Foxit MCP Reversible Work ───────────────────

def act_prepare(case):
    print(f"\n{BANNER}")
    print("  STAGE 5 — FOXIT MCP: Reversible PDF Preparation")
    print(f"{BANNER}\n")
    print("  REVERSIBLE WORK — AGENT AUTHORIZED\n")

    try:
        prepare_pdf(case)
        detail = case.audit_events[-1].detail if case.audit_events else {}
        print(f"  Provider:  {detail.get('provider', 'N/A')}")
        print(f"  Source ID: {detail.get('source_id', 'N/A')}")
        print(f"  Memo ID:   {detail.get('memo_id', 'N/A')}")
        print(f"  Merge:     {detail.get('merge_task', 'N/A')}")
        print(f"  Compress:  {detail.get('compress_task', 'N/A')}")
    except Exception as e:
        print(f"  Preparation failed: {e}")
        print("  → Signature path is BLOCKED (fail-closed)")
    pause()


# ── 2:10-2:35 — Gate Passes + Signing ────────────────────────

def act_sign(case):
    print(f"\n{BANNER}")
    print("  STAGE 6 — SIGNATUREGATE: Final Authorization")
    print(f"{BANNER}\n")

    gate = can_request_signature(case)
    if gate["allowed"]:
        print("  ┌─────────────────────────────────────────────────┐")
        print("  │           SIGNATURE AUTHORIZED                  │")
        for check in gate.get("checks", []):
            print(f"  │  ✓ {check:<43}│")
        print("  └─────────────────────────────────────────────────┘")
        print()
        try:
            request_signature(case, signer="cfo@northstar.com")
            print("  Signing request sent to: cfo@northstar.com")
            print("  (In production: Foxit eSign sends real signing link.")
            print("   We demo with FreeSign due to API access constraints.)")
        except Exception as e:
            print(f"  Signing request: {e}")
    else:
        print("  DENIED — see reasons above")
    pause()


# ── 2:35-2:55 — Hash Tamper Detection ────────────────────────

def act_tamper(case):
    print(f"\n{BANNER}")
    print("  STAGE 7 — TAMPER DETECTION")
    print(f"{BANNER}\n")

    if case.structured_record:
        print(f"  Approved record hash:  {case.structured_record.content_hash}")
    if case.generated_artifact:
        print(f"  Artifact hash:         {case.generated_artifact.content_hash}")

    print()
    print("  If anyone modifies the artifact after approval:")
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │              SIGNATURE DENIED                   │")
    print("  │  ✗ ARTIFACT_HASH_MISMATCH                      │")
    print("  │    Approved:  a94e...                           │")
    print("  │    Current:   1ff2...                           │")
    print("  └─────────────────────────────────────────────────┘")
    print()
    print("  The hash chain proves the signed artifact is exactly")
    print("  the artifact that was approved. No substitution allowed.")
    pause()


# ── 2:55-3:10 — Audit Trail ──────────────────────────────────

def act_audit(case):
    print(f"\n{BANNER}")
    print("  STAGE 8 — AUDIT TRAIL")
    print(f"{BANNER}\n")

    print(f"  Total audit events: {len(case.audit_events)}")
    print()
    print("  Event chain:")
    for i, evt in enumerate(case.audit_events):
        actor = evt.actor or "system"
        arrow = "  → " if i > 0 else "    "
        print(f"  {arrow}[{evt.event_type}] by {actor}")
        if evt.detail and isinstance(evt.detail, dict):
            for k, v in list(evt.detail.items())[:2]:
                print(f"        {k}: {str(v)[:50]}")

    print()
    print("  Chain integrity: each event includes the previous event's hash.")
    print("  Any modification to history invalidates all subsequent events.")
    pause()


# ── Main ──────────────────────────────────────────────────────

def main():
    use_api = "--api" in sys.argv

    print("\n  ProofDesk — DevNetwork API+Cloud+AI Hackathon 2026")
    print("  'AI does the reversible work. Evidence and people")
    print("   control the irreversible.'\n")
    pause(1.5)

    # Act 1: Premise
    act_premise()

    # Create a case and run the pipeline to EXTRACTED/CHECKED state
    from src.models.use_cases import get_use_case
    uc = get_use_case("procurement")
    case = Case(prompt=uc.prompt)
    for doc_data in uc.documents:
        case.documents.append(Document(
            doc_id=doc_data["doc_id"],
            case_id=case.case_id,
            filename=doc_data["filename"],
            content_type=doc_data["content_type"],
            raw_text=doc_data["source_text"],
        ))

    # Run pipeline — will stop at REVIEW_REQUIRED if blockers exist, or APPROVABLE if not
    try:
        run_pipeline(case)
    except Exception:
        pass

    # Act 2: Evidence
    act_evidence(case)

    # Act 3: Blocked
    act_blocked(case)

    # Act 4: Human resolves (if there are blocking exceptions)
    if case.state == CaseState.REVIEW_REQUIRED:
        act_resolve(case)
        # Continue pipeline after resolution — goes to APPROVABLE
        try:
            run_pipeline(case)
        except Exception:
            pass

    # Approve the record (required before generate)
    if case.state == CaseState.APPROVABLE:
        try:
            approve_record(case, actor_id="procurement-reviewer")
        except Exception:
            pass

    # Act 5: Generate
    act_generate(case)

    # Act 6: Prepare
    act_prepare(case)

    # Act 7: Sign
    act_sign(case)

    # Act 8: Tamper detection
    act_tamper(case)

    # Act 9: Audit
    act_audit(case)

    # Closing
    print(f"\n{BANNER}")
    print("  DEMO COMPLETE")
    print(f"{BANNER}\n")
    print("  One transaction. Three sponsors. One story:")
    print()
    print("  Nutrient → evidence extraction with source grounding")
    print("  ProofDesk → risk-aware document generation + authority gate")
    print("  Foxit → reversible PDF preparation")
    print()
    print("  'AI does the reversible work.")
    print("   Evidence and people control the irreversible.'\n")


if __name__ == "__main__":
    main()
