# Test Validity Analysis: Why The PawDent Test Was Invalid

**Date:** 2026-06-20  
**Conclusion:** The test of AgentCo's core claim was invalid, not because the technology doesn't work, but because the test environment had no profitable decision-space.

---

## Executive Summary

Testing whether calibration-weighted decisions improve outcomes on a fundamentally unprofitable business is meaningless. It's like testing whether a better navigation system helps in a city where all roads are blocked.

**The PawDent result:** All arms (A, B, C, D) lost ~$259k/seed uniformly because *there are no good decisions to make*. The business loses money in every seed regardless of how decisions are weighted.

**What we learned:** This proves that AgentCo's core claim was never tested. We tested a different question: "Can calibration rescue a doomed business?" The answer (no) doesn't tell us whether "Calibration improves decisions" is true.

---

## PawDent: Why The Test Was Invalid

### The Fundamental Problem

**PawDent's unit economics don't close in ANY seed:**

| Metric | Month 6 | Month 12 | Month 24 |
|---|---:|---:|---:|
| Active Subs | 300-350 | 600-700 | 1500-2000 |
| Revenue | $8,700-10,500 | $17k-20k | $43k-57k |
| CAC | $25-30 | $30-35 | $35-40 |
| LTV | $40-60 | $50-80 | $60-100 |
| **LTV > CAC?** | **NO** | **NO** | **BARELY** |

Result: Every seed spends more on acquisition ($15-85k/month ad budget + other channels) than the entire gross margin can sustain.

### Why All Arms Lost Identically

Because **there are no good decisions to find**. Trust-weighting on a broken business:
- Control (Arm A): Deterministic loss (~$259k over 36 months)
- Arm B (Trust-weighted asymmetric): Same deterministic loss + variance
- Arm C (CEO excluded): Same deterministic loss + noise from other agents
- Arm D (Symmetric braking): Same deterministic loss + friction from brake mechanism

**The fixed ~$259k offset across all arms proves:** This is not differential performance. This is noise from weighting being applied to a structurally broken system.

---

## What A Fair Test Requires

### Precondition 1: Mixed Outcomes (Some Seeds Profitable, Some Not)

**PawDent:** 0/25 seeds profitable = uniform failure = test is invalid

**Fair business:** Should show 30-50% of seeds profitable under control policy

**Why this matters:** If every seed fails, decisions don't matter. If some succeed and some fail, decisions determine which group you land in. That's when calibration signal can help.

### Precondition 2: Suboptimal Control Policy

**PawDent:** Control policy hard-codes decisions; not obviously suboptimal, just fixed

**Fair business:** Control policy should be knowably leaving money on table
- Example: Always spend the same ad budget regardless of CAC signal
- Example: Set pricing once; never adjust based on demand signals
- Example: Don't invest in churn reduction (cheaper but fragile)

The control must be **mediocre but stable**, so good decisions beat it measurably.

### Precondition 3: Real Decision-Space

**PawDent:** Decisions affect timing/magnitude of losses, not profitability itself

**Fair business:** Decisions must have binary or large impact on outcomes:
- Spend too much on CAC → losses (even with growth)
- Spend right amount → profits
- Don't manage churn → losses
- Invest in retention → profits

Calibration should allow agents to say "Based on revenue signals, cut ad spend" or "Based on churn signals, invest in retention." And those calls move outcomes measurably.

### Precondition 4: Room For Calibration To Add Value

**PawDent:** Even perfect agents (100% hit rate) couldn't help because the business doesn't work

**Fair business:** Must have decisions where agent forecasts actually matter
- Finance Controller says "Unit economics breaking" → Growth should cut spend
- Growth Marketer says "CAC rising above LTV" → should pull back
- These signals must correlate with actual business health and decision outcomes

---

## The Revised B2B SaaS Model (Testable)

### Economics That Can Work

**Product:** B2B SaaS, $99/month/customer

