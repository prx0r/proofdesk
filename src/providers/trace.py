"""Vendor API call trace — every outbound provider call recorded for live display."""
from __future__ import annotations

import threading
import time
from typing import Any

_trace_lock = threading.Lock()
_traces: dict[str, list[dict]] = {}  # case_id -> [call records]
_current: list[str] = [""]            # context case id for provider calls


def set_current(case_id: str) -> None:
    _current[0] = case_id


def resolve(case_id: str) -> str:
    return _current[0] if case_id == "current" else case_id


def record(case_id: str, provider: str, operation: str,
           method: str, url: str,
           request_summary: Any = None,
           status: int | None = None,
           response_summary: Any = None,
           duration_ms: float = 0.0) -> None:
    cid = resolve(case_id)
    with _trace_lock:
        _traces.setdefault(cid, []).append({
            "ts": time.time(),
            "provider": provider,
            "operation": operation,
            "method": method,
            "url": url,
            "request": request_summary,
            "status": status,
            "response": response_summary,
            "duration_ms": round(duration_ms),
        })


def get(case_id: str) -> list[dict]:
    with _trace_lock:
        return list(_traces.get(case_id, []))


def drop(case_id: str) -> None:
    with _trace_lock:
        _traces.pop(case_id, None)
