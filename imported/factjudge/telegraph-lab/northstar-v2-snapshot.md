# NORTHSTAR v2 — FactJudge as evolutionary experiment

*2026-08-23. Supersedes northstar-v1 (2026-08-22, preserved alongside this file).
Portfolio verdict: B is the core Track-2 experiment engine → A becomes the miner
shaped by what B discovers → E documents the experiment → D becomes the later
application using official Telegraph plumbing → C is only a conditional pivot if
the live registry exposes a suitable objective numeric Intent.*

> **We are not building an evolutionary framework. We are evolving a Telegraph
> scorer. Infrastructure is permitted only when the current experiment requires it.**

## Verification note (read first)

Several precise constants circulating in earlier planning — 75/25 judging split,
Stage-2 ≥0.75 threshold, 100-request requirement, exact live miner counts, some
incumbent-quality claims — are **not confirmed on the current public hackathon
page**. The official page lists ranking/performance, app usage, requests, X updates
and engagement for Miners; automated evaluation, ranking accuracy, gaming
resistance, X updates and community visibility for Scripts. Treat exact constants
as hypotheses until the developer console / private rules confirm them.

## Portfolio ranking

| Plan | H1 value | Long-term | Overengineering risk | Verdict |
|---|---:|---:|---:|---|
| **B — Refinery** | **9.5** | 9 | Medium | **Build first, one Intent only** |
| **A — Provenance Miner** | 8 | **10** | **Very high** | **A-lite after B exposes failures** |
| E — Build-in-public | 7.5 | 6 | Low | Run continuously, tiny implementation |
| D — Demand Engine | 8 (Track 3) | 8 | High if custom | Defer; reuse Telegraph MCP/x402 |
| C — Deterministic Sniper | 5–9 by registry | 6 | Low | Conditional pivot only |

Key strategic fact: Telegraph itself already implements the evolutionary pattern —
one canonical WASM scorer per Intent, challengers in a testing cohort, replacement
after satisfying catch-rate criteria over epochs. **Telegraph is already our first
evolutionary laboratory.**

---

# A — Provenance Miner (becomes EvidenceMiner, A-lite)

Verdict: excellent thesis, ~2× too complicated for H1.

### Delete from v1
- **Merkle tree** — proves claims unchanged, not claims true; Telegraph's own
  zkTLS→validator→WASM pipeline is the stronger provenance story. → FUTURE.md.
- **Overlap formula as "entailment"** — `0.5·overlap + 0.3·numbers + 0.2·polarity`
  is a cheap signal, not entailment (same nouns can flip meaning).

### Correct architecture (SAFE / RefChecker / VeriCite lineage)
```text
RETRIEVAL → 3–8 good passages
   ↓
CLAIM DECOMPOSITION → atomic claim objects
   ↓
EVIDENCE SELECTION → claim ↔ exact source span
   ↓
SUPPORT CHECK → supported / contradicted / unknown
   ↓
SHORT ANSWER
```
Miner may use LLM/NLI for claim extraction+support. WASM Script stays deterministic.

### EvidenceMiner output contract (H1)
```json
{
  "answer": "...",
  "claims": [
    {"text": "...", "source": "...", "support_span": "...",
     "published_at": "...", "status": "supported"}
  ]
}
```
No Merkle · no giant source fleet · no 40-doc retrieval. Start OpenAlex + OpenAIRE +
one web provider if needed; retrieve 8–12 candidates, rerank to 3–5 evidence passages.

### Gaming problem (critical)
Script must NOT award points because a miner self-reports `"status": "supported"`
— a malicious miner fabricates that field. Script score comes primarily from:
ground-truth factual agreement · number/date/entity agreement · contradiction
detection · coverage. Receipt structure = modest bonus at most. Otherwise we built
a scorer our own miner can game.

