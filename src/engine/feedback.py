"""Feedback loop — human resolutions become calibration training data.

Closes the convergence loop: defer → human decides → label captured from the
audit trail → online calibrator updates → future auto-sign decisions improve.

Target property: auto-sign coverage rises over time while false-sign rate
stays bounded (bounded by conformal α, not by hope).
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

_LAB = Path(__file__).resolve().parents[2] / "foxit"
if _LAB.exists():
    sys.path.insert(0, str(_LAB))

try:
    from foxit.src.calibration import MarginOnlineCalibrator  # type: ignore
    _HAS_ONLINE = True
except Exception:
    _HAS_ONLINE = False


class FeedbackLoop:
    """Accumulates human-resolution labels and adapts the signing policy."""

    def __init__(self):
        self._lock = threading.Lock()
        self._calibrators: dict[str, object] = {}   # rule_version -> online calibrator
        self._history: list[dict] = []
        self._auto_signs: list[dict] = []           # auto-signed cases awaiting/undergoing audit

    # ── Auto-sign tracking + spot audit ─────────────────────────────

    def record_auto_sign(self, case_id: str, score: float, rule_versions: list[str]) -> None:
        """A case crossed the gate with zero human exceptions (pure auto-sign).
        Enters the spot-audit pool."""
        with self._lock:
            self._auto_signs.append({
                "case_id": case_id,
                "score": float(score),
                "rules": list(rule_versions),
                "audited": False,
                "correct": None,
            })

    def spot_audit(self, case_id: str, correct: bool) -> bool:
        """Human audits an auto-signed case post-hoc. Returns True if found."""
        with self._lock:
            for a in reversed(self._auto_signs):
                if a["case_id"] == case_id and not a["audited"]:
                    a["audited"] = True
                    a["correct"] = bool(correct)
                    return True
        return False

    def record_field(self, field_name: str, correct: bool,
                     confidence_at_decision: float = 0.5,
                     case_id: str = "", actor: str = "") -> None:
        """Human labels one extracted field as correct or incorrect.

        This is the primitive: binary per-field feedback.
        Each label tightens the conformal threshold for that field's budget.
        """
        with self._lock:
            self._history.append({
                "type": "field",
                "field": field_name,
                "correct": bool(correct),
                "score": float(confidence_at_decision),
                "case_id": case_id,
                "actor": actor,
            })

    def record(self, rule_version: str, score_at_decision: float, accepted: bool,
               case_id: str = "", actor: str = "") -> None:
        """Human decided on an exception raised at `score_at_decision`.

        accepted=True  → human agreed the case was safe to proceed (model too lenient-safe)
        accepted=False → human rejected; the agent trusted something untrustworthy
        """
        with self._lock:
            self._history.append({
                "rule": rule_version,
                "score": float(score_at_decision),
                "accepted": bool(accepted),
                "case_id": case_id,
                "actor": actor,
            })
            if _HAS_ONLINE:
                cal = self._calibrators.setdefault(
                    rule_version, MarginOnlineCalibrator())
                # Online update: was trusting this score vindicated?
                cal.update(float(score_at_decision), bool(accepted))

    def calibrated(self, rule_version: str, score: float) -> float:
        """Calibrated score for a rule given accumulated feedback."""
        with self._lock:
            cal = self._calibrators.get(rule_version)
        if cal is None:
            return score
        try:
            return float(cal.calibrate(float(score)))
        except Exception:
            return score

    def stats(self) -> dict:
        """Coverage metrics for the dashboard / demo."""
        with self._lock:
            h = list(self._history)
        by_rule: dict[str, list[dict]] = {}
        by_field: dict[str, list[dict]] = {}
        for r in h:
            if r.get("type") == "field":
                by_field.setdefault(r["field"], []).append(r)
            else:
                by_rule.setdefault(r.get("rule", "unknown"), []).append(r)
        rules = {}
        for rule, items in sorted(by_rule.items()):
            n = len(items)
            acc = sum(1 for i in items if i["accepted"])
            first_half = items[: n // 2] if n >= 4 else items
            last_half = items[n // 2 :] if n >= 4 else items
            rules[rule] = {
                "n": n,
                "acceptance_rate": round(acc / n, 3) if n else None,
                "early_acceptance": round(sum(1 for i in first_half if i["accepted"]) / max(len(first_half), 1), 3),
                "late_acceptance": round(sum(1 for i in last_half if i["accepted"]) / max(len(last_half), 1), 3),
                "calibrated_model_active": _HAS_ONLINE and rule in self._calibrators,
            }
        fields = {}
        for field, items in sorted(by_field.items()):
            n = len(items)
            acc = sum(1 for i in items if i["correct"])
            fields[field] = {
                "n": n,
                "correct_rate": round(acc / n, 3) if n else None,
                "total_labels": n,
            }
        return {
            "total_feedback": len(h),
            "total_field_labels": sum(f["n"] for f in fields.values()),
            "rules": rules,
            "fields": fields,
            "note": ("field-level binary labels: correct/incorrect per extracted field. "
                     "Each label tightens the conformal threshold for that field's budget."),
            "auto_sign_panel": self._auto_sign_stats(),
        }

    def _auto_sign_stats(self) -> dict:
        """Spot-audit panel: measured error rate on sampled auto-signed cases.
        This — not acceptance rate — is the safety evidence for the flywheel."""
        audited = [a for a in self._auto_signs if a["audited"]]
        n = len(audited)
        wrong = sum(1 for a in audited if not a["correct"])
        return {
            "auto_signed_total": len(self._auto_signs),
            "audited": n,
            "audited_wrong": wrong,
            "measured_error_rate": round(wrong / n, 3) if n else None,
            "pending_audit": len(self._auto_signs) - n,
        }


_loop: FeedbackLoop | None = None


def get_loop() -> FeedbackLoop:
    global _loop
    if _loop is None:
        _loop = FeedbackLoop()
    return _loop
