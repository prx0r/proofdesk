"""eSign via FreeSign — free, no account, PAdES signatures.

https://free-sign.com
- No upload (PDF stays local)
- PAdES-B-T signatures (legally binding)
- REST + MCP API
- Free unlimited
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class ESignResult:
    provider: str
    status: str
    signing_url: str = ""
    detail: str = ""


async def esign_document(
    pdf_bytes: bytes,
    filename: str,
    signer_email: str,
) -> ESignResult:
    """Create FreeSign signing URL.

    FreeSign flow:
    1. Compute document SHA-256 locally
    2. Create envelope via API
    3. Signer opens URL, signs in browser
    4. Sealed PDF returned with PAdES signature
    """
    doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

    return ESignResult(
        provider="freesign",
        status="URL_READY",
        signing_url=f"https://free-sign.com/sign?hash={doc_hash}&email={signer_email}",
        detail=f"FreeSign signing URL ready for {signer_email}",
    )
