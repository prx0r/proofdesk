"""Hash-chained event ledger with Merkle epoch sealing.

Sourced from QDW: src/qdw/core/ledger/events.py

Every event is hash-chained to its predecessor. Periodically, ranges
of events are sealed into Merkle epochs for compact inclusion proofs.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from .merkle import merkle_root, inclusion_path


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_object(obj: Any) -> str:
    return _sha256_hex(_canonical_json(obj))


GENESIS_HASH = "0" * 64


@dataclass
class LedgerEvent:
    """Single event in the hash chain."""
    seq: int
    case_id: str
    event_type: str
    actor: str
    payload: dict
    timestamp: float = field(default_factory=time.time)
    payload_hash: str = ""
    prev_event_hash: str = GENESIS_HASH
    event_hash: str = ""

    def compute_hashes(self) -> None:
        self.payload_hash = _hash_object(self.payload)
        body = {
            "seq": self.seq,
            "case_id": self.case_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload_hash": self.payload_hash,
            "prev_event_hash": self.prev_event_hash,
        }
        self.event_hash = _hash_object(body)

    def to_dict(self) -> dict:
        return {
            "seq": self.seq,
            "case_id": self.case_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "payload_hash": self.payload_hash,
            "prev_event_hash": self.prev_event_hash,
            "event_hash": self.event_hash,
        }


@dataclass
class MerkleEpoch:
    """Sealed Merkle root over a range of events."""
    epoch_id: int
    start_seq: int
    end_seq: int
    root: str
    event_count: int
    sealed_at: float = field(default_factory=time.time)


class EventLedger:
    """Append-only hash-chained event ledger with Merkle sealing.

    Usage:
        ledger = EventLedger()
        ledger.append("case_1", "EXTRACTION", "system", {"doc_id": "doc_1", "fields": 12})
        ledger.append("case_1", "REVIEW", "human", {"decision": "CONDITIONAL_ACCEPT"})
        ok, reason = ledger.verify_chain()
        proof = ledger.proof_for_seq(1)
    """

    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []
        self._epochs: list[MerkleEpoch] = []
        self._by_case: dict[str, list[int]] = {}

    def append(
        self,
        case_id: str,
        event_type: str,
        actor: str,
        payload: dict,
    ) -> LedgerEvent:
        """Append a new event to the ledger."""
        seq = len(self._events)
        prev_hash = self._events[-1].event_hash if self._events else GENESIS_HASH

        event = LedgerEvent(
            seq=seq,
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            payload=payload,
            prev_event_hash=prev_hash,
        )
        event.compute_hashes()

        self._events.append(event)
        self._by_case.setdefault(case_id, []).append(seq)

        return event

    def get_events(self, case_id: str | None = None) -> list[LedgerEvent]:
        """Get events, optionally filtered by case."""
        if case_id:
            return [self._events[i] for i in self._by_case.get(case_id, [])]
        return list(self._events)

    def verify_chain(self) -> tuple[bool, str]:
        """Verify the entire hash chain integrity.

        Returns (ok, reason). ok=True means no tampering detected.
        """
        for i, event in enumerate(self._events):
            # Recompute event hash
            body = {
                "seq": event.seq,
                "case_id": event.case_id,
                "event_type": event.event_type,
                "actor": event.actor,
                "payload_hash": event.payload_hash,
                "prev_event_hash": event.prev_event_hash,
            }
            recomputed = _hash_object(body)
            if recomputed != event.event_hash:
                return False, f"Event {i} hash mismatch: expected {recomputed[:16]}, got {event.event_hash[:16]}"

            # Verify chain link
            if i > 0:
                expected_prev = self._events[i - 1].event_hash
                if event.prev_event_hash != expected_prev:
                    return False, f"Event {i} chain break: prev_hash doesn't match event {i-1}"

        return True, f"Chain OK: {len(self._events)} events verified"

    def seal_epoch(self, start_seq: int = 0) -> MerkleEpoch:
        """Seal a range of events into a Merkle epoch.

        The epoch root commits to all events in the range.
        """
        end_seq = len(self._events)
        if end_seq == 0:
            raise ValueError("Cannot seal empty ledger")

        epoch_id = len(self._epochs)
        leaf_data = [
            _canonical_json(e.to_dict()) for e in self._events[start_seq:end_seq]
        ]
        root = merkle_root(leaf_data)

        epoch = MerkleEpoch(
            epoch_id=epoch_id,
            start_seq=start_seq,
            end_seq=end_seq,
            root=root,
            event_count=end_seq - start_seq,
        )
        self._epochs.append(epoch)
        return epoch

    def proof_for_seq(self, seq: int) -> dict | None:
        """Generate a Merkle inclusion proof for a specific event.

        Returns proof dict with leaf data, path, and root.
        """
        if seq >= len(self._events):
            return None

        # Find which epoch covers this seq
        epoch = None
        for e in reversed(self._epochs):
            if e.start_seq <= seq < e.end_seq:
                epoch = e
                break

        if epoch is None:
            # No epoch sealed yet — generate proof over all events
            leaf_data = [_canonical_json(e.to_dict()) for e in self._events]
            idx = seq
        else:
            leaf_data = [
                _canonical_json(e.to_dict())
                for e in self._events[epoch.start_seq:epoch.end_seq]
            ]
            idx = seq - epoch.start_seq

        path = inclusion_path(leaf_data, idx)
        root = merkle_root(leaf_data)

        return {
            "seq": seq,
            "event_hash": self._events[seq].event_hash,
            "leaf_index": idx,
            "path": path,
            "root": root,
            "epoch_id": epoch.epoch_id if epoch else None,
            "verified": root == (epoch.root if epoch else root),
        }

    def stats(self) -> dict:
        return {
            "total_events": len(self._events),
            "total_epochs": len(self._epochs),
            "cases": len(self._by_case),
        }
