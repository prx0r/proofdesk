# ProofDesk Agent — Composable Skill Architecture

## The Idea

Instead of building separate pipelines per use case, build ONE agent with Nutrient-powered skills that can be composed intelligently.

```
USER: "Process these vendor documents"
        ↓
AGENT (brain)
  - Analyzes input documents
  - Determines document types
  - Selects skill chain
  - Routes uncertain cases to human
        ↓
SKILL CHAIN (executed in order)
  1. OCR (if scanned)
  2. Extract (get structured fields)
  3. Parse (get full structure)
  4. Verify (FactMiner 4-way verdict)
  5. Review (DWS Viewer for uncertain)
  6. Redact (PII removal if needed)
  7. Generate (PDF output)
  8. Validate (PDF/A compliance)
  9. Sign (digital signature)
        ↓
OUTPUT: Signed document + audit trail
```

## Skills (each wraps a Nutrient API + logic)

| Skill | Nutrient API | What It Does | Returns |
|-------|-------------|--------------|---------|
| `ocr` | `/processor/ocr` | Make scanned docs searchable | Searchable PDF |
| `extract` | `/extraction/extract` | Get structured fields with confidence | Facts + citations |
| `parse` | `/extraction/parse` | Get full document structure | Spatial elements |
| `verify` | (FactMiner) | 4-way verdict on each fact | SUPPORTED/REFUTED/CONFLICTING/INSUFFICIENT |
| `review` | Viewer API | Route uncertain facts to human | Human resolutions |
| `redact` | `/processor/redact` | Remove PII | Clean PDF |
| `generate` | `/processor/generate_pdf` | Create output document | PDF |
| `convert` | `/processor/convert_to_pdf` | Format conversion | PDF |
| `validate` | `/validate_pdfa` | Check compliance | Compliance report |
| `sign` | `/sign` | Digital signature | Signed PDF |
| `cross_check` | (logic) | Compare fields across documents | Discrepancies |
| `audit` | (logic) | Hash-linked event trail | Audit receipt |

## Use Cases as Skill Chains

### Procurement Onboarding
```
extract → extract → extract → extract  (4 docs)
  → cross_check (find insurance gap)
  → verify (4-way verdict per fact)
  → review (human resolves gap)
  → generate (approval memo)
  → sign (digital signature)
  → audit (full trail)
```

### Customer KYC
```
ocr → extract (ID)
  → extract (proof of address)
  → extract (bank statement)
  → verify (cross-check names, addresses)
  → review (low confidence → human)
  → redact (PII before storage)
  → generate (onboarding report)
  → audit
```

### Invoice → E-Invoice
```
extract (invoice fields)
  → verify (amounts, dates, tax IDs)
  → convert (to EU e-invoice format)
  → validate (PDF/A compliance)
  → sign (authenticate)
  → audit
```

### Trade Document Cross-Check
```
extract (invoice)
  → extract (bill of lading)
  → extract (certificate of origin)
  → cross_check (compare shipper, consignee, quantities)
  → verify (4-way verdict on each match)
  → review (mismatches → human)
  → generate (compliance report)
  → audit
```

### Mortgage Appraisal
```
extract (appraisal fields)
  → verify (value, condition, comparables)
  → review (low confidence → human)
  → generate (formatted appraisal report)
  → validate (PDF/A)
  → sign
  → audit
```

### PII Redaction
```
extract (identify PII fields)
  → redact (SSN, names, addresses, account numbers)
  → review (human confirms redactions)
  → sign (tamper-evident)
  → audit (proof of what was removed)
```

## Agent Brain (simple router)

```python
class NutrientAgent:
    def __init__(self):
        self.skills = {
            "ocr": OCRSkill(),
            "extract": ExtractSkill(),
            "parse": ParseSkill(),
            "verify": VerifySkill(),
            "review": ReviewSkill(),
            "redact": RedactSkill(),
            "generate": GenerateSkill(),
            "convert": ConvertSkill(),
            "validate": ValidateSkill(),
            "sign": SignSkill(),
            "cross_check": CrossCheckSkill(),
            "audit": AuditSkill(),
        }
    
    def process(self, documents, intent):
        # 1. Analyze documents
        doc_types = [self.analyze_doc(d) for d in documents]
        
        # 2. Select skill chain based on intent + doc types
        chain = self.select_chain(doc_types, intent)
        
        # 3. Execute chain
        context = {"documents": documents, "facts": [], "verdicts": []}
        for skill_name in chain:
            skill = self.skills[skill_name]
            result = skill.execute(context)
            context.update(result)
            
            # 4. If human review needed, pause and route
            if result.get("needs_human"):
                return {"status": "review_required", "context": context}
        
        return {"status": "complete", "context": context}
```

## Why This Wins

1. **One agent, all use cases** — not 6 separate apps
2. **Composable** — mix and match skills for any document workflow
3. **Uses ALL Nutrient APIs** — extraction, parsing, viewer, redaction, generation, conversion, signatures, compliance
4. **FactMiner integration** — 4-way verdict system for intelligent routing
5. **Auditable** — every skill call recorded in hash-linked trail
6. **Demo-friendly** — show the agent deciding which skills to use
7. **Extensible** — add new skills without changing the agent core

## What We Already Have

| Component | Status | Location |
|-----------|--------|----------|
| Extraction skill | ✅ Real API tested | `src/providers/nutrient.py` |
| Verification (FactMiner) | ✅ Architecture ready | `imported/factminer/` |
| State machine | ✅ 15 states, SignatureGate | `src/state/machine.py` |
| Reconciliation engine | ✅ 6 domains, 20+ rules | `src/engine/reconciliation.py` |
| Audit trail | ✅ Hash-linked events | `src/models/domain.py` |
| A/B test harness | ✅ 61 fields, 100% on synthetic | `tests/ab_test_nutrient.py` |

## What We Need to Build

| Component | Priority | Effort |
|-----------|----------|--------|
| OCR skill | High | 1 API call |
| Parse skill | High | 1 API call |
| Review skill (Viewer embed) | High | Frontend integration |
| Redact skill | High | 1 API call |
| Generate skill | High | 1 API call |
| Convert skill | Medium | 1 API call |
| Validate skill | Medium | 1 API call |
| Sign skill | Medium | 1 API call |
| Agent brain (router) | High | ~200 lines |
| Cross-check skill | High | Already exists in reconciliation |
| Audit skill | High | Already exists |
| Frontend (4 screens) | High | SPA with Viewer embed |
