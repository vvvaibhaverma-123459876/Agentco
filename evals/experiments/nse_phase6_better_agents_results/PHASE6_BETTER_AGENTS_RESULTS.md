# NSE Phase 6 Better Agents Results

**Date:** 2026-06-20
**Mode:** `historical_backtest_paper_only`
**Pre-registration commit hash:** `93c3b6d0f1321dbbf635762e52b82365a8baf087`
**Executable code commit hash:** `f2b2626791897accf9a709254d00d364811c7b29`

## Lookahead Check

- Passed: `True`

## Verdict

Phase 6 remains a null under the pre-registered criteria.

This is paper only: no live orders, no brokerage connection, and no real capital.

## Split

- Train rows: `7237` (2019-07-01 to 2023-08-31)
- Validation rows: `2413` (2023-08-30 to 2025-01-27)
- Test rows: `2413` (2025-01-23 to 2026-06-18)

## A/B/P Test Returns

| Arm | Return | P&L | Sharpe-style | Positive Days |
|---|---:|---:|---:|---:|
| A_equal | -0.1732% | -1731.77 | -0.0363 | 165/348 |
| B_trust | -0.1724% | -1723.74 | -0.0360 | 166/348 |
| P_random | -0.1228% | -1227.65 | -0.0250 | 172/348 |
| A_equal_costed | -8.9458% | -89457.52 | -1.6284 | 18/348 |
| B_trust_costed | -12.5297% | -125297.38 | -2.5357 | 6/348 |
| P_random_costed | -12.5575% | -125575.15 | -2.4833 | 6/348 |

## Headline

- B-P return: `-0.0496%`
- B-P Sharpe-style: `-0.0110`
- Costed B-P return: `0.0278%`
- B beats P instrument share: `28.6%`

## Per-Instrument B vs P

| Instrument | B Return | P Return | B-P | Costed B-P |
|---|---:|---:|---:|---:|
| BANK NIFTY | -0.0160% | 0.0829% | -0.0989% | -0.0169% |
| HDFCBANK | 0.3018% | 0.5213% | -0.2195% | -0.1269% |
| ICICIBANK | 0.2342% | 0.4291% | -0.1949% | -0.1313% |
| INFY | -1.1036% | -1.3490% | 0.2454% | 0.3226% |
| NIFTY 50 | -0.2402% | -0.2269% | -0.0133% | 0.0278% |
| RELIANCE | 0.2634% | 0.3905% | -0.1271% | -0.0376% |
| TCS | -0.5456% | -0.5779% | 0.0323% | 0.1183% |

## Test Calibration

| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |
|---|---:|---:|---:|---:|
| GradientBoostingCrossSectional | 2413 | 47.8% | 51.6% | 3.7% |
| LogisticCrossSectional | 2413 | 50.4% | 51.1% | 0.6% |
| RandomForestCrossSectional | 2413 | 47.8% | 51.7% | 3.9% |
| RegimeGradientBoosting | 2413 | 49.3% | 51.8% | 2.6% |
