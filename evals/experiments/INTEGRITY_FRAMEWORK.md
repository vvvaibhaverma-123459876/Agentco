# Integrity Framework: Fair Test of Calibration-Weighting

**Date:** 2026-06-20  
**Purpose:** Document all safeguards against bias and co-design in the trust-weighting experiment.

---

## The Integrity Challenge

Testing whether "calibration-weighting improves decisions" is vulnerable to two opposite biases:

### Bias 1: PawDent's Failure-Rigging (What We Fell Into)
- Business is broken (no profitable region)
- All arms fail uniformly
- Conclude: "Calibration can't help" (true, but unfair test)
- Problem: Can't test anything when decisions don't matter

### Bias 2: Co-Design Success-Rigging (What We Must Prevent)
- Design business with specific weaknesses (e.g., inflexible pricing)
- Design agents to predict exactly those weaknesses
- Agents help weight spending away from broken decisions
- Conclude: "Calibration helps!" (but only because we built it that way)
- Problem: Artifact of design, not real calibration value

---

## Safeguards We've Built

### SAFEGUARD 1: Frozen Independence

**Principle:** Business model and agents must be designed independently.

**Implementation:**
1. **Commit business model FIRST** (before any agent code)
   - Unit economics, oracle, control policy
   - Artifact: `B2B_SAAS_FROZEN_MODEL.md`
   - Commit hash recorded before agents exist

2. **Document control suboptimality independently**
   - Why is control bad? (Generic SaaS anti-patterns, not agent-specific)
   - Don't reference agent strengths
   - Commit this reasoning with the frozen model

3. **Wire in agents AFTER model is locked**
   - Agents generate forecasts based on their heuristics
   - Agent accuracy emerges from oracle, not hand-tuned
   - No parameter tuning to match business structure

4. **Verify in final report**
   - Show both commit hashes (model, then agents)
   - Confirm temporal order
   - Confirm control policy reasons were independent

---

### SAFEGUARD 2: Profitable Decision-Space Verification

**Principle:** Can't test decision-weighting if no decision-space exists.

**Implementation:**
1. **Run control arm ONLY on 25 seeds** (prerequisite 2 gate)
2. **Verify mixed outcomes** (30-60% profitable, not 0% or 100%)
3. **Stop and redesign if gate fails**
   - 0% profitable → broken unit economics (like PawDent)
   - 100% profitable → no decisions matter
   - Flat variance → no signal possible

**Verification in Report:**
- Report profit distribution (histogram of 25 seeds)
- Confirm variance exists (SD > threshold)
- Show specific seeds where control left money on table

---

### SAFEGUARD 3: Weighting Formula Integrity

**Principle:** De-weighting must actually work (not blocked by hardcoded floors).

**Implementation:**
1. **Fixed floor flaw** (prerequisite 1)
   - OLD: `(0.5 + 1.5*trust)` → min floor 0.5x
   - NEW: `(2.0*trust)` → true zero possible
   - Applied to all decision levers

2. **Verified by test suite**
   - trust=0 → 0x influence ✓
   - trust=1 → 2x influence ✓
   - No hardcoded floors ✓

**Verification in Report:**
- Cite test suite (test_weighting_floor_fix.py passes)
- Confirm no agent can be given nonzero weight below actual influence floor

---

### SAFEGUARD 4: Pre-Registration Lock-In

**Principle:** Hypothesis and falsification criteria set BEFORE results are seen.

**Implementation:**
1. **Pre-register before running full experiment**
   - Hypothesis: Trust-weighting beats control ≥14/25 seeds
   - Falsification: B does not beat A in ≥14/25 seeds
   - Metrics: final cash balance, spread analysis

2. **Cannot adjust after seeing results**
   - Commit pre-registration to git before experiment runs
   - Report includes hash of pre-registration

**Verification in Report:**
- Show pre-registered hypothesis commit hash
- Show actual results
- Report whether hypothesis was rejected or supported

---

### SAFEGUARD 5: Spread Analysis (Not Just Mean)

**Principle:** Uniform offset is a red flag (noise, not signal).

**Implementation:**
1. **Report full distribution, not just averages**
   - All 25 seeds, all four arms
   - Cash balance spread (min, max, SD)
   - Per-seed winner (A vs B vs C vs D)

