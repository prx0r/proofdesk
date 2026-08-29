# Nutrient DWS — Full API Surface

Source: https://www.nutrient.io/api/
Fetched: 2026-08-25

---

## 8 APIs Available

| # | API | Endpoint | Purpose |
|---|-----|----------|---------|
| 1 | **Data Extraction** | `POST /extraction/extract` | Extract structured JSON from documents with schema |
| 2 | **Data Parsing** | `POST /extraction/parse` | Full document structure as spatial JSON or Markdown |
| 3 | **PDF Generator** | `POST /processor/generate_pdf` | Create PDFs from HTML/templates |
| 4 | **Converter** | `POST /processor/convert_to_pdf` | Convert Word/Excel/PPT/HTML/images to PDF |
| 5 | **OCR** | `POST /processor/ocr` | Make scanned documents searchable |
| 6 | **Viewer** | Embedded JS SDK | Document viewing, annotation, form filling, collaboration |
| 7 | **Digital Signatures** | `POST /sign` | Add signing and approval flows |
| 8 | **Redaction** | `POST /processor/redact` | Find and remove sensitive data (names, SSNs, patterns) |
| 9 | **PDF/A Validation** | `POST /validate_pdfa` | Check PDF/A and PDF/UA compliance |

---

## API 1: Data Extraction (already tested)

**Endpoint:** `POST https://api.nutrient.io/extraction/extract`

```python
import json, requests

response = requests.post(
    "https://api.nutrient.io/extraction/extract",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("document.pdf", "rb")},
    data={"instructions": json.dumps({
        "schema": {"type": "object", "properties": {...}},
        "parseConfig": {"mode": "understand"},
        "instructions": "Extract all procurement fields."
    })}
)
# Returns: output.data (extracted values), output.metadata (citations with bbox, confidence, page)
```

**Modes:** text, structure, understand, agentic
**Free tier:** 5,000 credits/month

---

## API 2: Data Parsing (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/extraction/parse`

```python
response = requests.post(
    "https://api.nutrient.io/extraction/parse",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("document.pdf", "rb")},
    data={"instructions": json.dumps({
        "mode": "understand",
        "output": {"format": "spatial"}
    })}
)
# Returns: elements[] with type, text, bounds, confidence, page, readingOrder
```

**Use for:** Full document structure, not just specific fields. Good for understanding document layout.

---

## API 3: PDF Generator (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/processor/generate_pdf`

```python
response = requests.post(
    "https://api.nutrient.io/processor/generate_pdf",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"html": open("approval_memo.html", "rb")}
)
# Returns: PDF file
```

**Use for:** Generating the approval memo, compliance report, or any output document.

---

## API 4: Converter (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/processor/convert_to_pdf`

```python
response = requests.post(
    "https://api.nutrient.io/processor/convert_to_pdf",
    headers={"Authorization": f"Bearer {API_KEY}"},
    data=open("contract.docx", "rb"),
    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
# Returns: PDF file
```

**Use for:** Converting uploaded Word/Excel/PPT documents to PDF for processing.

---

## API 5: OCR (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/processor/ocr`

```python
response = requests.post(
    "https://api.nutrient.io/processor/ocr",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("scanned.pdf", "rb")},
    data={"data": json.dumps({"language": "english"})}
)
# Returns: searchable PDF
```

**Use for:** Making scanned documents extractable before running extraction.

---

## API 6: Viewer (new — not tested yet)

**Embed:**
```html
<script src="https://cdn.nutrient.io/viewer.js"></script>
<div id="viewer"></div>
<script>
NutrientViewer.load({
    container: "#viewer",
    session: "pdf_pub_live_5XyMAX7APEG6bj5uxJGrdoproYPYcCOhsFXwfWCy8nJ",
    document: "https://example.com/document.pdf"
});
</script>
```

**Use for:** Human review of extracted facts with source context. Click fact → jump to source in viewer.

---

## API 7: Digital Signatures (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/sign`

```python
response = requests.post(
    "https://api.nutrient.io/sign",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("approved_memo.pdf", "rb")}
)
# Returns: signed PDF
```

**Use for:** Digitally signing the final approval memo after human review.

---

## API 8: Redaction (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/processor/redact`

```python
response = requests.post(
    "https://api.nutrient.io/processor/redact",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("intake_form.pdf", "rb")},
    data={"data": json.dumps({
        "strategy": "text",
        "strategyOptions": {"text": "SSN", "caseSensitive": False},
        "redactionState": "apply"
    })}
)
# Returns: redacted PDF
```

**Use for:** Redacting PII before sharing documents externally.

---

## API 9: PDF/A Validation (new — not tested yet)

**Endpoint:** `POST https://api.nutrient.io/validate_pdfa`

```python
response = requests.post(
    "https://api.nutrient.io/validate_pdfa",
    headers={"Authorization": f"Bearer {API_KEY}"},
    files={"file": open("final_document.pdf", "rb")}
)
# Returns: compliance report
```

**Use for:** Validating that output documents meet regulatory compliance.

---

## The Nutrient Hackathon Pipeline (all 8 APIs)

```
UPLOAD DOCUMENTS
    ↓
[OCR] Make scans searchable
    ↓
[EXTRACTION] Extract structured fields with confidence + citations
    ↓
[PARSING] Get full document structure for cross-referencing
    ↓
FactMiner verification (SUPPORTED/REFUTED/CONFLICTING/INSUFFICIENT)
    ↓
[VIEWER] Human reviews uncertain facts with source context
    ↓
[REDACTION] Remove PII before external sharing
    ↓
[PDF GENERATOR] Generate approval memo from structured record
    ↓
[CONVERTER] Ensure output is PDF/A compliant format
    ↓
[PDF/A VALIDATION] Verify compliance
    ↓
[DIGITAL SIGNATURES] Sign the approved document
    ↓
AUDIT TRAIL (hash-linked, every step recorded)
```

This uses ALL 8 Nutrient APIs in a single pipeline. That's what wins.