### Frontier references to steal from
- SAFE (google-deepmind/long-form-factuality): fact decomposition + supported-fact eval
- RAGChecker (amazon-science): claim-level diagnostics, retriever vs generator separation
- RefChecker (archived — don't depend): claim-triplet abstraction

### Final A sequencing
Don't build first. Let B measure which factual failure modes matter, then design
EvidenceMiner to beat exactly those. `FactJudge finds failures → EvidenceMiner
architecture avoids them` — selection pressure before producer design.

---

# B — The Refinery (becomes THE project: FactJudge)

Verdict: core project. Identity change: not "one scorer sprayed across many
intents" but **one experimental scorer continuously evolved against ONE intent.**

## Center everything on metamorphic testing

Normal benchmark asks "is X correct?" Metamorphic asks: *when I apply a
transformation with known semantic effect, does the scorer react appropriately?*

```text
INVARIANCE                          SENSITIVITY
├── paraphrase                      ├── wrong number
├── clause reorder                  ├── wrong date
├── formatting                      ├── wrong entity
├── equivalent unit                 ├── negation flip
├── date format                     ├── unit mismatch
└── aliases                         ├── omitted fact
                                    ├── contradiction
score(original) ≈ score(paraphrase) └── unsupported addition
score(good) > score(mutated)
```

Frontier grounding: 2025 survey catalogued 191 metamorphic relations for NLP;
LLMORPH automated 36 across ~561k executions; Aug-2026 logic-grounded metamorphic
testing shows static benchmarks miss defects exposed by invariant transformations.

Score on multiple axes, not one aggregate:
```text
invariance_accuracy · sensitivity_accuracy · pairwise_accuracy · mean_margin · worst_category
```

## Evaluator stress tests (= Telegraph's "gaming resistance" criterion)

Attack set:
```text
repeat ground truth 10× · very long fluent answer · correct answer followed by
contradiction · list every plausible number · copy question verbatim · stuff
entity names · correct answer then "actually no" · Unicode number variants
```
If the scorer rewards these, we found a vulnerability — in ours or theirs.

## Property-based testing (Hypothesis)

Don't hand-author 500 unit-conversion variants. Properties:
```text
equivalent_unit(x) ⇒ score delta < ε
replace_number(x, wrong) ⇒ score(wrong) < score(correct)
append_contradiction(x) ⇒ score cannot increase
paraphrase(x) ⇒ score must not collapse
```
Hypothesis shrinks failures to minimal counterexamples — ideal for scorer dev.

## Dynamic benchmark generation (anti-contamination)

```text
candidate frozen → seed = random → generate dates/numbers/entities
→ apply known mutation → evaluate
```
Candidate can't memorize examples. Ditto methodology without importing Ditto.

## Cut list (do NOT build initially)
200-entity alias table · general unit library · 14 date formats · many-intent config
machinery · ticket-EV system · registry-wide auto-registration.

## References
steven-b-cho/llmorph (organization) · HypothesisWorks/hypothesis (pip install, not
vendored) · SeekingDream/Static-to-Dynamic-LLMEval (research index) ·
ditto-assistant/ditto-subnet (philosophy only) · UKGovernmentBEIS/inspect_ai
(optional structural reference, no dependency jungle).

---

# C — Deterministic Sniper (conditional only)

Factual correction: the published canonical Intent list does NOT currently show
CRYPTO_PRICE or GAS_PRICE. Do not build until `list_intents` proves the target
exists. Generalize to **Deterministic Numeric Sniper**: any intent where ground
truth = objectively measurable quantity.

### Numeric error fix
Relative error blows up near zero. Use symmetric percentage error
`e = 2|a−b| / (|a|+|b|+ε)` or log-ratio `e = |log(a/b)|` for positive quantities;
map to domain tolerance bands:
```text
within ideal tolerance → 1.0
acceptable band        → smooth decay
outside tolerance      → near 0
```

### Consensus correction
Independence > count: three APIs sharing an upstream source ≠ three observations.
Record `{source_family, observed_at, value, unit}`; penalize stale/correlated
inputs. Median+MAD stays the baseline. No Byzantine oracle network.

### Best use even if unsubmitted
Calibration environment: objective ground truth tests whether our candidate/
promotion machinery works at all.

### Kill gate (hour zero)
```text
live list_intents → objective numeric intent available?
  no → kill C
  yes → probe incumbent quality → clear scoring weakness?
        no → kill C
        yes → build
```

---

# D — Demand Engine (Track 3 only, implementation stale)

Corrections:
1. Hand-written x402 v1 flow is obsolete: x402 is now **v2** with standardized
   `PAYMENT-REQUIRED` / `PAYMENT-SIGNATURE` / `PAYMENT-RESPONSE` headers, CAIP-2
   networks, official SDKs.
2. Telegraph's official MCP dynamically discovers live tools every five minutes and
   handles x402 internally (depends on @x402/core, @x402/fetch, @x402/evm, @x402/svm).
   Custom payment/signing/retry/discovery = pure overengineering.

D becomes: **one genuinely useful application demonstrating demand for our winning
Miner/Script pair.** Natural choice — HackathonHelp integration:
```text
hackathon opportunity page
   ↓ extract major claims
Telegraph MCP → NEWS_SEARCH / RESEARCH_SYNTHESIS / FACT_CHECK live miners
   ↓ verified opportunity report (eligibility / deadline / prize evidence)
```
Continuity: FactJudge → EvidenceMiner → HackathonHelp consumes EvidenceMiner → real
requests. App track judges usage/adoption/usefulness/engagement on LIVE miners.

If direct HTTP needed later: x402-foundation/x402 SDKs — never hand-roll unless the
official client demonstrably fails.

Caching warning: cached answers are WRONG for "latest X"/news/weather intents.
Cache must be intent-specific, freshness-aware, explicitly surfaced. No cache-arbitrage
monetization for H1.

---

# E — Build in Public (open experiment notebook, not marketing)

Real multiplier (progress/community visibility is explicit judging input), but not
a content OS. Concept: **open science notebook** — every post comes from runs.jsonl:

```text
C004 → C005
Hypothesis: explicit negation checking catches polarity reversals.
Heldout: +2.7pp · Negation subset: +19.4pp · Correct paraphrase: −0.3pp
Decision: PROMOTE
```

Automate ONLY the boring part:
```bash
python scripts/report_run.py run_005
# → experiments/run_005/report.md + card.svg ; human decides whether to post
```
Do not automate replies/engagement. High-value signal = measured result · failure ·
method · reproducible artifact. Rejected mutations visible too — that's what makes it
believable. No extra repo needed.

---

# THE ARCHITECTURE

```text
                    TELEGRAPH

             ┌─────────────────┐
             │    FACTJUDGE    │
             │     Plan B      │
             │ dynamic bench   │
             │ metamorphic     │
             │ stress tests    │
             │ challenger loop │
             └────────┬────────┘
                      │ discovers failures
                      ▼
             ┌─────────────────┐
             │ EVIDENCE MINER  │
             │    Plan A-lite  │
             │ retrieve → atomic│
             │ claims → evidence│
             │ spans → verify   │
             └────────┬────────┘
                      │ real traffic
                      ▼
             ┌─────────────────┐
             │ HACKATHONHELP   │
             │    Plan D-lite  │
             │ Telegraph MCP   │
             │ live Miners     │
             └─────────────────┘

Every experiment → runs.jsonl → Plan E report
Plan C = conditional side experiment only
```

## Workspace
```bash
~/telegraph/upstream/ : telegraph-docs · telegraph-api-docs · telegraph-mcp
~/telegraph/research/ : long-form-factuality · llmorph · RAGChecker · ditto-subnet
pip install hypothesis          # never vendor
GEPA: bookmarked only — after enough manual generations
```

## The one repo
```text
telegraph-factjudge/
├── AGENTS.md · README.md · FUTURE.md
├── benchmark/{cases/, generators/{numeric,date,negation,entity,support}.py,
│              dev.jsonl, heldout.jsonl, stress.jsonl}
├── scorer/{numeric,date/entity,negation,coverage,compose}.*
├── candidates/C000…Cnnn/
├── experiments/runs.jsonl
├── scripts/{generate.py, evaluate.py, compare.py, report_run.py}
└── telegraph/wasm/
```
No DB · No Hydra · No server unless submission requires · No agent framework.

---

# FINAL DEVELOPMENT PLAN

**Phase 0 — Reality check (first session).** Clone upstream repos; via MCP/API answer:
live intents? miners per intent? which have canonical scripts? exact Script ABI? WASM
constraints? benchmark feedback exposed? official scoring constants?
Write `docs/LIVE-CONTRACT-<date>.md`, every statement sourced.
Gate: if FACT_CHECK/CONTENT_VERIFICATION viable → PRIMARY = B on FACT_CHECK; else
NEWS_SEARCH / RESEARCH_SYNTHESIS. C only if an objective scalar intent has an obvious hole.

**Phase 1 — C000 baseline.** Minimum scorer `score(gt,answer)→[0,1]`; freeze
commit+WASM hash+benchmark version; determinism proof (repeated identical runs).

**Phase 2 — Benchmark BEFORE scorer.** 400–800 cases; half invariance, half
sensitivity; plus stress set (stuffing/copying/verbose-falsehood/unicode…).
Split DEV 50% / HELDOUT 30% / STRESS 20%; holdout seed frozen before scorer work.

**Phase 3 — Manual evolution loop.**
```text
C000 → failure analysis → hypothesis → C001 → heldout → promote/reject → …
Expected order: numbers → units → dates → negation → entities → coverage →
unsupported additions → composition/calibration
```
Run record per candidate: {candidate, parent, hypothesis, benchmark_version, seed,
metrics, worst_group, runtime, decision}. This JSONL IS EvoLab.

**Promotion gate:**
```text
PROMOTE iff pairwise heldout > champion AND stress ≥ champion AND
worst-category regression < threshold AND paraphrase invariance healthy AND
WASM deterministic AND resource limits pass
```
Track margin m = score(good) − score(bad); .51/.49 ranking ≪ .90/.10 convincing.

**Phase 4 — Submit EARLY.** As soon as clearly better than C000: submit. Real
Telegraph feedback is another environment signal feeding the next hypothesis.

**Phase 5 — A-lite only after the scorer teaches what matters.** Failure scoreboard
(e.g. unsupported additions / wrong numbers / incomplete evidence) becomes
EvidenceMiner requirements. Benchmark EvidenceMiner vs simple search+LLM baseline
using our champion FactJudge; register only if substantially better. First true
evaluator→selection-pressure→producer-adapts experiment.

**Phase 6 — E from beginning.** Every meaningful run emits one public-ready report.
"C002 rejected: numbers +18pp, paraphrase-invariance −9pp" beats "Day 4 building!"

**Phase 7 — Track 3.** Use telegraph-mcp, not custom plumbing. One HackathonHelp
integration: opportunity URL → extract claims → live miners verify → verified
opportunity report. Measure requests/users/success/latency/failures.

**Phase 8 — after H1.** Inventory: 8–15 scorers, hundreds of metamorphic cases,
stress generator, promotion history, rejected hypotheses, one miner, one app.
Only then compare Telegraph vs Ditto experiment structures; if both use
Candidate/Benchmark/Mutation/Evaluation/Promotion — extract those five. That is when
the broader evolutionary-cognition project earns its existence. Not before.
