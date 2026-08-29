# Confidence Calibration Research — Complete Reference

## 1. Confidence Calibration for Agents

### UCCI (2026)
Token-margin uncertainty + isotonic regression → calibrated error probabilities (ECE=0.03).
- Extract per-token margin: `m_t = p_top1 - p_top2`
- Aggregate: `u(x) = 1 - mean(margins)`
- Calibrate via isotonic regression

### MARGIN (2026)
Online calibration for multi-agent systems. Per-agent, per-confidence-band factors learned from the task stream. No model access, no held-out data. 3-6x lower calibration error than design-time baselines under distribution shift.
**Key finding:** raw verbalized confidence fails to beat random on hard tasks (43-50% pairwise resolution).

### HTC (2026)
Holistic Trajectory Calibration. 48 process-level features across 4 categories (cross-step dynamics, intra-step stability, positional, structural). Simple logistic model achieves best ECE on out-of-domain GAIA benchmark. The General Agent Calibrator (GAC) transfers across domains.

### Agentic Confidence Calibration (2026)
First formalization of the problem. Key insight: compounding errors along trajectories means single-turn calibration methods fail. Need trajectory-level features.

## 2. Conformal Risk Control (Statistical Guarantees)

### ToolChain-CRC (2026)
Treats each agent run as a full trajectory. Step-level risk scores → trajectory risk → accept-or-intervene rule with drift detection. Key result: final-answer-only calibration misses retrieval and tool failures. Trajectory-level calibration keeps risk below target.

### Conformal Risk Control (Angelopoulos et al., ICLR 2024)
The foundational 5-line algorithm. Control expected value of any monotone loss.
Core: `λ* = min{λ : upper_bound(R(λ)) ≤ α}`

### Role-Stratified CRC (2026)
Per-field risk budgets for different argument roles. Critical for signing: the signer field has different risk than the document_body field. Aggregate certification dilutes rare-role failures by 1/p_r.

### Impossibility Bound (Kotte 2026)
When base risk µ > α, any method must abstain on ≥ (µ-α)/(1-α) examples. Gives a feasibility test before running CRC.

## 3. Decision-Theoretic Foundations

### BAS (2026)
Behavioral Alignment Score. Decision-theoretic metric for answer-or-abstain utility. Asymmetric penalty that strongly prioritizes avoiding overconfident errors. Key: truthful confidence uniquely maximizes expected BAS utility.

### Behavioral Credibility Trilemma (2026)
Proves no RL policy with confidence-gated autonomy can simultaneously achieve helpfulness, calibration, and autonomy. The inflation magnitude scales as w_A/(2w_C). Detection requires Θ(1/Δ²) observations.

### Calibration Is Not Control (2026)
The central paper. Two trajectory prefixes can have the same risk estimate while requiring different actions. Intervention advantage (expected utility gain from intervening) is the correct decision object, not scalar risk. Calibrating the same scalar improves prediction but leaves control regret unchanged.

## 4. Nutrient DWS Confidence Signals

Nutrient provides per-field confidence signals:
- `confidence` — composite score 0-1 (relative, uncalibrated)
- `match` label — id_match (exact, grounded), fuzzy_match (uncertain), not_found (ungrounded)
- `confidenceComponents` — breakdown: probabilityScore, marginScore, groundingScore, formatScore
- `recognitionScore` — OCR confidence per matched block
- `bbox` — bounding box for source verification

**Key from Nutrient:** "A confidence score tells you how sure the model was. A grounded confidence score also tells you what the model was sure about — and both are needed." Their NLI groundedness model shifts from "how decisive was the model?" to "does the source support the value?"

## 5. Existing Implementations

| Repo | What |
|------|------|
| [Lelu](https://github.com/Lelu-ai/lelu) | Agent calibration |
| [CORA](https://github.com/ys-feng/CORA) | Confidence calibration |
| [ToolChain-CRC](https://github.com/jopoku16/toolchain-crc) | Trajectory-level conformal risk |
| [conformal-risk](https://github.com/aangelopoulos/conformal-risk) | Foundational CRC implementation |
| [Selective Prediction Toolkit](https://github.com/ercedut/selective-prediction-toolkit) | Selective prediction baselines |
| [LLM Confidence Benchmark](https://github.com/NIKHIL0VERMA/LLM-Confidence-Calibration-Benchmark) | Calibration benchmarks |

## 6. Key Metrics

### Risk-Coverage Curve
For each threshold τ:
- Coverage = fraction of documents auto-signed
- Risk = error rate among auto-signed documents
- Conformal guarantee: at threshold τ*, error rate ≤ α with probability 1-δ

### BAS (Behavioral Alignment Score)
Decision-theoretic metric balancing calibration with abstention utility. Asymmetric penalty prioritizes avoiding overconfident errors.

### ECE (Expected Calibration Error)
Difference between predicted confidence and actual accuracy. Lower = better calibrated.

### Brier Score
Mean squared difference between predicted probability and outcome. Lower = better.
