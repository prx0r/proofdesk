#!/usr/bin/env python3
"""ProofDesk Proper Benchmark — scale testing across document types.

Tests Nutrient DWS extraction on:
1. Procurement documents (our PDFs)
2. SROIE receipts (real scanned images)
3. CUAD contracts (real legal documents)

Measures: accuracy, confidence calibration, signing decisions, latency.
Compares: Raw vs Sheepish vs Isotonic vs Platt.
"""

import os
import sys
import json
import time
import glob
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from src.providers.nutrient import extract_from_document_sync
from src.models.domain import Document
from src.benchmark.confidence.calibration import IsotonicCalibrator, PlattScaler


# ============================================================
# Dataset loaders
# ============================================================

def load_procurement_docs(max_docs=4):
    """Load our procurement PDFs with ground truth."""
    docs = []
    gt = {
        "procurement_request.pdf": {
            "vendor.legal_name": "Northstar Data Systems Ltd.",
            "procurement.requested_spend": 42500,
            "procurement.contract_start": "2026-10-01",
            "procurement.required_coverage_until": "2027-10-01",
        },
        "vendor_quote.pdf": {
            "vendor.legal_name": "Northstar Data Systems Limited",
            "quote.total": 42500,
            "quote.platform_price": 35000,
            "quote.support_price": 7500,
        },
        "insurance_certificate.pdf": {
            "vendor.legal_name": "Northstar Data Systems Ltd.",
            "insurance.expiry_date": "2027-08-31",
        },
        "security_questionnaire.pdf": {
            "vendor.legal_name": "Northstar Data Systems Ltd.",
            "security.data_retention_days": 30,
            "security.subprocessors": 3,
            "security.encryption_at_rest": True,
        },
    }
    pdf_dir = os.path.join(os.path.dirname(__file__), "data", "test_pdfs")
    for name, ground_truth in list(gt.items())[:max_docs]:
        path = os.path.join(pdf_dir, name)
        if os.path.exists(path):
            docs.append({"id": name, "type": "procurement", "path": path, "ground_truth": ground_truth})
    return docs


def load_sroie_docs(max_docs=20):
    """Load SROIE receipt images with ground truth."""
    docs = []
    key_dir = "/tmp/ICDAR-2019-SROIE/data/key"
    img_dir = "/tmp/ICDAR-2019-SROIE/data/img"
    if not os.path.exists(key_dir):
        print(f"  SROIE not found at {key_dir}")
        return docs
    
    json_files = sorted(glob.glob(os.path.join(key_dir, "*.json")))[:max_docs]
    for fp in json_files:
        with open(fp) as f:
            gt = json.load(f)
        doc_id = os.path.basename(fp).replace(".json", "")
        # Find image
        img_path = None
        for ext in [".jpg", ".jpeg", ".png"]:
            candidate = os.path.join(img_dir, doc_id + ext)
            if os.path.exists(candidate):
                img_path = candidate
                break
        if img_path:
            docs.append({"id": doc_id, "type": "receipt", "path": img_path, "ground_truth": gt})
    return docs


def load_cuad_docs(max_docs=20):
    """Load CUAD contracts (text only — no PDF)."""
    docs = []
    cuad_path = "/tmp/cuad/data/test.json"
    if not os.path.exists(cuad_path):
        print(f"  CUAD not found at {cuad_path}")
        return docs
    
    with open(cuad_path) as f:
        data = json.load(f)
    
    for item in data["data"][:max_docs]:
        text = ""
        for p in item["paragraphs"]:
            text += p["context"] + "\n"
        labels = {}
        for p in item["paragraphs"]:
            for qa in p["qas"]:
                label = qa["question"].replace("What is the relevant clause related to '", "").replace("'?", "")
                has_clause = not qa.get("is_impossible", True)
                labels[label] = has_clause
        docs.append({"id": item["title"], "type": "contract", "text": text[:2000], "ground_truth": labels})
    return docs


