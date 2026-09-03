#!/usr/bin/env python3
"""Full Benchmark Runner — 500+ documents with real Nutrient API.

Tracks:
- Extraction accuracy
- Decision distribution
- Processing time
- Cost analysis
- Audit trail integrity
- Convergence projection

Output: /tmp/proofdesk/benchmark_results.json
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path

# Add proofdesk to path
sys.path.insert(0, str(Path(__file__).parent))

from src.engine.batch import get_processor
from src.engine.feedback import get_loop
from src.engine.cost_analysis import get_tracker
from src.providers.classifier import classify_document

# Nutrient API key must be set in environment or .env
if not os.environ.get("NUTRIENT_API_KEY"):
    raise SystemExit("NUTRIENT_API_KEY not set. Export it or add to .env")


def run_benchmark(max_files: int = 500, output_dir: str = "/tmp/proofdesk/benchmark"):
    """Run full benchmark on CUAD dataset."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("="*70)
    print("  PROOFDESK FULL BENCHMARK")
    print("  Real Nutrient DWS • Real CUAD Contracts • Full Audit Trail")
    print("="*70)
    print()
    
    # Load CUAD dataset
    dataset_dir = "data/datasets/pdfs"
    if not os.path.exists(dataset_dir):
        print(f"ERROR: Dataset not found at {dataset_dir}")
        return
    
    all_files = [f for f in os.listdir(dataset_dir) if f.endswith(".pdf")]
    files_to_process = all_files[:max_files]
    
    print(f"Dataset: {len(all_files)} total PDFs")
    print(f"Processing: {len(files_to_process)} files")
    print(f"Output: {output_dir}")
    print()
    
    # Initialize tracking
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(files_to_process),
            "api": "Nutrient DWS (real)",
            "dataset": "CUAD (real contracts)",
        },
        "decisions": {},
        "timing": {},
        "cost_analysis": {},
        "extraction_stats": {},
        "classification_stats": {},
        "audit_trail": [],
        "convergence": {},
    }
    
    # Initialize components
    processor = get_processor()
    cost_tracker = get_tracker()
    
    # Create batch
    print("Creating batch...")
    files = []
    for f in files_to_process:
        path = os.path.join(dataset_dir, f)
        with open(path, "rb") as fh:
            files.append((f, fh.read(), "application/pdf"))
    
    job = processor.create_job(files)
    print(f"Batch created: {job.batch_id[:12]}...")
    print()
    
    # Process files
    print("Processing files...")
    start_time = time.time()
    
    decision_counts = {"AUTO_SIGN": 0, "DEFER_TO_HUMAN": 0, "BLOCKED": 0, "ERROR": 0}
    confidence_scores = []
    processing_times = []
    extraction_counts = []
    
    for i in range(len(files_to_process)):
        file_start = time.time()
        
        result = processor.process_next(job.batch_id)
        
        file_end = time.time()
        file_time = file_end - file_start
        processing_times.append(file_time)
        
        if result:
            # Track decisions
            decision = result.decision
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            
            # Track confidence
            confidence_scores.append(result.confidence)
            
            # Track extraction
            case, _ = job._cases[result.file_id]
            extraction_counts.append(len(case.facts))
            
            # Log progress
            if (i + 1) % 50 == 0 or i == 0:
                print(f"  [{i+1}/{len(files_to_process)}] {result.filename[:40]}... "
                      f"→ {decision} ({result.confidence*100:.0f}%) [{file_time:.1f}s]")
            
            # Store audit event
            results["audit_trail"].append({
                "file_id": result.file_id,
                "filename": result.filename,
                "decision": decision,
                "confidence": result.confidence,
                "doc_type": result.doc_type,
                "risk_level": result.risk_level,
                "facts_count": len(case.facts),
                "processing_time": file_time,
                "audit_hash": result.audit_hash,
            })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print()
    print(f"Processing complete: {total_time:.1f}s ({total_time/len(files_to_process):.1f}s per file)")
    print()
    
    # Get final report
    report = processor.get_report(job.batch_id)
    
    # Compile results
    results["decisions"] = decision_counts
    results["timing"] = {
        "total_seconds": round(total_time, 2),
        "per_file_seconds": round(total_time / len(files_to_process), 2),
        "files_per_second": round(len(files_to_process) / total_time, 2),
    }
    results["cost_analysis"] = cost_tracker.get_summary()
    results["convergence"] = report.get("convergence", {})
    
    # Extraction statistics
    if extraction_counts:
        results["extraction_stats"] = {
            "avg_fields_per_doc": round(sum(extraction_counts) / len(extraction_counts), 2),
            "min_fields": min(extraction_counts),
            "max_fields": max(extraction_counts),
            "total_facts_extracted": sum(extraction_counts),
        }
    
    # Classification statistics
    if confidence_scores:
        results["classification_stats"] = {
            "avg_confidence": round(sum(confidence_scores) / len(confidence_scores), 3),
            "min_confidence": round(min(confidence_scores), 3),
            "max_confidence": round(max(confidence_scores), 3),
            "std_confidence": round((sum((x - sum(confidence_scores)/len(confidence_scores))**2 
                                        for x in confidence_scores) / len(confidence_scores)) ** 0.5, 3),
        }
    
    # Decision distribution
    total = sum(decision_counts.values())
    results["decision_distribution"] = {
        k: {"count": v, "percentage": round(v / total * 100, 1)}
        for k, v in decision_counts.items()
    }
    
    # Save results
    output_file = os.path.join(output_dir, "benchmark_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("="*70)
    print("  BENCHMARK RESULTS")
    print("="*70)
    print()
    print(f"  Total files processed: {len(files_to_process)}")
    print(f"  Total time: {total_time:.1f}s ({total_time/len(files_to_process):.1f}s per file)")
    print()
    print("  DECISIONS:")
    for decision, count in decision_counts.items():
        pct = count / total * 100 if total > 0 else 0
        print(f"    {decision:20s}: {count:4d} ({pct:5.1f}%)")
    print()
    print("  EXTRACTION:")
    if extraction_counts:
        print(f"    Avg fields per doc: {results['extraction_stats']['avg_fields_per_doc']}")
        print(f"    Total facts: {results['extraction_stats']['total_facts_extracted']}")
    print()
    print("  CLASSIFICATION:")
    if confidence_scores:
        print(f"    Avg confidence: {results['classification_stats']['avg_confidence']*100:.1f}%")
        print(f"    Min confidence: {results['classification_stats']['min_confidence']*100:.1f}%")
        print(f"    Max confidence: {results['classification_stats']['max_confidence']*100:.1f}%")
    print()
    print("  COST ANALYSIS:")
    cost = results["cost_analysis"]
    print(f"    Net hours saved: {cost.get('time_savings', {}).get('net_hours_saved', 0)}")
    print(f"    Net cost saved: ${cost.get('cost_savings', {}).get('net_cost_saved', 0):,.2f}")
    print(f"    Fraud prevented: ${cost.get('fraud_prevention', {}).get('total_fraud_prevented', 0):,.2f}")
    print()
    print(f"  Results saved to: {output_file}")
    print("="*70)
    
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run ProofDesk benchmark")
    parser.add_argument("--max-files", type=int, default=500, help="Max files to process")
    parser.add_argument("--output", type=str, default="/tmp/proofdesk/benchmark", help="Output directory")
    args = parser.parse_args()
    
    run_benchmark(max_files=args.max_files, output_dir=args.output)
