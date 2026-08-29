"""Adapter: ProofDesk case -> foxit lab ConfidenceModule -> Doctavian risk band.

Bridges the signing-confidence lab (foxit/src/confidence_module.py) into the
main pipeline so document generation renders the calibration decision.
"""

from __future__ import annotations

import sys
from pathlib import Path

_LAB = Path(__file__).resolve().parents[2] / "foxit"
if _LAB.exists():
    sys.path.insert(0, str(_LAB))

try:
    from foxit.src.confidence_module import ConfidenceModule  # type: ignore
    _HAS_LAB = True
except Exception:
    _HAS_LAB = False


def _signals_from_case(case) -> dict:
    """Derive lab-input signals from ProofDesk facts/checks (no ground truth)."""
    confidences = [f.confidence for f in case.facts if f.confidence]
    hunter = sum(confidences) / len(confidences) if confidences else 0.5

    # mapper: cross-document agreement — fraction of passing checks
    if case.assertions:
        mapper = sum(1 for a in case.assertions if a.result.value == "PASS") / len(case.assertions)
    else:
        mapper = 0.5

    # grounding: share of facts carrying page provenance
    grounded = sum(1 for f in case.facts if f.source_page) or 1
    grounding = min(1.0, len(case.facts) / max(grounded, 1))

    return {
        "hunter_score": hunter,
        "mapper_score": mapper,
        "field_accuracy": hunter,          # held-out estimate proxy: raw extraction quality
        "match_score": mapper,
        "grounding_score": grounding,
        "doc_type": "procurement",
    }


def score_case(case) -> dict:
    """Return {confidence, band, field_risks} for build_generation_payload."""
    sig = _signals_from_case(case)

    score = 0.5 * sig["hunter_score"] + 0.5 * sig["mapper_score"]
    if _HAS_LAB:
        try:
            module = ConfidenceModule()
            score = float(module.score(**sig))
        except Exception:
            pass  # deterministic fallback below already computed

    # Hard failures cap the band regardless of numeric score:
    #   FAIL + no resolution -> ESCALATED
    #   FAIL + human resolution -> at most CONDITIONAL
    has_fail = any(a.result.value == "FAIL" for a in case.assertions)
    has_resolution = len(case.resolutions) > 0

    band = "CLEARED" if score >= 0.80 else "CONDITIONAL" if score >= 0.55 else "ESCALATED"
    if has_fail and not has_resolution:
        band = "ESCALATED"
    elif has_fail:
        band = min(band, "CONDITIONAL", key=lambda b: ["CLEARED", "CONDITIONAL", "ESCALATED"].index(b))
        if band == "CLEARED":
            band = "CONDITIONAL"

    # Per-field risks: low-confidence material fields exceed their budgets
    budgets = {"signer": 0.01, "amount": 0.02, "date": 0.03}
    field_risks = []
    for f in case.facts:
        budget = next((v for k, v in budgets.items() if k in f.field_name.lower()), None)
        threshold = 0.90 if budget is not None else 0.75
        if f.confidence < threshold:
            field_risks.append({
                "field": f.field_name,
                "detail": f"confidence {f.confidence:.2f} below {'material' if budget is None else 'budgeted'} floor {threshold}",
            })

    return {"confidence": round(score, 3), "band": band, "field_risks": field_risks[:10]}
