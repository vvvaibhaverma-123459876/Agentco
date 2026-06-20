# NSE Phase 6 Better Agents — PRE-REGISTERED

**Date:** 2026-06-20
**Status:** Locked before data freeze and execution
**Mode:** Historical paper-only backtest on frozen real NSE data

## Objective

Retest AgentCo's calibration-weighted decision claim with stronger agents and the same integrity controls.

Prior canonical result on the already-frozen 126-session NSE sample was null:

- A equal-weighted: `-0.1907%`
- B trust-weighted: `-0.2217%`
- P random-placebo: `-0.0834%`

The Phase 6 hypothesis is that better calibrated, real-data-trained agents may produce a detectable calibration signal where toy technical agents did not.

## Dataset Freeze

The data freeze is part of this pre-registered procedure.

- Source: yfinance NSE tickers
- Field used for prediction and resolution: raw `Close`
- Adjusted close is not used because it can be retroactively rewritten by future splits/dividends.
- Window requested: `2019-01-01` through `2026-06-20`
- Frozen output directory: `evals/experiments/nse_phase6_data_frozen`

Instruments:

- NIFTY 50 (`^NSEI`)
- BANK NIFTY (`^NSEBANK`)
- RELIANCE (`RELIANCE.NS`)
- HDFCBANK (`HDFCBANK.NS`)
- TCS (`TCS.NS`)
- INFY (`INFY.NS`)
- ICICIBANK (`ICICIBANK.NS`)

If yfinance/network access is unavailable, Phase 6 execution is blocked rather than replaced with synthetic data.

## Split

For each instrument after freezing:

- Train: first 60% of chronological feature rows
- Validation/calibration: next 20%
- Test: final 20%

No random split is allowed. The primary A/B/P comparison is test-only.

## Agents

All agents are fixed before execution:

1. `LogisticCrossSectional`
   - Logistic regression with standard scaling.
   - Trained on pooled train rows from all instruments.

2. `GradientBoostingCrossSectional`
   - Gradient boosting classifier.
   - Trained on pooled train rows from all instruments.

3. `RandomForestCrossSectional`
   - Random forest classifier.
   - Trained on pooled train rows from all instruments.

4. `RegimeGradientBoosting`
   - Separate gradient boosting models for uptrend and downtrend train rows when enough samples exist.
   - Falls back to pooled gradient boosting otherwise.

## Features

Each row for prediction date `D` uses only rows with `Date < D`:

- return lags: 1, 2, 5, 10, 20 sessions
- rolling volatility: 10, 20, 60 sessions
- moving-average distance: 20, 50, 100 sessions
- RSI-like 14-session momentum
- volume z-score over 20 sessions
- trend/regime flags
- instrument one-hot features

Label: whether raw close on the next trading session is higher than raw close on prediction date.

## Confidence Calibration

Raw model probabilities are calibrated on validation only.

- For each agent, probability buckets are mapped to empirical validation hit rate.
- If a bucket has fewer than 20 validation samples, fallback to the agent's overall validation hit rate.
- Test confidence must never be fit on test outcomes.

## Arms

On each test date:

- A: equal-weighted ML agent views.
- B: trust-weighted ML agent views, using only validation history plus already-resolved test predictions.
- P: random-placebo weighted ML agent views, fixed RNG seed `42`.

All arms use the same paper capital and same signals. Only weighting differs.

## Paper Portfolio

- Initial paper capital: `1,000,000`
- Equal capital sleeve per active instrument.
- Max gross position per sleeve: `5%`
- Costless result and costed result both reported.
- Costed result uses:
  - 0.10% cost on absolute position change
  - fixed commission of 50 currency units per instrument trade

## Primary Success Criterion

Phase 6 supports a candidate calibration edge only if all are true on the held-out test split:

1. B beats P on total paper return.
2. B beats P on Sharpe-style ratio.
3. B beats P after transaction costs.
4. B beats P on more than 60% of instruments.

If these are not all true, the honest verdict remains null for this dataset/sample.

## Required Outputs

- Frozen dataset and metadata.
- Lookahead check result.
- A/B/P aggregate and per-instrument test returns.
- Costed A/B/P returns.
- Calibration curves on validation and test outcomes.
- Honest verdict with paper-only caveat.

