# Trust-Weighting Decision Experiment — Pre-Registered Hypothesis

**Registration Date:** 2026-06-19  
**Registrant:** AgentCo Calibration Team  
**Experiment Status:** Pre-registered (before execution)

---

## Research Question

**Does calibration-weighted decision-making produce better business outcomes than calibration-blind decision-making in a deterministic market simulation?**

---

## Core Hypothesis

**H1 (Primary):**  
A PawDent business whose continue/scale/cut decisions are weighted by each agent's resolved calibration trust score ends with **higher final cash balance** after 36 months than an identical business that weights all agents equally.

**Rationale:**  
If agents with poor calibration history provide lower-quality forecasts, weighting their inputs lower should lead to better spending allocation and faster recognition of when to cut burn or shut down. Conversely, if calibration provides no predictive signal, trust-weighting should have no effect.

---

## Primary Metric

- **Final Cash Balance (Arm B minus Arm A):** After 36 simulated months, the cash balance difference between the treatment arm (trust-weighted decisions) and control arm (equal-weighted decisions).
- **Decision Rule for Primary Metric:** Arm B wins if median final cash (B) > median final cash (A) across 25 seeds with statistical clarity (binomial test, alpha=0.05).

---

## Secondary Metrics

1. **Win Rate:** In how many of 25 seeds did Arm B end with strictly more cash than Arm A?
   - Success threshold: ≥14 of 25 seeds (binomial p=0.5, alpha=0.05)

2. **Months Survived:** When does each arm become insolvent (cash < $0)?
   - Better outcome: Arm B survives longer (indicates better cost discipline)

3. **Profitable Months:** How many of 36 months had operating_profit > 0?
   - Better outcome: Arm B has more profitable months

4. **Capital Burned:** Total cumulative operating losses.
   - Better outcome: Arm B burns less capital total

5. **Decision Timing:** At what month does each arm first cut ad spend or shut down?
   - Better outcome: Arm B makes these decisions earlier (faster course correction)

6. **Calibration Curve:** Across all resolved predictions (both arms), what is the expected calibration error (ECE)?
   - Plot: stated confidence p vs. realized hit rate for each confidence bin (0.0-0.1, 0.1-0.2, ..., 0.9-1.0)
   - If ECE is high (>0.10), calibration provides weak signal; trust-weighting cannot help

---

## Experimental Design

### Population
- **N = 25 seeds:** Fixed before execution, listed below
- **All seeds reported:** No cherry-picking

### Seeds (Pre-Committed)
```
1234, 1235, 1236, 1237, 1238,
2001, 2002, 2003, 2004, 2005,
3333, 3334, 3335, 3336, 3337,
4999, 5000, 5001, 5002, 5003,
6789, 7000, 8000, 9000, 9999
```

### Arm A: Control (Calibration-Blind)
- **Decision Rule:** All agents' forecasts weighted equally (baseline behavior)
- **CEO Strategy:**
  ```
  "explore" if month <= 3
  else "pilot" if month <= 6
  else "scale carefully" if cash_balance > 90,000
  else "cut burn and preserve runway"
  ```
- **Ad Budget:** Determined without regard to Growth Marketer trust
- **Inventory:** Determined without regard to Operations Manager trust
- **Pricing:** Determined without regard to Product Manager trust
- **No changes to oracle, circular-resolution guard, or other infrastructure**

### Arm B: Treatment (Calibration-Weighted)
- **Decision Rule:** Each agent's forecast weighted by their current trust score (0.0-1.0)
- **CEO Strategy:** Same temporal flow as Arm A, but weighted by Founder CEO trust score
  ```
  strategy_confidence = trust_score_founder_ceo if Arm B else 0.56
  if strategy_confidence < 0.40:
    → cut burn and preserve runway (earlier)
  if strategy_confidence > 0.75:
    → scale carefully or pilot (more aggressive)
  else:
    → baseline per month
  ```
- **Ad Budget:** Scaled by Growth Marketer trust score
  ```
  adjusted_ad_budget = baseline_ad_budget * (0.5 + 1.5 * trust_score_growth_marketer)
  (bounds: [min_budget, max_budget])
  ```
