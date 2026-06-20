# NSE Walk-Forward Architecture — Implementation Guide

**Date:** 2026-06-20  
**Scope:** Design document for NSE-based fair test with structural lookahead prevention

---

## System Components (Layered)

```
┌─────────────────────────────────────────────────────────────────┐
│ Data Layer (FROZEN, External Verifier)                          │
│ ├─ NSE OHLC CSV files (committed, immutable)                    │
│ ├─ Metadata (source, limitations, freeze date)                  │
│ └─ Lookahead prevention: get_data_up_to(date) returns < date    │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────┐
│ Agent Layer (PREDICTION ISOLATION)                              │
│ ├─ Agent 1 (Technical)   → Technical Analysis Module            │
│ ├─ Agent 2 (Sentiment)   → Sentiment Analysis Module            │
│ ├─ Agent 3 (Fundamental) → Fundamental Analysis Module          │
│ └─ CONSTRAINT: Each agent(prediction_date) asserts               │
│    "cannot read data >= prediction_date"                        │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────┐
│ Prediction Ledger (SCHEMA)                                      │
│ ├─ agent_name: str                                               │
│ ├─ prediction_date: date                                         │
│ ├─ prediction_type: str ("directional" | "threshold" | "rel")   │
│ ├─ instrument: str (e.g., "NIFTY 50")                            │
│ ├─ claim: str (e.g., "closes higher")                            │
│ ├─ confidence: float [0, 1]                                      │
│ ├─ resolution_date: date (when we'll know the outcome)           │
│ ├─ resolution_rule: str (e.g., "close > 20000")                  │
│ ├─ posted: datetime (when prediction was recorded)               │
│ ├─ resolved: bool                                                │
│ ├─ resolution_value: float (e.g., actual close)                  │
│ ├─ hit: bool (resolved and claimed > resolved)                   │
│ └─ metadata: dict (original signal, model version, etc.)         │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────┐
│ Trust Scoring (CALIBRATION)                                     │
│ ├─ For each agent:                                               │
│ │  ├─ Total predictions made                                     │
│ │  ├─ Total predictions resolved (so far)                        │
│ │  ├─ Hits (predictions that were correct)                       │
│ │  ├─ Hit rate = hits / resolved                                 │
│ │  ├─ Confidence calibration error                               │
│ │  └─ Trust score = f(hit_rate, calibration_error)               │
│ └─ Trust scores update ONLY from past-resolved predictions       │
│    (NEVER includes future data)                                  │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────┐
│ Walk-Forward Engine (DAILY LOOP)                                │
│ ├─ For each trading day D in [2024-06-01, 2026-06-20]:           │
│ │  ├─ 1. Load data up to D-1 (strict cutoff)                     │
│ │  ├─ 2. Agents make predictions (resolution_date > D)           │
│ │  ├─ 3. Register predictions in ledger                          │
│ │  ├─ 4. Resolve predictions where resolution_date == D          │
│ │  ├─ 5. Update trust scores from newly-resolved predictions     │
│ │  ├─ 6. Size paper positions (Arm A: equal, Arm B: trust)       │
│ │  ├─ 7. Compute P&L for day D                                   │
│ │  └─ 8. Accumulate to total paper return                        │
│ └─ Output: Daily P&L for both arms                               │
└──────────────┬──────────────────────────────────────────────────┘
               │
┌──────────────┴──────────────────────────────────────────────────┐
│ Analysis & Reporting                                            │
│ ├─ Total return: Arm A vs Arm B                                  │
│ ├─ Sharpe ratio (risk-adjusted)                                  │
│ ├─ Calibration curves (confidence vs hit rate per agent)         │
│ ├─ Per-agent trust over time                                     │
│ ├─ Prediction distribution (types, confidences)                  │
│ └─ Falsification check (is lookahead present? metrics make sense?)│
└─────────────────────────────────────────────────────────────────┘
```

---

## Lookahead Prevention: Three Layers of Defense

