"""Real Foxit eSign API client — documented endpoints (developer-api.foxit.com guides).

Flow: OAuth2 client_credentials → upload/createfolder → sendDraftFolder.
Credentials: FOXIT_ESIGN_CLIENT_ID / FOXIT_ESIGN_CLIENT_SECRET (free self-registration,
separate from PDF Services keys). Base: https://na1.foxitesign.foxit.com

Signature fields: documents must carry a text tag like ${s:1:______} OR fields are
placed via createfolder parties/fields config. We embed text tags in the memo at
generation time so processTags creates the field automatically.

Note (Foxit's own docs): /folders/createfolder is NOT idempotent — retries duplicate
signers. ProofDesk's SignatureGate is the state check they recommend calling first.
"""
from __future__ import annotations

import base64
import os
import time

import httpx


class FoxitESignError(Exception):
    pass


class FoxitESignClient:
    TOKEN_URL = "https://na1.foxitesign.foxit.com/api/oauth2/access_token"

    def __init__(self):
        self.client_id = os.environ.get("FOXIT_ESIGN_CLIENT_ID", "")
        self.client_secret = os.environ.get("FOXIT_ESIGN_CLIENT_SECRET", "")
        self.base = os.environ.get("FOXIT_ESIGN_BASE_URL", "https://na1.foxitesign.foxit.com")
        self._token: str | None = None
        self._token_exp = 0.0

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = httpx.post(self.TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "read-write",
        }, timeout=30)
        if r.status_code != 200:
            raise FoxitESignError(f"token exchange {r.status_code}: {r.text[:200]}")
        data = r.json()
        self._token = data.get("access_token")
        self._token_exp = time.time() + int(data.get("expires_in", 3600))
        if not self._token:
            raise FoxitESignError("no access_token in response")
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token()}"}

    def create_and_send(
        self,
        pdf_path: str,
        signer_email: str,
        signer_name: str = "",
        subject: str = "ProofDesk approval packet",
        message: str = "",
        expire_days: int = 5,
    ) -> dict:
        """Upload PDF → create folder w/ signer + text-tag field → send for signature."""
        token = self._access_token()
        pdf_b64 = base64.b64encode(open(pdf_path, "rb").read()).decode()

        # 1. createfolder with embedded document + signer party
        payload = {
            "name": subject[:100],
            "folderType": "template",
            "descriptionText": message[:500],
            "parties": [{
                "firstName": (signer_name or signer_email).split("@")[0][:40],
                "lastName": ".",
                "emailId": signer_email,
                "permission": "FILL_FIELDS_AND_SIGN",
                "sequence": 1,
            }],
            "expireAfterDays": expire_days,
            "processTextTags": True,   # converts ${s:1:____} tags into fields
            "createEmbeddedSigningSession": False,
        }
        files = {
            "file": (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf"),
            "json": (None, __import__("json").dumps(payload), "application/json"),
        }
        r = httpx.post(
            f"{self.base}/api/folders/createfolder",
            headers={"Authorization": f"Bearer {token}"},
            files=files, timeout=60)
        if r.status_code >= 400:
            raise FoxitESignError(f"createfolder {r.status_code}: {r.text[:300]}")
        folder_id = r.json().get("folderId") or r.json().get("id")
        if not folder_id:
            raise FoxitESignError(f"no folderId: {str(r.json())[:200]}")

        # 2. sendDraftFolder — dispatches signing email to the party
        r2 = httpx.post(
            f"{self.base}/api/folders/sendDraftFolder",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"folderId": folder_id}, timeout=60)
        if r2.status_code >= 400:
            raise FoxitESignError(f"send {r2.status_code}: {r2.text[:300]}")

        return {"folder_id": folder_id, "status": "SENT", "signer": signer_email}

    def status(self, folder_id: str) -> str:
        r = httpx.get(
            f"{self.base}/api/folders/{folder_id}/status",
            headers=self._headers(), timeout=30)
        if r.status_code >= 400:
            raise FoxitESignError(f"status {r.status_code}")
        return r.json().get("folderStatus") or r.json().get("status") or "UNKNOWN"


def add_signature_tag_to_text(text: str) -> str:
    """Append a Foxit eSign text tag line so processTextTags creates a real field."""
    return text + "\n\nApprover signature: ${s:1:____________________}   Date: ${d1:1:_/_/_}\n"
