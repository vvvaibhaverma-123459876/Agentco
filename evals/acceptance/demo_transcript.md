# AgentCo Demo Transcript

## Scenario: Market Decision Under Calibration

**Time:** 2026-06-20 06:30 UTC
**Event:** TECH sector drops 8% on earnings surprise
**Decision:** Should we rebalance?

## Agents and Predictions

### Momentum-Trader-Bot
- **Claim:** TECH sector will continue falling (another 3-5% down) by market close
- **Confidence:** 92%
- **Trust Before:** 0.820
- **Prediction ID:** b48ef292-261...

### Mean-Reversion-Agent
- **Claim:** TECH sector will partially recover (rebound 2-3%) by market close
- **Confidence:** 78%
- **Trust Before:** 0.610
- **Prediction ID:** 282d99fb-c0a...

### Macro-Risk-Monitor
- **Claim:** Broad market will decouple from TECH; S&P 500 will gain 0.5% today
- **Confidence:** 61%
- **Trust Before:** 0.540
- **Prediction ID:** 83df380f-a7e...

## Calibration Weights

- **Momentum-Trader-Bot:** 41.6%
- **Mean-Reversion-Agent:** 31.0%
- **Macro-Risk-Monitor:** 27.4%

## Circular Verification Guard

✓ Successfully blocked attempt to resolve via claim source.
✓ Prevented circular reasoning.

## Resolution

Reality: XYZ closed down 6.2%, confirming continued decline. Momentum-Trader-Bot was correct.

## Final Insight

AgentCo applies **calibration-weighted decision-making** where trust scores
from past performance influence current decisions. This differs from equal
weighting (typical) or random weighting (control).

The system also enforces source independence and maintains an immutable
audit trail. Both prevent the kinds of blind spots that plague typical
autonomous systems.