### Layer 1: Data Fetching
```python
# nse_data_fetcher.py
def get_data_up_to(data_dict, cutoff_date):
    """Return only data STRICTLY BEFORE cutoff_date."""
    # Never includes cutoff_date itself
    return {name: df[df['Date'] < cutoff_date] for name, df in data_dict.items()}

# Test: Assert no data >= cutoff_date is returned
def test_lookahead_prevention(data_dict, test_date):
    visible = get_data_up_to(data_dict, test_date)
    for df in visible.values():
        assert df['Date'].max() < test_date
    return True
```

### Layer 2: Agent Forecast Functions
```python
# nse_agents.py
def technical_analyst_forecast(market_data, prediction_date):
    """Make prediction using only data strictly before prediction_date."""
    # market_data = get_data_up_to(frozen_data, prediction_date)
    # Asserts:
    # - market_data['Date'].max() < prediction_date
    # - No data on or after prediction_date is accessible
    # - Signals derived only from market_data
    
    assert market_data['Date'].max() < prediction_date, "LOOKAHEAD LEAKAGE DETECTED"
    
    # Technical analysis on past data only
    rsi = compute_rsi(market_data)
    macd = compute_macd(market_data)
    ...
    
    return {
        'prediction': 'NIFTY up',
        'confidence': 0.65,
        'resolution_date': prediction_date + timedelta(days=1),
        'metadata': {'rsi': rsi, 'macd': macd}
    }
```

### Layer 3: Walk-Forward Loop
```python
# walk_forward_engine.py
def walk_forward_backtest(frozen_data, start_date, end_date):
    """Daily loop: predict on D, resolve predictions from earlier dates."""
    
    trading_days = get_nse_trading_days(frozen_data, start_date, end_date)
    
    for current_date in trading_days:
        # Get data up to current_date - 1
        # This is ENFORCED before agents see anything
        past_data = get_data_up_to(frozen_data, current_date)
        
        # Agents forecast (cannot escape data cutoff)
        predictions = {
            'technical': technical_analyst_forecast(past_data, current_date),
            'sentiment': sentiment_analyst_forecast(past_data, current_date),
            'fundamental': fundamental_analyst_forecast(past_data, current_date),
        }
        
        # Record predictions in ledger
        ledger.record_predictions(predictions, current_date)
        
        # Resolve predictions where resolution_date == current_date
        # Use REAL NSE close (from frozen_data)
        actual_close = frozen_data['NIFTY 50'][frozen_data['NIFTY 50']['Date'] == current_date]['Close']
        ledger.resolve_predictions(current_date, actual_close)
        
        # Update trust scores ONLY from resolved predictions
        # All resolved predictions have resolution_date < current_date
        # So no future data influences trust
        trust_scores = ledger.compute_trust_scores()
        
        # Size positions based on current trust scores
        # Trust scores contain no future information
        arm_a_position = equal_weight_size(predictions)
        arm_b_position = trust_weight_size(predictions, trust_scores)
        
        # Compute P&L
        day_pnl_a = compute_pnl(arm_a_position, actual_close)
        day_pnl_b = compute_pnl(arm_b_position, actual_close)
        
        # Accumulate
        total_pnl_a += day_pnl_a
        total_pnl_b += day_pnl_b
    
    return {
        'arm_a_final_value': initial_capital + total_pnl_a,
        'arm_b_final_value': initial_capital + total_pnl_b,
        'arm_a_pnl_daily': [...],
        'arm_b_pnl_daily': [...],
        'prediction_ledger': ledger,
    }
```

---

## Agent Implementations

### Agent 1: Technical Analyst
```
Inputs: OHLC, Volume (only data < prediction_date)
Signals:
  - RSI (14): Mean reversion signal
  - MACD: Momentum/trend
  - Moving average crossover (20/50 SMA)
  - Support/resistance levels (recent swings)
Predictions:
  - Directional (next day: up/down/sideways)
  - Threshold (e.g., "NIFTY > 25000 by Friday")
Confidence:
  - High (0.65+) when signals align (RSI extreme + MACD confirmed)
  - Medium (0.50-0.65) when mixed
  - Low (0.45-0.50) when conflicting
```

