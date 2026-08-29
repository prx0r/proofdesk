# ProofDesk — How We Assess Signing Safety

## The Problem

Foxit asks: "When should an agent sign a document?"

**Current approach:** Hardcoded domain rules (KYC = review, procurement = sign).

**Better approach:** Actually verify the document content against business rules.

## What We Should Verify

### 1. Amount Consistency
- Does invoice total match quote total?
- Are line items arithmetic correct?
- Is the amount within expected range?

### 2. Vendor Legitimacy
- Is vendor name consistent across documents?
- Does vendor exist in approved vendor list?
- Are there multiple vendor names (suspicious)?

### 3. Date Validity
- Are contract dates in the future?
- Does insurance cover the contract period?
- Are there date gaps?

### 4. Cross-Document Consistency
- Do facts agree across procurement docs?
- Are there contradictions?
- Is the story coherent?

### 5. Domain Rules
- Is this document type safe to sign?
- Does it need human review?
- Are there regulatory requirements?

## How This Maps to Foxit

Foxit's challenge: "How do you design the handoff?"

Our answer:
1. Agent extracts fields (Nutrient)
2. Agent verifies against business rules (our logic)
3. If verification passes → sign (Foxit MCP → eSign)
4. If verification fails → review (SignatureGate blocks)

**The verification IS the assessment. Not a lookup table.**
