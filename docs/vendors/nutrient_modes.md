# Nutrient DWS — Processing Modes (Complete Reference)

Source: https://www.nutrient.io/guides/dws-data-extraction/parsing/processing-modes/

---

## Mode Comparison

| | text | structure | understand | agentic |
|---|---|---|---|---|
| **Cost/page** | 1 credit | 1.5 credits | 9 credits | 18 credits |
| **Speed** | Fastest | Fast | Slower | Slowest |
| **OCR** | No | Yes | Yes | Yes |
| **AI augmentation** | No | No | Yes | Hybrid (AI+VLM) |
| **Layout analysis** | No | Basic | Full AI-augmented | Hybrid |
| **Word-level data** | — | Yes (spatial) | Yes (spatial) | Yes (spatial) |
| **Output formats** | Markdown only | Spatial, Markdown | Spatial, Markdown | Spatial, Markdown |

## Extract Mode Costs (includes parse component)

| Mode | Credits/page |
|------|-------------|
| Text | 7 |
| Structure | 7.5 |
| Understand | 15 |
| Agentic | 24 |

## Mode Selection Guide

1. **Only need Markdown from born-digital docs?** → `text` mode (1 credit, fastest)
2. **Need Markdown from scans/images?** → `structure` mode with OCR
3. **Extracting forms, key-value pairs, invoices?** → `understand` mode (default)
4. **Need image descriptions or cursive handwriting?** → `agentic` mode (VLM-enhanced)

## When to Use Each

### text
- RAG ingestion, search indexing, content migration
- Born-digital documents where text is enough
- High-throughput, cost-sensitive pipelines

### structure
- Scanned documents needing OCR
- Simple layouts where cost matters
- OCR-backed Markdown from scans
- **NOT for forms/key-value** — use `understand` for that

### understand (DEFAULT)
- Complex documents with tables, multicolumn, nested structures
- Invoice and form processing
- Key-value extraction (keyValueRegion.pairs)
- Formulas, tables, printed handwriting
- Any workflow where accuracy > cost

### agentic
- Embedded images, charts, diagrams (need alt descriptions)
- Degraded scans, faxes, low-quality images
- Cursive/connected/freeform handwriting
- When `understand` produces visible gaps

## Language Hints

```json
{
  "parseConfig": {
    "mode": "understand",
    "options": { "language": ["eng", "deu"] }
  }
}
```

Accepts: lowercase name ("english"), ISO 639-2 ("eng"), array, or "+"-joined string.

## Handwriting

- **Printed-style** (separated letters, short entries) → `understand` handles well
- **Cursive/connected/freeform** → `agentic` required (VLM interprets whole words)

Even in agentic mode, ambiguous words can be confident but wrong. Check confidence scores for high-stakes fields.