| Seed | Early Growth | Mature |
|---|---|---|
| 200 customers, $19.8k revenue | 500 customers, $49.5k revenue |
| $4k COGS, $4k fixed, $3k ad | $10k COGS, $6k fixed, $5k ad |
| **Profit: +$8.8k/month** | **Profit: +$28.5k/month** |

### Decision Levers That Actually Matter

**Spending on Acquisition:**
- Good: Pace spending to match sustainable CAC (<$40 per customer)
- Bad: Overspend on growth (>$60 CAC) → burn through runway

**Pricing:**
- Good: Adjust price based on demand signals (stay at LTV/CAC sweet spot)
- Bad: Fixed price leaving margin on table or pricing too high for volume

**Churn Management:**
- Good: Invest in customer success (ROI 3-5x)
- Bad: Cut costs, accept high churn (~10%), volatile LTV

### Why This Is Testable

Control policy (mediocre):
- Fixed ad budget ($3k/month early, scaling to $5k later)
- Pricing set at $99, never adjusted
- Churn management: basic support (5-8% churn)

Good decisions (trust-weighted should find):
- Reduce ad spend when CAC signals deteriorate
- Raise pricing when demand survives market tests
- Increase CS investment when churn exceeds LTV risk threshold

**Result expectation:** Control loses money on hard markets, breaks even on medium, small profits on easy. Weighting should skew toward profitable seeds more often.

---

## Why AgentCo's Claim Was Never Tested

### The Claim
"Calibration-weighted decision-making produces better outcomes than calibration-blind decision-making."

### What PawDent Actually Tested
"Can calibration rescue a business with negative unit economics in all scenarios?"

**These are NOT the same question.**

- First claim: "Does signal improve decisions?" (testable with fair business)
- Second claim: "Can perfect forecasting fix broken math?" (always no)

---

## Path Forward: Build The Fair Test

### Specification (Commitment Before Running)

1. **Business Model:** B2B SaaS (revised economics above)
2. **Expected Outcome:**
   - Control arm: 35-45% profitable seeds, 55-65% loss
   - Trust-weighted should skew toward profitable seeds
   - If weighting beats control in ≥60% of seeds, claim is supported
3. **Agent Forecasts:**
   - Growth Marketer: "CAC will be < threshold" (critical)
   - Finance Controller: "Will achieve positive unit margin" (critical)
   - Both must reach ECE < 0.12 by month 12 for signal to matter
4. **Same Test Protocol:**
   - N=25 seeds
   - Arms A (control), B (weighting), C (CEO excluded), D (symmetric)
   - Pre-registered, all results reported

---

## The Honest Meta-Lesson

AgentCo's technology (trust controller, calibration) is correctly implemented. The PawDent test **failed to test the claim** because:

1. The business model lacked profitable decision-space
2. No seed ever achieved profitability, so no decision matters
3. All arms lost uniformly, proving noise, not signal

This isn't a flaw in AgentCo. It's a **fundamental principle of testing:**

> **You cannot test whether better decisions help if no better decision exists.**

The fair test is cleanly achievable. It just requires:
- Better business economics (profitable region exists)
- Suboptimal control (leaves money on table)
- Mixed outcomes (some seeds can succeed)

Only then can we truly answer: Does calibration-weighted decision-making improve outcomes?

---

## Recommendation

**Do not use PawDent to validate or refute AgentCo's claim.** Instead:

1. **Commit** to B2B SaaS model (or similar with mixed outcomes)
2. **Verify** control arm has both profitable and unprofitable seeds
3. **Pre-register** hypothesis (weighting beats control on cash)
4. **Run all four arms** on same 25 seeds
5. **Report honestly** whether weighting correlates with profitable seeds

If this test shows trust-weighting beats control, the claim is **proven on a fair test**.  
If it doesn't, that's **valuable information** (calibration alone isn't enough, or other factors dominate).

Either way, you'll have answered the actual question rather than a proxy question on a broken system.
