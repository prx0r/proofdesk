# Foxit API — Agentic Document Workflows Guide

Source: https://developer-api.foxit.com/developer-blogs/api-guides-tutorials/agentic-document-workflows/

---

## Architecture

Two modes:
- **Mode 1 (Programmatic pipeline):** MCP host registers Foxit MCP Server → agent calls PDF tools → server handles REST
- **Mode 2 (In-app orchestration):** Foxit PDF Editor acts as MCP Host, connects to external MCP servers

## Setup

```bash
# PDF Services (MCP server)
export FOXIT_CLOUD_API_HOST="https://na1.fusion.foxit.com/pdf-services"
export FOXIT_CLOUD_API_CLIENT_ID="your_client_id"
export FOXIT_CLOUD_API_CLIENT_SECRET="your_client_secret"

# eSign (separate service, separate credentials)
export FOXIT_ESIGN_BASE_URL="https://na1.foxitesign.foxit.com"
export FOXIT_ESIGN_CLIENT_ID="your_esign_client_id"
export FOXIT_ESIGN_CLIENT_SECRET="your_esign_client_secret"
```

## Tool Categories (32 tools)

| Category | Tools |
|----------|-------|
| Document lifecycle | upload_document, download_document, delete_document |
| Creation | pdf_from_word, pdf_from_excel, pdf_from_ppt, pdf_from_text, pdf_from_html, pdf_from_url, pdf_from_image |
| Conversion | pdf_to_word, pdf_to_excel, pdf_to_ppt, pdf_to_text, pdf_to_html, pdf_to_image |
| Manipulation | pdf_merge, pdf_split, pdf_extract, pdf_compress, pdf_flatten, pdf_linearize, pdf_watermark, pdf_manipulate |
| Security | pdf_protect, pdf_remove_password |
| Properties | get_pdf_properties |
| Analysis | pdf_compare, pdf_ocr, pdf_structural_analysis |
| Forms | export_pdf_form_data, import_pdf_form_data |

## eSign Workflow (separate from MCP)

1. Get OAuth2 token: `POST /api/oauth2/access_token` (form-encoded, not JSON)
2. Create folder: `POST /api/folders/createfolder` with base64 PDF + parties
3. Send folder: `POST /api/folders/sendDraftFolder`
4. Get activity: `GET /api/folders/viewActivityHistory?folderId={id}`

**Critical notes:**
- eSign token endpoint is form-encoded (JSON returns 415)
- `createfolder` is NOT idempotent — gate behind state check
- Use `inputType: "base64"` with `base64FileString` array
- `processTextTags: True` to auto-create signature fields from `${s:1:______}` tags
- Signer needs `FILL_FIELDS_AND_SIGN` permission
- Foxit uses "folder" not "envelope"

## Credit Model

- Developer: 500 credits/year (free)
- Startup: $1,750/year, 3,500 credits
- Business: $4,500/year, 150,000 credits
- Failed requests (4xx/5xx) do NOT consume credits

## Compliance

eSign API supports: eIDAS, ESIGN Act, UETA, HIPAA, GDPR, CCPA
PDF Services: SOC 2 Type II, HIPAA BAA