- **Inventory:** Scaled by Operations Manager trust score
  ```
  adjusted_inventory = baseline_inventory * (0.7 + 1.3 * trust_score_operations)
  ```
- **Pricing:** Scaled by Product Manager trust score
  ```
  adjusted_price = baseline_price * (0.9 + 0.2 * trust_score_product_manager)
  ```
- **Trust History:** Beginning month 1, use trust_after from resolved predictions from prior months
  - Months 1-5: Insufficient trust history (< 5 resolved claims per agent per domain), use penalty-downgraded trust (see trust_controller.py line 78-92)
  - Months 6+: Full ECE-calibrated trust scores guide decisions
- **Same oracle, circular-resolution guard active**

### Matching & Determinism
- **Same seed** → identical pre_decision_signal(month, state)
- **Same initial state** → ProductState() identical at month 0
- **Different decisions** → different monthly_actual() because state_bits diverge
- **Expected outcome:** Deterministic divergence (two arms follow different paths due to different decision policies)

---

## Falsification Conditions

**H1 is rejected (trust-weighting provides no decision value) if:**
1. Arm B does not beat Arm A on final cash in ≥14 of 25 seeds (binomial test, p=0.5, alpha=0.05), OR
2. Median final cash (B) ≤ Median final cash (A) across all 25 seeds, OR
3. Expected calibration error (ECE) > 0.15 across all resolved predictions (calibration noise dominates signal)

**H1 is partially supported (weak signal) if:**
- Arm B beats Arm A in 13-14 of 25 seeds but with low confidence
- Median final cash (B) ≈ Median final cash (A) (±$10k)
- ECE is moderate (0.10-0.15)

**H1 is supported if:**
- Arm B beats Arm A in ≥15 of 25 seeds (binomial p<0.05)
- Median final cash (B) > Median final cash (A) with $50k+ difference
- ECE < 0.10 (agents are well-calibrated)

---

## What This Experiment Does NOT Test

- **Real-world market predictions:** The market is a deterministic oracle, not real customer behavior
- **Scaling to other business domains:** Only PawDent pet subscription
- **Multi-agent coordination:** Agents act independently; no coalition-building
- **Feedback loops in learning:** Trust updates inform next month's decisions, but learning is algorithmic, not behavioral
- **Whether AgentCo should exist:** Only whether calibration-weighted decisions beat equal-weighting in this synthetic setup

---

## What This Experiment DOES Test

- **Mechanism:** Can a calibration signal (trust score) improve decision quality in a controlled counterfactual?
- **Signal-to-Noise Ratio:** Is the calibration noise (ECE) low enough for weighting to help?
- **Decision Responsiveness:** When do trust-weighted decisions cut spend or pivot earlier than naive equal-weighting?
- **Honesty:** Whether the method works even when the answer is "no"

---

## Reporting Standard

**All 25 results will be reported.** No removal of "outliers," no selective reporting of high-performing seeds. Negative results are valid and valuable.

**Output artifacts:**
1. `trust_weighting_results.md` — summary statistics, distributions, win rate, calibration curve
2. `trust_weighting_seed_details.csv` — per-seed cash, survival, profitability for both arms
3. `trust_weighting_calibration_curve.png` — stated confidence vs. hit rate across all predictions

**Verdict will state:**
- Which arm won (or null result)
- Supporting numbers (win rate, cash difference, timing of decisions)
- Confidence (binomial test p-value)
- What this does and does NOT prove
- Recommendation for next steps

---

## Statistical Significance

- **Primary metric (win rate):** Binomial test, H0: p=0.5 (arms equal), Ha: p≠0.5
  - n=25, alpha=0.05 → critical value ≈14 wins for one arm
- **Cash difference:** Paired t-test or Wilcoxon signed-rank test (final_cash_B - final_cash_A)
  - Report mean, median, 95% CI
- **Months survived:** Kaplan-Meier or median time-to-event

---

## Commitment

This hypothesis is committed and locked before any experimental execution. All 25 seeds will be run, all results reported. No post-hoc changes to the hypothesis or decision rule.

*Signed virtually: AgentCo Calibration Team, 2026-06-19*