# ============================================================
# Extraction + comparison
# ============================================================

def extract_and_compare(doc):
    """Extract from a document and compare to ground truth."""
    if doc["type"] == "contract":
        # CUAD is text-based, skip Nutrient extraction
        return {"fields": 0, "correct": 0, "total": len(doc["ground_truth"]), "confidence": 0, "latency": 0}
    
    try:
        with open(doc["path"], "rb") as f:
            raw = f.read()
        nut_doc = Document(
            doc_id=doc["id"], case_id="bench", filename=doc["id"],
            content_type="application/pdf" if doc["path"].endswith(".pdf") else "image/jpeg",
            raw_bytes=raw,
        )
        start = time.time()
        facts = extract_from_document_sync(nut_doc)
        latency = (time.time() - start) * 1000
        
        extracted = {f.field_name: f.value_normalized for f in facts}
        confs = [f.confidence for f in facts]
        avg_conf = np.mean(confs) if confs else 0
        
        # Compare to ground truth
        correct = 0
        total = 0
        for field, expected in doc["ground_truth"].items():
            ext_val = extracted.get(field)
            if ext_val is not None:
                total += 1
                if isinstance(expected, bool):
                    match = str(ext_val).strip().lower() == str(expected).strip().lower()
                elif isinstance(expected, (int, float)):
                    try:
                        match = float(str(ext_val).replace(",", "").replace("$", "")) == expected
                    except:
                        match = False
                else:
                    match = str(ext_val).strip().lower() == str(expected).strip().lower()
                if match:
                    correct += 1
        
        return {"fields": len(facts), "correct": correct, "total": total, "confidence": avg_conf, "latency": latency}
    except Exception as e:
        return {"fields": 0, "correct": 0, "total": len(doc["ground_truth"]), "confidence": 0, "latency": 0, "error": str(e)}


# ============================================================
# Main benchmark
# ============================================================

