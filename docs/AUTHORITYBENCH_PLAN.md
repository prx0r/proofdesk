# AuthorityBench + Trust Lab + Technical Preprint

**The one major stretch goal for the ProofDesk Nutrient submission.**

This document is the canonical plan for the extra-credit research layer. It supersedes any earlier paper plans in `foxit/docs/`. The old `foxit/docs/PAPER.md` becomes historical research provenance.

**Status:** Plan complete, execution pending.
**Priority:** After PHASE 1–6 of `DEV_PLAN.md` are done.

---

## The Three Artifacts

> **AuthorityBench** — a reproducible benchmark for measuring when document AI has enough evidence to act rather than merely extract.
>
> **ProofDesk Trust Lab** — the interactive visualization of AuthorityBench.
>
> **"From Confidence to Authority: Risk-Calibrated Document Automation with Source-Grounded Evidence"** — the accompanying arXiv-style technical report.

Two views over the exact same benchmark artifacts. Not two separate side projects.

---

## Why This Is the Right Stretch Goal

This hits almost everything Nutrient is signaling: source-grounded confidence, deterministic workflows, human review, auditability, and empirical evidence that you understand when automation should stop.

Nutrient explicitly describes the desired pipeline as extraction → confidence → human judgment → recorded workflow.

### Existing research infrastructure already close to a paper-producing system

You have real code for:

- risk–coverage curves
- ECE/MCE/Brier/AURC
- reliability diagrams
- threshold landscapes
- bootstrap-style analysis
- hard-world comparisons
- calibration experiments
- online learning
- mixture-of-experts
- Cogym evolution
- hash/audit experiments
- real Nutrient benchmark result files
- direct Nutrient `/extraction/extract`
- per-field confidence
- page provenance
- bounding boxes
- real API provider traces

### The Nutrient provider is already using their newer purpose-built Data Extraction API

```text
POST https://api.nutrient.io/extraction/extract

schema
parseConfig.mode
includeCitations

→ value
→ confidence
→ page
→ bbox
```

That is excellent.

---

## 1. First: Clean Up the Science (P0)

### The existing "CRC" claim is too strong

One `ConformalRiskController` currently chooses thresholds based on empirical calibration risk. Another implementation takes a standard split-conformal quantile of scores while **ignoring the supplied losses**, yet its documentation claims a distribution-free risk guarantee.

That is not enough to headline:

> "Conformal guarantee: false-sign rate ≤ α."

Also, one implementation computes false-sign loss as a mean over **all documents**, whereas the operational quantity we care about is:

```
FAR = unsafe actions automatically authorized
      / all automatically authorized actions
```

Those are materially different.

Fix this rather than hiding it.

### The easy rigorous replacement

Use a **tune → certify → test** protocol.

```
dataset
  ↓
50% threshold/policy tuning
  ↓
25% independent certification
  ↓
25% untouched evaluation
```

Tune the policy on split A.

Freeze it.

On split B, calculate the one-sided exact binomial/Clopper-Pearson upper confidence bound for the false-authorization rate among automatically authorized cases.

For risk target α and confidence 1-δ:

```
if upper_confidence_bound(FAR) <= α:
    CERTIFIED
else:
    NOT CERTIFIED
```

Then report completely untouched split-C performance.

Now you can accurately say:

> "This policy satisfied a 1% authority-risk certificate at 95% confidence on the held-out certification set under the benchmark assumptions."

That is much stronger than incorrectly saying "conformal guarantee."

If you later implement true CRC/LTT correctly, add it as another method.

### Also downgrade the faux reproductions

Your EXTRACTCONF-inspired implementation contains placeholder/simplified features such as fixed neighbourhood overlap and zero centroid divergence.

So:

```
BAD:  Reproduction of EXTRACTCONF
GOOD: EXTRACTCONF-inspired multi-signal verification prototype
```

Same treatment for anything else not exactly reproduced.

That scientific restraint will **increase** credibility.

---

## 2. Kill Every Fake Graph

