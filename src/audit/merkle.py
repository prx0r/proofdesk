"""Merkle tree — RFC 6962-style with domain-separated leaf/node hashing.

Sourced from QDW: src/qdw/core/ledger/merkle.py
"""

from __future__ import annotations

import hashlib
from typing import Sequence


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(data: bytes) -> bytes:
    """Domain-separated leaf hash (RFC 6962)."""
    return _h(b"\x00" + data)


def node_hash(left: bytes, right: bytes) -> bytes:
    """Domain-separated internal node hash (RFC 6962)."""
    return _h(b"\x01" + left + right)


def merkle_root(leaf_data_list: Sequence[bytes]) -> str:
    """Compute Merkle root over a list of leaf data items.

    Returns hex-encoded SHA-256 root hash.
    """
    if not leaf_data_list:
        return _h(b"").hex()

    hashes = [leaf_hash(d) for d in leaf_data_list]

    while len(hashes) > 1:
        next_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else left
            next_level.append(node_hash(left, right))
        hashes = next_level

    return hashes[0].hex()


def inclusion_path(leaf_data_list: Sequence[bytes], index: int) -> list[str]:
    """Generate Merkle inclusion proof path for leaf at index.

    Returns list of sibling hashes (hex-encoded) from leaf to root.
    """
    if not leaf_data_list or index >= len(leaf_data_list):
        return []

    hashes = [leaf_hash(d) for d in leaf_data_list]
    path = []

    level = hashes
    idx = index
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(node_hash(left, right))

        # Record sibling
        if idx % 2 == 0:
            sibling = level[idx + 1] if idx + 1 < len(level) else level[idx]
        else:
            sibling = level[idx - 1]
        path.append(sibling.hex())

        idx = idx // 2
        level = next_level

    return path


def verify_inclusion(
    leaf_data: bytes,
    index: int,
    path: list[str],
    expected_root: str,
) -> bool:
    """Verify a Merkle inclusion proof.

    Args:
        leaf_data: Original leaf data
        index: Leaf index in the original list
        path: List of sibling hashes from inclusion_path()
        expected_root: Expected Merkle root (hex)
    """
    current = leaf_hash(leaf_data)

    idx = index
    for sibling_hex in path:
        sibling = bytes.fromhex(sibling_hex)
        if idx % 2 == 0:
            current = node_hash(current, sibling)
        else:
            current = node_hash(sibling, current)
        idx = idx // 2

    return current.hex() == expected_root
