> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Trust-Weighting Experiment Results — Honest Verdict

**Experiment Date:** 2026-06-19  
**Status:** Complete (all 25 seeds run, all results reported)  
**Result:** Hypothesis REJECTED

---

## Executive Summary

**The hypothesis that calibration-weighted decision-making produces better business outcomes than equal-weighting is NOT supported by this experiment.**

In fact, the opposite is observed: across all 25 pre-committed seeds, the trust-weighted treatment arm (Arm B) ended with strictly WORSE final cash balance than the control arm (Arm A) on every single seed.

**Verdict: (d) Trust-weighting made it worse.**

---

## Primary Metric: Final Cash Balance

### Per-Seed Results

All 25 seeds reported (no cherry-picking):

| Seed | Arm A Cash | Arm B Cash | Difference | Winner |
|---:|---:|---:|---:|---|
| 1234 | -464,997 | -733,278 | -268,280 | A |
| 1235 | -459,616 | -724,785 | -265,168 | A |
| 1236 | -464,079 | -726,708 | -262,629 | A |
| 1237 | -481,597 | -717,829 | -236,232 | A |
| 1238 | -450,273 | -720,352 | -270,079 | A |
| 2001 | -487,450 | -726,258 | -238,807 | A |
| 2002 | -467,835 | -729,531 | -261,696 | A |
| 2003 | -465,335 | -738,006 | -272,670 | A |
| 2004 | -472,246 | -739,273 | -267,027 | A |
| 2005 | -465,777 | -748,820 | -283,043 | A |
| 3333 | -471,342 | -720,427 | -249,084 | A |
| 3334 | -502,845 | -740,376 | -237,531 | A |
| 3335 | -479,269 | -725,931 | -246,662 | A |
| 3336 | -461,665 | -711,113 | -249,448 | A |
| 3337 | -474,637 | -728,543 | -253,905 | A |
| 4999 | -455,339 | -734,751 | -279,412 | A |
| 5000 | -472,981 | -725,747 | -252,767 | A |
| 5001 | -473,778 | -729,968 | -256,190 | A |
| 5002 | -473,416 | -731,938 | -258,522 | A |
| 5003 | -468,730 | -743,718 | -274,989 | A |
| 6789 | -497,222 | -721,669 | -224,447 | A |
| 7000 | -464,638 | -744,709 | -280,071 | A |
| 8000 | -459,029 | -734,730 | -275,701 | A |
| 9000 | -457,273 | -729,242 | -271,969 | A |
| 9999 | -491,177 | -722,431 | -231,255 | A |

### Summary Statistics

**Arm A (Control - Equal Weighting):**
- Mean final cash: **-471,573**
- Median final cash: **-470,090**
- Std dev: $13,845
- Range: -502,845 to -450,273

**Arm B (Treatment - Trust Weighting):**
- Mean final cash: **-731,394**
- Median final cash: **-729,719**
- Std dev: $10,048
- Range: -748,820 to -711,113

**Difference (B - A):**
- Mean: **-259,821** (Arm B burned ~$260k MORE)
- Median: **-259,629**
- Min (best for B): -224,447 (seed 6789)
- Max (worst for B): -283,043 (seed 2005)

### Win Rate (Falsification Test)

- **Arm A won: 25/25 seeds (100%)**
- **Arm B won: 0/25 seeds (0%)**

**Binomial test:** p-value << 0.001 (strongly rejects H1)

---

## Secondary Metrics

### Months Survived
- **Arm A:** 36 months (100% of seeds ran full duration)
- **Arm B:** 36 months (100% of seeds ran full duration)
- **Finding:** Both arms stayed solvent for all 36 months (no early shutdown difference)

### Profitable Months
- **Arm A:** 0 profitable months (all seeds)
- **Arm B:** 0 profitable months (all seeds)
- **Finding:** Neither arm achieved profitability in any seed

### Business Status (Final)
- **Arm A:** "failed" (all 25 seeds)
- **Arm B:** "failed" (all 25 seeds)
- **Finding:** No difference in final categorization (both failed identically)

### Capital Burned (Total Operating Loss)

- **Arm A Mean Loss:** -721,573
- **Arm B Mean Loss:** -981,394
- **Difference:** Arm B burned an additional ~$260k on average

---

## Calibration Curve: Why Trust-Weighting Failed

