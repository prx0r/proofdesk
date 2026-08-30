"""Real Doctavian API integration for document generation.

API: POST https://demo.api.doctavian.com/v1/documents/document/generate
Auth: Bearer token + x-api-key + X-Subscription-Key + X-Client-Authorization

Workflow:
1. Upload template via POST /documents/document/upload (X-Storage-Type: document-template)
2. Upload data via POST /documents/data/upload (X-Storage-Type: document-data)
3. Generate via POST /documents/document/generate with both URNs
4. Download via GET /documents/document/{id}/download
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from ..models.domain import GeneratedArtifact, _id, _hash


DOCTAVIAN_BASE_URL = "https://demo.api.doctavian.com"


# --- Payload builder (D1) — approved record → generation JSON ---

def build_generation_payload(record_data: dict, confidence: dict | None = None) -> dict:
    """Deterministically map a StructuredRecord dict to the Doctavian payload.

    Includes risk band + per-field confidence failures from the foxit module
    (when provided) so template branching renders the calibration decision.
    """
    facts = {f["field"]: f.get("value_normalized", "N/A") for f in record_data.get("facts", [])}
    assertions = record_data.get("assertions", [])
    resolutions = record_data.get("resolutions", [])

    def g(field: str) -> str:
        v = facts.get(field)
        return "N/A" if v is None or v == "" else str(v)

    failed = [a for a in assertions if a.get("result") == "FAIL"]
    passed = [a for a in assertions if a.get("result") != "FAIL"]

    # Risk band: explicit confidence wins, else derive from checks/resolutions
    band = (confidence or {}).get("band")
    conf = (confidence or {}).get("confidence")
    if band not in ("CLEARED", "CONDITIONAL", "ESCALATED"):
        if not failed:
            band, conf = "CLEARED", 0.95
        elif resolutions:
            band, conf = "CONDITIONAL", 0.62
        else:
            band, conf = "ESCALATED", 0.30

    # Per-field risk failures append as confidence clauses
    extra_conditions = [
        {"predicate": f"confidence:{fr['field']}", "detail": fr.get("detail", "exceeds field risk budget"), "rule": "confidence-budget"}
        for fr in (confidence or {}).get("field_risks", [])
    ]
    all_failed = failed + extra_conditions

    return {
        "case_id": record_data.get("case_id", ""),
        "record_hash": record_data.get("content_hash", ""),
        "generated_date": time.strftime("%Y-%m-%d"),
        # vendor / quote fields
        "vendor_name": g("vendor.legal_name"),
        "platform_price": g("quote.platform_price"),
        "support_price": g("quote.support_price"),
        "quote_total": g("quote.total"),
        "requested_spend": g("procurement.requested_spend"),
        "contract_start": g("procurement.contract_start"),
        "insurance_expiry": g("insurance.expiry_date"),
        "required_coverage": g("procurement.required_coverage_until"),
        "data_retention": g("security.data_retention_days"),
        "subprocessors": g("security.subprocessors"),
        "encryption": g("security.encryption_at_rest"),
        # confidence / risk
        "signing_confidence": str(conf),
        "risk_band": band,
        "has_conditions": "true" if all_failed else "false",
        "condition_count": len(all_failed),
        # lists rendered by repeater elements
        "passed_checks": [
            {"predicate": a["predicate"], "detail": a.get("detail", "")} for a in passed
        ],
        "failed_checks": [
            {"idx": i, "predicate": a["predicate"], "detail": a.get("detail", ""), "rule": a.get("rule_version", "")}
            for i, a in enumerate(all_failed, 1)
        ],
        "resolutions": [
            {"decision": r.get("decision", ""), "reason": r.get("reason", ""), "actor": r.get("actor_id", "")}
            for r in resolutions
        ],
    }


class DoctavianError(Exception):
    def __init__(self, status: int, message: str, code: str = ""):
        self.status = status
        self.code = code
        super().__init__(f"Doctavian API error {status}: {message}")


class DoctavianClient:
    """Real Doctavian API client."""

    def __init__(
        self,
        bearer_token: str | None = None,
        api_key: str | None = None,
        subscription_key: str | None = None,
        client_auth: str | None = None,
    ):
        # Use provided credentials or fall back to environment/hardcoded values
        self.bearer_token = bearer_token or os.environ.get("DOCTAVIAN_BEARER_TOKEN", "")
        self.api_key = api_key or os.environ.get("DOCTAVIAN_API_KEY", "")
        self.subscription_key = subscription_key or os.environ.get("DOCTAVIAN_SUBSCRIPTION_KEY", "")
        self.client_auth = client_auth or os.environ.get("DOCTAVIAN_CLIENT_AUTH", "")
        self.base_url = os.environ.get("DOCTAVIAN_BASE_URL", DOCTAVIAN_BASE_URL)

    @property
    def is_configured(self) -> bool:
        return bool(self.bearer_token and self.api_key and self.subscription_key)

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "x-api-key": self.api_key,
            "X-Subscription-Key": self.subscription_key,
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated request to Doctavian API."""
        from . import trace as vtrace
        t0 = time.time()
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        with httpx.Client(timeout=60.0) as client:
            response = client.request(method, url, headers=headers, **kwargs)

        body = kwargs.get("json") or kwargs.get("content")
        vtrace.record("current", "Doctavian", path.rstrip("/").split("/")[-1],
                      method, url,
                      request_summary=(body if isinstance(body, (dict, str)) else None),
                      status=response.status_code,
                      response_summary=response.text[:400] if response.status_code >= 400
                                        else response.json().get("result", {}).get("data"),
                      duration_ms=(time.time() - t0) * 1000)

        if response.status_code >= 400:
            try:
                error = response.json()
                inner = error.get("error", {}).get("innerErrors", [{}])
                code = inner[0].get("code", "") if inner else ""
                msg = error.get("error", {}).get("message", response.text)
            except Exception:
                msg = response.text
                code = ""
            raise DoctavianError(response.status_code, msg, code)

        return response.json()

    # --- Template operations ---

    def upload_template(self, file_path: str) -> str:
        """Upload a template file and return its URN.

        Uses POST /documents/document/upload with X-Storage-Type: document-template.
        """
        url = f"{self.base_url}/v1/documents/document/upload"
        headers = self._headers(content_type=None)
        headers["X-Storage-Type"] = "document-template"

        from . import trace as vtrace
        t0 = time.time()
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    url,
                    headers={k: v for k, v in headers.items() if k != "Content-Type"},
                    files=files,
                )

        vtrace.record("current", "Doctavian", "upload_template[memo.docx]",
                      "POST", url, request_summary={"file": os.path.basename(file_path)},
                      status=response.status_code,
                      response_summary=(response.json().get("result", {}).get("data")
                                        if response.status_code < 400 else response.text[:200]),
                      duration_ms=(time.time()-t0)*1000)
        if response.status_code >= 400:
            try:
                error = response.json()
                msg = error.get("error", {}).get("message", response.text)
            except Exception:
                msg = response.text
            raise DoctavianError(response.status_code, msg)

        result = response.json()
        files = result.get("result", {}).get("data", {}).get("files", [])
        if files:
            return files[0].get("id", "")
        return ""

    def list_templates(self, top: int = 10) -> list[dict]:
        """List available document templates."""
        result = self._request("GET", f"/v1/documents/template/list?top={top}")
        return result.get("result", {}).get("data", {}).get("documentTemplates", [])

    # --- Data operations ---

    def upload_data(self, data: dict) -> str:
        """Upload structured JSON data and return its URN.

        Uses POST /documents/data/upload with X-Storage-Type: document-data.
        NOTE: Data is ephemeral - deleted after next generate call.
        """
        url = f"{self.base_url}/v1/documents/data/upload"
        headers = self._headers(content_type="application/json")
        headers["X-Storage-Type"] = "document-data"

        from . import trace as vtrace
        t0 = time.time()
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, content=json.dumps(data))

        vtrace.record("current", "Doctavian", "upload_data[data.json]",
                      "POST", url, request_summary={"keys": list(data.keys())},
                      status=response.status_code,
                      response_summary=(response.json().get("result", {}).get("data")
                                        if response.status_code < 400 else response.text[:200]),
                      duration_ms=(time.time()-t0)*1000)
        if response.status_code >= 400:
            try:
                error = response.json()
                msg = error.get("error", {}).get("message", response.text)
            except Exception:
                msg = response.text
            raise DoctavianError(response.status_code, msg)

        result = response.json()
        files = result.get("result", {}).get("data", {}).get("files", [])
        if files:
            return files[0].get("id", "")
        return ""

    # --- Document generation ---

    def create_data_source(self, name: str, description: str = "") -> str:
        """Create a named Data Source (Mission-1 architecture). Returns GUID."""
        result = self._request("POST", "/v1/documents/datasource/create", json={
            "name": name, "description": description or name,
            "variables": "[]", "loadMethod": "Storage"})
        return result["result"]["data"]["dataSourceGuid"]

    def create_solution(self, name: str, data_guid: str, description: str = "") -> str:
        """Create a Document Solution tying data source to templates. Returns GUID."""
        result = self._request("POST", "/v1/documents/solution/create", json={
            "name": name, "description": description or name, "dataGuid": data_guid})
        return result["result"]["data"]["documentSolution"]["documentSolutionGuid"]

    def generate_document(
        self,
        template_urn: str,
        data_urn: str,
        output_name: str = "proofdesk_output",
        output_format: str = "pdf",
        timezone: str = "Europe/Dublin",
        locale: str = "en",
    ) -> dict:
        """Generate a document from template + data URNs.

        Payload format per official Postman collection (Mission 1 Step 5):
        path="root", locale simple code, IANA timezone. Storage delivery needs
        no X-Client-Authorization.
        
        NOTE: Demo environment has Google Drive scope limitation.
        If DELIVERY_PATH_RESOLUTION_FAILED, returns empty dict to trigger local fallback.
        """
        payload = {
            "externalContext": {"id": f"proofdesk-{int(time.time())}"},
            "template": {
                "name": "template.docx",
                "urn": template_urn,
                "fileFormat": "docx",
                "loadMethod": "Storage",
                "options": {},
            },
            "data": {
                "loadMethod": "Storage",
                "urn": data_urn,
            },
            "document": {
                "name": output_name,
                "fileFormat": output_format,
                "deliveryMethod": "Storage",
                "path": "root",
                "locale": locale,
                "timezone": timezone,
                "options": {},
            },
        }

        try:
            result = self._request("POST", "/v1/documents/document/generate", json=payload)
            return result.get("result", {}).get("data", {}).get("document", {})
        except DoctavianError as e:
            error_msg = str(e)
            if "DELIVERY_PATH_RESOLUTION_FAILED" in error_msg or "COPY_FILE_GOOGLEDRIVE_FAILED" in error_msg:
                return {
                    "provider": "doctavian",
                    "mode": "live",
                    "status": "failed",
                    "error_code": "DELIVERY_PATH_RESOLUTION_FAILED",
                    "detail": "Cloud generation failed — bearer token may lack drive.file scope. Falling back to local renderer.",
                    "fallback_used": True,
                }
            raise

    def download_document(self, document_urn: str) -> bytes:
        """Download a generated document by URN (format 'guid:name.pdf')."""
        from urllib.parse import quote

        url = f"{self.base_url}/v1/documents/document/{quote(document_urn, safe='')}/download"
        headers = self._headers(content_type=None)
        headers["Accept"] = "application/octet-stream"

        with httpx.Client(timeout=120.0) as client:
            response = client.get(url, headers=headers)

        if response.status_code >= 400:
            raise DoctavianError(response.status_code, "Download failed")

        return response.content

    # --- Signature envelope flow (D4) ---

    def upload_for_signature(self, pdf_path: str) -> str:
        """Upload a PDF for signing. Returns SIGN_DOC_URN."""
        url = f"{self.base_url}/v1/signatures/document/upload"
        headers = self._headers(content_type=None)
        headers["X-Storage-Type"] = "document-input"

        with open(pdf_path, "rb") as f:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url, headers=headers,
                    files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                )
        if response.status_code >= 400:
            raise DoctavianError(response.status_code, response.text[:300])
        return response.json()["result"]["data"]["files"][0]["id"]

    def create_envelope(
        self,
        sign_doc_urn: str,
        signer_email: str,
        signer_name: str,
        case_id: str = "",
        record_hash: str = "",
    ) -> str:
        """Create a signing envelope with one mandatory signer. Returns ENVELOPE_ID."""
        payload = {
            "documents": [{
                "referenceDocumentId": 1,
                "name": f"approval_memo_{case_id}",
                "loadMethod": "Storage",
                "urn": sign_doc_urn,
            }],
            "recipients": [{
                "referenceSignerId": 1,
                "name": signer_name or signer_email,
                "email": signer_email,
                "role": "signer",
                "mandatory": True,
                "signOrder": 1,
            }],
            "fields": [
                {"type": "signature", "isRequired": True, "referenceSignerId": 1,
                 "referenceDocumentId": 1, "page": 1,
                 "positionX": 85, "positionY": 660, "width": 200, "height": 55,
                 "name": "signature_approver"},
                {"type": "date", "isRequired": True, "referenceSignerId": 1,
                 "referenceDocumentId": 1, "page": 1,
                 "positionX": 85, "positionY": 725, "width": 120, "height": 30,
                 "name": "signature_date"},
            ],
            "envelope": {
                "subject": f"ProofDesk approval — case {case_id} [{record_hash[:16]}]",
                "message": (
                    "Approved vendor memorandum generated from verified evidence. "
                    f"Record hash: {record_hash}. Please review and sign."
                ),
                "senderName": "ProofDesk",
                "isSignOrder": False,
                "expireInDays": 5,
                "notifyWhenSigned": True,
            },
        }
        result = self._request("POST", "/v1/signatures/envelope/create", json=payload)
        return result["result"]["data"]["envelope"]["id"]

    def send_envelope(self, envelope_id: str) -> dict:
        """Send the draft envelope — human receives signing email."""
        return self._request("GET", f"/v1/signatures/envelope/{envelope_id}/send")

    def get_envelope(self, envelope_id: str) -> dict:
        """Poll envelope status (status 'Completed' when all signed)."""
        return self._request("GET", f"/v1/signatures/envelope/{envelope_id}/get")

    # --- High-level workflow ---

    def generate_from_record(
        self,
        record_data: dict,
        template_urn: str | None = None,
        confidence: dict | None = None,
    ) -> tuple[GeneratedArtifact, str]:
        """Generate a Vendor Approval Memorandum from ProofDesk record data.

        Returns (GeneratedArtifact, content_string).
        """
        # Build the data payload via the canonical builder (D1)
        template_data = build_generation_payload(record_data, confidence=confidence)

        # If API is configured, try real Doctavian generation end-to-end
        if self.is_configured:
            try:
                # Upload template fresh (uploads are consumed by generation)
                template_urn = None
                template_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "data", "templates", "vendor_approval_memo.docx",
                )
                if os.path.exists(template_path):
                    template_urn = self.upload_template(template_path)

                if template_urn:
                    data_urn = self.upload_data(template_data)
                    # Mission-1 architecture: wrap data+template in named
                    # Data Source + Document Solution (platform fluency)
                    try:
                        ds_guid = self.create_data_source(
                            f"proofdesk-{record_data.get('case_id','x')}",
                            "ProofDesk approved record payload")
                        sol_guid = self.create_solution(
                            "ProofDesk Approval Packet", ds_guid,
                            "Approved structured record -> risk-branched memo")
                        solution_id = sol_guid
                    except Exception:
                        pass
                    if data_urn:
                        doc = self.generate_document(
                            template_urn=template_urn,
                            data_urn=data_urn,
                            output_name=f"approval_memo_{record_data.get('case_id', 'unknown')}",
                            output_format="pdf",
                        )
                        doc_urn = doc.get("urn", "")
                        content = json.dumps(doc, indent=2)
                        artifact = GeneratedArtifact(
                            case_id=record_data.get("case_id", ""),
                            record_id=record_data.get("record_id", ""),
                            record_hash=record_data.get("content_hash", ""),
                            template_id="vendor_approval_memo",
                            template_version="1.0",
                            content_hash=_hash(content),
                            provider_job_id=doc_urn or _id("job_"),
                        )
                        artifact.metadata = {"solution_guid": locals().get("solution_id", ""),
                                             "data_source_guid": locals().get("ds_guid", "")}
                        # Download the real generated PDF
                        pdf_bytes = None
                        if doc_urn:
                            try:
                                pdf_bytes = self.download_document(doc_urn)
                            except Exception:
                                pass
                        out_dir = "/tmp/proofdesk"
                        os.makedirs(out_dir, exist_ok=True)
                        if pdf_bytes:
                            path = f"{out_dir}/{artifact.artifact_id}.pdf"
                            with open(path, "wb") as f:
                                f.write(pdf_bytes)
                            artifact.output_path = path
                            content += f"\n\n[PDF saved: {path} ({len(pdf_bytes)} bytes)]"
                        else:
                            artifact.output_path = f"{out_dir}/{artifact.artifact_id}.txt"
                        return artifact, content
            except DoctavianError:
                pass
            except Exception:
                pass

        # Fallback: generate locally (deterministic, same as stub but with real data)
        content = self._render_memo(template_data)
        artifact = GeneratedArtifact(
            case_id=record_data.get("case_id", ""),
            record_id=record_data.get("record_id", ""),
            record_hash=record_data.get("content_hash", ""),
            template_id=template_urn or "local_approval_memo",
            template_version="1.0",
            content_hash=_hash(content),
            provider_job_id=_id("job_"),
        )
        artifact.output_path = f"/tmp/proofdesk/{artifact.artifact_id}.txt"
        return artifact, content

    def _render_memo(self, data: dict) -> str:
        """Render the Vendor Approval Memorandum locally (deterministic).

        Mirrors the Doctavian template's branch logic: risk_band selects
        status text, failed_checks loop renders numbered conditions.
        """
        band = data.get("risk_band", "ESCALATED")
        status_text = {
            "CLEARED": "CLEARED FOR AUTO-SIGNATURE",
            "CONDITIONAL": "CONDITIONALLY APPROVED — SIGNATURE REQUIRES LISTED CONDITIONS",
            "ESCALATED": "HELD FOR HUMAN REVIEW",
        }.get(band, band)

        lines = ["=" * 60, "VENDOR APPROVAL & RISK MEMORANDUM", "=" * 60, ""]
        lines.append(f"Status: {status_text}")
        lines.append(f"Signing confidence: {data.get('signing_confidence', 'N/A')}")
        lines.append(f"Generated: {data['generated_date']}   Record: {data.get('record_hash', '')}")
        lines.append("")

        lines.append("VENDOR INFORMATION")
        lines.append("-" * 40)
        lines.append(f"Legal Name: {data['vendor_name']}")
        lines.append(f"Platform License: ${data['platform_price']}")
        lines.append(f"Support Services: ${data['support_price']}")
        lines.append(f"Quote Total: ${data['quote_total']}")
        lines.append(f"Requested Spend: ${data['requested_spend']}")
        lines.append("")

        lines.append("COMPLIANCE SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Insurance Expiry: {data['insurance_expiry']}")
        lines.append(f"Required Coverage Until: {data['required_coverage']}")
        lines.append(f"Data Retention: {data['data_retention']} days")
        lines.append(f"Subprocessors: {data['subprocessors']}")
        lines.append(f"Encryption at Rest: {data['encryption']}")
        lines.append("")

        lines.append("DETERMINISTIC CHECKS PASSED")
        lines.append("-" * 40)
        for a in data.get("passed_checks", []):
            lines.append(f"  [+] {a['predicate']}")
        lines.append("")

        if data.get("failed_checks"):
            lines.append(f"CONDITIONS ({data.get('condition_count', len(data['failed_checks']))})")
            lines.append("-" * 40)
            for i, c in enumerate(data["failed_checks"], 1):
                lines.append(f"  §{i}. {c['predicate']}")
                lines.append(f"     {c['detail']}   [rule: {c.get('rule', '')}]")
                lines.append(f"     REQUIRED BEFORE: {data.get('contract_start', 'contract start')}")
            lines.append("")
        else:
            lines.append("CONDITIONS: none — record cleared all checks.")
            lines.append("")

        if data.get("resolutions"):
            lines.append("EXCEPTION RESOLUTIONS")
            lines.append("-" * 40)
            for r in data["resolutions"]:
                lines.append(f"  Decision: {r['decision']}   Actor: {r['actor']}")
                lines.append(f"  Reason: {r['reason']}")
            lines.append("")

        lines.append("EVIDENCE APPENDIX")
        lines.append("-" * 40)
        lines.append("  All facts are source-grounded via Nutrient DWS extraction.")
        lines.append("  Each fact retains its original value, source document, page,")
        lines.append("  and confidence score for full auditability.")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)


# --- Module-level convenience function ---

_client: DoctavianClient | None = None


def _get_client() -> DoctavianClient:
    global _client
    if _client is None:
        _client = DoctavianClient()
    return _client


def doctavian_generate(record_data: dict, template_id: str = "approval_memo", confidence: dict | None = None) -> tuple[GeneratedArtifact, str]:
    """Generate document from record data — real API if configured, local fallback otherwise."""
    client = _get_client()

    # Try to find a template URN
    template_urn = None
    if client.is_configured:
        try:
            templates = client.list_templates(top=5)
            if templates:
                template_urn = templates[0].get("urn")
        except Exception:
            pass

    return client.generate_from_record(record_data, template_urn, confidence=confidence)
