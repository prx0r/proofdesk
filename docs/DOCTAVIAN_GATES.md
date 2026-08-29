# Doctavian — 20 Acceptance Gates

**Target:** 17/20 minimum. Items 1-5 are sacred.

---

* [ ] **1. REAL DOCTAVIAN GENERATION CALL** — The agent actually calls Doctavian's generation API and receives a generated document.
* [ ] **2. DOCTAVIAN SHAPES THE RESULT** — Replacing the Doctavian generation stage with a no-op prevents production of the final formatted document.
* [ ] **3. COMPLEX STRUCTURED INPUT** — The input contains multiple meaningful fields/collections/conditions rather than only swapping a name/date into a static template.
* [ ] **4. REAL-WORLD PROBLEM** — The structured input represents an actual business-document problem such as procurement, contracts, proposals, regulatory forms, or approvals.
* [ ] **5. REPEATABLE CORRECTNESS** — Multiple different inputs through the same template produce predictably appropriate documents without manually modifying the template between runs.
* [ ] **6. CONDITIONAL LOGIC** — At least one data condition changes which section/clause/content appears in the generated document.
* [ ] **7. COLLECTION/LOOP LOGIC** — At least one variable-length collection such as line items, obligations, approvers, or milestones is rendered dynamically.
* [ ] **8. CALCULATED OUTPUT** — At least one final document value is calculated or derived from input data rather than copied verbatim.
* [ ] **9. AI → STRUCTURED DATA → TEMPLATE** — The AI agent produces/normalizes structured data that Doctavian subsequently turns into the authoritative document.
* [ ] **10. OUTPUT IS A REAL DOCUMENT** — The demo retrieves and opens the actual generated PDF/DOCX/etc., rather than showing only JSON or a mocked preview.
* [ ] **11. DIFFERENT INPUTS PRODUCE VISIBLY DIFFERENT DOCUMENTS** — The demo can run Case A and Case B and visibly show appropriate template branching.
* [ ] **12. INVALID DATA IS CAUGHT** — Malformed/missing required input causes an explicit validation/review state rather than silently generating a misleading document.
* [ ] **13. HUMAN APPROVAL PRECEDES LEGAL COMMITMENT** — Consequential AI-generated decisions can be reviewed before the resulting document becomes binding or externally committed.
* [ ] **14. DOCUMENT PROVENANCE EXISTS** — The system stores which structured payload/template/run produced the final artifact.
* [ ] **15. EVALUATION EXISTS** — A frozen test set automatically checks at least some expected clauses, totals, fields, or conditions in generated outputs.
* [ ] **16. SIGNATURE PATH WORKS WHEN RELEVANT** — A workflow claiming to end in agreement/signature actually progresses from generated document toward a real signing workflow.
* [ ] **17. DOCTAVIAN'S ROLE IS EXPLICIT** — The Devpost submission includes the requested one-line explanation of where Doctavian did the real work and why.
* [ ] **18. REPOSITORY IS REPRODUCIBLE** — The public/shared repo contains setup instructions sufficient to understand/run the integration.
* [ ] **19. VIDEO PROVES IT** — The 2–4 minute video actually shows the generation call and resulting document rather than describing them with slides.
* [ ] **20. COMMERCIAL STORY** — The judge can identify who repeatedly generates these documents today and why automating that process saves money/time/risk.

---

**Status:** ___/20 TRUE

**Critical path:** Gates 1-5 are non-negotiable. Doctavian explicitly requires a real API call producing a real document.
