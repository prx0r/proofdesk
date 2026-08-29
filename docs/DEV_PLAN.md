# ProofDesk — Dev Plan: Win All Three Sponsor Challenges

**Strategy:** One monolith entry. One procurement workflow. Three sponsor stories.
**Deadline:** Sep 3, 2026 @ 10:00 AM PT (9 days)

---

## Phase 0: Unwire the Stubs (30 min)

The single biggest change. The real provider code exists but is dead code.

**Files to change:**
- `src/engine/orchestrator.py` — swap imports from `stubs` to real providers
- `requirements.txt` — add `httpx`
- `src/providers/nutrient.py:112` — fix PDF bytes bug (sends text instead of PDF)
- `src/providers/foxit.py:242-279` — fix sync convenience wrappers to call async functions

**Verification:** Run `python3 tests/test_all.py` — should still pass (tests use stubs via golden fixture, unaffected by orchestrator import change).

---

## Phase 1: Real PDFs + Nutrient (Day 1-2)

### 1a. Create procurement PDF fixtures

Create 4 real PDF files for the Northstar Data Systems scenario:
- `data/procurement_request.pdf`
- `data/vendor_quote.pdf`
- `data/certificate_insurance.pdf`
- `data/security_questionnaire.pdf`

Use `fpdf2` or `reportlab` to generate them from the existing text fixtures in `golden_fixture.py`. Each PDF should look like a real business document (headers, logos, line items, signatures).

### 1b. Wire Nutrient DWS

- Fix `nutrient.py` to accept PDF bytes, not text
- Add file upload endpoint to `app.py`: `POST /v1/cases/{id}/documents` with multipart upload
- Wire orchestrator to call real Nutrient extraction when `NUTRIENT_API_KEY` is set
- Test against real PDFs

### 1c. Add Nutrient Viewer embed

- Embed DWS Viewer in frontend Screen B (Evidence Board)
- Click-to-source: clicking a fact opens the PDF at its source page/bbox
- This is a hard Nutrient gate requirement

**Verification:** Upload real PDFs → Nutrient extracts facts with coordinates → click source in Viewer.

---

## Phase 2: Doctavian Integration (Day 2-3)

### 2a. Get Doctavian API key

Contact `hello@doctavian.com` to register for hackathon credentials.

### 2b. Wire Doctavian generation

- Wire orchestrator to call `doctavian.generate_document()` when `DOCTAVIAN_API_KEY` is set
- Ensure the `APPROVAL_MEMO_TEMPLATE` schema is compatible with Doctavian's actual API format
- Test: change fixture data → document branches/loops/totals change correctly

### 2c. Verify template complexity

Doctavian judges want to see:
- Branch: approve / conditional approve / reject
- Loop: quote line items
- Calculation: totals
- Conditional clause: insurance gap obligation

The template already defines all of these. Verify they produce correct output against real API.

**Verification:** Change insurance expiry → document changes conditional clause. Add line items → table expands. Different approval status → different branch.

---

## Phase 3: Foxit Integration (Day 3-4)

### 3a. Get Foxit API keys

Register for:
- Foxit PDF Services API (`FOXIT_CLOUD_API_CLIENT_ID` + `SECRET`)
- Foxit eSign API (`FOXIT_ESIGN_CLIENT_ID` + `SECRET`)

Contact: `theodore_castro@foxitsoftware.com`

### 3b. Wire Foxit PDF Services

- Fix `foxit.py` convenience wrappers to call real async functions
- Wire orchestrator to call real PDF merge/compress when keys are set
- Use Foxit MCP server if possible, direct API if not

### 3c. Wire Foxit eSign

- Ensure OAuth2 token flow works
- Create signing folder with real PDF
- Send to real signer email
- Handle webhook/callback for signature completion

### 3d. Authority boundary demo

- Show premature signature attempt → SignatureGate denies
- Show approved path → eSign succeeds
- This is the core Foxit story

**Verification:** Agent prepares PDF via Foxit MCP → SignatureGate checks → eSign sends to real person → person signs → signed document returned.

---

## Phase 4: Frontend Polish (Day 4-5)

The SPA already has 4 screens. Enhance:

### 4a. Screen A — Case / Prompt
- Add file upload for real PDFs
- Show uploaded document thumbnails
- "Run ProofDesk" button

### 4b. Screen B — Evidence Board
- Embed Nutrient DWS Viewer for source-jump
- Three columns: source facts, deterministic checks, exceptions
- Confidence badges with color coding
- Click source chip → Viewer opens at source context

### 4c. Screen C — Human Decision
- Only unresolved exceptions
- Show requirement, source value, rule result, evidence
- Actions: reject / conditional accept / corrected with evidence

