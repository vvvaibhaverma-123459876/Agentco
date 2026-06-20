# NSE Walk-Forward Fair Test — PRE-REGISTERED HYPOTHESIS

**Date:** 2026-06-20  
**Status:** LOCKED (before walk-forward run begins)  
**Commit Hash:** (to be filled before agents run)

---

## The Claim Being Tested

**AgentCo's Core Claim:**  
"Calibration-weighted decision-making produces better outcomes than equal-weighted decision-making."

**Operationalized on Real Market Data:**  
Trust-weighted paper positions (Arm B) will outperform equal-weighted paper positions (Arm A) on NSE price prediction over the walk-forward test window.

---

## Design Principles (Anti-Lookahead)

This test is designed to make lookahead structurally impossible:

1. **All data is frozen before agents run**
   - Commit hash: [frozen NSE data with explicit date range]
   - Agents never see future data (code enforces cutoff_date < max_data_date)

2. **Predictions are point-in-time with unambiguous external resolution**
   - Each prediction specifies: the claim, confidence, resolution date, resolution rule
   - Resolution uses real NSE closes (happened data, exogenous, can't be rigged)
   - No LLM in resolution path — market is the verifier

3. **Walk-forward one trading day at a time**
   - On each day, agents predict using only past data
   - When predictions' resolution dates arrive, resolve against real closes
   - Trust scores update from resolved predictions (past-only data)
   - Paper positions sized using CURRENT trust scores (which contain no future signal)

---

## Test Window

**Period:** 2024-06-01 to 2026-06-20 (approximately 2 years of NSE trading)

**Instruments:**
- NIFTY 50 (index)
- BANK NIFTY (index)
- 5 large-cap NSE stocks: RELIANCE, HDFCBANK, TCS, INFY, ICICIBANK

**Reason:** Liquid, unambiguous closes, survivorship-bias-free for test window.

---

## Prediction Types (Exogenous, Resolvable)

Each agent makes predictions from the following menu (pick 2-3 most reliable):

### Type 1: Directional (Next Trading Day)
```
Prediction: "NIFTY 50 closes higher on [next NSE trading day] than [today's close]"
Confidence: [0.0-1.0], agent's honest estimate
Resolution: [next NSE trading day close] > [today close]
Base rate: ~50% (neutral market assumption)
```

### Type 2: Threshold (Specific Date)
```
Prediction: "[INSTRUMENT] closes above [level] on [specific NSE trading date]"
Confidence: [0.0-1.0]
Resolution: [actual close on date] > [level]
Level: e.g., 25000 for NIFTY, 55000 for BANK NIFTY
Base rate: ~50% (depends on level selection)
```

### Type 3: Relative (Multi-Day Performance)
```
Prediction: "[INSTRUMENT A] outperforms [INSTRUMENT B] over next [N trading days]"
Confidence: [0.0-1.0]
Resolution: [cumulative return A] > [cumulative return B]
Base rate: ~50%
```

**Why these types:**
- Exogenous: Outcomes determined by market, not agent design
- Unambiguous: Single numerical threshold, no interpretation needed
- Resolvable: Public market data provides ground truth
- Challenging: ~50% base rate makes 55-60% hit rates meaningful signal

---

## Agent Forecast Processes (What Agents Predict)

Three agents, each generating predictions independently:

### Agent 1: Technical Analyst
- Inputs: Historical price/volume, moving averages, RSI, MACD
- Prediction types: Directional (next day), Threshold (nearby levels)
- Confidence: High when signals align, low when conflicting
- **Data cutoff enforced:** Can only read data strictly before prediction_date

### Agent 2: Sentiment Analyst
- Inputs: Market news sentiment, VIX-style volatility signals, regime classification
- Prediction types: Directional, Relative performance
- Confidence: High when sentiment is extreme and coordinated
- **Data cutoff enforced:** Can only read sentiment/news data strictly before prediction_date

### Agent 3: Fundamental Analyst
- Inputs: Earnings estimates, sector rotation signals, macro indicators (if available)
- Prediction types: Threshold, Relative (sector-relative)
- Confidence: High when conviction is clear
- **Data cutoff enforced:** Can only read past earnings/sector data

**CRITICAL:** Each agent's forecast function takes prediction_date as a parameter and ASSERTS it can't access data on or after that date. This is the lookahead-prevention test.

---

## The Walk-Forward Engine

### Daily Loop
```
For each trading day D in the test window:
  1. Get data up to D-1 (enforced strict cutoff)
  2. Each agent generates predictions for:
     - Next trading day (resolution D+1)
     - Specific future dates (D+5, D+10, D+20)
  3. Register predictions in ledger (confidence, resolution_date, rule)
  4. Check if any predictions from past predict_dates now resolve
  5. Resolve against actual NSE close
  6. Update agent trust scores (only from resolved predictions)
  7. Size paper positions:
     - Arm A: Each agent's prediction weighted 1.0 (equal)
     - Arm B: Each agent's prediction weighted by trust[agent]
  8. Update paper P&L
  9. Continue
```

### Paper Position Sizing

**Example: NIFTY Directional Prediction**
```
Agent Technical predicts: "NIFTY up next day" with confidence 0.65, trust 0.72
Agent Sentiment predicts: "NIFTY down next day" with confidence 0.58, trust 0.45
Agent Fundamental predicts: "NIFTY sideways" → neutral, confidence 0.50, trust 0.80

Arm A (Equal-weight):
  Signal = (+1 * 0.65 + -1 * 0.58 + 0 * 0.50) / 3 = +0.023
  Position = capital * 0.023 (bet $1 up per $50 capital)

Arm B (Trust-weight):
  Signal = (+1 * 0.65 * 0.72 + -1 * 0.58 * 0.45 + 0) / (0.72+0.45+0.80)
         = (+0.468 - 0.261 + 0) / 1.97 = +0.105
  Position = capital * 0.105 (trust upweights agents with higher past accuracy)
```

**Sizing constraints:**
- Max position per day: ±5% of paper capital
- No leverage, no shorting (conservative, befit paper-only)
- Flat at close of each day (daily rebalance)

---

## Pre-Registered Success Criteria

### Primary Metric: Total Paper Return
```
Test statistic: Arm B final value - Arm A final value
Hypothesis: Arm B - Arm A > 0 (trust-weighting adds value)
Falsification: Arm B - Arm A <= 0 (trust-weighting fails)
```

### Secondary Metric: Risk-Adjusted Return (Simple Sharpe-Like)
```
Sharpe ≈ average_daily_return / stdev_daily_return
Hypothesis: Sharpe_B > Sharpe_A
This controls for luck; a lucky month shouldn't count as edge
```

### Diagnostic: Agent Calibration Curve
```
For each agent, plot: average confidence vs realized hit rate
Expected if calibrated: points should lie near y=x line
If points lie above: agent is overconfident (said 65% confidence, only hit 50%)
If points lie below: agent is underconfident (said 50%, actually hit 65%)
```

---

## Falsification Criteria (Hard Stops)

**Hypothesis is FALSIFIED if ANY of these occur:**

1. **Arm B does NOT beat Arm A on total return**
   - Even by small amount, trust-weighting must add value

2. **Arm B has worse Sharpe than Arm A**
   - Victory must come from superior predictiveness, not just luck

3. **Lookahead is detected at any point**
   - Any agent reads data on or after prediction_date → test invalid, stop

4. **Agent calibration curves are clearly divergent**
   - If agents' stated confidences don't match realized hit rates, trust scoring is fundamentally broken

---

## What This Test Does (and Does NOT) Prove

### If Trust-Weighting Wins
✓ On this specific set of agents and instruments, calibration-weighting added value
✓ On real market data over ~2 years of history
✓ In paper trading (no slippage, no commissions, no real capital pressure)
✓ The trust-scoring methodology worked on real exogenous outcomes

✗ This does NOT prove calibration helps on live trading
✗ This does NOT prove it generalizes to other agents/instruments
✗ This does NOT mean edge is large enough to overcome real-world costs
✗ Real-world performance would likely be 30-50% lower (slippage, commissions, psychology)

### If Trust-Weighting Loses
✓ On these agents, trust-scoring either didn't work or agents were poor quality
✓ Equal-weighting was at least as good as trust-weighting

✗ This does NOT prove calibration is useless (agents or scoring may be fixable)
✗ This does NOT prove the synthetic B2B test was wrong (different domain)
✗ This does NOT mean the principle is unsound (implementation may be)

---

## Commitment

This hypothesis is LOCKED at this commit. No changes to:
- Test window dates
- Instruments
- Prediction types
- Confidence scoring rules
- Position sizing rules
- Falsification criteria

If bugs are found during testing, they will be fixed, but the test will be RE-RUN from the start (not patched mid-stream).

---

## Timeline

1. **Now:** Freeze NSE dataset + lock this hypothesis (commit)
2. **Next:** Implement agent forecast functions (with lookahead tests)
3. **Next:** Run walk-forward simulation over full test window
4. **Next:** Generate paper P&L, calibration curves, final report
5. **Final:** Publish results with full transparency on what was proven vs. not

---

## Honest Caveat

This test uses REAL market data, which is powerful and honest. But:

- Markets are near-efficient; any edge will be small (1-2% annual outperformance is already very good)
- 2 years of history contains ~500 trading days; this is limited statistical power
- Paper trading ignores real costs; live performance would be 30-50% lower
- Agent quality matters critically; poor agents will fail, good agents may still fail due to randomness

**The bar for "success" is: trust-weighting beats equal-weighting on paper, using real market data, with no lookahead leakage.**

**That is a legitimate, real test. It will be conducted fairly.**

---

## Commit Hash for This Document

[To be filled before agents run]

Commit hash of frozen NSE data: [To be filled]

No changes after this point.
