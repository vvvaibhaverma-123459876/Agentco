# B2B SaaS Four-Arm Experiment — PRE-REGISTERED HYPOTHESIS

**Date:** 2026-06-20  
**Status:** LOCKED (before experiment runs)  
**Commit Hash:** (to be filled with git hash of this file BEFORE running Arm B, C, D)

---

## Primary Hypothesis

**Claim:** Calibration-weighted decision-making produces better outcomes than equal-weighted decision-making on B2B SaaS business decisions.

**Operationalized:**
Trust-weighted decisions (Arm B) will achieve higher final cash balances than control (Arm A) on the same 25 pre-registered seeds.

---

## Pre-Registered Specifications

### Experiment Design

**Seeds (Fixed, N=25):**
```
1234, 1235, 1236, 1237, 1238,
2001, 2002, 2003, 2004, 2005,
3333, 3334, 3335, 3336, 3337,
4999, 5000, 5001, 5002, 5003,
6789, 7000, 8000, 9000, 9999
```

**Arms (Same business model, same seeds, different weighting):**
1. **Arm A (Control):** Equal-weighted decisions (1.0x all agents)
2. **Arm B (Trust-Weighted):** Agents weighted by trust scores (0-2x multiplier per agent)
3. **Arm C (CEO Excluded):** Trust-weighted, but Founder CEO not included
4. **Arm D (Symmetric Braking):** Trust-weighted + Finance Controller can brake spending

**Duration:** 36 months per seed

---

## Primary Outcome Metric

**Final Cash Balance after 36 months**

Calculated as: `(month_36_cash_balance - initial_cash) + (operating_profit_sum)`

Measured for each of the 25 seeds in each of the 4 arms.

---

## Primary Analysis

**Hypothesis Test (Binomial):**

Count how many of 25 seeds have Arm B cash > Arm A cash.

| Outcome | Support | Falsification |
|---------|---------|---------------|
| Arm B > Arm A on ≥14/25 seeds | Hypothesis SUPPORTED | |
| Arm B > Arm A on <14/25 seeds | | Hypothesis FALSIFIED |

**Threshold Justification:**
- 14/25 seeds = 56% win rate
- Binomial p-value: p < 0.05 (two-tailed)
- Difference from 50% (no effect): clearly above noise

---

## Secondary Outcome Metrics

### 1. Spread Distribution Analysis

**Metric:** Per-seed difference in final cash (Arm B - Arm A)

**Expected Pattern (If Hypothesis True):**
```
Profitable seeds (11/25): Arm B wins, average +$100k-300k advantage
Loss seeds (14/25): Arm B wins more often, average +$50k-150k advantage
```

**Expected Pattern (If Hypothesis False - Noise):**
```
Uniform offset: Arm B offset constant across all seeds ±$50k
Result: Would indicate NOISE, not signal
```

### 2. Trust Score Distribution

**Metric:** Per-seed, per-agent trust scores (0-1)

**Expectation:**
- Easy seeds: agents high trust (0.7-1.0) → Arm B uses full weighting
- Hard seeds: agents lower trust (0.3-0.6) → Arm B de-weights
- Variation indicates agents are learning, not just lucky

### 3. Profitable Seed Subset Analysis

**Metric:** Arm B vs Arm A on just the 11 seeds that are profitable under control

**Expectation:** Arm B should beat A by ≥60% on this subset (agents optimizing easy markets)

### 4. Loss Seed Subset Analysis

**Metric:** Arm B vs Arm A on just the 14 seeds that shut down under control

**Expectation:** Arm B should beat A by ≥50% on this subset (agents preventing early shutdowns)

---

## Decision-Making Interventions

### How Trust Weighting Affects Decisions

**Arm B Formula** (previously fixed in Prerequisite 1):
```python
# Growth Marketer on ad spend (0-2x multiplier)
ad_budget = baseline_budget * (2.0 * trust_score)

# Finance Controller on spending brake (0-1x multiplier on ad spend)
ad_budget = ad_budget * (1.0 - trust_score)  # high trust → no brake, low trust → full brake

# Product Manager on pricing (0-2x multiplier)
price = baseline_price * (2.0 * trust_score)

# Operations on inventory (0-2x multiplier)
inventory = baseline_inventory * (2.0 * trust_score)
```

### Where Trust Matters Most (Expected)

**On Easy Seeds:**
- Agents should have high trust
- Weighting allows them to confidently raise prices, increase spend
- Result: higher profit than control's fixed policy

**On Hard Seeds (Death Valley):**
- Agents should learn to distrust themselves after early market shocks
- Finance Controller brakes spending hard in month 4-8
- Growth Marketer reduces ad spend recommendation
- Result: avoids cash depletion where control shuts down