2. **Diagnostic: Compare to PawDent's failed signal**
   - PawDent: fixed ~$259k offset (ALL arms identical offset)
   - Fair test: spread should vary by decision-quality
   - Signal: weighting wins cluster on profitable seeds
   - Noise: weighting offset is uniform (B's loss is constant across all seeds)

**Verification in Report:**
- Show distribution plots (not just means)
- Show correlation between spread and profitable decision-space
- Flag if offset is uniform (indicates test failure, not result)

---

### SAFEGUARD 6: Honest Verdict

**Principle:** Report what's actually been shown, not oversell.

**Implementation:**

**Do NOT assert:**
- "The trust controller is sound" (too broad; co-design bias possible)
- "Calibration improves all decisions" (narrow finding only)
- "This proves AgentCo's claim" (only proves on this one model)

**DO assert:**
- "Business model was frozen before agents" (cite hashes)
- "Control policy suboptimality was chosen independently" (cite reasoning)
- "Weighting formula floor flaw was fixed and verified" (cite tests)
- "On this specific B2B SaaS model, trust-weighting [did/did not] beat equal-weighting"
- "Spread analysis shows [signal/noise] — weighting wins [clustered/uniform]"
- "This provides evidence that calibration [can/cannot] improve decisions in this setup"

---

## Audit Checklist (For Final Report)

**Before declaring results:**
- [ ] Git commit hash of frozen business model (BEFORE any agents)
- [ ] Git commit hash of agents wiring (AFTER model locked)
- [ ] Verify temporal order: model → agents (not simultaneous)
- [ ] Show control policy reasoning (independent of agents)
- [ ] Confirm 30-60% of seeds profitable under control (gate passed)
- [ ] Show weighting floor test results (prerequisite 1 passed)
- [ ] Show pre-registration hash (hypothesis locked before runs)
- [ ] Report all 25 seeds (no cherry-picking)
- [ ] Show spread distribution (not just means)
- [ ] Compare spread to PawDent's failed signal (noise vs signal analysis)
- [ ] Honest verdict (what's actually proven, not oversold)

---

## The Integrity Statement (To Include in Final Report)

Example language:

> **Integrity Framework**
>
> This experiment was conducted under multiple safeguards to prevent co-design bias:
>
> 1. **Independent Design:** Business model (`B2B_SAAS_FROZEN_MODEL.md`) was designed and committed [HASH] before any agent implementation. Control policy suboptimality was chosen for generic SaaS anti-pattern reasons, not based on anticipated agent predictions.
>
> 2. **Frozen Prerequisite:** Control arm ran on 25 seeds before agents were wired in, verifying profitable decision-space existed (30-60% profitable seeds, high variance).
>
> 3. **Weighting Integrity:** Weighting formula floor flaw (prerequisite 1) was fixed and verified by test suite; true zero-weighting is now possible.
>
> 4. **Pre-Registration:** Hypothesis and falsification criteria were locked in git [HASH] before running the full four-arm experiment.
>
> 5. **Spread Analysis:** Results are reported per-seed and by distribution. Spread is analyzed for clustering (signal) vs. uniform offset (noise). Compared to PawDent's failed signal to confirm methodological improvement.
>
> **Conclusion:** This experiment provides evidence that [trust-weighting did/did not] improve decisions on this specific B2B SaaS model, with [high/low] confidence that the result reflects calibration benefit rather than experimental design.

---

## Why This Matters

Without these safeguards:
- ✗ PawDent-style: We tested on broken business, concluded nothing
- ✗ Co-design-style: We'd test on business+agents designed together, claimed success

With these safeguards:
- ✓ We test on viable business with real decision-space
- ✓ Business and agents designed independently
- ✓ Results reflect calibration quality, not bias
- ✓ Honest verdict accurately scoped

The integrity framework ensures: **A "trust-weighting win" would mean calibration actually helps, not that we rigged the experiment.**

---

## Implementation Checklist

**Phase 1: Freeze (NOW)**
- [✓] Weighting formulas fixed (prerequisite 1)
- [✓] Frozen model artifact created (`B2B_SAAS_FROZEN_MODEL.md`)
- [✓] Independence safeguard documented

**Phase 2: Verify (Next)**
- [ ] Build B2B SaaS harness from frozen model
- [ ] Run control arm on 25 seeds (prerequisite 2 gate)
- [ ] Verify 30-60% profitable, confirm variance
- [ ] Stop or proceed based on gate

**Phase 3: Wire (If Gate Passes)**
- [ ] Implement agent forecasting code
- [ ] Pre-register hypothesis (commit to git)
- [ ] Run full four-arm experiment
- [ ] Analyze spread (signal vs. noise)

**Phase 4: Report (Final)**
- [ ] Include integrity statement
- [ ] Show commit hashes (model → agents)
- [ ] Report all 25 seeds, full distribution
- [ ] Honest verdict (what's actually proven)
