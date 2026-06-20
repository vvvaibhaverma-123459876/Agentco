# NSE Phases 3-5 — PRE-REGISTERED

**Date:** 2026-06-20
**Status:** Locked before Phase 3-5 execution
**Prior result:** STOP 2, Phase 1, and Phase 2 found no robust calibration edge on frozen real NSE spot/large-cap data.

## Objective

Implement the remaining feasible offline work:

- Phase 3: agent improvement with trained models, train/validation/test split, and regime-specific agents.
- Phase 4: transaction-cost and risk-management simulation on the held-out test split.
- Phase 5: documentation and reusable toolkit extraction.

Live brokerage/paper-to-live validation is explicitly not executed because it requires external live systems and small-capital trading authorization.

## Frozen Inputs

- Data directory: `evals/experiments/nse_data_frozen`
- Real files only: `*_REAL.csv`
- No online fetching.
- Every feature row for date `D` must use data strictly before `D`.

## Phase 3 Fixed Design

For each frozen real instrument:

1. Build daily feature rows with strictly past data:
   - return lags
   - rolling volatility
   - moving-average distance
   - RSI-like momentum
   - volume z-score
   - trend/regime flags
2. Label: whether next close is higher than current close.
3. Split chronologically:
   - train: first 50%
   - validation: next 25%
   - test: final 25%
4. Train fixed model agents:
   - `LogisticRegression`
   - `GradientBoosting`
   - `RegimeSpecificGradientBoosting`, with separate models for uptrend and downtrend rows when enough samples exist.
5. Calibrate confidence using validation only:
   - confidence = empirical validation hit rate for the probability bin
   - fallback = validation agent hit rate

## Phase 4 Fixed Design

On test rows only, compare:

- `equal_ml`: equal-weight ML ensemble
- `trust_ml`: trust-weighted ML ensemble, initialized from validation resolved predictions and updated walk-forward on test
- `random_ml`: random-placebo weighted ML ensemble, fixed seed `42`
- `risk_managed_trust_ml`: trust-weighted ML with:
  - max gross position: 5% capital
  - half exposure after 1% strategy drawdown
  - halt exposure for 5 sessions after 2% strategy drawdown
- `costed_risk_managed_trust_ml`: same as risk managed with transaction costs:
  - 0.10% slippage/spread on absolute position change
  - fixed commission: 50 currency units per trade

The primary comparison remains trust vs random-placebo on held-out test data. Cost/risk results are feasibility diagnostics, not edge claims.

## Phase 5 Outputs

- Research-paper draft summarizing methods and null findings.
- Reusable toolkit modules:
  - frozen data loader
  - walk-forward helpers
  - calibration analyzer
  - trust scoring
- Internal documentation with lessons learned and blocked live-validation items.

## Locked Interpretation

If `trust_ml` beats `random_ml` in more than 60% of instruments and median trust-random return is positive, Phase 3 finds a candidate signal requiring Phase 2b retesting on older and alternative frozen datasets.

If `trust_ml` approximately equals or trails `random_ml`, improved agents did not rescue the calibration edge on the available frozen NSE dataset.

If transaction costs eliminate returns, live deployment remains unsupported regardless of paper outperformance.

## Success Criteria

- No lookahead leakage.
- Pre-registration commit hash and executable code hash recorded.
- Results reproducible with fixed seeds.
- Calibration curves included as primary diagnostics.
- Honest blocked-items documentation for live validation and missing datasets.