### Agent 2: Sentiment Analyst
```
Inputs: Market regime (implied from OHLC), volatility proxy
Sources: (if available) News sentiment, VIX-style signals
Signals:
  - Realized volatility (recent days)
  - Trend direction (daily closes)
  - Regime classification (up/down/sideways)
Predictions:
  - Directional (how regime likely to persist)
  - Relative (RELIANCE vs NIFTY performance)
Confidence:
  - High when regime is clear and recent
  - Low when choppy/undefined
```

### Agent 3: Fundamental Analyst
```
Inputs: Fixed data (not time-series)
  - Sector rotation signals
  - Macro regime (if available)
  - Historical earnings patterns (fixed data)
Predictions:
  - Threshold (e.g., "RELIANCE above historical avg over 10 days")
  - Relative (sector plays)
Confidence:
  - High when conviction is strong in historical data
  - Low when data is uncertain
```

---

## Trust Scoring Formula (Calibration)

```python
def compute_trust(agent_name, prediction_ledger):
    """Score agent based on historical calibration."""
    
    # Get all RESOLVED predictions for this agent
    resolved_preds = ledger.get_resolved_predictions(agent_name)
    
    if len(resolved_preds) == 0:
        return 0.5  # No history → neutral
    
    # Hit rate
    hits = sum(1 for p in resolved_preds if p['hit'])
    hit_rate = hits / len(resolved_preds)
    
    # Calibration: avg confidence vs actual hit rate
    avg_confidence = statistics.mean(p['confidence'] for p in resolved_preds)
    calibration_error = abs(avg_confidence - hit_rate)
    
    # Trust score: hit_rate is the primary signal
    # Calibration_error slightly penalizes overconfidence/underconfidence
    trust = hit_rate - 0.1 * calibration_error
    trust = max(0.0, min(1.0, trust))
    
    return trust

# Example:
# If agent has 60% hit rate and avg confidence of 60%: trust = 0.60 - 0.0 = 0.60
# If agent has 60% hit rate but avg confidence of 80%: trust = 0.60 - 0.02 = 0.58 (penalized for overconfidence)
# If agent has 50% hit rate: trust = 0.50 (baseline)
```

---

## Position Sizing (Arm A vs Arm B)

### Arm A: Equal-Weighted
```python
def size_position_equal(predictions, capital=1_000_000):
    """Size positions giving equal weight to each agent."""
    
    # Aggregate signal: average of agent signals weighted by confidence
    signals = []
    for agent, pred in predictions.items():
        if pred['prediction_type'] == 'directional':
            signal = (+1 if 'up' in pred['claim'].lower() else -1) * pred['confidence']
            signals.append(signal)
    
    aggregate_signal = statistics.mean(signals) if signals else 0
    
    # Position size: ±5% per ±1.0 signal (neutral at 0)
    position_size = capital * aggregate_signal * 0.05
    position_size = max(-0.05 * capital, min(0.05 * capital, position_size))  # Cap at ±5%
    
    return position_size
```

### Arm B: Trust-Weighted
```python
def size_position_trust_weighted(predictions, trust_scores, capital=1_000_000):
    """Size positions using agent trust scores."""
    
    signals = []
    weights = []
    for agent, pred in predictions.items():
        if pred['prediction_type'] == 'directional':
            signal = (+1 if 'up' in pred['claim'].lower() else -1) * pred['confidence']
            trust = trust_scores.get(agent, 0.5)
            signals.append(signal)
            weights.append(trust)
    
    if not signals:
        return 0
    
    # Weighted average signal
    aggregate_signal = sum(s * w for s, w in zip(signals, weights)) / sum(weights)
    
    # Position size: same rule as Arm A
    position_size = capital * aggregate_signal * 0.05
    position_size = max(-0.05 * capital, min(0.05 * capital, position_size))
    
    return position_size
```

---

## Output & Reporting

