"""Ed25519 signed attestations for approval records.

Sourced from Patalacheckpoints: pipeline/products/scholar_review/signing.py

Approvals, resolutions, and certificates are content-hashed and
optionally signed to provide non-repudiation.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def content_hash(data: dict) -> str:
    """SHA-256 of canonical JSON."""
    return hashlib.sha256(_canonical(data)).hexdigest()


@dataclass
class SignedAttestation:
    """A content-hashed and optionally signed attestation."""
    attestation_type: str
    case_id: str
    payload: dict
    timestamp: float = field(default_factory=time.time)
    content_hash: str = ""
    signature: str = ""
    public_key: str = ""

    def compute_hash(self) -> str:
        self.content_hash = content_hash(self.payload)
        return self.content_hash

    def sign(self, private_key_pem: bytes) -> None:
        """Sign the attestation with an Ed25519 private key."""
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography library required for signing")

        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        if not isinstance(private_key, Ed25519PrivateKey):
            raise TypeError("Expected Ed25519 private key")

        canonical = _canonical({
            "type": self.attestation_type,
            "case_id": self.case_id,
            "payload_hash": self.content_hash,
            "timestamp": self.timestamp,
        })
        sig = private_key.sign(canonical)
        self.signature = sig.hex()

        # Store public key for verification
        pub = private_key.public_key()
        self.public_key = pub.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ).hex()

    def verify(self) -> tuple[bool, str]:
        """Verify signature and content hash.

        Returns (ok, reason).
        """
        # First: verify content hash matches current payload
        recomputed = content_hash(self.payload)
        if recomputed != self.content_hash:
            return False, f"Content hash mismatch: payload was tampered (expected {recomputed[:16]}, got {self.content_hash[:16]})"

        if not self.signature:
            return True, "No signature (unsigned attestation, hash-only)"

        if not HAS_CRYPTO:
            return False, "cryptography library not installed"

        try:
            pub_bytes = bytes.fromhex(self.public_key)
            public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)

            canonical = _canonical({
                "type": self.attestation_type,
                "case_id": self.case_id,
                "payload_hash": self.content_hash,
                "timestamp": self.timestamp,
            })
            sig_bytes = bytes.fromhex(self.signature)
            public_key.verify(sig_bytes, canonical)
            return True, "Signature valid"
        except Exception as e:
            return False, f"Signature verification failed: {e}"

    def to_dict(self) -> dict:
        return {
            "attestation_type": self.attestation_type,
            "case_id": self.case_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
            "signature": self.signature,
            "public_key": self.public_key,
        }


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate Ed25519 keypair. Returns (private_pem, public_pem)."""
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library required")

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem
