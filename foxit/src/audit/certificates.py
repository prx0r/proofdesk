"""Self-hashing certificates for generated documents.

Sourced from Dell2: src/dell2/certificate/verify.py

A certificate includes its own content hash, making it tamper-evident.
Anyone can recompute the hash and detect if the certificate was altered.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from .chain import _hash_object


@dataclass
class Certificate:
    """Self-hashing certificate for a generated document or decision.

    The certificate_hash is computed from all other fields, making
    the certificate tamper-evident by construction.
    """
    cert_type: str  # "approval", "generation", "extraction", "resolution"
    case_id: str
    subject: str  # what this certifies
    evidence: list[dict] = field(default_factory=list)  # hash refs to evidence
    issued_at: float = field(default_factory=time.time)
    issuer: str = "proofdesk"
    metadata: dict = field(default_factory=dict)
    certificate_hash: str = ""

    def compute_hash(self) -> str:
        """Compute self-hash from all fields except certificate_hash."""
        data = {
            "cert_type": self.cert_type,
            "case_id": self.case_id,
            "subject": self.subject,
            "evidence": self.evidence,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "metadata": self.metadata,
        }
        self.certificate_hash = _hash_object(data)
        return self.certificate_hash

    def verify_integrity(self) -> tuple[bool, str]:
        """Recompute hash and compare to stored certificate_hash.

        Returns (ok, reason).
        """
        stored = self.certificate_hash
        recomputed = self._recompute_hash()

        if recomputed == stored:
            return True, "Certificate integrity OK"
        return False, f"Certificate tampered: expected {recomputed[:16]}, got {stored[:16]}"

    def _recompute_hash(self) -> str:
        data = {
            "cert_type": self.cert_type,
            "case_id": self.case_id,
            "subject": self.subject,
            "evidence": self.evidence,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "metadata": self.metadata,
        }
        return _hash_object(data)

    def to_dict(self) -> dict:
        return {
            "cert_type": self.cert_type,
            "case_id": self.case_id,
            "subject": self.subject,
            "evidence": self.evidence,
            "issued_at": self.issued_at,
            "issuer": self.issuer,
            "metadata": self.metadata,
            "certificate_hash": self.certificate_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Certificate:
        cert = cls(
            cert_type=data["cert_type"],
            case_id=data["case_id"],
            subject=data["subject"],
            evidence=data.get("evidence", []),
            issued_at=data.get("issued_at", 0),
            issuer=data.get("issuer", ""),
            metadata=data.get("metadata", {}),
            certificate_hash=data.get("certificate_hash", ""),
        )
        return cert
