"""Content-addressed hashing — adapted from cogymkernel.

Provides tamper-evident content IDs with volatile field exclusion.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import secrets
import statistics
from typing import Any


# Fields that change between runs but shouldn't affect content identity
VOLATILE = frozenset({
    "started_ns", "finished_ns", "wall_ms", "wall_latency_ms",
    "timestamp", "created_at", "run_at", "processed_at",
    "request_id", "request_hash", "response_hash",
    "cache_hit", "provider",
})


def content_id(prefix: str, data: Any) -> str:
    """Content-addressed ID: prefix + blake3/sha256 of canonical JSON."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"),
                           default=str)
    h = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return f"{prefix}:{h}"


def strip_volatile(d: dict) -> dict:
    """Remove volatile fields before hashing."""
    return {k: v for k, v in d.items() if k not in VOLATILE}


def events_root(hashes: list[str]) -> str:
    """Merkle root of event hashes."""
    if not hashes:
        return content_id("merkle", "empty")
    level = list(hashes)
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            pair = level[i] if i + 1 >= len(level) else level[i] + level[i + 1]
            next_level.append(content_id("merkle", pair))
        level = next_level
    return level[0]


def now_ns() -> int:
    import time
    return time.time_ns()
