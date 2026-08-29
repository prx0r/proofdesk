# Doctavian API Reference

Source: https://developers.doctavian.com/
OpenAPI spec: https://developers.doctavian.com/openapi/latest/resources/doctavian-openapi-specification.json
AI docs: https://developers.doctavian.com/openapi/llms.txt

---

## Base URL
```
https://api.doctavian.com
```

## Auth
- Bearer token (OAuth2) or API key header/query
- Get token: POST /v1/common/service/token

## Two API Surfaces

### 1. Document Generation
Templates + data → PDF, DOCX, XLSX, PPTX

| Resource | Endpoints |
|----------|-----------|
| **Document Solution** | CRUD — named pipeline (template + data source + settings) |
| **Document Template** | CRUD — Word/Excel/PPT template with elements + expressions |
| **Data Source** | CRUD — GraphQL queries or embedded JSON |
| **Document** | Create, Generate, Generate Async, Merge, Merge Async, Manage, Manage Async, Upload, Download, Delete, List, Get, Update, Reference |
| **Document Request** | CRUD — generation request tracking |
| **Option Value** | CRUD — template option values |
| **Template** | Upload |

**Key flow:**
1. Create/upload a template (Word doc with `{{dynamic_tags}}`)
2. Create a data source (JSON payload or GraphQL query)
3. Create a Document Solution linking template + data source
4. Call Document Generate → get finished PDF/DOCX

### 2. Digital Signatures
Envelopes + recipients + fields → signed document + audit trail

| Resource | Endpoints |
|----------|-----------|
| **Envelope** | Create, Send, Sign, Cancel, Decline, Delete, Edit, Get, List, Count, Check, Reassign, Resend, Restore, Open, Update |
| **Document** | Upload, Download, Get, Manage (DOCX→PDF), Comment, Retrieve |
| **Signature** | Create, Get, List, Update, Delete |
| **Template** | CRUD + Create From Template |
| **Folder** | CRUD |
| **Attachment** | Upload, Download |
| **AuditTrail** | Get, Download |
| **MFA** | Initiate, Verify |
| **Comment** | Document Comment |
| **Content** | Envelope Update |

**Key flow:**
1. Create envelope with documents + recipients
2. Place signature fields (pixel precision)
3. Send envelope → recipients sign
4. Track status + download audit trail

## For AI Agents

Fetch `/openapi/llms.txt` for site map, append `.md` to any URL for Markdown.

## Registration

Free trial: https://portal.doctavian.com/trial
Contact: hello@doctavian.com
