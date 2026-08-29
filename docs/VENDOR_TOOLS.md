# ProofDesk — Vendor MCP Servers & SDKs

All tools cloned to `proofdesk/vendor/`. Each has its own venv/deps.

---

## Installed Tools

| Vendor | Location | Type | Tools | Auth Required |
|--------|----------|------|-------|---------------|
| **Foxit PDF API MCP** | `vendor/foxit-pdf-api-mcp-server/python/` | Python (FastMCP) | 32 PDF tools | `FOXIT_CLOUD_API_CLIENT_ID` + `SECRET` |
| **SerpApi MCP** | `vendor/serpapi-mcp/` | Python (FastMCP) | 1 search tool + resources | `SERPAPI_API_KEY` |
| **Xano Developer MCP** | `vendor/xano-developer-mcp/` | TypeScript (MCP SDK) | 7 tools (docs, validation, knowledge) | None (local docs only) |
| **Xano CLI** | Global npm install | CLI | Workspace/function management | Browser OAuth via `xano login` |
| **name.com MCP** | `vendor/namecom-mcp/` | TypeScript (MCP SDK) | Auto-generated from OpenAPI | `NAME_USERNAME` + `NAME_TOKEN` |
| **Bruno CLI** | Global npm install | CLI | API collection runner | None (local collections) |

---

## Quick Reference

### Foxit PDF MCP (32 tools)
```bash
export FOXIT_CLOUD_API_HOST="https://na1.fusion.foxit.com/pdf-services"
export FOXIT_CLOUD_API_CLIENT_ID="..."
export FOXIT_CLOUD_API_CLIENT_SECRET="..."

cd vendor/foxit-pdf-api-mcp-server/python/foxit-pdf-api-mcp-server
.venv/bin/python -m foxit_pdf_api_mcp_server.main  # stdio
```

**Key tools:** `upload_document`, `pdf_merge`, `pdf_compress`, `pdf_split`, `pdf_from_word`, `pdf_to_word`, `pdf_structural_analysis`, `pdf_compare`, `pdf_ocr`, `download_document`

### SerpApi MCP (1 tool + resources)
```bash
export SERPAPI_API_KEY="..."

cd vendor/serpapi-mcp
.venv/bin/python -m src.server  # stdio or http
```

**Tool:** `search` — unified search across Google, Bing, YouTube, eBay, etc.
**Resources:** `serpapi://engines` (list), `serpapi://engines/{name}` (per-engine params)

### Xano Developer MCP (7 tools)
```bash
cd vendor/xano-developer-mcp
node dist/index.js  # stdio
```

**Tools:** `xano_validate_xanoscript`, `xano_xanoscript_docs`, `xano_meta_api_docs`, `xano_cli_docs`, `xano_knowledge_get`, `xano_knowledge_list`, `xano_version`

**Xano CLI:**
```bash
xano login          # browser OAuth
xano workspace list  # list workspaces
```

### name.com MCP (auto-generated tools)
```bash
export NAME_USERNAME="..."
export NAME_TOKEN="..."
export NAME_API_URL="https://mcp.dev.name.com"  # test env

cd vendor/namecom-mcp
node dist/index.js  # stdio
```

**Tools:** auto-generated for all name.com API endpoints (domain search, registration, DNS, etc.)

### Bruno CLI
```bash
bru --version
bru run /path/to/collection --env local
```

---

## What's NOT Available as MCP/SDK

| Sponsor | Status |
|---------|--------|
| **Doctavian** | REST API only, no MCP server. Register at portal.doctavian.com for API key. Docs at developers.doctavian.com |
| **Perfect Corp** | AR/AI platform, not relevant to ProofDesk |
| **Kong** | MCP exists but deprecated (use Konnect remote MCP). Not relevant to ProofDesk |
| **WunderGraph** | GraphQL federation MCP, not relevant to ProofDesk |

---

## Doctavian Integration Notes

Doctavian is a REST API, not an MCP server. To integrate:

1. Register at https://portal.doctavian.com/trial (free trial)
2. Get API credentials
3. Use the REST API directly: `POST https://api.doctavian.com/v1/generate`
4. The existing `src/providers/doctavian.py` already has the HTTP client code — just needs the API key

**API surface:**
- Document Generation: templates + data → PDF/DOCX/XLSX
- Digital Signatures: envelopes, recipients, fields, audit trail
- OpenAPI spec available at developers.doctavian.com/openapi/latest
