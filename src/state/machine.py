"""State machine + Authority Gate for ProofDesk."""

from __future__ import annotations

from ..models.domain import (
    Case,
    CaseState,
    AuditEvent,
    FORBIDDEN_TRANSITIONS,
    _hash,
)


# Valid transitions: from_state -> set of allowed to_states
TRANSITIONS: dict[CaseState, set[CaseState]] = {
    CaseState.RECEIVED: {CaseState.INGESTED},
    CaseState.INGESTED: {CaseState.EXTRACTED},
    CaseState.EXTRACTED: {CaseState.RECONCILED},
    CaseState.RECONCILED: {CaseState.CHECKED},
    CaseState.CHECKED: {CaseState.REVIEW_REQUIRED, CaseState.APPROVABLE},
    CaseState.REVIEW_REQUIRED: {CaseState.RESOLVED},
    CaseState.RESOLVED: {CaseState.APPROVABLE},
    CaseState.APPROVABLE: {CaseState.APPROVED},
    CaseState.APPROVED: {CaseState.GENERATED},
    CaseState.GENERATED: {CaseState.PREPARED},
    CaseState.PREPARED: {CaseState.SIGNATURE_AUTHORIZED, CaseState.CHECKED},
    CaseState.SIGNATURE_AUTHORIZED: {CaseState.SIGNATURE_REQUESTED},
    CaseState.SIGNATURE_REQUESTED: {CaseState.SIGNED},
    CaseState.SIGNED: {CaseState.ARCHIVED},
}

# Optional global ledger — set by app.py at startup
_global_ledger = None


def set_ledger(ledger) -> None:
    """Register the global event ledger for automatic recording."""
    global _global_ledger
    _global_ledger = ledger


def transition(case: Case, to_state: CaseState, actor: str = "system",
               detail: dict | None = None) -> Case:
    """Execute a state transition with guard checks.

    Records the event in both:
    1. case.audit_events (per-case, hash-chained)
    2. global ledger (cross-case, Merkle-sealable)
    """
    from_state = case.state

    if (from_state, to_state) in FORBIDDEN_TRANSITIONS:
        raise ValueError(
            f"Forbidden transition: {from_state.value} -> {to_state.value}"
        )

    allowed = TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise ValueError(
            f"Invalid transition: {from_state.value} -> {to_state.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )

    case.state = to_state
    case.updated_at = __import__("time").time()

    event = AuditEvent(
        case_id=case.case_id,
        event_type="STATE_TRANSITION",
        actor=actor,
        from_state=from_state.value,
        to_state=to_state.value,
        detail=detail or {},
    )
    event.compute_hash(
        case.audit_events[-1].content_hash if case.audit_events else ""
    )
    case.audit_events.append(event)

    # Record in global ledger (if registered)
    if _global_ledger is not None:
        _global_ledger.append(
            case_id=case.case_id,
            event_type="STATE_TRANSITION",
            actor=actor,
            payload={
                "from": from_state.value,
                "to": to_state.value,
                "detail": detail or {},
            },
        )

    return case


def can_request_signature(case: Case) -> dict:
    """Authority Gate — returns allowed=True, denial reasons, and passing checks."""
    reasons = []
    checks = []

    if case.state != CaseState.PREPARED:
        reasons.append({
            "code": "INVALID_STATE",
            "detail": f"Case state is {case.state.value}, expected PREPARED",
        })
    else:
        checks.append("state_is_PREPARED")

    if case.unresolved_blockers > 0:
        failing = [a for a in case.assertions if a.result.value == "FAIL"
                   and a.severity.value == "BLOCKER"
                   and not any(
                       r.assertion_id == a.assertion_id
                       for r in case.resolutions
                       if r.decision.value in ("ACCEPT", "CONDITIONAL_ACCEPT")
                   )]
        for a in failing:
            reasons.append({
                "code": "UNRESOLVED_BLOCKER",
                "assertion_id": a.assertion_id,
                "detail": a.detail,
            })
    else:
        checks.append("no_unresolved_blockers")

    if case.human_approval is None:
        reasons.append({
            "code": "NO_HUMAN_APPROVAL",
            "detail": "No human approval recorded",
        })
    else:
        checks.append("human_approval_present")

    if case.structured_record is None:
        reasons.append({
            "code": "NO_STRUCTURED_RECORD",
            "detail": "No approved structured record",
        })
    else:
        checks.append("structured_record_exists")

    if case.generated_artifact is None:
        reasons.append({
            "code": "NO_ARTIFACT",
            "detail": "No generated artifact",
        })
    else:
        checks.append("generated_artifact_exists")
        if case.structured_record and case.generated_artifact:
            if case.generated_artifact.record_hash != case.structured_record.content_hash:
                reasons.append({
                    "code": "ARTIFACT_HASH_MISMATCH",
                    "detail": "Generated artifact hash does not match approved record",
                })
            else:
                checks.append("artifact_record_hash_matches")

    # Calibrated confidence check — the key innovation
    cert = getattr(case, '_decision_certificate', None)
    conf = getattr(case, '_confidence', None) or {}
    score = conf.get("score") or conf.get("confidence")
    threshold = conf.get("threshold")
    violations = cert.get("violations", []) if cert else conf.get("field_risks", [])

    # Fail closed: no certificate = no signing
    if cert is None and score is None:
        reasons.append({
            "code": "NO_DECISION_CERTIFICATE",
            "detail": "No decision certificate available — cannot evaluate risk",
        })
    elif score is not None and threshold is not None:
        if score >= threshold:
            checks.append(f"calibrated_score_{score:.3f}_gte_threshold_{threshold:.3f}")
        else:
            reasons.append({
                "code": "BELOW_CALIBRATED_THRESHOLD",
                "detail": f"Calibrated confidence {score:.3f} < threshold {threshold:.3f}",
            })

    # Per-field risk violations block directly
    if violations:
        violated_fields = [v.get("field", "?") for v in violations[:5]]
        reasons.append({
            "code": "FIELD_RISK_BUDGET_EXCEEDED",
            "detail": f"Fields outside risk budget: {', '.join(violated_fields)}",
        })
    else:
        checks.append("all_fields_within_risk_budget")

    # Prepared artifact hash check — recompute and compare
    prepared_hash = getattr(case, '_prepared_artifact_hash', None)
    prepared_path = getattr(case, '_prepared_artifact_path', None)
    if prepared_hash and prepared_path:
        import hashlib
        try:
            with open(prepared_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()
            if current_hash == prepared_hash:
                checks.append(f"final_artifact_sha256_verified_{current_hash[:12]}")
            else:
                reasons.append({
                    "code": "ARTIFACT_HASH_MISMATCH",
                    "detail": f"Expected {prepared_hash[:16]}..., got {current_hash[:16]}...",
                })
        except Exception:
            reasons.append({
                "code": "ARTIFACT_UNREADABLE",
                "detail": "Cannot read prepared artifact for hash verification",
            })
    elif prepared_hash:
        checks.append(f"final_artifact_sha256_{prepared_hash[:12]}")

    return {"allowed": len(reasons) == 0, "reasons": reasons, "checks": checks}
