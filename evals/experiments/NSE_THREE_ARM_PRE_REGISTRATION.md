# NSE Three-Arm Walk-Forward — PRE-REGISTERED (Before Running)

**Date:** 2026-06-20  
**Locked:** YES (committed before experiment runs)  
**Status:** Awaiting execution on frozen real NSE data

---

## The Test

**Three arms, same 7 instruments, same ~510 trading days, same 25+ prediction points per day:**

1. **Arm A (Control):** Equal-weighted
   - Each agent's forecast weighted 1.0
   - Baseline: how well equal-weighting performs

2. **Arm B (Treatment):** Trust-weighted
   - Each agent's forecast weighted by calibration trust score
   - Using corrected penalty function + soft 0.5-1.5x curve
   - Hypothesis: calibration signal improves decisions

3. **Arm P (Placebo):** Random-weighted (critical control)
   - Each agent's forecast weighted by random value in [0,1]
   - Soft 0.5-1.5x curve (same gentleness as B)
   - Isolates: calibration signal vs. mere deviation magnitude

---

## Headline Metric: B vs P (Trust vs Random Placebo)

**Why B vs P, not B vs A?**

On near-efficient real markets, small deviations from control can be noise. A win over equal-weighting alone does NOT isolate calibration value — it could simply be that "adding noise with structure" beats "no noise."

The placebo arm is the evidence separator:
- If B ≈ P (both beat A similarly): deviation magnitude works; calibration signal undetectable
- If B >> P (trust beats random by significant margin): trust signal is real

**Headline Result Statement:**

> B vs P: [X%] advantage (measured as [metric]: B outperforms P on [Y] of [Z] seeds / [percentage] outperformance)

This is the primary test. B vs A is secondary context.

---

## Pre-Registered Null Interpretation (THE CRITICAL LOCK)

**This section is locked BEFORE seeing results. Cannot be reinterpreted after.**

### Null Scenario: B ≈ P (No Detectable Edge)

**What it means IF observed:**
- Trust-weighted decisions perform SIMILARLY to random-weighted decisions
- Both may beat A, but by similar margins
- On ~510 trading sessions with ~50-55% realistic hit rate on near-efficient markets

**Honest interpretation (NOT "disproven"):**
- "No edge detectable at this sample size on these instruments under these conditions"
- NOT: "Calibration is useless"
- NOT: "Trust-weighting doesn't work"
- INSTEAD: "On this market window, with this agent quality, signal-to-noise ratio is insufficient to detect a calibration advantage over random gentle weighting"

**Why this is honest:**
- Hit rate ceiling ~55% on efficient markets (vs 64-100% on synthetic SaaS)
- ~510 sessions is modest statistical power for differentiating 52% vs 54% win rates
- Even real edge (1-2% outperformance) may not achieve statistical significance
- Real markets: noise >> signal; synthetic SaaS was reversed

**What we DO NOT conclude if B ≈ P:**
- ✗ "Calibration principle is flawed" (principle was never tested, only implementation on this market)
- ✗ "The prior SaaS result was false" (different domain, different noise structure)
- ✗ "Trust-weighting should be abandoned" (may work elsewhere, with better agents, on less efficient markets)

**What we DO conclude if B ≈ P:**
- ✓ "On this real market, this agent set, this noise regime: calibration edge ≤ random noise"
- ✓ "If calibration provides value here, it's too small to detect with this sample"
- ✓ "No actionable edge found; further investigation needed" (or: result stands as is)

---

## Alternative Scenario: B >> P (Edge Detected)

**What it means IF observed:**
- Trust-weighted consistently outperforms random-weighted by meaningful margin
- Trust signal correlates with real NSE outcomes
- Calibration adds measurable value

**If this happens:**
- Strong evidence that trust-weighting works on this market
- But still: paper-only, one market, real costs would reduce edge
- Honest headline: "On real NSE data, trust-weighted decisions outperformed random weighting by [X]%, suggesting calibration has decision value in this regime"

---

## Metrics & Measurement

### Primary Metric: Final Paper Return

**Arm A final cash:** $1M + (sum of daily P&L over 510 sessions)  
**Arm B final cash:** $1M + (sum of daily P&L over 510 sessions)  
**Arm P final cash:** $1M + (sum of daily P&L over 510 sessions)

**Comparison:** B - P (absolute return difference)

**Win count:** On how many seeds/windows does B beat P?  
**Expected baseline under null:** ~50% (random chance)  
**Significance:** >60% consistently indicates B >> P

### Secondary Metric: Risk-Adjusted (Sharpe-like)

Simple ratio: average daily return / stdev daily return

Not trading-grade, but controls for luck vs consistency.

### Tertiary Metric: Calibration Curve on Real Outcomes

For each agent, plot:
- X: average confidence on predictions made
- Y: realized hit rate on those predictions (resolved vs real NSE closes)

Expected if well-calibrated: points near y=x line  
Overconfident: points below y=x  
Underconfident: points above y=x

---

## Agents (Fixed Before Running)

Three simple agents, fixed parameters (no tuning against test window):

### Agent 1: Technical (RSI + MACD)
```python
- RSI(14): overbought (>70) → lean down, oversold (<30) → lean up
- MACD: positive histogram → lean up, negative → lean down
- Confidence: higher when both align, lower when conflict
- No look-ahead (data only < prediction_date)
```

