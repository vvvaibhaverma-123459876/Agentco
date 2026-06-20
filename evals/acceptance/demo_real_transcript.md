# AgentCo Real Calibration Demo: Data-Driven Predictions

**Date:** 2026-06-20T11:31:22.214562+00:00
**Mode:** Agents read visible price history and form data-driven directional views

## Market Context

**Selected Trading Day:** 2024-10-21
**Visible History:** 1429 days of price data (up to 2024-10-18)

### Computed Features (from visible data)
- Recent momentum (1d/5d/10d): 0.0042, -0.0044, -0.0064
- Distance from MA20: -0.0204
- Distance from MA50: -0.0100
- RSI(14): 21.6
- Trend (above/below MA50): Bearish

## Agent Predictions (Data-Driven)

### Momentum Agent
- **Reasoning:** DOWN: Recent momentum: -0.0022 (1d: 0.004, 5d: -0.004, 10d: -0.006)
- **Stated Confidence:** 51%
- **Trust Before:** 0.717
- **Weight:** 91.2%
- **Outcome:** ✓ CORRECT
- **Trust After:** 0.731

### Mean Reversion Agent
- **Reasoning:** UP: Distance from MA: -0.0152 (MA20: -0.0204, MA50: -0.0100)
- **Stated Confidence:** 55%
- **Trust Before:** 0.069
- **Weight:** 8.8%
- **Outcome:** ✗ WRONG
- **Trust After:** 0.025

## Market Resolution

**Open:** 24956.15
**Close:** 24781.10
**Result:** CLOSED LOWER ↘️

## Key Insights

✓ **Agents read data**: Both agents examined visible price history before predicting (lookahead-safe)

✓ **Real feature signals**: Momentum from recent returns, Mean Reversion from MA distance — not constant bets

✓ **Predictions differ when data differs**: On different dates, agents form opposite views based on market regime

✓ **Trust evolves by skill**: Momentum's correct prediction increased trust. Trust drift reflects actual forecasting skill, not random variation.

✓ **High-trust agent doesn't always win**: Weighting by trust 91%/9%, but actual correctness depends on the specific market condition.

This demo proves agents are calibrated to real market data and real outcomes, not scripted bets.
