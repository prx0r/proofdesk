# Nutrient DWS — 20 Acceptance Gates

**Target:** 18/20 minimum. Items 1-9 should all be TRUE first.

---

* [ ] **1. CORE DWS DEPENDENCY** — Removing Nutrient DWS breaks a core ProofDesk workflow rather than merely removing an optional feature.
* [ ] **2. REAL API EXECUTION** — The submitted build makes a real Nutrient DWS API/SDK/Viewer call against an actual document.
* [ ] **3. REAL BUSINESS PROBLEM** — The demo contains a concrete document error, discrepancy, compliance issue, or costly decision rather than generic summarization.
* [ ] **4. END-TO-END RESULT** — The demo begins with raw documents and ends with a usable reviewed business output.
* [ ] **5. SOURCE-GROUNDED FINDINGS** — Every consequential extracted fact shown to the reviewer can be traced to a page/location in the original source.
* [ ] **6. UNCERTAINTY IS EXPLICIT** — Extracted or inferred values carry confidence/uncertainty information rather than being presented as unquestionably correct.
* [ ] **7. HUMAN EXCEPTION GATE** — At least one uncertain/high-impact case is deliberately routed to a human instead of autonomously approved.
* [ ] **8. AUDITABILITY** — The system records what document/data/decision produced the final action and this history can be inspected.
* [ ] **9. REPRODUCIBLE PIPELINE** — Running the same fixed document case through deterministic document stages produces the same structured intermediate results.
* [ ] **10. MULTI-DOCUMENT REASONING** — ProofDesk compares information across at least two documents rather than operating only on one isolated PDF.
* [ ] **11. DWS ADVANTAGE IS VISIBLE** — The demo visibly uses a capability such as structured extraction, coordinates, confidence, Viewer review, redaction, conversion, or signing that a plain LLM call does not provide.
* [ ] **12. FAILURE CASE EXISTS** — At least one deliberately difficult/ambiguous case is tested and routed safely rather than silently producing an answer.
* [ ] **13. REVIEWER CAN CORRECT AI** — A human can override/correct the machine's proposed interpretation before an irreversible downstream action.
* [ ] **14. EVIDENCE SURVIVES THE PIPELINE** — The generated decision/document can still be traced backward to the evidence that justified it.
* [ ] **15. MEASURED EVALUATION** — ProofDesk is run against a frozen test set with at least one objective metric such as discrepancy recall, false positives, extraction correctness, or escalation precision.
* [ ] **16. MULTIPLE REALISTIC CASES** — The system is demonstrated/tested on multiple document packets rather than a single hand-crafted happy path.
* [ ] **17. REALISTIC REGULATED/CONTROLLED SETTING** — The chosen procurement/compliance workflow has an understandable reason why mistakes matter.
* [ ] **18. STARTUP FEASIBILITY** — A judge can identify the business user, existing manual workflow being replaced, and economic reason to buy it.
* [ ] **19. REPRODUCIBLE SETUP** — The submitted repository/shared project contains enough setup instructions for the principal workflow to be reproduced.
* [ ] **20. 30-SECOND EXPLANATION** — A judge can understand what ProofDesk does, what goes wrong without it, and why Nutrient matters within the first 30 seconds.

---

**Status:** ___/20 TRUE

**Critical path:** Gates 1-9 must all be TRUE before polishing anything else.
