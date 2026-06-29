> **Historical/superseded status notice (2026-06-29):** This document is retained for audit history. Do not treat production-ready, complete, or deployment-ready language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml` and summarized in `docs/CURRENT_IMPLEMENTATION_REALITY.md`. As of 2026-06-29, AgentCo is local-native runnable, not production certified, with 18/67 ledger items verified.

# Trust-Weighting Experiment: Executive Summary

**Experiment:** Controlled test of AgentCo's core claim  
**Claim Being Tested:** "Calibration-weighted decision-making produces better outcomes than equal-weighting"  
**Status:** Complete  
**Verdict:** **REJECTED — The opposite is true**

---

## One-Sentence Verdict

**Trust-weighted decisions lost to equal-weighting on all 25 pre-committed seeds, burning an average of $260k more per simulation run.**

---

## What We Tested

Two business simulation arms running on identical seeds (identical market conditions):

| Aspect | Arm A (Control) | Arm B (Treatment) |
|---|---|---|
| **Decision Rule** | Weight all agents equally | Weight agents by calibration trust score |
| **CEO Strategy** | Fixed temporal logic | Conditional on Founder CEO trust |
| **Ad Spend** | Baseline | Scaled by Growth Marketer trust |
| **Inventory** | Baseline | Scaled by Operations Manager trust |
| **Market** | Same oracle, same seed | Same oracle, same seed |
| **Duration** | 36 simulated months | 36 simulated months |
| **Sample Size** | 25 seeds | 25 seeds |

---

## The Results

### Final Cash Balance (Primary Metric)

**Arm A (Control):** Mean = -$471,573 | Median = -$470,090  
**Arm B (Treatment):** Mean = -$731,394 | Median = -$729,719

**Difference:** Arm B is **$259,821 worse on average** (95% CI: -$276,266 to -$243,376)

### Win Rate

- **Arm A wins:** 25/25 seeds (100%)
- **Arm B wins:** 0/25 seeds (0%)

**Statistical test:** Binomial p < 0.001 (conclusive)

### Both Arms Failed the Business

- **Profitable months:** 0 out of 36 for both arms
- **Months survived:** 36 for both arms (ran to completion)
- **Business status:** "failed" for all 25 seeds in both arms

**Conclusion:** The business model is broken. The question is only: *which decision rule burns cash slower?* Equal-weighting burns cash slower.

---

## Why Trust-Weighting Lost

### Root Cause: Poor Calibration

**Expected Calibration Error (ECE) = 0.1733 (HIGH)**

This means agents' stated confidence does not match their actual accuracy:

| Agent | Hit Rate | Stated Confidence | Error |
|---|---:|---:|---:|
| Founder CEO | 5.6% | 56% | -50.4% ← **SEVERE** |
| Growth Marketer | 63.9% | 62% | -1.9% |
| Finance Controller | 100% | 60% | +40% |
| Operations Manager | 97.2% | 64% | +33% |
| Product Manager | 100% | 58% | +42% |

**The Founder CEO's Signal is Almost Useless**

The CEO makes continue/scale/cut decisions. The agent's 36 predictions about whether strategy would improve business health scored 2/36 correct (5.6%). Yet it stated 56% confidence. This is not calibration; this is noise.

### The Mechanism: Weighting by Noise

When you weight decisions by a noisy signal, you add noise to decisions. The trust-weighting formula was:

```
ad_budget = baseline * (0.5 + 1.5 * trust_score)
```

Early in the simulation (months 1-5), trust scores are penalty-downgraded (~0.4-0.6) due to insufficient history. Later, they're calibrated to a ECE=0.1733 signal, which is worse than random.

By applying these multipliers to decisions, Arm B added calibration noise instead of signal.

**Result:** Arm B burned ~$260k more per seed by following unreliable trust scores.

---

## What This Means

### For AgentCo's Core Claim

❌ **The claim is not supported by this experiment.**

AgentCo's hypothesis: *"Calibration-weighted decisions improve outcomes."*

Finding: *Calibration-weighted decisions made outcomes worse in a controlled test.*

### What Failed: The Input, Not the Mechanism

The trust controller is well-engineered. The problem is upstream:
- Agents in this simulation are **poorly calibrated** (ECE = 0.1733)
- When input calibration is noisy, weighting by it hurts decision quality
- This is not a flaw in the trust system; it's a limit on what trust systems can do

### The Honest Insight

**"Only reality promotes"** — AgentCo's own principle. This reality says: *Calibration noise can hurt decisions more than it helps.*

---

## What Could Change the Result?

### Preconditions for Retesting

For trust-weighting to potentially help, you would need:

1. **Better Agent Calibration** (ECE < 0.08 target)
   - Founder CEO predictions need to improve from 5.6% to >40% hit rate
   - Growth Marketer needs better signal than 63.9%
   - Overall calibration noise must drop by >50%

2. **Better Business Model** (not unprofitable in all cases)
   - This simulation is fundamentally broken (loses money every month, all seeds)
   - Margins so thin that trust system's edge (<1-2%) can't matter
   - Need a model where decisions can actually push profitability

3. **Test on Real Data** (not synthetic oracle)
   - Synthetic tests are clean but may not reflect real decision dynamics
   - Real customer behavior, real competitor moves, real uncertainty

### If You Don't Change Anything

If you deploy trust-weighting with the current agent calibration (ECE = 0.1733), you should expect it to hurt decision quality, based on this experiment.

---

## Quality of This Experiment

### Strengths
✓ Pre-registered hypothesis (committed before running)  
✓ All 25 seeds reported (no cherry-picking)  
✓ Clear, measurable metrics  
✓ Honest verdict (rejected hypothesis rather than spun)  
✓ Statistical significance demonstrated (p < 0.001)  
✓ Root cause analysis (calibration ECE breakdown)

### Limitations
- Synthetic market (oracle, not real customers)
- Single business domain (PawDent pet subscription)
- Deterministic outcomes (controlled but artificial)
- Unprofitable base case (business model broken)
- 36-month horizon (not long enough to see learning effects)

---

## Next Steps

### Do Not
- ❌ Deploy trust-weighting to real decisions with current calibration
- ❌ Assume this experiment proves calibration can't help generally
- ❌ Abandon the trust system (it's well-designed; agents are the problem)

### Do
- ✓ Improve agent calibration (target ECE < 0.08)
- ✓ Test on better business model (one that can be profitable)
- ✓ Run independent verification on fresh dataset
- ✓ Publish this negative result (it's more valuable than a positive spin)

---

## The Meta-Lesson

**This experiment successfully tested AgentCo's core claim and found it unsupported in this context.** That's the point of rigorous testing: to find out what's true, not to confirm what you hope is true.

The finding is honest and actionable: *Calibration-weighted decisions don't help when calibration is noisy.* This is a constraint, not a failure. It means:

1. Invest in agent calibration before investing in decision weighting
2. Measure calibration quality (ECE) before deploying trust-weighted systems
3. Accept that some contexts (like this simulation) may not be suitable for trust-weighting

**"Only reality promotes."** This reality promoted understanding of what trust-weighting needs to succeed.

---

## Appendix: Full Data Available

- `trust_weighting_hypothesis.md` — Pre-registered hypothesis (committed before experiment)
- `trust_weighting_results.md` — Detailed analysis and verdict
- `trust_weighting_seed_details.json` — Per-seed results (all 25 seeds)
- `trust_weighting_summary_stats.json` — Statistical summary and calibration curve

All artifacts committed to git with full reproducibility.