Your generic `generate_visuals.py` contains hardcoded or simulated presentation data:

- confidence values sampled from `np.random.normal`
- auto-sign projection `[59, 65, 83, 96]`
- $20,000 "fraud prevention"
- 3,239% ROI
- various manually populated counts

Keep those away from the paper.

The new rule:

> **Every pixel in a research chart must be derivable from a committed JSON benchmark artifact.**

Every plot gets a small footer:

```
AuthorityBench run: ab-20260902-1842
commit: 4ba7...
dataset_sha256: ...
n=480
seed=42
DWS mode=understand
```

And every paper figure can have:

```bash
python -m research.authoritybench.plot \
  --run benchmarks/authoritybench/ab-20260902-1842.json
```

This alone makes the project look far more serious.

---

## 3. The Killer Research Question

Do **not** write another paper about whether a classifier is calibrated.

That literature now exists.

ConfBench was published on **August 3, 2026** specifically to study document-extraction calibration and human-review routing across controlled degradation pipelines. It created 1,346 variants and 70K+ field evaluations and introduced review-budget-oriented evaluation.

A March 2026 paper likewise found that calibration changes dramatically across document domains, supporting domain-specific calibration.

More importantly, Nutrient itself now explicitly frames its product around **source-grounded confidence rather than arbitrary model certainty**. Its extraction API returns coordinates, confidence and page context, and its benchmark material is explicitly about validating output before downstream action.

So the question goes one level higher:

> ## When is a correctly extracted document fact sufficient evidence for an automated action?

That is the ProofDesk question.

And it is genuinely more interesting.

---

## 4. Build AuthorityBench

The benchmark unit is not:

```
one extracted field
```

It is:

```
document bundle
+
extracted evidence
+
business rule
+
proposed irreversible action
```

Example:

```
Purchase request
    service_until = Dec 31

Insurance certificate
    insured_until = Oct 1

DWS correctly extracts BOTH.

Extraction accuracy = 100%.

But:

insurance_until < service_until

Therefore:

authority = DENIED
```

This perfectly demonstrates the **evidence-to-authority gap**.

A conventional document benchmark calls that extraction successful.

AuthorityBench asks:

> "Did the system nevertheless prevent the unsafe action?"

That becomes the actual research contribution.

---

## 5. Exact Benchmark Design

Create:

```
research/
  authoritybench/
    README.md
    generate_cases.py
    degrade.py
    run_dws.py
    evaluate.py
    certify.py
    plots.py
    schemas/
    paper/
      main.tex
      references.bib

benchmarks/
  authoritybench/
    manifest.json
    latest.json
    runs/
```

### Tier A — controlled procurement worlds

Generate deterministic PDF bundles where you know every ground-truth field and authority outcome.

Each case contains roughly:

```
purchase request
vendor quote
insurance certificate
security questionnaire
```

Generate perhaps 40–60 base cases.

Vary:

```
safe bundle
amount mismatch
insurance expiry mismatch
wrong vendor identity
missing certificate
incomplete security answer
retention-policy violation
duplicate contradictory value
near-miss date
transposed number
currency mismatch
```

Because you generate the PDF yourself, you know:

- exact textual value
- expected normalized value
- true authority outcome
- source page
- ideally the actual source bounding box

That last point is particularly cool.

You could measure **citation IoU**:

> Did Nutrient not only extract the correct value but point back to the correct place on the page?

---

## 6. Add Controlled Degradation

Produce variants:

```
clean
blur
JPEG compression
low resolution
rotation/skew
contrast reduction
scan noise
partial occlusion
crop/margin damage
```

At perhaps three levels:

```
mild
medium
severe
```

Now you can make a gorgeous heatmap:

```
                   CLEAN  MILD  MEDIUM  SEVERE
DWS accuracy         ...
DWS ECE              ...
ProofDesk FAR        ...
review rate          ...
```

The key question isn't simply:

> Does OCR accuracy drop?

It is:

> **As evidence quality degrades, does ProofDesk become appropriately more conservative?**

