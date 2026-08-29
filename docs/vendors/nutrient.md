# Nutrient DWS — Integration Reference (Master Doc)

All docs saved to `docs/vendors/nutrient_*.md`.

---

## Quick Reference: How to Use Each API

### 1. Extract (get structured fields)
```python
POST https://api.nutrient.io/extraction/extract
Authorization: Bearer pdf_live_...
Content-Type: multipart/form-data

file: @document.pdf
instructions: {
  "schema": { "type": "object", "properties": {...} },
  "parseConfig": { "mode": "understand" },
  "instructions": "Extract all procurement fields.",
  "options": { "includeCitations": true }
}

# Response: output.data (values), output.metadata (citations with bbox, confidence, match)
```

### 2. Parse (get full document structure)
```python
POST https://api.nutrient.io/extraction/parse
instructions: { "mode": "understand", "output": { "format": "spatial" } }

# Response: output.elements[] with type, text, bounds, confidence, page
```

### 3. OCR (make scans searchable)
```python
POST https://api.nutrient.io/processor/ocr
file: @scanned.pdf
data: { "language": "english" }

# Returns: searchable PDF
```

### 4. Redact (remove PII)
```python
POST https://api.nutrient.io/processor/redact
file: @document.pdf
data: {
  "strategy": "text",
  "strategyOptions": { "text": "SSN", "caseSensitive": false },
  "redactionState": "apply"
}

# Returns: redacted PDF
```

### 5. Generate PDF
```python
POST https://api.nutrient.io/processor/generate_pdf
html: @approval_memo.html

# Returns: PDF file
```

### 6. Convert to PDF
```python
POST https://api.nutrient.io/processor/convert_to_pdf
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Body: <binary docx>

# Returns: PDF file
```

### 7. Sign
```python
POST https://api.nutrient.io/sign
file: @document.pdf

# Returns: signed PDF
```

### 8. Validate PDF/A
```python
POST https://api.nutrient.io/validate_pdfa
file: @document.pdf

# Returns: compliance report JSON
```

---

## Key Integration Details

### Confidence Routing (from citations docs)

```python
# Route by match label
if match in ("fuzzy_match", "not_found"):
    route_to_human_review()

# Route by confidence score
if confidence < 0.7:
    route_to_human_review()

# Route by confidence components
if confidenceComponents.get("groundingScore", 1) < 0.5:
    route_to_human_review()
```

### Mode Selection (from modes docs)

- **Born-digital PDFs** → `text` mode (1 credit, fastest)
- **Scanned docs, simple layout** → `structure` mode (1.5 credits)
- **Forms, invoices, key-value** → `understand` mode (9 credits, DEFAULT)
- **Degraded scans, cursive handwriting** → `agentic` mode (18 credits)

### Schema Best Practices (from schema docs)

- Root must be `type: "object"`
- Use `description` on every field — guides the extraction model
- Use `required` for fields that must always appear
- Max 500 fields, 5 levels nesting, 32KB schema size
- Don't use `$ref`, `allOf`, `additionalProperties`

### Error Handling (from errors docs)

- 401 → check Bearer token format
- 402 → insufficient credits
- 413 → file too large (max 150MB)
- 429 → rate limit, exponential backoff
- 500/503 → retry, include requestId in support contact
