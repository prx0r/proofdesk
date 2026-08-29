# Signing Confidence Benchmark — Tradeoff-First Design

## Core Principle

**Don't claim 0% false sign. Show the tradeoff and let judges decide.**

| False Sign Rate | Coverage | Tradeoff |
|-----------------|----------|----------|
| 0% | 60% | Maximum safety, must review 40% |
| 1% | 75% | Balanced |
| 5% | 90% | Higher risk, less review |

The question isn't "can we achieve 0%?" — it's "what does 0% cost you in coverage?"

## The Experiment

### Step 1: Find Optimal Thresholds per Document Type

For each document type, find the threshold that maximizes coverage at a given false sign rate.

**Method:** Conformal Risk Control (Angelopoulos et al., ICLR 2024)

**Datasets:**
- Invoices: InvoiceBenchmark (200), FATURA (10K)
- Contracts: ContractNER (3,240), CUAD (510)
- Insurance: INS-007 (5K), AIForge-Doc (4K)
- Securities: 10K Fraud (10K)

### Step 2: Show Risk-Coverage Curve

For each document type, plot:
- X-axis: False sign rate (0%, 1%, 2%, 5%, 10%)
- Y-axis: Coverage (what % can we auto-sign?)

### Step 3: Let Judges Decide

Present the curve and ask: "What false sign rate is acceptable for your use case?"

### Step 4: Cogym Optimization

Use cogym patterns to find optimal thresholds:
- **HardWorlds**: each document type is a world
- **Evolution**: mutate thresholds → benchmark → select
- **BehaviorSignature**: fingerprint each signer's profile

## The Tradeoff Graph

```
Coverage (%)
    |
90% |                              *
    |                         *
80% |                    *
    |               *
70% |          *
    |     *
60% |*
    +----+----+----+----+----+----→
    0%   1%   2%   3%   4%   5%
         False Sign Rate
```

**At 0% false sign:** You can auto-sign 60% of documents. 40% need human review.
**At 1% false sign:** You can auto-sign 75%. 25% need review.
**At 5% false sign:** You can auto-sign 90%. 10% need review.

**The judges decide: which operating point is right for their use case?**

## Why This Is Better Than Claiming 0%

1. **Honest** — shows the real tradeoff
2. **Actionable** — judges can pick their risk tolerance
3. **Auditable** — every decision is calibrated
4. **Optimized** — thresholds tuned per document type

## Cogym Patterns Used

| Pattern | How We Use It |
|---------|---------------|
| HardWorlds | Each document type = one world |
| Evolution | Mutate thresholds → benchmark → select |
| BehaviorSignature | Fingerprint each signer's profile |
| State Transfer | Test if thresholds transfer to new docs |

## The Story

"We don't claim 0% false sign. We show you the tradeoff: at 0% you can auto-sign 60% of documents. At 1% you can auto-sign 75%. You decide what's acceptable for your use case."

That's honest, actionable, and auditable.