That maps directly to safe automation.

---

## 7. Do the Four-Mode Nutrient Experiment

This may be the single most sponsor-impressive technical experiment.

Nutrient currently exposes different extraction modes so developers can trade speed/cost/depth. Its public benchmark reports separate performance for the modes and explicitly recommends using the cheapest mode that meets the workflow's accuracy requirement.

Your provider already supports:

```python
mode="understand"
```

Benchmark:

```
text
structure
understand
agentic
```

Measure:

| Metric                | text | structure | understand | agentic |
| --------------------- | ---: | --------: | ---------: | ------: |
| field accuracy        |      |           |            |         |
| citation availability |      |           |            |         |
| ECE                   |      |           |            |         |
| AURC                  |      |           |            |         |
| authority coverage    |      |           |            |         |
| false authorization   |      |           |            |         |
| review rate           |      |           |            |         |
| latency               |      |           |            |         |
| credits               |      |           |            |         |

---

## 8. Build Adaptive Mode Escalation

Instead of always invoking expensive/deep extraction:

```
STRUCTURE
     ↓ uncertain?
UNDERSTAND
     ↓ still uncertain?
AGENTIC
     ↓ still unsafe?
HUMAN
```

That is a genuinely nice product contribution.

ProofDesk becomes:

> **A risk-aware router over Nutrient's own document-processing depth.**

Experiment:

```
always text
always structure
always understand
always agentic
ProofDesk adaptive cascade
```

Then measure:

```
authority risk
review volume
latency
DWS credits
```

If the data shows the adaptive cascade approaches agentic-mode safety for less latency/credits, that is an outstanding result.

If it doesn't, report that.

Either result is interesting.

And it demonstrates unusually deep use of the sponsor API.

---

## 9. Use Nutrient's Own Grounding Research

Nutrient has released `grounding-en`, a 0.4B Apache-2.0 model specifically trained to answer:

> Does the source document actually support this extracted claim?

Its public results report ROC-AUC .923 for number grounding, .998 for dates, and .955 for strings on its English benchmark.

So add an optional signal:

```
raw DWS confidence
+
citation grounding / match label
+
grounding-en entailment score
+
cross-document rule status
```

Compare:

```
A. DWS confidence only
B. DWS confidence + citation grounding
C. B + grounding-en verification
D. C + cross-document assertions
E. full ProofDesk authority gate
```

Now the entire project becomes a love letter to Nutrient's technical philosophy.

Not:

> "We called your PDF API."

But:

> "We took your extraction API, confidence semantics, spatial grounding, processing modes and open grounding model and studied how they can form an authority layer for agents."

That is a serious sponsor entry.

---

## 10. The Main Paper Figure: Risk Versus Automation

Your existing metrics system already has the correct form of a standard risk–coverage curve: error among accepted cases versus the proportion automatically accepted.

Make the hero graph:

```
Y: False Authorization Rate
X: Automated Action Coverage
```

Curves:

```
DWS confidence only
DWS + grounding
DWS + calibrated confidence
DWS + cross-doc assertions
ProofDesk full gate
Oracle
```

The visual question is immediately understandable:

> How far toward the bottom-right can we move?

Low false authorization.

High automation.

No 30-second explanation of conformal prediction required.

---

## 11. Figure Set

Your final technical report only needs 6–8 strong figures.

**Figure 1 — Evidence-to-authority architecture**

```
PDF pixels
→ Nutrient extraction
→ source citations
→ grounded facts
→ reconciliation
→ risk calibration
→ authority gate
→ human review
→ artifact hash
→ action
```

**Figure 2 — Calibration**

Reliability diagram:

```
raw DWS confidence
vs
empirical field correctness
```

Possibly split by:

```
clean
degraded
```

**Figure 3 — Risk/coverage frontier**

The key graph above.

**Figure 4 — Degradation heatmap**

Rows = degradation.

Columns = severity.

Value = false-authority risk or extraction accuracy.