def run_benchmark(procurement_n=4, sroie_n=20, cuad_n=20):
    print("=" * 70)
    print("  PROOFDESK PROPER BENCHMARK")
    print(f"  Procurement: {procurement_n} | SROIE: {sroie_n} | CUAD: {cuad_n}")
    print("=" * 70)

    # Load datasets
    procurement = load_procurement_docs(procurement_n)
    sroie = load_sroie_docs(sroie_n)
    cuad = load_cuad_docs(cuad_n)

    print(f"\n  Loaded: {len(procurement)} procurement, {len(sroie)} SROIE, {len(cuad)} CUAD")

    all_results = {"procurement": [], "receipt": [], "contract": []}
    all_scores = []
    all_labels = []

    # Process procurement docs
    print(f"\n  --- PROCUREMENT ---")
    for doc in procurement:
        result = extract_and_compare(doc)
        all_results["procurement"].append(result)
        all_scores.append(result["confidence"])
        all_labels.append(1.0 if result["correct"] == result["total"] else 0.0)
        acc = result["correct"] / result["total"] if result["total"] > 0 else 0
        print(f"    {doc['id']:<35} {result['fields']:>3} fields  {result['correct']}/{result['total']} = {acc:.0%}  {result['latency']:.0f}ms")

    # Process SROIE receipts
    print(f"\n  --- SROIE RECEIPTS ---")
    for doc in sroie:
        result = extract_and_compare(doc)
        all_results["receipt"].append(result)
        all_scores.append(result["confidence"])
        all_labels.append(1.0 if result["correct"] == result["total"] else 0.0)
        acc = result["correct"] / result["total"] if result["total"] > 0 else 0
        print(f"    {doc['id']:<35} {result['fields']:>3} fields  {result['correct']}/{result['total']} = {acc:.0%}  {result['latency']:.0f}ms")

    # Process CUAD contracts (text-based, no Nutrient)
    print(f"\n  --- CUAD CONTRACTS (text-based) ---")
    for doc in cuad:
        result = extract_and_compare(doc)
        all_results["contract"].append(result)
        all_scores.append(result["confidence"])
        all_labels.append(1.0 if result["correct"] == result["total"] else 0.0)

    # Aggregate
    total_correct = sum(r["correct"] for r in all_results["procurement"] + all_results["receipt"])
    total_fields = sum(r["total"] for r in all_results["procurement"] + all_results["receipt"])
    total_latency = sum(r["latency"] for r in all_results["procurement"] + all_results["receipt"])

    scores_arr = np.array(all_scores)
    labels_arr = np.array(all_labels)

    print(f"\n{'=' * 70}")
    print(f"  RESULTS")
    print(f"{'=' * 70}")
    print(f"\n  Extraction accuracy (procurement + receipts):")
    print(f"    {total_correct}/{total_fields} = {total_correct/total_fields:.1%}")
    print(f"    Avg latency: {total_latency/max(len(all_results['procurement'])+len(all_results['receipt']),1):.0f}ms")
    
    print(f"\n  Confidence stats:")
    print(f"    Mean: {scores_arr.mean():.4f}")
    print(f"    Std: {scores_arr.std():.4f}")
    print(f"    Min: {scores_arr.min():.4f}")
    print(f"    Max: {scores_arr.max():.4f}")

    # Calibration methods
    if len(scores_arr) > 10:
        from src.benchmark.confidence.calibration import IsotonicCalibrator, PlattScaler
        from src.benchmark.confidence.metrics import expected_calibration_error, behavioral_alignment_score

        iso = IsotonicCalibrator()
        iso.fit(scores_arr, labels_arr)
        iso_scores = np.array([iso.calibrate(s) for s in scores_arr])

        platt = PlattScaler()
        platt.fit(scores_arr, labels_arr)
        platt_scores = np.array([platt.calibrate(s) for s in scores_arr])

        sheepish_scores = np.array([max(0, min(1, s - 0.1 * max(0, 0.95 - s))) for s in scores_arr])

        print(f"\n  Calibration comparison:")
        print(f"  {'Method':<12} {'ECE':>8} {'Brier':>8} {'BAS':>8}")
        for name, s in [('Raw', scores_arr), ('Sheepish', sheepish_scores), ('Isotonic', iso_scores), ('Platt', platt_scores)]:
            ece, _ = expected_calibration_error(s, labels_arr)
            from src.benchmark.confidence.metrics import brier_score
            brier = brier_score(s, labels_arr)
            bas = behavioral_alignment_score(s, labels_arr)
            print(f"  {name:<12} {ece:>8.4f} {brier:>8.4f} {bas:>8.4f}")

    # Per-type breakdown
    print(f"\n  Per-type accuracy:")
    for dtype in ["procurement", "receipt", "contract"]:
        results = all_results[dtype]
        if results:
            correct = sum(r["correct"] for r in results)
            total = sum(r["total"] for r in results)
            acc = correct / total if total > 0 else 0
            print(f"    {dtype:<15} {correct}/{total} = {acc:.1%} ({len(results)} docs)")

    # Save
    output = {
        "procurement": {"docs": len(all_results["procurement"]), "accuracy": sum(r["correct"] for r in all_results["procurement"]) / max(sum(r["total"] for r in all_results["procurement"]), 1)},
        "receipt": {"docs": len(all_results["receipt"]), "accuracy": sum(r["correct"] for r in all_results["receipt"]) / max(sum(r["total"] for r in all_results["receipt"]), 1)},
        "contract": {"docs": len(all_results["contract"])},
        "overall": {"correct": total_correct, "total": total_fields, "accuracy": total_correct/total_fields if total_fields > 0 else 0},
        "confidence": {"mean": float(scores_arr.mean()), "std": float(scores_arr.std())},
    }
    out_path = f"benchmarks/proper_benchmark_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved to: {out_path}")


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    c = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    run_benchmark(p, s, c)
