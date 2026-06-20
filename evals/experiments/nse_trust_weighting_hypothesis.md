# NSE Trust-Weighting Fair Test — PRE-REGISTERED

**Date:** 2026-06-20
**Status:** Locked before canonical fair-test execution
**Mode:** Historical backtest on frozen real NSE data, paper only

## Core Claim

AgentCo's calibration-weighted decisions should beat equal-weighted decisions.

## Hypothesis

Over the full pre-registered test window, Arm B (trust-weighted paper portfolio) will outperform Arm A (equal-weighted paper portfolio) on:

1. total paper return, and
2. a basic Sharpe-style ratio: mean daily paper return divided by daily-return standard deviation.

## Falsification

The hypothesis is falsified for this dataset/window if Arm B does not beat Arm A on risk-adjusted paper return. Total return is reported as primary economic context, but the pre-registered falsification criterion is the Sharpe-style ratio.

No sub-period cherry-picking is allowed. The full window must be reported.

## Dataset

- Frozen directory: `evals/experiments/nse_data_frozen`
- Source: yfinance NSE tickers, fetched previously into committed local CSV files
- Price field: raw `Close`
- Adjusted close is not used, because adjusted history can be retroactively rewritten after future splits/dividends.
- Invalid/malformed date rows are excluded from the trading calendar before any walk-forward loop.

Known limitations:

- yfinance may differ slightly from official NSE records.
- Raw close ignores dividend/split total-return accounting.
- Large-cap/index selection reduces illiquid-close noise but does not prove survivorship-bias-free behavior outside this fixed window.
- This is a historical backtest, not live or forward validation.

## Instruments

Index instruments:

- NIFTY 50
- BANK NIFTY

Large-cap NSE stocks:

- RELIANCE
- HDFCBANK
- TCS
- INFY
- ICICIBANK

## Test Window

- Start trading session: `2025-12-12`
- End trading session: `2026-06-19`
- Window length: 126 NIFTY trading sessions before filtering instrument-specific gaps

Resolution dates always map to actual trading sessions from the frozen instrument calendar, never naive calendar days.

## Prediction Types

Each agent emits the following pre-registered predictions where inputs are available:

1. `direction_next_session`
   - Claim: instrument closes higher on the next trading session than on the prediction date.
   - Resolution: compare raw close on `resolution_date` to raw close on `prediction_date`.

2. `relative_5_session`
   - Claim: each stock outperforms NIFTY 50 over the next 5 trading sessions.
   - Resolution: compare 5-session raw-close return of the stock to 5-session raw-close return of NIFTY 50.
   - Applies only to stocks, not index instruments.

3. `threshold_next_session`
   - Claim: instrument closes above its visible trailing 20-session moving average on the next trading session.
   - Resolution: compare raw close on `resolution_date` to the 20-session moving average computed only from data strictly before `prediction_date`.

## Agents

The agents are fixed before execution:

- `TechnicalAgent`: RSI-like momentum and MACD-like short/long moving average signal.
- `RegimeAgent`: 20-session trend and realized-volatility regime.
- `MeanReversionAgent`: distance from 50-session moving average.

Agents are deterministic and use no LLM in this test. Resolution is mechanical and uses no LLM.

## Lookahead Prevention

For a prediction date `D`, the agent input function returns rows with `Date < D` only. Rows with `Date >= D` are physically absent from the object passed to agents.

Any ambiguity about visible data is a stop-and-fix condition.

The implementation must include a passing lookahead-prevention test proving that predictions for `D` cannot read data from `D` or later.

## Walk-Forward Arms

On each trading session in the window:

1. Build agent inputs using strictly past rows only.
2. Register predictions with `post_hoc=False` and future `resolution_date`.
3. Resolve any predictions whose resolution date has arrived.
4. Update trust scores from resolved historical predictions only.
5. Size paper positions in parallel:
   - Arm A: equal-weighted agent directional views.
   - Arm B: trust-weighted agent directional views, using current resolved calibration only.

Both arms use the same paper capital and same underlying signals. Only weighting differs.

## Paper Portfolio

- Initial paper capital: `1,000,000`
- Per-instrument notional sleeve: equal capital allocation across instruments available that day.
- Max gross position per instrument sleeve: `5%`
- No leverage.
- No transaction costs or slippage in this canonical test.

Important caveat: no slippage model means paper results overstate real-world performance. Even a positive paper result is not evidence of live profitability.

## Trust Score

Trust for an agent is computed only from resolved predictions available before the current decision:

```python
hit_rate = hits / resolved_count
avg_confidence = mean(confidence)
if avg_confidence <= hit_rate:
    trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
else:
    trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
trust = clamp(trust, 0.0, 1.0)
```

Agents with no resolved history start at neutral trust `0.5`.

## Required Outputs

- Frozen data source/limitations documentation.
- Lookahead-prevention test result.
- Prediction ledger with `post_hoc=False`.
- Full-window Arm A vs Arm B paper P&L, daily and aggregate.
- Calibration curves: confidence vs realized hit rate on real market outcomes.
- Honest verdict stating what the result does and does not prove.

