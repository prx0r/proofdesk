# NORTHSTAR — Telegraph FactJudge plan

*Saved 2026-08-22. Governing document for ~/telegraph-lab. Verbatim from the founding directive.*

---

**Do not build EvoLab.** That would be QDW all over again: spend days constructing the perfect machine for experiments before doing the experiment.

Use this rule:

> **EvoLab is the notebook we wish existed after doing 20 real experiments. Telegraph is experiment #1.**

Telegraph is especially good for this because its organizers explicitly say they want **evidence that the quality flywheel works**, not the fanciest demo, and they specifically call out signal quality/verification as a high-value area. (Telegraph Hackathon)

Also, Track 1 and Track 2 close **August 31**, while the application phase runs August 31–September 7. So the immediate target should be brutally narrow.

# What we build now

The Telegraph project:

## **FactJudge**

A better deterministic evaluator for `FACT_CHECK`/closely related verified factual outputs.

Not: HydraDB, GEPA, MAP-Elites, generic evolution framework, agent OS, dashboard, ontology, memory system, generic benchmark platform.

Just:

```text
ground truth + miner answer → FactJudge → 0.0 ───────── 1.0
```

But we **develop FactJudge evolutionarily**.

Start with Telegraph's existing scorer as `CHAMPION_0`. Every modification is a challenger:

```text
CHAMPION_0
    ├── mutation: numeric agreement → CHALLENGER_1 → benchmark
    ├── better? promote : reject → CHAMPION_1 ...
```

That's already evolutionary systems research. We don't need an evolutionary-system codebase to do it.

# Keep only six tiny experiment objects

```text
telegraph-factjudge/
├── scorer/src/
├── benchmark/{dev.jsonl, heldout.jsonl}
├── mutations/generate.py
├── experiments/runs.jsonl
├── compare.py
└── README.md
```

A run record might literally be:

```json
{
  "candidate": "c004",
  "parent": "c003",
  "change": "penalize contradictory numbers",
  "benchmark": "heldout-v2",
  "baseline_score": 0.781,
  "candidate_score": 0.814,
  "regressions": 1,
  "promoted": true
}
```

This JSONL file is our **temporary HydraDB**. If six months from now there are 30,000 interconnected experiments and we desperately want graph queries, *then* Hydra earns its existence.

# The first scientific question

> **Where does Telegraph's existing semantic evaluator systematically mistake a worse factual answer for a better one?**

Build pairs like:

```text
GROUND TRUTH: Paris has approximately 2.1 million residents.
GOOD: Paris has about 2.1 million residents.
BAD: Paris has about 3.1 million residents.
```

Semantic similarity is almost identical. Factual correctness isn't.

Mutate systematically: number, date, entity, unit, polarity/negation, missing fact, extra unsupported claim, contradiction.

# First week phases

- **Phase A — reproduce**: official baseline scorer locally; same input → same output.
- **Phase B — adversarial corpus**: hundreds of answer pairs; DEV/HELDOUT separate; don't tune against heldout.
- **Phase C — measure baseline failure**: pairwise preference table per mutation class.
- **Phase D — mutate scorer**: one mechanism at a time (C1 numbers, C2 dates, C3 negation, C4 entities, C5 contradiction).

## The cognition-lab mapping

Same world, different cognition becomes: same benchmark `(B, S_a) → scores_a` vs `(B, S_b) → scores_b`. Telegraph = first champion/challenger laboratory without constructing a laboratory. Later: Ditto (retrieval/memory), coding (repo issue), more.

# Only three "EvoLab features" permitted

1. **Parent ID**: every challenger says what it came from (`c7 → MUTATED_FROM → c6`). JSON only.
2. **Mutation description**: exactly one sentence.
3. **Immutable run result**: candidate, commit, benchmark_version, seed, scores, failures, promoted.

That's the entire evolutionary infrastructure.

# QDW distilled to one command

```bash
python compare.py champion challenger
```

```text
CHALLENGER c007
dev: +4.8%   heldout: +3.1%   adversarial: +7.2%
critical regressions: 0    wasm: PASS    size: 8.7 MB
PROMOTION: PASS
```

QDW rules: code existing ≠ evidence it works; freeze acceptance criteria; record the exact verification run.

# No GEPA until manual evolution works (10 generations). No Hydra until this query hurts.

Install Hydra when you genuinely ask: *"Which mutations descended from numeric-checking changes, improved factuality across both Telegraph and Ditto, but caused latency regressions?"* Until then `runs.jsonl` wins.

# Three-step progression

1. **Now — Track 2**: build the referee (FactJudge). Script prize $1,000, $500 first.
2. **If time — Track 1**: use evaluator knowledge to build FactMiner. Co-evolution loop.
3. **August 31 onward — Track 3**: tiny real app consuming live Telegraph Miners (must be live, not mocks).

