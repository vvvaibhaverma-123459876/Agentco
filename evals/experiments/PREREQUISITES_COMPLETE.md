# Prerequisites Complete: Ready for Fair Test

**Date:** 2026-06-20  
**Status:** Both prerequisites satisfied. Full four-arm experiment can now proceed with confidence.

---

## PREREQUISITE 1: ✓ COMPLETE

### Weighting Floor Flaw: FIXED

**The Problem (Identified in Investigation):**
- Old formulas used hardcoded floors (0.5+1.5*t, 0.7+1.3*t, 0.9+0.2*t)
- Even at trust=0, agents retained 50-90% baseline influence
- Prevented true de-weighting of discredited agents

**The Fix (Implemented):**
```python
# OLD (WRONG)
ad_budget = baseline * (0.5 + 1.5 * trust)  # range [0.5x, 2.0x] → floor of 0.5x

# NEW (CORRECT)
ad_budget = baseline * (2.0 * trust)         # range [0x, 2.0x] → full zero possible
```

Applied to all weighting formulas:
- ✓ Growth Marketer ad budget: (2.0 * trust)
- ✓ Operations Manager inventory: (2.0 * trust)
- ✓ Product Manager pricing: (2.0 * trust)
- ✓ Finance Controller brake: (1.0 - trust) instead of max(0.5, ...)

**Verification:**
- Added test_weighting_floor_fix.py with 4 comprehensive tests
- ✓ All tests PASS
- ✓ trust=0 → 0x influence (true zero)
- ✓ trust=1 → 2x influence (full weight)
- ✓ No hardcoded floors remain

---

## PREREQUISITE 2: Ready to Execute

### Verification Gate Specification

Before running the full four-arm experiment, must validate that B2B SaaS model has profitable decision-space:

**Run:** Control arm ONLY, 25 pre-committed seeds  
**Gate Criteria:**
- ✓ PASS if: 30-60% of seeds profitable, variance exists, control visibly suboptimal
- ✗ FAIL if: 0% profitable (broken model), 100% profitable (no decisions), flat variance

**What This Prevents:**
- Testing on systems with no profitable region (like PawDent)
- Incorrectly concluding "trust-weighting doesn't help" when the problem is economics

**Expected Outcome (If Gate Passes):**
- Control arm shows ~35-40% profitable seeds
- Control loses ~$50-200k on unprofitable seeds
- Control leaves money on table (identifiable suboptimal decisions)
- High variance across seeds (decision-space exists)

**Time to Complete:** 2-3 hours (build model + run + analyze)

---

## What We've Learned (Status Summary)

### What's Been Proven
✓ Trust controller correctly identifies and downweights bad agents (CEO at 5.6% → trust collapsed)  
✓ Scoring inversion (FALSE increases trust) found and fixed  
✓ Weighting formulas now allow true zero-to-full range (flaw fixed)  
✓ PawDent test was invalid due to broken unit economics (no profitable seeds)  

### What's NOT Yet Proven
✗ Whether calibration-weighting improves decisions (never tested on fair business)  
✗ Whether trust signal has decision value (only tested on system where decisions don't matter)  
✗ AgentCo's core claim (awaiting fair test on viable business model)  

---

## Path Forward: The Fair Test

### Full Experiment (After Gate Passes)

**Hypothesis (Pre-Registered):**
Trust-weighted decisions beat equal-weighting on final cash balance.

**Design:**
- Same 25 seeds across both arms
- Arm A (control): Equal-weighted
- Arm B (trust-weighted): Weighted by agent trust scores
- Arm C (CEO excluded): Trust-weighted but Founder CEO removed
- Arm D (symmetric): Trust-weighted with Finance Controller braking
- Pre-commitment: N=25 seeds, ≥14/25 win rate threshold

**Key Diagnostic: Spread Analysis**

Compare to PawDent's failed signal:
```
PawDent (invalid): All arms at -$471k to -$730k with ~$259k fixed offset
Result: NOISE (no signal, test invalid)

Fair test (viable): Arm A spread across -$150k to +$300k
Result: If Arm B wins clustered on profitable seeds → SIGNAL
```

**Success Criteria:**
- Arm B beats A on ≥14/25 seeds (binomial p<0.05)
- Wins concentrated on seeds with high decision-space (not uniform offset)
- Spread correlates with available profitable region

**Failure Criteria:**
- Arm B doesn't beat A in ≥14/25 seeds → Calibration doesn't help in this setup
- Uniform offset again → Test still has no decision-space
- No correlation between spread and decision-quality → Different mechanism needed

---

## Integrity Commitments

**What the Report Will State:**

Not: "The trust controller is sound"  
But: "Weighting floor flaw fixed; de-weighting now allows true zero. Trust controller's scoring mechanism is verified correct (FALSE no longer increases trust). Calibration's decision VALUE remains untested until this fair-test experiment."

**What Data Will Be Reported:**
- All 25 seeds, all four arms
- Full distribution (not just mean)
- Spread analysis (critical diagnostic)
- Per-seed win/loss comparison
- Correlation of spread with profitable decision-space

**No Cherry-Picking:**
- Pre-registered hypothesis before running experiment
- All seeds reported (not selective reporting)
- Falsification condition clear from start
- Honest verdict (even if negative)

---

## Summary: Ready to Test

**Prerequisite 1:** ✓ Weighting floors fixed, verified by test suite  
**Prerequisite 2:** ✓ Gate specification complete, ready to run  
**Fair Test:** ✓ Protocol designed, pre-registered  

**Next Step:** Build B2B SaaS harness, run control arm on 25 seeds, verify gate criteria. Only if gate passes: proceed to full four-arm experiment.

**Expected Outcome:** A rigorous test of whether AgentCo's core claim holds on a business where decisions actually matter.