### Daily Log
```
Date,Arm,Position,Actual_Close,Day_PnL,Cumulative_PnL
2024-06-03,A,+5000,25150,+250,+250
2024-06-03,B,+3250,25150,+163,+163
2024-06-04,A,-2000,25220,-44,-294
2024-06-04,B,-1300,25220,-29,-192
...
```

### Final Summary
```json
{
  "test_window": "2024-06-01 to 2026-06-20",
  "arm_a": {
    "initial_capital": 1000000,
    "final_value": 1025000,
    "total_return_pct": 2.5,
    "total_days": 500,
    "positive_days": 260,
    "sharpe_ratio": 0.45
  },
  "arm_b": {
    "initial_capital": 1000000,
    "final_value": 1050000,
    "total_return_pct": 5.0,
    "total_days": 500,
    "positive_days": 270,
    "sharpe_ratio": 0.68
  },
  "hypothesis_test": {
    "arm_b_minus_arm_a": 25000,
    "arm_b_beats_arm_a": true,
    "sharpe_b_beats_sharpe_a": true,
    "verdict": "HYPOTHESIS SUPPORTED"
  },
  "agent_calibration": {
    "technical": {"hit_rate": 0.58, "avg_confidence": 0.60, "trust": 0.58},
    "sentiment": {"hit_rate": 0.52, "avg_confidence": 0.55, "trust": 0.52},
    "fundamental": {"hit_rate": 0.61, "avg_confidence": 0.59, "trust": 0.61}
  }
}
```

### Calibration Curves (Per Agent)
Plot: confidence (X) vs hit_rate (Y)
```
Technical Analyst:
  Confidence 0.50-0.60: 55% hit rate (slightly underconfident)
  Confidence 0.60-0.70: 60% hit rate (well-calibrated)
  Confidence 0.70-0.80: 62% hit rate (slightly overconfident)

If points lie on y=x line: agent is perfectly calibrated
If points lie above: agent is underconfident (should be more confident)
If points lie below: agent is overconfident (should be less confident)
```

---

## Implementation Phases

### Phase 1: Data & Schema (DONE or ready)
- [x] NSE data fetcher with lookahead test
- [x] Prediction ledger schema
- [ ] Pre-registration (ready to commit)

### Phase 2: Agents
- [ ] Technical analyst module
- [ ] Sentiment analyst module
- [ ] Fundamental analyst module
- [ ] Lookahead assertion in each

### Phase 3: Walk-Forward Engine
- [ ] Daily loop implementation
- [ ] Trust scoring
- [ ] Position sizing (both arms)
- [ ] P&L calculation

### Phase 4: Analysis & Reporting
- [ ] Calibration curve plotting
- [ ] Final stats computation
- [ ] HTML report generation

### Phase 5: Execution & Publishing
- [ ] Run backtest (historical NSE data)
- [ ] Optionally: run forward test (live data, if continuing)
- [ ] Publish results with full transparency

---

## Safety Checklist

Before running the experiment:
- [ ] Lookahead test passes (agents can't see future data)
- [ ] Hypothesis is committed (no changes mid-run)
- [ ] NSE data source documented (yfinance with limitations noted)
- [ ] Position sizing capped (no leverage, no shorting)
- [ ] Trust scores verified (only past-resolved predictions included)
- [ ] Paper-only caveat stated (will mention slippage, commissions, etc.)

---

## What This Test Actually Tells Us

**If trust-weighting wins (Arm B > Arm A):**
- Calibration-weighted decisions had measurable value on NSE over 2 years
- On these specific agents and instruments, in paper trading
- The trust-scoring methodology worked on real exogenous outcomes
- But it doesn't prove this generalizes or works live

**If trust-weighting loses (Arm A ≥ Arm B):**
- Either agents were low-quality, or trust-scoring didn't work
- Equal-weighting was at least as good
- Doesn't mean the principle is unsound; implementation may be fixable

**In either case:**
- We'll have real-market evidence (not synthetic)
- Full transparency on what was proven and what wasn't
- Honest caveats on applicability to live trading
