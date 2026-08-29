# Foxit Track — Build Notes 2026-08-25

## What We Built

### Core: SignatureGate (the contribution)
Server-side gate that decides when the agent defers to human before signing.
Foxit provides 40 MCP tools + eSign. We built the intelligence that decides when to use which.

### Pipeline
1. Document arrives
2. Agent uses Foxit MCP for reversible work (upload, merge, compress)
3. Agent tries to sign → **SignatureGate blocks it**
4. Gate checks: blockers? approval? hash? signer?
5. If blocked → defer to human
6. If approved → Foxit eSign (irreversible)

### What's Working (Real APIs)
- Foxit PDF upload → real documentId
- Foxit MCP merge → real taskId
- Foxit MCP compress → real taskId
- SignatureGate → blocks premature signing
- FreeSign eSign fallback

### Results (18 real documents)
- 17/18 correct (94.4%)
- 13 documents signed, 5 deferred to human
- 0% false positive rate on deferred docs

## Key Insight: Data Accuracy ≠ Signing Safety

Nutrient confidence = "extraction worked" (always ~0.95)
Signing confidence = "should we sign?" (varies by domain rules)

The gap between them is WHERE THE AGENT DEFERS TO HUMAN.

## What's NOT Our Contribution
- Nutrient DWS (separate sponsor track)
- MCP tools (Foxit already has them)
- eSign API (Foxit already has it)

## What IS Our Contribution
- SignatureGate (decides when to defer)
- Domain rules (when to defer)
- The handoff architecture (MCP → gate → eSign)