**Figure 5 — Nutrient mode frontier**

Perhaps:

```
x = latency / credits
y = authority accuracy
```

with four modes + adaptive cascade.

**Figure 6 — Human-review learning**

```
x = number of resolved cases
y = review rate
```

and another line:

```
observed automated error
```

The story:

> review falls, while risk remains bounded.

**Figure 7 — Failure atlas**

Four actual document snippets:

```
high confidence + wrong
low confidence + right
correct extraction + cross-document contradiction
post-approval tampering
```

This will look fantastic.

**Figure 8 — Reproducibility/audit**

One run receipt:

```
dataset hash
config hash
code SHA
raw output hash
decision hash
artifact hash
```

---

## 12. Interactive Site: ProofDesk Trust Lab

This should not be a normal dashboard.

Make it an **interactive scientific exhibit**.

Route:

```
/trust-lab
```

Hero:

> # When should document AI be allowed to act?
>
> Explore 480 controlled document trials using Nutrient DWS and ProofDesk.

### Section A — Break the document

Display one canonical insurance certificate.

Slider:

```
Clean ───────────── Severe corruption
```

Use **precomputed results**, not live API calls.

As slider changes:

```
DWS value:
2026-10-01

DWS confidence:
0.96 → 0.91 → 0.72 → 0.44

grounding:
exact → fuzzy → not_found

ProofDesk:
AUTO
AUTO
REVIEW
REVIEW
```

Then one button:

```
RUN THIS EXAMPLE LIVE
```

does an actual DWS call.

That gives reliability + live sponsor proof.

---

## 13. Interactive Risk-Budget Slider

```text
Maximum tolerated authority risk:

0.1% ───────────── 5%
```

As the judge moves it:

```
AUTO-AUTHORIZED      42%
HUMAN REVIEW         56%
BLOCKED               2%

certification:
PASS

upper 95% FAR:
0.83%
```

And the risk–coverage curve moves.

That turns your calibration research into something anyone understands in 10 seconds.

---

## 14. Add "Why Did It Abstain?"

Pick any point.

Trust Lab shows:

```
REVIEW_REQUIRED

Why?

Evidence completeness       PASS
DWS confidence              0.94
Source grounding            PASS
Cross-document agreement    FAIL
Policy check                FAIL
Human authority             MISSING
Artifact integrity          PASS
```

Then:

> "High extraction confidence did not override contradictory evidence."

That is the entire project thesis in one UI.

---

## 15. Add a Nutrient Mode Explorer

Four cards:

```
TEXT
STRUCTURE
UNDERSTAND
AGENTIC
```

Judge clicks each.

Show measured:

```
accuracy
latency
review rate
confidence calibration
credits
```

Then:

```
PROOFDESK ADAPTIVE
```

with measured result.

Nutrient explicitly markets these modes as speed/cost/depth choices. A sponsor engineer will immediately recognize that you explored their platform rather than just hit one endpoint.

---

## 16. Add the Human-Learning Experiment

ProofDesk already does something conceptually similar to recent document-AI work on selective human intervention.

The repo's human feedback path updates the online calibrator and records field correctness rather than treating review as a dead-end manual process.

So expose it experimentally.

Run:

```
deployment begins
↓
100 decisions
↓
review corrections arrive sequentially
↓
calibration updates
```

Graph:

```
review rate
│\
│ \
│  \
│   ──────
└────────── time

FAR
│──────── under risk target
└────────── time
```

Do **not** hardcode this projection. Generate it from replayed labeled observations.

---

## 17. Tamper Experiment

This one is deterministic and wonderfully simple.

For 100 generated approved PDFs:

```
original
flip one random byte
insert one character
modify amount
modify approval text
truncate
```

Expected:

```
100/100 modifications rejected by artifact hash
```

You can make an actual deterministic claim:

> Every tested post-approval byte modification changed the artifact digest and was rejected.

No ML uncertainty.

It visually contrasts:

```
probabilistic evidence
+
deterministic execution boundary
```