### 4d. Screen D — Execution Timeline
- Expandable receipt rows per pipeline stage
- Each row shows provider ID, timestamp, hash
- Final receipt with full audit trail

---

## Phase 5: Evaluation Fixtures (Day 5-6)

### 5a. Create 10-20 adversarial procurement packets

- Different vendor names (with entity variations)
- Different discrepancy types (payment terms, dates, amounts, insurance gaps)
- Edge cases: missing fields, ambiguous dates, multi-currency
- Some with no discrepancies (should pass clean)

### 5b. Frozen evaluation

Run all fixtures through the pipeline. Measure:
- Discrepancy recall (did we catch the real problem?)
- False positives (did we flag non-problems?)
- Unsafe autonomous approvals (must be 0)
- Extraction correctness

Print results as a table. This aligns with Nutrient's engineering culture of deterministic benchmarks.

---

## Phase 6: Demo Video + Submission (Day 7-9)

### 6a. Record 2-4 minute demo video

Script (from PROOFDESK_CANONICAL.md §17):

```
0:00-0:20  "Agents can read and draft documents. The dangerous part
            is letting uncertain model output become a signed commitment."

0:20-0:55  [Nutrient] Show extraction. Click insurance expiry → source evidence.

0:55-1:20  [Evidence gate] Quote arithmetic ✓. Entity normalization ✓.
            Insurance coverage ✕. Attempt irreversible → blocked.

1:20-1:45  [Human] Review source. Select conditional approval.

1:45-2:15  [Doctavian] Generate approval memo. Show line items, total,
            conditional clause, resolution appendix.

2:15-2:40  [Foxit] Prepare PDF. SignatureGate green. eSign → human.

2:40-3:00  [Receipt] Source → fact → failed rule → resolution →
            approved hash → generated hash → signature.

Close: "AI does the reversible work. Evidence and people control
        the irreversible work."
```

### 6b. Write Devpost submission

- Project name + one-line pitch
- Public repo with setup instructions
- Demo video link
- One line per sponsor: where they did the real work and why
- Build story: what software replaced, why chosen, which AI tools used

### 6c. Optional: SerpApi integration ($3k prize)

Easiest add. Wire `serpapi.py` to verify extracted vendor names against web search before human review. Adds 5 lines to the pipeline, earns $3k.

---

## Files to Change (ordered by priority)

| Priority | File | Change |
|----------|------|--------|
| 1 | `src/engine/orchestrator.py` | Swap stubs imports → real providers |
| 2 | `requirements.txt` | Add httpx, fpdf2 |
| 3 | `src/providers/nutrient.py:112` | Fix PDF bytes bug |
| 4 | `src/providers/foxit.py:242-279` | Fix sync wrappers |
| 5 | `src/api/app.py` | Add file upload endpoint |
| 6 | `src/static/index.html` | Add file upload UI, Viewer embed |
| 7 | `data/*.pdf` | Create 4 real procurement PDFs |
| 8 | `tests/test_all.py` | Add real-provider integration tests |
| 9 | `docs/NUTRIENT_GATES.md` | Create acceptance checklist |
| 10 | `docs/DOCTAVIAN_GATES.md` | Create acceptance checklist |
| 11 | `docs/FOXIT_GATES.md` | Create acceptance checklist |

---

## API Keys Needed

| Provider | How to get | Contact |
|----------|-----------|---------|
| Nutrient DWS | Already have (HANDOVER.md) | — |
| Doctavian | Register for hackathon | hello@doctavian.com |
| Foxit PDF + eSign | Register for hackathon | theodore_castro@foxitsoftware.com |
| SerpApi | Already have (HANDOVER.md) | alaa@serpapi.com |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Doctavian API incompatible with template schema | High | Adapt template format to match their API; local fallback works |
| Foxit eSign requires webhooks for callback | Medium | Poll activity endpoint instead; acceptable for demo |
| Nutrient DWS rejects text-based "PDFs" | High | Create real PDFs with fpdf2 in Phase 1a |
| Demo video too long / confusing | Medium | Follow the 3-minute script from canonical spec |
| No GPU for OCR (Tesseract) | Low | Not needed — Nutrient DWS replaces OCR |

---

## Success Criteria

At submission, every gate in the three checklists should be TRUE:

- **Nutrient:** 18/20 minimum (items 1-9 all TRUE)
- **Doctavian:** 17/20 minimum (items 1-5 all TRUE)
- **Foxit:** 18/20 minimum (items 1-10 all TRUE)
- **Overall:** Demo video works, repo is reproducible, story is coherent