# Meta-goal

By end of Telegraph: 1 real competition, 1 functioning scorer, 10 challenger generations, 500 adversarial cases, 10 measured hypotheses, 4 rejected ideas, 5 improvements, 1 champion, 1 submission, 1 evidence report. Then extract the reusable 20%.

# RULE OF THREE

> Nothing becomes generic infrastructure until three real experiments require it. Nothing becomes cross-environment infrastructure until two independent environments use it.

HydraDB: needed once → NO; twice → probably NO; three painful lineage analyses → consider.
GEPA: haven't manually evolved → NO; same mutation workflow 10× → YES.
Generic Environment interface: only Telegraph exists → NO; two environments → maybe; third → extract.

# Guiding star

> **Long-term:** develop an experimental science of agent cognition by repeatedly varying components of intelligent systems under reproducible evaluation, preserving lineage and only promoting measured improvements.
> **Current experiment:** Telegraph FactJudge.
> **Current question:** can deterministic factual checks outperform generic semantic similarity when distinguishing subtly incorrect answers?
> **Current deliverable:** one competitive WASM evaluation Script before August 31.

Everything must answer the current question or improve the submission. Else `FUTURE.md`, don't build.

---

## Execution annex (workspace layout decided 2026-08-22)

```text
~/telegraph-lab/
├── northstar.md          ← this file
├── vendor/
│   ├── telegraph-docs        (protocol spec)
│   ├── telegraph-api-docs    (API/OpenAPI)
│   ├── ditto-subnet          (benchmark design ideas only)
│   └── gepa                  (mutation automation specimen, unplugged)
├── refs/
│   ├── qdw                   (promotion discipline)
│   ├── agn1 -> /root/crypto-lab      (already on disk)
│   └── finalbuilds2 -> /root/finalbuilds2  (already on disk)
└── factjudge/                (the ONE new repo)
    ├── README.md             (guiding star)
    ├── AGENTS.md             (RULE 1-10 anti-overengineering gates)
    ├── FUTURE.md             (everything not now: cogym zips, Hydra, GEPA…)
    ├── docs/TELEGRAPH-CONTRACT.md   (P1 output: live WASM ABI facts)
    ├── scorer/
    ├── benchmark/{schema.json, dev.jsonl, heldout.jsonl, adversarial.jsonl}
    ├── candidates/C000/
    ├── experiments/runs.jsonl
    ├── scripts/{evaluate.py, compare.py, new_candidate.py}
    └── telegraph/adapter/
```

### Architectural decision: isolate Telegraph's ABI

```text
Telegraph input → telegraph/adapter → Internal EvalCase → FactJudge → float 0..1 → adapter → output
```

Internal case:
```json
{
  "case_id": "num_001",
  "ground_truth": "...",
  "candidate_answer": "...",
  "metadata": { "category": "number_mutation" }
}
```

Scorer needs only `score(ground_truth, candidate_answer) → [0,1]`.

### P0 sequence
- P0 clone upstream refs ✓ (this workspace)
- P1 inspect live Script/WASM contract → docs/TELEGRAPH-CONTRACT.md (exact ABI, input/output encoding, toolchain, limits, submission process, Intents, canonical scorer) with source links + observed date
- P2 select live Intent (EXP-000 decision record with evidence)
- P3 compile minimum valid WASM evaluator
- P4 deterministic local replay (1000 reps, zero variation)

Then: P5 corpus 500 cases (DEV 200 / HELDOUT 200 / ADVERSARIAL 100), P6 measure C000, P7 biggest failure cluster, P8+ generations C001…

Promotion policy v1: heldout > champion AND adversarial >= champion AND no critical category drop >5pp AND WASM validation passes AND runtime within limits.

### AGENTS.md gates (RULE 1–10)

1. No database until JSONL causes measurable pain.
2. No generic framework until a second environment needs the same code.
3. No abstraction for a hypothetical future environment.
4. Every day's work improves: (a) submission, (b) benchmark quality, or (c) measured understanding of evaluator failures.
5. FUTURE ideas go in FUTURE.md, not src/.
6. A mutation that isn't benchmarked does not exist.
7. Rejected experiments are valuable and remain recorded.
8. No GEPA until manual evolution works.
9. No Hydra until cross-environment lineage exists.
10. No UI until submission works.

### Definition of success (next stage)

[ ] official WASM contract captured [ ] valid WASM executes [ ] Intent selected w/ evidence [ ] C000 frozen [ ] 500 examples [ ] splits frozen [ ] baseline failure report [ ] ≥5 generations [ ] ≥2 rejected hypotheses [ ] champion better on heldout [ ] no severe adversarial regression [ ] deterministic clean build [ ] final WASM SHA recorded [ ] submission accepted
