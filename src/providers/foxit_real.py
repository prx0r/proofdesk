"""Foxit PDF Services + eSign integration for ProofDesk.

Uses real Foxit API with the keys provided.
Handles: upload, merge, compress, download, eSign.
"""

import requests
import json
import time
import os


class FoxitPDFClient:
    """Real Foxit PDF Services API client."""

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id or os.environ.get("FOXIT_CLOUD_API_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("FOXIT_CLOUD_API_CLIENT_SECRET", "")
        self.base_url = "https://na1.fusion.foxit.com/pdf-services"
        self.headers = {"client_id": self.client_id, "client_secret": self.client_secret}

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def upload(self, file_path: str) -> str:
        """Upload document, return documentId."""
        if not self.is_configured:
            return "simulated_doc_id"
        from . import trace as vtrace
        t0 = time.time()
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{self.base_url}/api/documents/upload",
                headers=self.headers,
                files={"file": (os.path.basename(file_path), f, "application/pdf")},
                timeout=30,
            )
        vtrace.record("current", "Foxit PDF Services", "upload",
                      "POST", f"{self.base_url}/api/documents/upload",
                      request_summary={"file": os.path.basename(file_path),
                                       "auth": "client credentials"},
                      status=r.status_code,
                      response_summary=r.json() if r.status_code == 200 else r.text[:200],
                      duration_ms=(time.time() - t0) * 1000)
        r.raise_for_status()
        return r.json()["documentId"]

    def merge(self, doc_ids: list[str]) -> str:
        """Merge documents, return taskId."""
        if not self.is_configured:
            return "simulated_task_id"
        from . import trace as vtrace
        t0 = time.time()
        r = requests.post(
            f"{self.base_url}/api/documents/enhance/pdf-combine",
            headers=self.headers,
            json={"documentInfos": [{"documentId": d} for d in doc_ids]},
            timeout=60,
        )
        vtrace.record("current", "Foxit PDF Services", "merge (pdf-combine)",
                      "POST", f"{self.base_url}/api/documents/enhance/pdf-combine",
                      request_summary={"documentInfos": doc_ids},
                      status=r.status_code,
                      response_summary=r.json() if r.status_code == 200 else r.text[:200],
                      duration_ms=(time.time() - t0) * 1000)
        r.raise_for_status()
        return r.json()["taskId"]

    def compress(self, doc_id: str, level: str = "LOW") -> str:
        """Compress document, return taskId."""
        if not self.is_configured:
            return "simulated_task_id"
        r = requests.post(
            f"{self.base_url}/api/documents/modify/pdf-compress",
            headers=self.headers,
            json={"documentId": doc_id, "compressionLevel": level},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["taskId"]

    def download(self, doc_id: str) -> bytes:
        """Download document as bytes."""
        if not self.is_configured:
            return b"simulated_pdf"
        r = requests.get(
            f"{self.base_url}/api/documents/{doc_id}/download",
            headers=self.headers,
            timeout=30,
        )
        r.raise_for_status()
        return r.content

    def delete(self, doc_id: str) -> None:
        """Delete document."""
        if not self.is_configured:
            return
        requests.delete(
            f"{self.base_url}/api/documents/{doc_id}",
            headers=self.headers,
            timeout=30,
        )


class FoxitESignClient:
    """Foxit eSign API client."""

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id or os.environ.get("FOXIT_ESIGN_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("FOXIT_ESIGN_CLIENT_SECRET", "")
        self.base_url = "https://na1.foxitesign.foxit.com"

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_token(self) -> str:
        """Get OAuth2 access token."""
        if not self.is_configured:
            return "simulated_token"
        r = requests.post(
            f"{self.base_url}/api/oauth2/access_token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "read-write",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def create_folder(self, pdf_bytes: bytes, signer_email: str) -> dict:
        """Create signing folder with PDF."""
        if not self.is_configured:
            return {"folderId": "simulated_folder", "request_id": f"esign_{int(time.time())}"}
        token = self.get_token()
        encoded = __import__("base64").b64encode(pdf_bytes).decode()
        r = requests.post(
            f"{self.base_url}/api/folders/createfolder",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "folderName": "ProofDesk Document",
                "inputType": "base64",
                "base64FileString": [encoded],
                "fileNames": ["document.pdf"],
                "processTextTags": True,
                "sendNow": False,
                "parties": [{"email": signer_email, "name": signer_email.split("@")[0], "role": "Signer", "permission": "FILL_FIELDS_AND_SIGN"}],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def send_folder(self, folder_id: str) -> dict:
        """Send draft folder to signers."""
        if not self.is_configured:
            return {"status": "sent"}
        token = self.get_token()
        r = requests.post(
            f"{self.base_url}/api/folders/sendDraftFolder",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"folderId": folder_id},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