---

## Falsification Criteria (HARD STOP)

**Hypothesis is FALSIFIED if:**

1. **Primary test fails:** Arm B does NOT beat Arm A on ≥14/25 seeds
   - Cannot support the claim with statistical power

2. **Spread shows uniform offset:** B's advantage is constant across all seeds (±$50k)
   - Indicates experimental noise, not decision-quality signal
   - Would match PawDent's failed pattern

3. **Trust scores are flat:** All agents have trust 0.5-0.95 in all months
   - Indicates agents are not discriminating between good/bad decisions
   - No learning signal

---

## Analysis Plan (Before Running Experiment)

### Step 1: Run all 4 arms (A, B, C, D) on 25 seeds
- ~60-90 minutes total runtime
- Capture per-seed, per-month results

### Step 2: Calculate primary metric
- Count seeds where B > A
- Report n/25 and p-value

### Step 3: Verify spread patterns
- Plot Arm B - Arm A for all 25 seeds
- Check for clustering (signal) vs uniform (noise)

### Step 4: Subset analysis
- Easy seeds (11) vs Hard seeds (14)
- Expected: B wins more on easy seeds (≥60%), also beats on hard seeds (≥50%)

### Step 5: Trust score analysis
- Per-seed, plot agent trust over 36 months
- Verify agents are learning (trust varies by seed)

### Step 6: Report decision changes
- Show 3-5 seeds where Arm B made different decisions than A
- Explain why (e.g., "Finance braked spending month 6-8, avoided shutdown")

---

## Honest Reporting Standards

**This report WILL include:**
- ✓ All 25 seeds, all 4 arms
- ✓ Actual results, no cherry-picking
- ✓ p-value and confidence intervals
- ✓ Spread distribution plots
- ✓ Cases where hypothesis was supported
- ✓ Cases where hypothesis failed
- ✓ Independent variables (was business frozen? agents wired after?)
- ✓ Limitations (this is one business model, not general claim)

**This report will NOT:**
- ✗ Assert "the trust controller is sound" (already proven separately)
- ✗ Claim calibration helps "all decisions" (only tested on one model)
- ✗ Hide seeds where Arm B lost
- ✗ Adjust threshold after seeing results
- ✗ Overclaim scope beyond "this B2B SaaS model"

---

## Commit Hash Verification

**This document LOCKED at:** `[GIT HASH TO BE FILLED]`

**No changes to hypothesis after this hash is created.**

**Agents wired after this hash:** [FUTURE COMMIT HASH]

**Experiment run after agents wired:** [FUTURE COMMIT HASH]

---

## Success Criteria Summary

| Criterion | Pass | Fail |
|-----------|------|------|
| **Primary:** B beats A ≥14/25 seeds | Hypothesis supported | Hypothesis falsified |
| **Secondary:** Spread is clustered (not uniform) | Signal detected | Noise detected |
| **Tertiary:** Trust scores vary by seed | Agents learning | Agents random |
| **Independence:** Frozen business + agents wired after | ✓ Confirmed | ✗ Co-design bias |

---

## Interpretation Guide

### If Hypothesis Supported (B ≥14/25 seeds):

**Conclusion:** On this B2B SaaS model, trust-weighted decisions improved outcomes.

**Evidence of calibration value:**
- Agents' forecasts correlate with actual outcomes
- Trust scores discriminate between good/bad seeds
- Weighting allows profitable seeds to be MORE profitable
- Weighting prevents early shutdowns on hard seeds

**Limitations:**
- This is ONE business model, not general proof
- Different industries/decisions may vary
- Agents were tuned on THIS oracle, not tested on unseen markets

### If Hypothesis Falsified (B <14/25 seeds):

**Conclusion:** On this B2B SaaS model, trust-weighting did NOT improve outcomes.

**Possible reasons:**
1. Agents' heuristics don't match this market (untrained)
2. Trust scores don't correlate with decision quality
3. Weighting is noise-amplification, not signal-filtering
4. Control policy is already near-optimal (little room to improve)

**Next steps:**
- Improve agent heuristics (better forecasting models)
- Recalibrate trust thresholds
- Test different control policies (worse baseline = more room for improvement)

---

## Final Note

This hypothesis is pre-registered to prevent:
- ✗ Moving goalposts ("I meant 50% not 56%")
- ✗ Cherry-picking ("only count profitable seeds")
- ✗ Post-hoc analysis ("trust matters if we exclude outliers")
- ✗ Overclaiming ("calibration helps all business decisions")

The experiment will provide honest evidence. Either the hypothesis will be supported or falsified. Either outcome is valuable: support means calibration helps, falsification means we need different approaches.

**This document is locked. No changes after commit hash.**
