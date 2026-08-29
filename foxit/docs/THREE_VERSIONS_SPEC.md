# Three Versions of ProofDesk — Provider Interchangeable

**Date:** 2026-08-26
**Goal:** Show SignatureGate works with any provider

---

## VERSION 1: Foxit-First

### Architecture
```
Document → Foxit PDF Services (merge/compress)
        → Foxit Document Generation (generate PDFs)
        → SignatureGate (risk-adaptive thresholds)
        → Foxit eSign (real signing)
        → Audit Trail (hash chain + Merkle)
```

### Providers Used
- **Foxit PDF Services**: Merge, compress, convert
- **Foxit Document Generation**: Generate PDFs from data
- **Foxit eSign**: Send for signature, track status
- **Nutrient**: Extraction only (for confidence scoring)

### What's Different
- All PDF operations go through Foxit
- Document generation uses Foxit's template engine
- Real eSign workflow (not simulated)
- Webhooks for signing status updates

### Implementation Steps
1. Use existing `foxit.py` for PDF Services
2. Add `foxit_docgen.py` for Document Generation API
3. Add `foxit_embed.py` for PDF Embed API
4. Add `foxit_esign_real.py` for eSign API
5. Wire into orchestrator

### Files to Create
- `src/providers/foxit_docgen.py` — Document Generation client
- `src/providers/foxit_embed.py` — PDF Embed client
- `src/providers/foxit_esign_real.py` — eSign client (already exists)

---

## VERSION 2: Nutrient-First

### Architecture
```
Document → Nutrient Data Extraction (primary)
        → Nutrient DWS Viewer (embedded)
        → SignatureGate (risk-adaptive thresholds)
        → Foxit PDF Services (reversible ops only)
        → Audit Trail (hash chain + Merkle)
```

### Providers Used
- **Nutrient Data Extraction**: Primary extraction
- **Nutrient DWS Viewer**: Embedded PDF viewer
- **Foxit PDF Services**: Merge, compress (reversible only)
- **Doctavian**: Template generation

### What's Different
- Nutrient is the primary extraction engine
- DWS Viewer embedded in dashboard
- Click-to-source: click exception → see source in viewer
- Foxit only used for reversible operations

### Implementation Steps
1. Use existing `nutrient.py` for extraction
2. Add `nutrient_viewer.py` for DWS Viewer integration
3. Add click-to-source functionality
4. Use Foxit only for merge/compress
5. Wire into orchestrator

### Files to Create
- `src/providers/nutrient_viewer.py` — DWS Viewer integration
- `src/providers/nutrient_click.py` — Click-to-source functionality

---

## VERSION 3: Doctavian-First

### Architecture
```
Document → Doctavian Document Generation (primary)
        → Doctavian Digital Signatures (real signing)
        → SignatureGate (risk-adaptive thresholds)
        → Nutrient Extraction (for confidence)
        → Audit Trail (hash chain + Merkle)
```

### Providers Used
- **Doctavian Document Generation**: Primary generation
- **Doctavian Digital Signatures**: Real signing
- **Nutrient**: Extraction only (for confidence)
- **Foxit**: PDF manipulation only

### What's Different
- Doctavian handles generation AND signing
- Template branching drives the entire flow
- Real Doctavian signatures (not simulated)
- Doctavian audit trail captured

### Implementation Steps
1. Use existing `doctavian.py` for generation
2. Add `doctavian_sign.py` for Digital Signatures
3. Capture Doctavian audit trail events
4. Use Nutrient only for extraction
5. Wire into orchestrator

### Files to Create
- `src/providers/doctavian_sign.py` — Digital Signatures client
- `src/providers/doctavian_audit.py` — Audit trail capture

---

## VERSION COMPARISON

| Feature | Foxit-First | Nutrient-First | Doctavian-First |
|---------|-------------|----------------|-----------------|
| **Primary Extraction** | Nutrient | Nutrient | Nutrient |
| **Primary Generation** | Foxit DocGen | Doctavian | Doctavian |
| **Primary Signing** | Foxit eSign | Foxit PDF | Doctavian |
| **Viewer** | Foxit Embed | Nutrient Viewer | Doctavian |
| **PDF Operations** | Foxit PDF | Foxit PDF | Foxit PDF |
| **Audit Trail** | ProofDesk | ProofDesk | Doctavian + ProofDesk |

---

## THE HACKATHON STORY

"We built three versions of ProofDesk, each optimized for a different provider. The SignatureGate logic is identical across all three — only the providers change. This proves our system is provider-agnostic and can work with any document processing stack."

### Version 1: "Foxit handles everything — merge, generate, sign"
### Version 2: "Nutrient extracts, Foxit manipulates, we decide"
### Version 3: "Doctavian generates and signs, we verify"

---

## IMPLEMENTATION PRIORITY

1. **Version 1 (Foxit-First)** — Most complete, uses all Foxit APIs
2. **Version 3 (Doctavian-First)** — Shows generation + signing
3. **Version 2 (Nutrient-First)** — Shows extraction focus

---

## WHAT WE NEED FOR EACH

### Version 1: Foxit-First
- [ ] Foxit eSign API keys (from developer-api.foxit.com)
- [ ] Foxit Document Generation API implementation
- [ ] Foxit PDF Embed API implementation
- [ ] End-to-end test with real eSign

### Version 2: Nutrient-First
- [ ] Nutrient DWS Viewer integration
- [ ] Click-to-source functionality
- [ ] End-to-end test with viewer

### Version 3: Doctavian-First
- [ ] Doctavian Digital Signatures implementation
- [ ] Doctavian audit trail capture
- [ ] End-to-end test with real signatures
