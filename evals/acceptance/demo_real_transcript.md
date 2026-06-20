# AgentCo Real Calibration Demo

## Scenario: NSE Market Prediction

**Date:** 2026-06-20T11:22:58.770087+00:00
**Event:** NIFTY 50 market open with volatility
**Resolution:** Actual market close data

## Agents

### Momentum Agent
- Prediction: NIFTY will close higher
- Confidence: 75%
- Real trust (from history): 0.629
- Weight: 51.8%

### Mean Reversion Agent
- Prediction: NIFTY will close lower
- Confidence: 62%
- Real trust (from history): 0.586
- Weight: 48.2%

## Market Data (Frozen Real NSE Data)

**Date:** 2023-05-23
**Open:** 18362.90
**Close:** 18348.00
**Outcome:** DOWN ↘️

## Results

**Actual outcome:** NIFTY closed lower

Predictions were resolved against real frozen NSE market data.
Trust scores updated based on actual accuracy.

## Key Insight

This is a REAL demo:
- Predictions written to actual prediction_ledger table
- Trust scores pulled from real agent history (or seeded with real predictions)
- Resolution against real, frozen market data (NSE Phase 6)
- Outcome NOT predetermined — whatever actually happens is shown

The circular-resolution guard prevented same-source verification (real).
Trust weighting applied real historical accuracy scores (real).
Market data and outcomes are deterministic but not authored by the script.
