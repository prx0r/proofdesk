# Foxit — 20 Acceptance Gates

**Target:** 18/20 minimum. Items 1-10 are the actual challenge.

---

* [ ] **1. PLAIN-PROMPT ENTRY** — A user can initiate the demonstrated workflow from a natural-language instruction rather than manually invoking each PDF operation.
* [ ] **2. REAL AGENT EXECUTION** — The model selects/executes document operations as part of completing the requested task rather than merely describing what a user should do.
* [ ] **3. FOXIT MCP USED FOR REVERSIBLE WORK** — At least one meaningful PDF operation is executed through Foxit's MCP/PDF Services tooling.
* [ ] **4. REAL FOXIT eSIGN API CALL** — The submitted workflow sends the prepared artifact into Foxit's actual eSign API rather than mocking the signing stage.
* [ ] **5. REAL HUMAN SIGNER** — A person actually receives/enters the signature workflow and performs the signature action.
* [ ] **6. FINAL SIGNED DOCUMENT** — The demo can retrieve/show the completed signed artifact rather than stopping at "sent for signature."
* [ ] **7. AUTHORITY BOUNDARY IS EXPLICIT** — The code/workflow contains a defined transition where autonomous reversible work stops and human commitment begins.
* [ ] **8. AGENT CANNOT SILENTLY SELF-SIGN** — The agent lacks a normal execution path that impersonates the human signer or automatically supplies human consent.
* [ ] **9. HANDOFF IS VISIBLE IN DEMO** — The audience actually sees the human-authority transition rather than hearing it described afterward.
* [ ] **10. BOUNDARY HAS A REASON** — The submission can explain in one sentence why the chosen action requires human authority while earlier operations do not.
* [ ] **11. MULTI-STEP FOXIT WORKFLOW** — The agent performs at least two meaningful document lifecycle operations overall rather than making one cosmetic Foxit call before signing.
* [ ] **12. SIGNED CONTENT MATCHES APPROVED CONTENT** — The artifact entering eSign is demonstrably the reviewed/final version rather than an uncontrolled regeneration.
* [ ] **13. STATE TRANSITIONS ARE RECORDED** — ProofDesk distinguishes states such as draft/reviewed/approved/sent/signed rather than representing everything as one generic "complete" state.
* [ ] **14. POST-APPROVAL MUTATION IS CONTROLLED** — Changing the document after approval invalidates/requires renewed approval rather than quietly continuing toward signature.
* [ ] **15. SIGNING FAILURE IS SAFE** — A declined, failed, expired, or incomplete signing attempt remains non-final and does not get reported as signed.
* [ ] **16. CREDENTIALS ARE SERVER-SIDE** — Foxit/eSign secrets are absent from the public repository and client-side application code.
* [ ] **17. AUDIT RECORD DISTINGUISHES AI FROM HUMAN ACTION** — The final log shows which actions were performed by the agent and which required human authorization.
* [ ] **18. BUSINESS WORKFLOW IS PLAUSIBLE** — There is a recognizable reason a real organization would delegate document preparation to an agent while retaining signature authority.
* [ ] **19. END-TO-END DEMO IS SHORT AND LEGIBLE** — The full prompt→agent→Foxit→human→signed journey can be understood within the hackathon demo format.
* [ ] **20. TECHNICAL BOUNDARY IS DEFENSIBLE** — You could answer a judge asking "Why exactly is this operation autonomous but signing isn't?" without appealing merely to the challenge instructions.

---

**Status:** ___/20 TRUE

**Critical path:** Gates 1-10 are the actual Foxit challenge. Everything after that makes the implementation convincing.

**Key insight:** The SignatureGate already exists in `src/state/machine.py:can_request_signature()`. It checks 6 conditions: state==PREPARED, zero unresolved blockers, human approval present, record hash matches, artifact hash matches, signer supplied. This is the authority boundary Foxit wants to see.
