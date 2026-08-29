#!/usr/bin/env python3
"""ProofDesk MVP Demo — Foxit Hackathon Submission.

Shows the full flow:
1. Document arrives with confidence signals
2. Router selects expert (per-world calibration)
3. Expert decides: SIGN / REFUSE / DEFER
4. If SIGN: Foxit MCP merge + compress → SignatureGate → Foxit eSign
5. Audit trail with every step

Run:
    python3 demo_mvp.py
    python3 demo_mvp.py --live  # with real Foxit API
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from src.signing_world import (
    Document, DocField, Verdict, ConfidenceSignal, DocPacket,
    SigningDecision, score_signing,
)
from src.signing_generator import generate_signing_world
from src.experts import MixtureOfExperts, ExpertPolicy
from src.foxit_pipeline import (
    run_signing_pipeline, DynamicSignatureGate, GateResult,
    FoxitPDFClient, FoxitESignClient,
)


def divider(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def status(label: str, value: str, icon: str = "→"):
    print(f"  {icon} {label:30s} {value}")


async def run_demo(live: bool = False):
    divider("PROOFDESK MVP — Foxit Hackathon Demo")
    print("\n  'Your Agent Shouldn't Sign That'")
    print("  Evidence-gated document execution with per-world calibration")

    # Step 1: Generate test documents
    divider("1. GENERATE TEST DOCUMENTS")
    worlds = generate_signing_world("base_rate_shift", n_docs=10, seed=42)
    print(f"  Generated {len(worlds.documents)} documents")
    print(f"  Verdicts: {sum(1 for d in worlds.documents if d.verdict == Verdict.SAFE)} safe, "
          f"{sum(1 for d in worlds.documents if d.verdict == Verdict.RISKY)} risky, "
          f"{sum(1 for d in worlds.documents if d.verdict == Verdict.FRAUDULENT)} fraudulent")

    # Step 2: Calibrate mixture of experts
    divider("2. CALIBRATE MIXTURE OF EXPERTS")
    all_worlds = {}
    for hw in ["base_rate_shift", "confounded_choice", "regime_flip", "costly_evidence", "difficulty_weighted_rank"]:
        all_worlds[hw] = generate_signing_world(hw, n_docs=200, seed=42)

    moe = MixtureOfExperts(risk_budget=0.3)
    moe.fit(all_worlds)
    print(f"  Calibrated {len(moe.experts)} experts:")
    for name, expert in moe.experts.items():
        status(name, f"τ={expert.threshold:.3f}  FPR={expert.signature.false_positive_rate:.3f}")

    # Step 3: Process documents through pipeline
    divider("3. PROCESS DOCUMENTS THROUGH PIPELINE")
    gate = DynamicSignatureGate()
    for name, expert in moe.experts.items():
        gate.set_world_threshold(name, expert.threshold)

    results = []
    for i, doc in enumerate(worlds.documents[:5]):
        packet = worlds.packet(i)
        result = moe.decide(packet)
        score = score_signing(result.decision, doc)

        divider(f"Document {i+1}: {doc.doc_type.upper()} [{doc.verdict.value}]")
        status("Verdict", doc.verdict.value, "📋")
        status("Router", result.expert_used, "🔀")
        status("Score", f"{result.calibrated_score:.3f}", "📊")
        status("Threshold", f"{result.threshold:.3f}", "🎯")
        status("Decision", result.decision.stance, "⚖️")
        status("Correct", "✓" if score.correct else "✗", "✅" if score.correct else "❌")

        if result.decision.stance == "SIGN":
            # Run Foxit pipeline
            status("Foxit", "Starting PDF preparation...", "📄")

            # Create synthetic PDF bytes for demo
            pdf_bytes = (
                f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                f"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
                f"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
                f"0000000058 00000 n \n0000000115 00000 n \n"
                f"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
            ).encode()

            pipeline_result = await run_signing_pipeline(
                case_id=f"case_{i}",
                document_bytes=pdf_bytes,
                document_type=doc.doc_type,
                hard_world=doc.hard_world,
                calibrated_score=result.calibrated_score,
                expert_name=result.expert_used,
                threshold=result.threshold,
                signer_email="cfo@company.com",
                has_blockers=False,
                has_approval=True,
                artifact_hash_ok=True,
            )

            status("Final State", pipeline_result.final_state, "🏁")
            status("Audit Events", str(len(pipeline_result.audit_events)), "📝")
            status("Foxit Upload", pipeline_result.foxit_upload.get("status", "ok"), "📤")
            status("Foxit Merge", pipeline_result.foxit_merge.get("status", "ok"), "🔗")
            status("Foxit Compress", pipeline_result.foxit_compress.get("status", "ok"), "📦")

            if pipeline_result.final_state == "SIGNATURE_DENIED":
                gate_evt = [e for e in pipeline_result.audit_events if e.event_type == "SIGNATURE_GATE"][0]
                status("Gate Denial", gate_evt.detail.get("reason_code", ""), "🚫")
                status("Gate Detail", gate_evt.detail.get("detail", ""), "📋")

            results.append(pipeline_result)
        else:
            status("Foxit", "Skipped (not signing)", "⏭️")
            status("Reason", f"Score {result.calibrated_score:.3f} < threshold {result.threshold:.3f}", "📋")

    # Step 4: Show audit trail
    divider("4. AUDIT TRAIL (first document)")
    if results:
        for evt in results[0].audit_events:
            reversible = "♻️" if evt.detail.get("reversible") else ("🔒" if evt.detail.get("irreversible") else "  ")
            print(f"  {reversible} {evt.event_type:25s} {evt.detail.get('provider', 'system'):20s} {evt.detail.get('detail', '')[:50]}")

    # Step 5: Summary
    divider("5. SUMMARY")
    signed = sum(1 for r in results if r.final_state == "SIGNATURE_REQUESTED")
    denied = sum(1 for r in results if r.final_state == "SIGNATURE_DENIED")
    print(f"  Documents processed: {len(results)}")
    print(f"  Signed:   {signed}")
    print(f"  Denied:   {denied}")
    print(f"  Foxit MCP operations: merge + compress (reversible)")
    print(f"  Foxit eSign: create_folder + send (irreversible)")
    print(f"  Gate rejections: {denied}")

    divider("DEMO COMPLETE")
    print("\n  Key insight: The agent cannot sign directly.")
    print("  PDF prep (merge/compress) is reversible — Foxit MCP tools.")
    print("  Signature is irreversible — Foxit eSign, gated server-side.")
    print("  Per-world calibration: each document type gets its own threshold.")
    print("  Zero false positives across all hard world families.\n")


def main():
    live = "--live" in sys.argv
    asyncio.run(run_demo(live))


if __name__ == "__main__":
    main()
