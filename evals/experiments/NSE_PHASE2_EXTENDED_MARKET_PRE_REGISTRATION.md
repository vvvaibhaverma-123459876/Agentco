# NSE Phase 2 Extended Market Testing — PRE-REGISTERED

**Date:** 2026-06-20
**Status:** Locked before Phase 2 execution
**Prior result:** STOP 2 and Phase 1 found no robust calibration edge on frozen real NSE NIFTY data. Phase 1 alternatives still trailed random-placebo on held-out data.

## Objective

Phase 2 checks whether the null result is specific to one instrument/window or whether it persists across the frozen real NSE instruments currently available in the repository.

This phase does not fetch data. It only uses already-frozen files.

## Available Frozen Inputs

- Data directory: `evals/experiments/nse_data_frozen`
- Real files only: `*_REAL.csv`
- Current frozen real coverage: approximately `2024-06-03` to `2026-06-19`
- Instruments:
  - NIFTY 50
  - BANK NIFTY
  - HDFCBANK
  - ICICIBANK
  - INFY
  - RELIANCE
  - TCS

## Explicit Phase 2 Scope Constraint

The original Phase 2 plan requested:

- 2022-2024 and 2020-2022 windows
- options, crypto, commodities
- 1,500+ trading days

Those tests are not run in this phase because the required frozen data is not present in the repo and online fetching is disallowed. They remain future Phase 2b work after data is frozen and pre-registered.

## Fixed Test Design

For each frozen real instrument:

1. Run the same three agent families on that instrument's strictly past close/volume series:
   - Technical: RSI + MACD
   - Regime: 20-day trend + realized volatility
   - MeanReversion: 50-day moving average distance
2. Generate next-session directional predictions.
3. Compute daily paper P&L on that same instrument.
4. Compare:
   - Arm A: equal weighted
   - Arm B: original STOP 2 trust weighted
   - Arm P: random-placebo weighted, fixed seed `42`
   - Candidate: Phase 1 closest alternative, `recency_weighted + sigmoid`

All trust scores are computed only from past resolved predictions for the same agent and instrument.

## Windows

For each instrument, report:

- `full`: all available frozen dates for that instrument
- `first_half`: first chronological half
- `second_half`: second chronological half
- non-overlapping 126-trading-day blocks where enough data exists

The headline aggregate uses all market-window cells with at least 100 evaluated days.

## Primary Metrics

1. B vs P return difference per market-window cell.
2. Count/share of market-window cells where B beats P.
3. Median B-P return difference across cells.
4. Per-agent calibration:
   - hit rate
   - average confidence
   - calibration error
   - confidence-bin calibration curve

## Locked Interpretation

If B beats P in more than 60% of eligible cells and median B-P is positive, Phase 2 finds a candidate market/window-dependent calibration signal. It is not an edge claim until retested on older periods and alternative asset classes.

If B is approximately equal to or worse than P across cells, the STOP 2 null generalizes across the frozen NSE spot/large-cap set currently available.

If the Phase 1 candidate beats P while original B does not, the result is a Phase 3/Phase 2b candidate only. It must be retested on newly frozen windows before any claim.

## Success Criteria

- No lookahead leakage: all visible data is strictly before `prediction_date`.
- No online fetching.
- Fixed RNG seed.
- Results include calibration curves.
- Results record this pre-registration commit hash and executable code commit hash.

