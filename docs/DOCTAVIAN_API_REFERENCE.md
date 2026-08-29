# Doctavian API Reference (Canonical)

**Source of truth:** Official Postman collection (provided by Doctavian, Aug 2026) + https://developers.doctavian.com/openapi/latest
**Demo Environment:** https://demo.api.doctavian.com
**Portal:** https://demo.portal.doctavian.com

---

## Credentials

| Item | Value | Source |
|------|-------|--------|
| Base URL | `https://demo.api.doctavian.com` | Hackathon email |
| API key | `edff22dbcc244bd0b709d7e632ce12e5` | Hackathon email (`x-api-key` header) |
| OAuth client ID | `11e71170-3499-43f3-b878-7df343f43d37` | Postman collection (preset) |
| Scope | `api://40728276-52a7-4932-bf32-76737f1fd01a/.default offline_access` | Postman collection |

## Authentication

Two layers:

1. **Gateway:** `X-Api-Key` header on every request.
2. **OAuth 2.0 (PKCE):** Bearer token via Doctavian's auth proxy:
   - Authorize: `GET {baseUrl}/public/v1/auth/{provider}/authorize`
   - Token: `POST {baseUrl}/public/v1/auth/{provider}/token`
   - Providers: `microsoft` or `google`
   - For hackathon use: log into the portal, copy the `Authorization: Bearer ya29...` header from DevTools Network tab. Expires ~1 hour.

**Key finding from Postman collection:** The Document Generate endpoint works with **just `X-Api-Key` + Bearer token**. The `X-Client-Authorization`/`X-Service-Authorization` headers are for Salesforce/OneDrive integrations — NOT needed for Storage delivery.

---

## The Generation Workflow (verified working)

### Step 1: Upload Template

```
POST /v1/documents/template/upload
Headers:
  Authorization: Bearer <token>
  x-api-key: <api_key>
  X-Storage-Type: document-template
Body: multipart/form-data, field "file" (.docx/.xlsx/.doc/.xls, lowercase extension!)
Response 201: result.data.files[0].id → TEMPLATE_URN
```

Note: templates are ephemeral-ish — auto-removed after next generation consumes them. Re-upload per run is fine.

### Step 2: Upload Data

```
POST /v1/documents/data/upload
Headers:
  Authorization: Bearer <token>
  x-api-key: <api_key>
  X-Storage-Type: document-data
Body: multipart/form-data .json file  OR  raw application/json body
Response 201: result.data.files[0].id → DATA_URN
```

Data IS deleted after the next generate call that consumes it.

### Step 3: Generate

```
POST /v1/documents/document/generate
Headers:
  Authorization: Bearer <token>
  x-api-key: <api_key>
Body:
{
  "externalContext": { "id": "<your tracking id>" },
  "template": {
    "name": "template.docx",
    "urn": "<TEMPLATE_URN>",
    "fileFormat": "docx",
    "loadMethod": "Storage",
    "options": {}
  },
  "data": {
    "loadMethod": "Storage",
    "urn": "<DATA_URN>"
  },
  "document": {
    "name": "Output-Name",
    "fileFormat": "pdf",
    "deliveryMethod": "Storage",
    "path": "root",
    "locale": "en",
    "timezone": "Europe/Dublin",
    "options": {}
  }
}
Response 201: result.data.document.urn → DOC_URN
              consumption: [{dimension:"pages-generated", value:N}]
```

**CRITICAL payload details (this is what broke our earlier attempts):**
- `document.path`: must be `"root"` — not `"proofdesk/"` or omitted
- `document.locale`: simple code like `"en"` — NOT `"en_US_POSIX"`
- `document.timezone`: IANA name like `"Europe/Dublin"` — NOT `"(GMT-05:00) Eastern..."`
- `data.variables` optional; data JSON structure maps directly to template fields
- Response URN format: `"guid:filename.pdf"` — use whole string for download

### Step 4: Download

```
GET /v1/documents/document/{DOC_URN}/download
Headers:
  Authorization: Bearer <token>
  x-api-key: <api_key>
Response 200: binary/octet-stream (the actual PDF/DOCX bytes)
```

URL-encode the URN (contains `:`).

---

## Other Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/signatures/document/upload` | POST | Upload doc for signing (`X-Storage-Type: document-input`) |
| `/v1/signatures/envelope/create` | POST | Create signing envelope w/ recipients + fields |
| `/v1/signatures/envelope/{id}/send` | GET | Send envelope (draft→sent) |
| `/v1/signatures/envelope/{id}/get` | GET | Poll status (Completed = all signed) |
| `/v1/signatures/envelope/{id}/audit/get` | GET | Audit trail JSON |
| `/v1/signatures/template/create` | POST | Reusable envelope template |
| `/v1/common/limits/get` | GET | Quota check |
| `/v1/common/user/get` | GET | Caller profile |

## Error Codes Seen

| Code | Cause |
|------|-------|
| `COPY_FILE_GOOGLEDRIVE_FAILED` | Output delivery copies to YOUR Google Drive; OAuth token lacks Drive scopes |
| `DELIVERY_PATH_RESOLUTION_FAILED` | Same root cause when `path: "root"` is set — storage backend unresolvable without Drive perms |
| `X_CLIENT_AUTH_ERROR` | Malformed X-Client-Authorization (don't send it at all for Storage) |
| `INVALID_TEMPLATE_FORMAT` | Wrong extension (case-sensitive, lowercase `.docx`) |
| `ApiKeyNotFound` / `Google token invalid` | Missing/mismatched auth headers |

### ROOT CAUSE of generation failure (verified 2026-08-25)

We sent the EXACT Mission 1 payload (path "root", locale "en", IANA timezone,
form-data .json data upload) and still got `DELIVERY_PATH_RESOLUTION_FAILED`.
Without path: `COPY_FILE_GOOGLEDRIVE_FAILED`. Earlier external error said:
*"Request had insufficient authentication scopes."*

Conclusion: **Storage delivery on the demo env copies the output file into the
authenticated user's Google Drive.** A Bearer token scraped from the portal
lacks `drive.file` scope. Fix = get a properly-scoped token:

1. Import the official Postman collection into the Postman desktop app.
2. Collection → Authorization tab → "Get New Access Token" (PKCE flow, their
   client ID + scope preset). Consent screen grants the needed scopes.
3. Copy the resulting access token into `DOCTAVIAN_BEARER_TOKEN`.

Everything else (template upload, data upload, auth headers, payload shape) is
verified working. Only the final delivery step needs the scoped token.

---

## ProofDesk Integration Status

- Client: `src/providers/doctavian.py` (`DoctavianClient`)
- Wired in orchestrator `generate_document()`; local deterministic fallback if API fails
- Template: `data/templates/vendor_approval_memo.docx` (uploaded fresh each run since uploads are consumed)

## Submission Line (Doctavian track)

> "Doctavian converts ProofDesk's approved structured record into the final Vendor Approval Memorandum PDF — one template handles branch-specific clauses (approved vs conditional), repeated line items, and calculated totals, so every case gets a correctly-shaped document without manual edits."
