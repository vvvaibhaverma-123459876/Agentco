# NSE Phase 1 Root Cause Investigation — PRE-REGISTERED

**Date:** 2026-06-20
**Status:** Locked before Phase 1 diagnostic execution
**Prior result:** STOP 2 found B ≈ P on frozen real NSE data because all agents were overconfident (about 43% hit rate vs 65% confidence).

## Objective

Phase 1 investigates why calibration-weighted decisions failed to separate from random-placebo weighting on real NSE data.

This is a diagnostic and optimization-screening study, not a claim of live trading edge.

## Frozen Inputs

- Data directory: `evals/experiments/nse_data_frozen`
- Real files only: `*_REAL.csv`
- Primary traded instrument for scoring: NIFTY 50, matching STOP 2
- No online fetching is allowed.
- Every prediction must use data strictly before `prediction_date`.

## Split

The chronological sample is split as follows:

- Train/history: first 50% of trading sessions
- Validation: next 25%
- Held-out test: final 25%

Phase 1 reports all diagnostics, but any return comparison between trust formulas/curves is interpreted from the held-out test segment only.

## Fixed Diagnostics

### 1. Agent Miscalibration Analysis

For each agent:

- Prediction count
- Hit rate
- Average confidence
- Calibration error: `avg_confidence - hit_rate`
- Binned calibration curve by confidence bucket
- Market regime calibration buckets:
  - trend: `uptrend` or `downtrend` based on latest close vs trailing 20-day SMA
  - volatility: `low`, `normal`, `high` based on trailing 20-day log-return volatility
- Indicator diagnostics:
  - Technical agent: RSI signal bucket and MACD signal bucket
  - Regime agent: trend and volatility buckets
  - MeanReversion agent: side of trailing 50-day moving average and distance bucket

Primary root-cause test:

- If hit rate remains materially below confidence across most agents/regimes, the root cause is agent miscalibration rather than weighting mechanics.
- If one agent/regime has materially lower calibration error, it becomes a candidate for Phase 3 model refinement.

### 2. Trust Scoring Optimization

The following formulas are fixed before execution. Trust scores use only past resolved predictions available before the decision date.

1. `original`
   - Existing STOP 2 formula: `hit_rate - 0.1 * max(avg_confidence - hit_rate, 0)` with small underconfidence bonus.

2. `confidence_adjusted`
   - `trust = hit_rate / avg_confidence`
   - Clamped to `[0, 1]`.

3. `recency_weighted`
   - Exponential weighted hit rate and confidence.
   - Half-life: 63 trading days.
   - Same calibration penalty shape as `original`.

4. `regime_adjusted`
   - Same formula as `original`, but computed on past predictions from the current regime (`trend|volatility`) when at least 20 matching past predictions exist.
   - Falls back to all past predictions for that agent otherwise.

### 3. Weighting Curve Refinement

The following curves are fixed before execution:

1. `linear`
   - Agent portfolio weight equals trust score.

2. `dynamic_clipped`
   - Penalizes overconfidence by multiplying trust by `max(0.25, 1 - calibration_error)`.

3. `sigmoid`
   - Non-linear penalty around neutral trust:
   - `weight = 1 / (1 + exp(-8 * (trust - 0.5)))`

Each formula/curve pair is evaluated on held-out final 25% returns against:

- Equal-weighted baseline
- Random-placebo baseline with fixed RNG seed `42`

## Null Interpretation

If alternative formulas and curves still perform approximately like random-placebo on held-out data, the locked interpretation is:

> The STOP 2 null is robust to reasonable trust-score and weighting-curve changes. The bottleneck is agent quality and market noise, not the specific trust formula.

If one formula materially beats placebo on held-out data, the locked interpretation is:

> This is a candidate signal only. It must be retested in Phase 2 across other windows/markets before any edge claim.

## Success Criteria

- No lookahead leakage: all forecasts use strictly past data.
- Reproducible fixed seeds.
- Calibration curves are generated as the primary diagnostic.
- Held-out comparison identifies whether improvement is real enough to justify Phase 2 retesting.
- Pre-registration commit hash is recorded in result artifacts.

