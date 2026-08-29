# Nutrient DWS Mode Comparison — Procurement Request PDF

| Mode | Facts | Latency | Notes |
|------|-------|---------|-------|
| text | ERROR | - | Can't extract with text mode (Markdown only) |
| structure | 4 | 2.3s | Fastest, all fields extracted |
| understand | 4 | 3.4s | Default, same result as structure |
| agentic | 4 | 3.4s | Same as understand on clean PDFs |

**Recommendation:** Use `structure` for clean PDFs (2x faster), `understand` for complex/scanned docs, `agentic` for degraded scans with handwriting.
