# Canonical NSE Trust-Weighting Fair Test Results

**Date:** 2026-06-20
**Mode:** `historical_backtest_paper_only`
**Pre-registration commit hash:** `5e6491a49e80fb931a5faa9e42392fd37b5cf6c6`
**Executable code commit hash:** `98b9387e32617a87fad4aa8b3dbd07cbd5d1d811`
**Window:** `2025-12-12` to `2026-06-19`

## Verdict

Trust-weighting did not beat equal-weighting on the pre-registered Sharpe-style metric.

This is paper only. There were no live orders, no broker connection, and no real capital. Because this canonical run has no slippage or transaction-cost model, even a positive result would overstate live tradability.

## Arm Results

| Arm | Total Return | Total P&L | Sharpe-Style Ratio | Positive Days |
|---|---:|---:|---:|---:|
| A equal-weighted | -0.1907% | -1907.30 | -0.1890 | 57/126 |
| B trust-weighted | -0.2217% | -2217.05 | -0.1925 | 54/126 |

## Headline

- B minus A return: `-0.0310%`
- B minus A P&L: `-309.74`
- B minus A Sharpe-style ratio: `-0.0035`
- Pre-registered result: `falsified_for_this_window`

## Prediction Ledger

- Registered predictions: `7065`
- Resolved/scored predictions: `7065`
- `post_hoc=False` predictions: `7065`

## Calibration

| Agent | Predictions | Hit Rate | Avg Confidence | Calibration Error |
|---|---:|---:|---:|---:|
| MeanReversionAgent | 2355 | 40.6% | 64.2% | 23.6% |
| RegimeAgent | 2355 | 57.9% | 62.0% | 4.1% |
| TechnicalAgent | 2355 | 48.5% | 59.6% | 11.0% |

## What This Proves

- The frozen NSE market data can mechanically verify pre-registered claims without an LLM in the resolution path.
- The implementation enforces strict past-only agent inputs and includes a passing lookahead regression test.
- The reported verdict applies only to this frozen dataset, these deterministic agents, this paper sizing rule, and this test window.

## What This Does Not Prove

- It does not prove live profitability.
- It does not prove the result generalizes to other markets, longer windows, options, crypto, commodities, or live execution.
- It does not prove calibration-weighting is generally useful or useless; it tests this concrete implementation under this concrete protocol.