which is a very strong system design.

---

## 18. Determinism Experiment

Run identical document + schema repeatedly.

For each processing mode:

```
5 repeated calls × 20 documents
```

Measure:

```
value exact-match rate
confidence variance
citation variance
canonical response hash match rate
```

Nutrient emphasizes reproducible/deterministic output, particularly in non-VLM workflows.

This gives you an independently observed reproducibility table.

---

## 19. The Paper

Completely supersede the old `foxit/docs/PAPER.md`.

Do not delete it.

Move it conceptually into historical research.

New canonical paper:

```
paper/
  proofdesk_authoritybench.pdf
  proofdesk_authoritybench.tex
  references.bib
```

Title:

> **From Confidence to Authority: Risk-Calibrated Human-in-the-Loop Document Automation with Source-Grounded Evidence**

Subtitle if desired:

> **AuthorityBench: Evaluating When Document AI Should Act, Abstain, or Escalate**

Paper structure:

```
Abstract

1 Introduction
2 From extraction accuracy to authority risk
3 ProofDesk architecture
4 AuthorityBench
5 Experimental protocol
6 Nutrient DWS evaluation
7 Risk-budgeted abstention
8 Human-feedback adaptation
9 Integrity and reproducibility
10 Limitations
11 Related work
12 Conclusion
```

Keep it around **7–9 pages**, not 30.

---

## 20. What the Abstract Should Establish

Approximately:

```
Document AI benchmarks generally measure whether a field was extracted
correctly. Enterprise automation requires a harder question: whether the
available evidence is sufficient to authorize a downstream action.

We introduce AuthorityBench, a controlled benchmark for evidence-gated
document automation, and ProofDesk, a system combining source-grounded
Nutrient DWS extraction with cross-document validation, calibrated
abstention, human exception handling and content-addressed execution.

We evaluate extraction calibration, document degradation, processing-mode
tradeoffs, authority risk, human review burden and post-approval integrity.

Our results characterize the gap between extraction confidence and action
safety and show [ONLY WHATEVER THE RESULTS ACTUALLY SHOW].
```

The final sentence gets generated **after the experiment**.

No reverse engineering the data to fit the abstract.

---

## 21. Add a Reproducibility Capsule

At the paper/site bottom:

```
REPRODUCE THIS PAPER

git clone ...
make research

Code SHA:
f26d...

AuthorityBench:
v0.1

Dataset:
...

Nutrient API:
Data Extraction API

DWS modes:
text / structure / understand / agentic

Seeds:
...

Raw runs:
benchmarks/authoritybench/runs/

Generated figures:
research/figures/
```

And:

```bash
make paper
```

should:

```
validate benchmark manifests
regenerate all figures
regenerate tables
compile LaTeX
```

---

## 22. Generate Machine-Verifiable Run Receipts

Every run:

```json
{
  "run_id": "...",
  "timestamp": "...",
  "git_sha": "...",
  "dataset_sha256": "...",
  "config_sha256": "...",
  "dws_mode": "understand",
  "schema_sha256": "...",
  "seed": 42,
  "n_cases": 120,
  "raw_results_sha256": "...",
  "metrics_sha256": "..."
}
```

Then hash the receipt.

It creates a beautiful recursive story:

> ProofDesk produces auditable document decisions, and its benchmark results are themselves auditable.

---

## 23. Paper Badge in README

Above the fold:

```
[ LIVE DEMO ] [ TRUST LAB ] [ TECHNICAL PAPER ] [ REPRODUCE ]
```

Then:

> **480 controlled document trials · 4 Nutrient modes · source-grounded evidence · risk/coverage evaluation**

Obviously replace `480` with actual N.

No invented number.

---

## 24. The Resulting Demo Becomes Better Too

You don't even need to add much time to the 3-minute video.

After the main product flow:

### 2:40

> "We didn't choose the authority threshold arbitrarily."

Open Trust Lab.

### 2:45

Show risk–coverage graph.

> "We built AuthorityBench to measure the tradeoff between automation and false authorization."

