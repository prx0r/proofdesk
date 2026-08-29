# Nutrient DWS Challenge — Exact Requirements

Source: https://api-cloud-ai-hackathon-2026.devpost.com/
Fetched: 2026-08-25

---

## Prize

$1,500 in cash — 2 winners

1st Place: $750 Visa Cash Giftcard + DWS Credits ($250 Cash Value)
2nd Place: $250 Visa Cash Giftcard + DWS Credits ($250 Cash Value)

Contact: douglas@nutrient.io

---

## Challenge Description (word-for-word)

Every business runs on documents — contracts, invoices, forms, IDs, claims, reports — and when they're regulated, "almost right" isn't good enough. Nutrient DWS is the deterministic document platform for agents and humans: REST APIs and SDKs to parse, extract, convert, redact, digitally sign, and archive documents, plus the embeddable DWS Viewer for human review — all with replayable output and full audit trails the AI-alone approach can't guarantee. The best document work isn't one magic call — it's a pipeline: pull the data out, judge how confident you are, bring a human in exactly where it matters, and keep a record of every step.

And the timing isn't academic — a wave of new mandates is hitting regulated document work right now. Your mission: turn messy documents into something useful — and trustworthy enough to run on real, regulated work.

Free DWS access for the whole event. Create a DWS account and you're building in minutes — every account starts with free credits, and if you need more, just ask and we'll top you up.

The one rule: your project must use Nutrient DWS — the API, an SDK, or the Viewer — for at least one core document operation, meaningfully (not a single throwaway call). Everything else is yours to invent. Bonus respect for pipelines that lean on what makes DWS different: deterministic, auditable output, with a human in the loop where a guess isn't acceptable.

---

## Ideas (from Nutrient, not requirements)

Each shares the same shape — let AI do the heavy lifting, pull a human in for the tricky calls, keep an audit trail — and each is anchored to a real regulation landing right now.

**Onboard a customer the regulators will accept.** Read someone's ID and supporting docs, auto-approve the clear cases, send the doubtful ones to a human — with a trail a regulator can follow. (EU digital-identity + anti-money-laundering rules, 2026–2027.) → DWS: Data Extraction API to parse the ID and supporting docs into key fields with confidence scores; DWS Viewer for the cases a human must judge.

**Turn a PDF invoice into a compliant e-invoice.** Read a messy invoice, convert it to the EU's required structured format, let a human fix what the model wasn't sure about, keep a dated record of what was sent. (France mandate Sept 1 — mid-event.) → DWS: Data Extraction API for line items and totals; digitally sign the result so its authenticity is provable.

**Catch the costly mismatch in a bundle of trade documents.** Cross-check an invoice, a shipping doc, and a certificate, surface the discrepancy that would cost a customs penalty, and let a human make the final call. (New electronic-transferable-records laws.) → DWS: Data Extraction API to parse each document into comparable fields; DWS Viewer for the human decision.

**Beat the mortgage-appraisal cutover.** US home appraisals switch to a new required format at the end of 2026 — miss it and the report gets bounced. Read an appraisal, fill the new format, flag anything uncertain, keep a full audit trail. → DWS: Data Extraction API to lift fields (confidence scores flag the uncertain ones); DWS Viewer to review before the report goes out.

**Redact, then release.** Black out personal info, have a human sign off on the redactions, export a clean copy plus proof of what was removed. (New EU AI-transparency rules, live Aug 2026.) → DWS: AI redaction; DWS Viewer for human approval; digitally sign the cleared copy so it's tamper-evident and dated.

---

## What to submit

- Project name + one-line pitch
- Public repo (or shared link) with setup instructions
- 2–4 min demo video showing it working end-to-end
- One line on where DWS does the heavy lifting and why

---

## API Credentials

```
api.nutrient.io/campaigns/api-world-cloudx-ai-hackathon-2026/
username: api-world-cloudx-2026
password: 5746c8e69078fde0126109ce5f8c301f
```