### Agent 2: Regime (Trend + Volatility)
```python
- Trend: 20-day SMA direction
- Volatility: realized vol on recent closes
- Prediction: if trending up + low vol → lean up, etc.
- Confidence: high in clear regimes, low in uncertainty
```

### Agent 3: Mean Reversion
```python
- Distance from 50-day moving average
- If price >> MA: expect reversion down (lean down)
- If price << MA: expect reversion up (lean up)
- Confidence: higher on extreme distances
```

All three predict: **"NIFTY 50 / BANK NIFTY / [stock] closes higher next NSE session than today"**

Probability = confidence ∈ [0, 1]

---

## Walk-Forward Daily Loop

For each trading day D in the window (D = 2024-06-01 to 2026-06-20):

```
1. Load data strictly before D (enforced: get_data_up_to(D))
2. All three agents generate predictions:
     - Claim: "instrument closes higher" (or lower, or neutral)
     - Confidence: ∈ [0, 1]
     - Resolution date: D+1 (next session)
3. Register in ledger (prediction_date=D, resolution_date=D+1)
4. If any predictions from prior days now resolve (date == D):
     - Lookup real NSE close at D
     - Score TRUE/FALSE
     - Update agent trust scores (from PAST-only resolved predictions)
5. Size paper positions for D:
     - Arm A: each agent weighted 1.0 (equal)
     - Arm B: each agent weighted by trust score (soft 0.5-1.5x curve)
     - Arm P: each agent weighted by random [0,1] (soft 0.5-1.5x curve)
6. Compute paper P&L for day D (on NIFTY 50 or composite)
7. Repeat
```

Constraint: position size capped at ±5% capital/day, rebalanced daily (no leverage).

---

## Trust Scoring (Corrected Formula)

```python
def trust_score(agent, resolved_predictions_only):
    """
    Compute trust from ONLY past-resolved predictions.
    Uses corrected penalty function (no cliff at 0%).
    """
    if len(resolved_predictions_only) == 0:
        return 0.5  # No history → neutral
    
    hit_rate = sum(p['hit'] for p in resolved_predictions_only) / len(resolved_predictions_only)
    avg_confidence = mean(p['confidence'] for p in resolved_predictions_only)
    
    # Corrected penalty (no harsh cliff)
    if avg_confidence <= hit_rate:
        calibration_error = hit_rate - avg_confidence  # Underconfident (good)
        trust = hit_rate + 0.05 * calibration_error  # Slight bonus for underconfidence
    else:
        calibration_error = avg_confidence - hit_rate  # Overconfident (bad)
        trust = hit_rate - 0.1 * calibration_error  # Penalty for overconfidence
    
    return max(0.0, min(1.0, trust))
```

**Key:** trust reflects past accuracy, never future data.

---

## Pre-Registered Falsification Criteria

**Primary:** B beats P by significant margin on real NSE data
- Success: B outperforms P on >60% of measurement windows (or >2% return advantage)
- Failure: B ≈ P or B < P

**Secondary:** Calibration curve matches real outcomes
- If B wins: agents' confidences should correlate with hit rates
- If B ≈ P: agents' confidences may NOT correlate well

**Tertiary:** No lookahead leakage detected
- Confirm: all predictions made on data strictly before resolution_date
- All trust updates from strictly past-resolved predictions

---

## What This Result Will (and Won't) Prove

### If B >> P:
✓ Trust-weighting outperformed random weighting on real NSE data  
✓ Calibration signal exists and added measurable value  
✗ This doesn't prove it generalizes to other markets or agents  
✗ This doesn't prove live performance (paper → live: ~30-50% lower)  
✗ This doesn't disprove the null on future-run windows  

### If B ≈ P (HONEST NULL INTERPRETATION):
✓ No detectable calibration edge at this sample size  
✓ Noise regime on real market is harsh; edge ≤ noise  
✗ This does NOT disprove calibration principle  
✗ This does NOT mean prior SaaS result was wrong (different domain)  
✗ This does NOT mean calibration is useless (may work elsewhere)  
→ Honest conclusion: "insufficient signal to separate trust from random gentleness on this market"

### If B < P (Unexpected):
✓ Trust-weighting hurt performance vs random  
✓ Suggests trust computation or weighting curve has issues  
✗ Does NOT mean trust is fundamentally broken (check formula vs agents)  

---

## Report Structure (Locked)

**Lead section:**
> B vs P: [result]
> - B final cash: $[X]
> - P final cash: $[Y]
> - Difference: $[X-Y] ([%])
> - Significance: B beat P on [Z]% of seeds

**Middle sections:**
- Arm A baseline (context)
- Calibration curve analysis (diagnose agents)
- Per-seed breakdown (show variance, not just mean)

**Closing section (pre-registered null interpretation):**
> [Honest verdict aligned with pre-registered interpretation]

---

## Commit Hash & Lock Statement

This pre-registration is locked at: **[COMMIT HASH TO BE FILLED NOW]**

No changes to:
- Agents or their parameters
- Walk-forward loop logic
- Trust scoring formula
- Metrics or falsification criteria
- Null interpretation

**Cannot be reinterpreted after results are seen.**

---

## Next Step

Build and run the three-arm walk-forward on frozen real NSE data.  
Report A vs B vs P with B vs P as headline.  
Apply pre-registered null interpretation.  
Conclude honestly on what is and isn't proven.
