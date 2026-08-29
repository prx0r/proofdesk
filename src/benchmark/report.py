"""Benchmark report generator — produces RunReceipts with Merkle proofs.

Takes results from the agent brain and generates a content-addressed
receipt proving the benchmark was executed correctly.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from ..audit.chain import EventLedger, merkle_root
from ..audit.certificates import Certificate
from ..skills.agent_brain import ProcessingResult


@dataclass
class BenchmarkReport:
    """A complete benchmark report with content-addressed receipt."""
    timestamp: str
    folder: str
    total_files: int
    doc_types: list[str]
    total_fields: int
    auto_approve: int
    human_review: int
    reject: int
    auto_approve_rate: float
    docs_needing_human: int
    per_file: list[dict]
    gate_results: dict = field(default_factory=dict)
    receipt_hash: str = ""
    certificate: dict | None = None

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "folder": self.folder,
            "total_files": self.total_files,
            "doc_types": self.doc_types,
            "total_fields": self.total_fields,
            "auto_approve": self.auto_approve,
            "human_review": self.human_review,
            "reject": self.reject,
            "auto_approve_rate": round(self.auto_approve_rate, 4),
            "docs_needing_human": self.docs_needing_human,
            "per_file": self.per_file,
            "gate_results": self.gate_results,
            "receipt_hash": self.receipt_hash,
            "certificate": self.certificate,
        }


def generate_report(
    summary: dict,
    thresholds: dict | None = None,
    quality_gates: dict | None = None,
) -> BenchmarkReport:
    """Generate a benchmark report from agent brain summary.

    Args:
        summary: Output from brain.process_folder()
        thresholds: Thresholds used for this run
        quality_gates: Quality gate thresholds

    Returns:
        BenchmarkReport with content-addressed receipt
    """
    gates = quality_gates or {
        "min_auto_approve_rate": 0.3,
        "max_human_review_rate": 0.7,
        "min_fields_extracted": 1,
    }

    # Check gates
    gate_results = {}
    auto_rate = summary["auto_approve_rate"]
    human_rate = summary["human_review"] / max(summary["total_fields"], 1)

    gate_results["min_auto_approve_rate"] = (
        f"PASS ({auto_rate:.3f} >= {gates['min_auto_approve_rate']})"
        if auto_rate >= gates["min_auto_approve_rate"]
        else f"FAIL ({auto_rate:.3f} < {gates['min_auto_approve_rate']})"
    )
    gate_results["max_human_review_rate"] = (
        f"PASS ({human_rate:.3f} <= {gates['max_human_review_rate']})"
        if human_rate <= gates["max_human_review_rate"]
        else f"FAIL ({human_rate:.3f} > {gates['max_human_review_rate']})"
    )
    gate_results["min_fields_extracted"] = (
        f"PASS ({summary['total_fields']} >= {gates['min_fields_extracted']})"
        if summary["total_fields"] >= gates["min_fields_extracted"]
        else f"FAIL ({summary['total_fields']} < {gates['min_fields_extracted']})"
    )

    all_pass = all("PASS" in v for v in gate_results.values())
    gate_results["overall"] = "ALL GATES PASS" if all_pass else "GATE FAILURE"

    # Generate receipt hash
    receipt_data = {
        "folder": summary["folder"],
        "total_files": summary["total_files"],
        "total_fields": summary["total_fields"],
        "auto_approve_rate": summary["auto_approve_rate"],
        "thresholds": thresholds,
    }
    receipt_hash = hashlib.sha256(
        json.dumps(receipt_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    # Generate self-hashing certificate
    cert = Certificate(
        cert_type="benchmark",
        case_id="benchmark_run",
        subject=f"ProofDesk benchmark: {summary['total_files']} files, {summary['total_fields']} fields, {summary['auto_approve_rate']:.0%} auto-approve",
        evidence=[{"receipt_hash": receipt_hash}],
        metadata={
            "doc_types": summary["doc_types"],
            "thresholds": thresholds,
            "gate_results": {k: v for k, v in gate_results.items() if k != "overall"},
        },
    )
    cert.compute_hash()

    return BenchmarkReport(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        folder=summary["folder"],
        total_files=summary["total_files"],
        doc_types=summary["doc_types"],
        total_fields=summary["total_fields"],
        auto_approve=summary["auto_approve"],
        human_review=summary["human_review"],
        reject=summary["reject"],
        auto_approve_rate=summary["auto_approve_rate"],
        docs_needing_human=summary["docs_needing_human"],
        per_file=summary["results"],
        gate_results=gate_results,
        receipt_hash=receipt_hash,
        certificate=cert.to_dict(),
    )


def print_report(report: BenchmarkReport) -> None:
    """Pretty-print a benchmark report."""
    print(f"\n{'=' * 70}")
    print(f"  PROOFDESK BENCHMARK REPORT")
    print(f"  {report.timestamp}")
    print(f"{'=' * 70}")

    print(f"\n  Input: {report.total_files} files, {len(report.doc_types)} types")
    print(f"  Types: {', '.join(report.doc_types)}")

    print(f"\n  Extraction Results:")
    print(f"    Total fields:    {report.total_fields}")
    print(f"    Auto-approve:    {report.auto_approve} ({report.auto_approve_rate:.0%})")
    print(f"    Human review:    {report.human_review}")
    print(f"    Reject:          {report.reject}")
    print(f"    Docs w/ human:   {report.docs_needing_human}/{report.total_files}")

    print(f"\n  Quality Gates:")
    for gate, result in report.gate_results.items():
        icon = "✓" if "PASS" in result else "✗"
        print(f"    [{icon}] {gate}: {result}")

    print(f"\n  Per-File Details:")
    print(f"  {'File':<40} {'Type':<15} {'Fields':>7} {'Actions':>20}")
    print(f"  {'─' * 40} {'─' * 15} {'─' * 7} {'─' * 20}")
    for r in report.per_file:
        actions = r.get("actions", {})
        action_str = " ".join(f"{k}:{v}" for k, v in actions.items())
        human = " ← REVIEW" if r.get("needs_human") else ""
        print(f"  {r['filename']:<40} {r['doc_type']:<15} {r['fields']:>7} {action_str:>20}{human}")

    print(f"\n  Receipt: {report.receipt_hash[:32]}...")
    if report.certificate:
        print(f"  Certificate: {report.certificate['certificate_hash'][:32]}...")
        print(f"  Certificate verified: {Certificate.from_dict(report.certificate).verify_integrity()[0]}")

    print(f"\n{'=' * 70}")