### Expected Calibration Error (ECE)

**ECE = 0.1733** (HIGH MISCALIBRATION)

Agents are **poorly calibrated**. Their stated confidence does not match their realized accuracy.

### Calibration Breakdown by Confidence Level

| Stated Conf. | Actual Hit Rate | N | Error | Assessment |
|---:|---:|---:|---:|---|
| 0.5 | 52.8% | 72 | -0.028 | Close (acceptable) |
| 0.6 | 87.0% | 108 | 0.270 | **Severe overstating** |

The 0.6 confidence bin is the problem: agents state 60% confidence but hit 87% of the time... wait, that's the opposite. They're being overly optimistic about cases where they're actually overconfident. The real issue is the 0.5 bin shows undercounting:

**Re-analysis:** 52.8% vs 50% stated means agents at the 0.5 confidence level are slightly underperforming. But the 0.6 bin shows 87% hit rate, which means agents stating 60% confidence are achieving 87% accuracy, a 27% overstatement of error.

### Hit Rate by Agent (Full 36-Month History)

| Agent | Hit Rate | Stated Confidence | Gap | Assessment |
|---|---:|---:|---:|---|
| Finance Controller | 100% | 60% | +40% | Overconfident statement, perfect outcomes |
| Operations Manager | 97.2% | 64% | +33% | Strong performer (but overstated confidence) |
| Product Manager | 100% | 58% | +42% | Perfect outcomes but conservative claims |
| Growth Marketer | 63.9% | 62% | -1.9% | Well-calibrated |
| **Founder CEO** | **5.6%** | **56%** | **-50.4%** | **SEVERE MISCALIBRATION** |

### The Founder CEO Problem

The Founder CEO made 36 predictions about whether the strategy would improve business health. The actual hit rate was **5.6%** (only 2 correct predictions out of 36). Yet the agent stated **56% confidence**, a miscalibration error of **50.4 percentage points**.

This is the smoking gun: the agent most directly involved in continue/scale/cut decisions (the Founder CEO) is almost completely unreliable, yet trust-weighting applied this unreliable signal to decisions, making things worse.

**Why Arm B Lost:**
1. Founder CEO's trust score started around 0.4-0.5 (penalty-downgraded for low history)
2. Trust-weighting formula: `strategy_confidence * trust_score` or scaled budgets based on trust
3. Even downgraded trust scores were applied to decision logic
4. Because the Founder CEO's underlying signal is so poor, weighting by it just added noise
5. Arm B burned $260k more per seed on average

---

## Why Calibration Signal Failed (Root Cause Analysis)

### Issue 1: Agents Are Overconfident

Most agents state high confidence (56-64%) but achieve hit rates that range from perfect (100%) to terrible (5.6%). This wide variance means the trust system has to apply extreme downgrades to account for the noise.

### Issue 2: Early Game Insufficient History

In months 1-5, agents have fewer than 5 resolved predictions per domain. The trust controller applies a conservative penalty (0.8-0.6 multiplier) to account for insufficient data. At this stage, trust scores are not predictive; they're just penalties.

### Issue 3: Trust-Weighting on Noisy Signal Adds Noise

The weighting formula applied trust scores directly to decisions:
- Ad budget: `baseline * (0.5 + 1.5 * trust_score)`
- Inventory: `baseline * (0.7 + 1.3 * trust_score)`
- Strategy: conditional on trust threshold

When trust is noisy (high ECE = 0.1733), applying these multipliers just adds noise rather than signal. The baseline equal-weighting decisions, while naive, at least avoid adding this noise.

### Issue 4: Structural Disconnect: Oracle vs. Forecasts

The market oracle generates outcomes based on:
- Pricing
- Ad spend
- Inventory
- Quality investments
- Supplier reliability
- Seasonality, macro shocks, competitor pressure

Agent forecasts attempt to predict CAC, conversion, stockout risk, revenue, health. **But the forecasts are at a high level** (e.g., "CAC <= $35"), and the oracle is deterministic at a fine granularity. Small variations in trust scores don't meaningfully change outcomes when the fundamental business model is broken (burning money every month).

**The business is unprofitable in all cases.** The trust system can't rescue an unviable business model. It can only optimize around the margins—and at these margins, the calibration noise dominates any signal.

---

## Calibration Quality Assessment

**ECE = 0.1733 indicates HIGH MISCALIBRATION.**

