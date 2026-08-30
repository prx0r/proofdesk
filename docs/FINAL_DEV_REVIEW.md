# Final Dev Review — Timestamped

**Commit:** 91fb4df
**Date:** 2026-08-31
**Deadline:** Sep 3, 2026 10:00 AM PDT

## Scores

| Area | Now | Finish-line |
|------|-----|-------------|
| Concept | 9.5 | 9.6 |
| Technical ambition | 9.5 | 9.5 |
| Correctness | 8.0 | 9.4 |
| Demo credibility | 8.0 | 9.6 |
| Packaging | 8.2 | 9.5 |
| Nutrient track | 8.8 | 9.5+ |
| Foxit track | 6.0-6.5 | 9.3+ |
| Overall | 8.5 | 9.4+ |

## Phase A — Make the repo trustworthy

1. Fix red CI (test_doctavian.py fails, rename to test_generation.py)
2. Remove/rename stale Doctavian generation tests
3. Add python-dotenv; make README .env instructions actually work
4. Generate valid PDF fixtures on clean checkout (render_fixture_pdf)
5. Add required-field completeness assertions (REQUIRED_FIELDS set)
6. Fix field_risks/violations schema (within_budget not in violation objects)
7. Fail closed on absent decision certificate
8. Bind SignatureRequest to final prepared PDF hash
9. Expose final prepared hash through API/receipt
10. Add root LICENSE
11. Clean stale foxit/ submission docs
12. Rename Doctavian-named local renderer code
13. Push. Require green CI before proceeding.

## Phase B — Make Nutrient submission excellent

14. Make provider mode visible at runtime
15. Use /trace to prove actual DWS calls
16. Expose bounding boxes in facts
17. Make facts clickable to source page
18. Stop auto-resolving blockers
19. Show one real human evidence decision
20. Ideally provide/update a second certificate and rerun extraction
21. Test partial/missing required evidence
22. Record a clean Nutrient-only end-to-end run

## Phase C — Make Foxit eligible to win

23. Activate eSign in Foxit portal
24. Try the same existing Foxit developer credentials
25. Rewrite FoxitESignClient against current unified API
26. Add real signature field
27. sendNow: true
28. Parse real folder.folderId
29. No fallback under DEMO_REQUIRE_LIVE_PROVIDERS=true
30. Human receives email
31. Human actually signs
32. Poll Foxit status/activity
33. Only then transition to SIGNED
34. Download signed PDF
35. Hash signed PDF
36. Add signed artifact to audit receipt
37. Disable fake /sign completion in live mode
38. Add real tamper/rejection demonstration
39. If stable, put official Foxit MCP in front of reversible operations
40. Green CI again

## Phase D — Stop coding

41. Freeze commit
42. Create Git tag hackathon-submission-v1
43. Record video
44. Capture 3-5 screenshots
45. Complete Devpost
46. Verify every public claim against that exact tagged commit
47. Submit

## Release blockers

1. CI red (test_doctavian.py)
2. Per-field risk violations don't block SignatureGate (within_budget default)
3. Partial evidence can silently pass (missing required fields)
4. Fixture PDFs not in repo
5. .env not loaded (python-dotenv missing)
6. SignatureRequest bound to wrong hash
7. eSign using stale API path
8. eSign never actually sends (sendNow: false)
9. No signature field in generated PDF
10. /sign endpoint fakes completion
11. eSign failure silently falls to simulation
12. Web demo doesn't prove providers were live
13. UI artifact hash is wrong hash
14. Tamper detection not demonstrated in demo
15. Human review is automatic, not interactive
16. Nutrient grounding not visible in UI
17. foxit/ tree is stale
18. Doctavian-named functions remain
19. Root LICENSE missing
20. README/test-count drift
21. case._classification and case._confidence overlap
22. Blocker resolution logic inconsistent
23. Foxit MCP needed for sponsor track
24. Demo prompt should be editable
