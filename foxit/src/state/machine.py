"""State machine + SignatureGate for ProofDesk."""

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
    """SignatureGate — returns allowed=True or denial reasons."""
    reasons = []

    if case.state != CaseState.PREPARED:
        reasons.append({
            "code": "INVALID_STATE",
            "detail": f"Case state is {case.state.value}, expected PREPARED",
        })

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

    if case.human_approval is None:
        reasons.append({
            "code": "NO_HUMAN_APPROVAL",
            "detail": "No human approval recorded",
        })

    if case.structured_record is None:
        reasons.append({
            "code": "NO_STRUCTURED_RECORD",
            "detail": "No approved structured record",
        })

    if case.generated_artifact is None:
        reasons.append({
            "code": "NO_ARTIFACT",
            "detail": "No generated artifact",
        })
    elif case.structured_record and case.generated_artifact:
        if case.generated_artifact.record_hash != case.structured_record.content_hash:
            reasons.append({
                "code": "ARTIFACT_HASH_MISMATCH",
                "detail": "Generated artifact hash does not match approved record",
            })

    return {"allowed": len(reasons) == 0, "reasons": reasons}