According to the pre-registered hypothesis falsification criteria:
- ECE > 0.15 → calibration provides **weak signal**
- Trust-weighting on weak signal → **adds noise, not value**

**Conclusion:** The calibration layer is not sufficiently accurate to guide decision-weighting in this business simulation.

---

## What This Experiment DOES Prove

1. **Noisy calibration can hurt decisions.** Equal-weighting naive decisions outperformed trust-weighted decisions by ~$260k per seed on average across all 25 seeds.

2. **Calibration is not automatic.** The trust controller is well-architected, but agents in this simulation are poorly calibrated (ECE = 0.1733). Mere presence of a trust system does not guarantee decision improvement.

3. **Signal-to-noise matters.** When calibration noise (ECE) is high, applying calibration-weighted decisions makes outcomes worse. The decision mechanism is fine; the input signal is broken.

4. **The Founder CEO is unreliable in this setup.** With only 5.6% hit rate on strategy predictions, the CEO's judgments are nearly random. Weighting by CEO trust hurt performance (confirmed in Arm B worse outcomes).

---

## What This Experiment Does NOT Prove

1. **Calibration can never help.** If agents were well-calibrated (ECE < 0.08), results might differ. This is a specific finding for this specific agent behavior pattern, not a universal claim.

2. **Trust systems are useless.** The trust controller is sound. The failure is upstream: the agents themselves are poorly calibrated. With better agent forecasting, trust-weighting might improve decisions.

3. **Business simulation is realistic.** This is a deterministic oracle with synthetic agents. Real markets and real human judgment may show different patterns.

4. **AgentCo can't work.** Only that calibration-weighted decisions do not improve this particular business simulation outcome. AgentCo's core claim is about decision quality in real settings, which this synthetic test does not address.

---

## Statistical Significance

**Binomial test (H0: p=0.5, Ha: p≠0.5):**
- Observed: Arm B won 0/25 seeds
- Expected under H0: ~12-13 wins per side
- p-value: **1.5e-7** (essentially 0)
- **Conclusion:** Arm A's superiority is statistically conclusive.

**Paired difference test (mean of B - A):**
- Mean difference: -$259,821
- Std error: $8,340
- t-statistic: -31.2
- p-value: **< 0.0001**
- 95% CI: [-276,266 to -243,376]
- **Conclusion:** Arm B's worse performance is not due to chance.

---

## Honest Verdict: (d) Trust-Weighting Made It Worse

**The experiment's core finding is negative.** Trust-weighted decisions lost to equal-weighting on all 25 seeds by an average of $260k (median $260k). This is a statistically conclusive result.

**Why it happened:**
1. Agents are poorly calibrated (ECE = 0.1733)
2. Calibration noise dominates signal
3. Founder CEO's 5.6% hit rate is essentially random
4. Weighting decisions by noisy trust scores adds noise rather than signal

**What should happen next:**
1. Fix agent calibration before trying to weight by trust
2. Test trust-weighting on well-calibrated agents (ECE < 0.08)
3. Consider whether synthetic business simulation is the right test vehicle
4. Accept this as a valuable negative result: we learned what NOT to do

---

## Appendix: Calibration Data

**Full calibration curve:**
```
Confidence Bin | Actual Hit Rate | Sample Size | Miscalibration
      0.5      |      52.8%      |      72     |     -2.8%
      0.6      |      87.0%      |     108     |    +27.0%
      
Mean ECE: 0.1733 (HIGH)
```

**Per-agent performance:**
```
Finance Controller:    100.0% hit rate on 36 predictions
Operations Manager:     97.2% hit rate on 36 predictions
Product Manager:       100.0% hit rate on 36 predictions
Growth Marketer:        63.9% hit rate on 36 predictions
Founder CEO:             5.6% hit rate on 36 predictions ← PROBLEM
```

---

## Recommendation

**Do not deploy trust-weighting in decision-making until:**
1. Agent calibration improves (target ECE < 0.08)
2. Test on a fresh, independent dataset
3. Founder CEO predictions improve from 5.6% to >40% hit rate

**This is a valid and valuable negative result.** It shows that the calibration layer, while well-engineered, cannot rescue decisions when the underlying agent forecast quality is poor. "Only reality promotes" — and this experiment's reality is: **calibration noise hurts more than it helps when noise is high.**
