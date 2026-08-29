"""Content-addressed artifact store.

Sourced from Dell2: src/dell2/evidence/artifact_store.py

Raw bytes are stored by SHA-256 hash. Same bytes always produce the
same key. Tamper detection by recompute.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from .chain import _sha256_hex


class ArtifactStore:
    """Content-addressed artifact storage.

    Usage:
        store = ArtifactStore("/tmp/proofdesk/artifacts")
        ref = store.put(b"raw PDF bytes", media_type="application/pdf")
        assert store.verify(ref["sha256"])
        data = store.get(ref["sha256"])
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _key(self, sha: str) -> Path:
        return self._root / sha[:2] / sha / "blob"

    def _meta_key(self, sha: str) -> Path:
        return self._root / sha[:2] / sha / "meta.json"

    def put(
        self,
        data: bytes,
        media_type: str = "application/octet-stream",
        metadata: dict | None = None,
    ) -> dict:
        """Store bytes content-addressed by SHA-256.

        Returns reference dict with sha256, media_type, size_bytes.
        """
        sha = _sha256_hex(data)
        blob_path = self._key(sha)

        if not blob_path.exists():
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            blob_path.write_bytes(data)

            meta = {
                "sha256": sha,
                "media_type": media_type,
                "size_bytes": len(data),
                "stored_at": time.time(),
                **(metadata or {}),
            }
            self._meta_key(sha).write_text(json.dumps(meta, indent=2))

        return {
            "sha256": sha,
            "media_type": media_type,
            "size_bytes": len(data),
        }

    def get(self, sha: str) -> bytes | None:
        """Retrieve artifact by SHA-256 hash."""
        blob_path = self._key(sha)
        if blob_path.exists():
            return blob_path.read_bytes()
        return None

    def verify(self, sha: str) -> bool:
        """Verify artifact integrity by recomputing hash."""
        data = self.get(sha)
        if data is None:
            return False
        return _sha256_hex(data) == sha

    def exists(self, sha: str) -> bool:
        return self._key(sha).exists()

    def list_all(self) -> list[dict]:
        """List all stored artifacts."""
        artifacts = []
        for two_digit_dir in sorted(self._root.iterdir()):
            if not two_digit_dir.is_dir() or len(two_digit_dir.name) != 2:
                continue
            for sha_dir in sorted(two_digit_dir.iterdir()):
                if not sha_dir.is_dir():
                    continue
                meta_path = sha_dir / "meta.json"
                if meta_path.exists():
                    artifacts.append(json.loads(meta_path.read_text()))
        return artifacts

    def stats(self) -> dict:
        artifacts = self.list_all()
        total_bytes = sum(a.get("size_bytes", 0) for a in artifacts)
        return {
            "count": len(artifacts),
            "total_bytes": total_bytes,
            "root": str(self._root),
        }
