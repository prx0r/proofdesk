# Nutrient DWS — Citations & Confidence (Complete Reference)

Source: https://www.nutrient.io/guides/dws-data-extraction/extract/citations-and-confidence/

---

## Citation Structure

`output.metadata` mirrors `output.data`. Each scalar field maps to a citation object.

```json
{
  "output": {
    "data": { "invoice_number": "INV-2024-0042", "total_amount": 1547.5 },
    "metadata": {
      "invoice_number": {
        "bbox": { "x": 878, "y": 268, "width": 82, "height": 25 },
        "match": "id_match",
        "confidence": 0.93,
        "pageIndex": 0,
        "pageNumber": 1,
        "source_bboxes": [{ "bbox": {...}, "block_id": "c5", "pageIndex": 0, "pageNumber": 1 }]
      }
    }
  }
}
```

## Citation Fields

| Field | Description |
|-------|-------------|
| `bbox` | Bounding box {x, y, width, height} on the page |
| `match` | How the API located the value (see match labels) |
| `confidence` | Composite score 0-1 (relative, not probability) |
| `confidenceComponents` | Per-signal breakdown: probabilityScore, marginScore, groundingScore, formatScore |
| `recognitionScore` | OCR confidence for scanned content |
| `pageIndex` | Zero-based page index |
| `pageNumber` | One-based page number |
| `source_bboxes` | Source regions with block_id and page reference |

## Match Labels

| Label | Meaning | Action |
|-------|---------|--------|
| `id_match` | Exact match to single source block | High confidence |
| `id_match_multiblock` | Matched across multiple blocks | Medium confidence |
| `id_match_partial` | Resolved some but not all blocks | Review recommended |
| `fuzzy_match` | Close but not identical to source | Route to human review |
| `not_found` | Couldn't ground to source location | Route to human review |

**Key insight:** Use `match` for review routing. `fuzzy_match` or `not_found` → human review.

## Confidence Interpretation

- Score is **relative, uncalibrated** (0-1). Higher = more confident.
- **NOT a probability or percentage.** Don't present as one.
- Absence of confidence = "no score available", not low confidence.
- `confidenceComponents` breakdown:
  - `probabilityScore` — model token-probability signal
  - `marginScore` — margin between top candidate and alternatives
  - `groundingScore` — strength of grounding to source location
  - `formatScore` — conformity to declared schema type

## Review Routing Pattern

```python
def fields_needing_review(data, metadata):
    flagged = []
    for field, citation in metadata.items():
        if not isinstance(citation, dict):
            continue
        match = citation.get("match")
        confidence = citation.get("confidence")
        if match in ("fuzzy_match", "not_found"):
            flagged.append(field)
        elif confidence is not None and confidence < 0.7:
            flagged.append(field)
    return flagged
```

## Coordinate Space

- Top-left origin: (x, y) = top-left corner
- x increases right, y increases downward
- Units depend on page dimensions (render-space pixels when width/height available)
- Scale against page's width/height, don't assume fixed units
