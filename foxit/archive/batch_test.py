#!/usr/bin/env python3
"""Batch test — runs multiple documents through the full Foxit pipeline.

Demonstrates:
1. Real Foxit PDF upload (when API keys set)
2. Real Foxit MCP merge + compress
3. SignatureGate blocking + passing
4. Audit trail for each document
5. Batch statistics

Usage:
    python3 batch_test.py
    python3 batch_test.py --live  # with real Foxit API
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from src.signing_world import Verdict, SigningDecision, score_signing, DocPacket
from src.signing_generator import generate_signing_world
from src.experts import MixtureOfExperts
from src.foxit_pipeline import (
    run_signing_pipeline, DynamicSignatureGate, GateResult,
    FoxitPDFClient, FoxitESignClient,
)

OUTPUT_DIR = "/tmp/proofdesk/batch_test"


def create_test_pdf(doc_type: str, verdict: str) -> bytes:
    """Create a minimal test PDF for each document type."""
    content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000226 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
305
%%EOF"""
    return content.encode()


async def run_batch_test(n_docs: int = 10, seed: int = 42):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    live = "--live" in sys.argv

    print(f"\n{'='*70}")
    print(f"  BATCH TEST — {n_docs} documents through Foxit pipeline")
    print(f"  Mode: {'LIVE (real API)' if live else 'SIMULATED'}")
    print(f"{'='*70}\n")

    # Generate test documents
    worlds = generate_signing_world("base_rate_shift", n_docs=n_docs, seed=seed)

    # Fit mixture
    all_worlds = {}
    for hw in ["base_rate_shift", "confounded_choice", "regime_flip"]:
        all_worlds[hw] = generate_signing_world(hw, n_docs=100, seed=seed)
    moe = MixtureOfExperts(risk_budget=0.1)
    moe.fit(all_worlds)

    # Set up gate
    gate = DynamicSignatureGate()
    for name, expert in moe.experts.items():
        gate.set_world_threshold(name, expert.threshold)

    # Run batch
    results = []
    t0 = time.time()

    for i in range(n_docs):
        doc = worlds.documents[i]
        packet = worlds.packet(i)
        result = moe.decide(packet)
        score = score_signing(result.decision, doc)

        print(f"--- Document {i+1}/{n_docs}: {doc.doc_type} [{doc.verdict.value}] ---")
        print(f"  Router: {result.expert_used}")
        print(f"  Score: {result.calibrated_score:.3f} (threshold: {result.threshold:.3f})")
        print(f"  Decision: {result.decision.stance}")

        if result.decision.stance == "SIGN":
            # Create test PDF
            pdf_bytes = create_test_pdf(doc.doc_type, doc.verdict.value)

            # Run pipeline
            pipeline_result = await run_signing_pipeline(
                case_id=f"batch_{i}",
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

            print(f"  Pipeline: {pipeline_result.final_state}")
            print(f"  Foxit Upload: {pipeline_result.foxit_upload.get('documentId', 'sim')[:12]}...")
            print(f"  Foxit Merge: {pipeline_result.foxit_merge.get('taskId', 'sim')[:12]}...")
            print(f"  Foxit Compress: {pipeline_result.foxit_compress.get('taskId', 'sim')[:12]}...")
            print(f"  Audit Events: {len(pipeline_result.audit_events)}")

            results.append({
                "doc_id": doc.doc_id,
                "doc_type": doc.doc_type,
                "verdict": doc.verdict.value,
                "decision": result.decision.stance,
                "score": result.calibrated_score,
                "threshold": result.threshold,
                "correct": score.correct,
                "pipeline_state": pipeline_result.final_state,
                "n_events": len(pipeline_result.audit_events),
                "foxit_upload": pipeline_result.foxit_upload.get("documentId", "sim"),
                "foxit_merge": pipeline_result.foxit_merge.get("taskId", "sim"),
            })
        else:
            print(f"  Pipeline: SKIPPED (not signing)")
            results.append({
                "doc_id": doc.doc_id,
                "doc_type": doc.doc_type,
                "verdict": doc.verdict.value,
                "decision": result.decision.stance,
                "score": result.calibrated_score,
                "threshold": result.threshold,
                "correct": score.correct,
                "pipeline_state": "SKIPPED",
                "n_events": 0,
            })

        print()

    elapsed = time.time() - t0

    # Summary
    print(f"{'='*70}")
    print(f"  BATCH TEST SUMMARY")
    print(f"{'='*70}")
    print(f"  Documents processed: {len(results)}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Avg time per doc: {elapsed/max(1,len(results)):.2f}s")

    signed = [r for r in results if r["decision"] == "SIGN"]
    refused = [r for r in results if r["decision"] == "REFUSE"]
    deferred = [r for r in results if r["decision"] == "DEFER"]

    print(f"\n  Decisions:")
    print(f"    SIGN:   {len(signed)}")
    print(f"    REFUSE: {len(refused)}")
    print(f"    DEFER:  {len(deferred)}")

    correct = sum(1 for r in results if r["correct"])
    print(f"\n  Accuracy: {correct}/{len(results)} ({correct/max(1,len(results)):.1%})")

    # Gate results
    signed_correctly = sum(1 for r in signed if r["verdict"] == "safe")
    signed_fraud = sum(1 for r in signed if r["verdict"] in ("risky", "fraudulent"))
    print(f"\n  Gate results:")
    print(f"    Correctly signed (safe): {signed_correctly}")
    print(f"    False positives (signed risky/fraud): {signed_fraud}")
    print(f"    FPR: {signed_fraud/max(1,len(signed)):.1%}")

    # Foxit operations
    foxit_uploads = sum(1 for r in results if r.get("foxit_upload"))
    foxit_merges = sum(1 for r in results if r.get("foxit_merge"))
    print(f"\n  Foxit operations:")
    print(f"    Uploads: {foxit_uploads}")
    print(f"    Merges: {foxit_merges}")

    # Save results
    report = {
        "n_docs": n_docs,
        "elapsed_s": elapsed,
        "results": results,
        "summary": {
            "signed": len(signed),
            "refused": len(refused),
            "deferred": len(deferred),
            "accuracy": correct / max(1, len(results)),
            "fpr": signed_fraud / max(1, len(signed)),
            "foxit_uploads": foxit_uploads,
            "foxit_merges": foxit_merges,
        }
    }

    report_path = f"{OUTPUT_DIR}/batch_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")

    return report


if __name__ == "__main__":
    asyncio.run(run_batch_test())