### 2:52

Move degradation slider.

> "As evidence deteriorates, the system abstains rather than pretending confidence equals authority."

### 3:00

Show Nutrient mode comparison.

> "We also benchmarked Nutrient's processing modes and can escalate harder documents to deeper extraction."

### 3:08

Show paper.

> "Every figure is generated from committed benchmark artifacts and the full technical report is reproducible from the repo."

### 3:15

Done.

That is a **massive** "what the fuck, this is a hackathon submission?" moment without turning the actual demo into a lecture.

---

## 25. What NOT to Spend Time On

Do not spend remaining time:

- improving ULB credit-card fraud AUC
- running Cogym evolution for another 500 generations
- implementing 14 papers
- claiming EXTRACTCONF reproduction
- developing Foxit functionality
- inventing economic ROI
- making fictional convergence curves
- training your own model
- attempting to publish to arXiv before submission

An **arXiv-style PDF in the repository** is enough.

Call it:

> Technical preprint

not:

> arXiv paper

unless it has actually been submitted to arXiv.

---

## 26. Priority Stack

If time becomes constrained, the order is:

1. **CI green / canonical fixtures.**
2. **AuthorityBench controlled procurement dataset.**
3. **Real Nutrient DWS runs + raw result capture.**
4. **risk–coverage + calibration + degradation figures.**
5. **adaptive DWS mode comparison.**
6. **Trust Lab interactive page.**
7. **6–9 page paper generated from same results.**
8. grounding-en experiment.
9. determinism experiment.
10. expanded real public-document benchmark.

The first six are the win package.

---

## 27. The Strongest Potential Result

The dream result is **not**:

> ProofDesk gets 99.8% accuracy.

The killer result would look something like:

```
At an observed authority-risk target:

DWS confidence threshold:
  X% automation
  Y% FAR

+ source grounding:
  higher automation / lower FAR

+ cross-document assertions:
  substantially lower FAR

ProofDesk full gate:
  highest safe automation coverage

Adaptive DWS:
  similar safety to always-agentic
  lower measured cost/latency

Human learning:
  review rate falls with accumulated labels
  held-out FAR remains controlled
```

If the experiments support that, the narrative writes itself.

If they don't, the failure atlas becomes equally interesting:

> "Here are exactly the cases where source confidence fails, and here is why ProofDesk refuses them."

---

## 28. Why This Is Unusually Aligned with Nutrient Right Now

The timing is almost ridiculous.

Nutrient's own current technical positioning emphasizes:

- per-field confidence
- bounding boxes
- match labels
- source-grounded output
- human review
- multiple extraction modes
- open grounding benchmarks
- deterministic reproducibility

And **ConfBench appeared August 3, 2026**, specifically arguing that document AI needs calibration-aware evaluation because confidence is what determines which fields get automated versus reviewed.

ProofDesk's natural next question is:

> **Fine. Once the field is calibrated, when can the agent actually do something irreversible with it?**

That is the paper.

That is the Trust Lab.

That is the startup thesis.

And that gives the Nutrient submission a much deeper identity than "procurement PDF automation."

**Make `AuthorityBench + Trust Lab + technical preprint` the one major stretch goal, rather than adding any other product feature.**

---

## References

1. DevNetwork Hackathon 2026 — Nutrient challenge description
2. ConfBench — "Can You Trust the Confidence? ConfBench for Vision-Language Models on Document Extraction" (arXiv, August 3, 2026)
3. "Conformal Prediction for Risk-Controlled Medical Entity Extraction Across Clinical Domains" (arXiv, March 2026)
4. Nutrient Data Extraction API
5. Nutrient Data Extraction API accuracy benchmarks
6. nutrientdocs/grounding-en — Hugging Face
7. HIRA — "A Human-in-the-Loop Retrieval-Augmented Cascade for Document Classification in Regulated Industries" (arXiv, August 2026)
8. Nutrient vs Reducto comparison
9. Nutrient vs Docparser comparison
