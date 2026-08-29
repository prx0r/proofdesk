# Nutrient DWS — Pricing (Complete Reference)

Source: https://www.nutrient.io/api/pricing/data-extraction-api/

---

## Free Tier

- **5,000 credits/month** — no credit card required
- Enough for: 5,000 text parse pages, 555 understand parse pages, or 208 agentic extract pages

## Plans

| Plan | Monthly | Annual | Credits/mo | PAYG rate |
|------|---------|--------|------------|-----------|
| Free | $0 | — | 5,000 | — |
| Starter | $59/mo | $49/mo | 25,000 | $0.0028/credit |
| Pro | $500/mo | $450/mo | 500,000 | $0.0012/credit |
| Custom | Contact sales | — | Custom | Volume discounts |

## Credit Costs

### Parse (per page)

| Mode | Credits |
|------|---------|
| Text | 1 |
| Structure | 1.5 |
| Understand | 9 |
| Agentic | 18 |

### Extract (per page, includes parse component)

| Mode | Credits |
|------|---------|
| Text | 7 |
| Structure | 7.5 |
| Understand | 15 |
| Agentic | 24 |

### Classify (flat rate)

| Mode | Credits |
|------|---------|
| Default | 1 |

## Credit Behavior

- Unused credits **do not roll over**
- PAYG: pre-authorize $25 increments, add credits as used
- Spending cap configurable (default: half monthly subscription)
- Set cap to $0 to stop at monthly limit

## For ProofDesk Benchmark

With 5,000 free credits:
- 333 documents in understand+extract mode (15 credits each)
- Or 555 documents in understand parse mode (9 credits each)
- Our A/B test used 195 credits (13 docs × 15) — well within free tier
