# PREREQUISITE 2 — Verification Gate

**Status:** Ready to execute  
**Purpose:** Confirm B2B SaaS model has profitable decision-space before running four-arm experiment

---

## The Gate (Before Running Full Experiment)

Run ONLY the control arm (equal-weighted decisions, no trust-weighting) on the B2B SaaS business model for N=25 pre-committed seeds.

**Report:**
1. How many of 25 seeds profitable? (Success criteria: 30-60%. If 0%, model is broken. If 100%, no decision-space.)
2. Is there variance in final cash across seeds? (Flat variance = no signal possible)
3. Does control policy visibly leave money on the table on losing seeds? (Evidence: identify specific suboptimal decisions)

**Pass/Fail:** 
- ✓ PASS: Mixed outcomes (30-60% profitable) + identified suboptimal decisions
- ✗ FAIL: Uniform profitability OR uniform losses OR flat variance across seeds

Only if PASS: proceed to full four-arm experiment (B, C, D) with pre-registered hypothesis.

---

## B2B SaaS Model Specification

### Product & Economics

**Product:** B2B SaaS, $99/month per customer

**Fixed Costs (scale-aware):**
- 0-50 customers: $3,000/month
- 51-150 customers: $5,000/month
- 151+ customers: $8,000/month

**COGS:**
- $20/customer/month (hosting, support, processing)

**Decision Levers:**
1. **Ad Spend:** $2k-8k/month (controls growth rate)
   - Low spend ($2-3k) → ~50-100 new customers/month (profitable)
   - Medium spend ($4-5k) → ~150-200 new customers/month (breakeven)
   - High spend ($6-8k) → ~250+ new customers/month (risky/loss)

2. **Churn Rate:** 3-8% depending on investment
   - Low churn ($1k CS investment): 3-4% churn, stable LTV
   - No CS investment: 6-8% churn, unstable LTV

3. **Pricing:** Dynamic adjustment available
   - Base $99, can adjust to $79-$129 per market signal

### The Control Policy (Intentionally Suboptimal)

**Control arm (equal-weighted, no trust-weighting):**
- Fixed ad spend schedule: $3k (months 1-6), $5k (months 7-18), $6k (months 19+)
- Pricing: Fixed $99, never adjusted
- Churn: No CS investment (6% churn)
- No decision-making based on signals

**Why suboptimal:**
- Doesn't scale spend down when CAC deteriorates
- Doesn't scale down on unprofitable market seeds
- Doesn't raise price on strong-demand seeds
- Doesn't invest in churn reduction (ROI > 3x)

**Result prediction:** Control should be profitable on "easy" seeds (good market), unprofitable on "hard" seeds (poor market signals).

---

## The Diagnostic Signal: Spread Analysis

### PawDent's Failed Signal (All Arms Uniform -$259k)
```
Arm A (control):     -$471k final cash (SD: $12.9k)
Arm B (weighting):   -$730k final cash (SD: $9.1k)
Arm C (CEO excluded): -$730k final cash (SD: $9.1k)
Arm D (symmetric):   -$730k final cash (SD: $10.5k)

Diagnosis: Fixed ~$259k offset across ALL arms
Result: NOISE, not signal (all formulas add variance to a broken system)
```

### Fair Test's Expected Signal (B2B SaaS)
```
Arm A (control):       -$100k to +$300k across 25 seeds
                       ~35-40% profitable, ~60-65% loss
                       SD: ~$150k (high variance = decision-space exists)
                       
Distribution: Some seeds win ($50-300k profit) due to good luck + control
              Some seeds lose ($50-200k loss) due to bad luck + control inability
              to adapt
```

**Why this is better signal:**
- Arm A has real win/loss variation (not uniform)
- Arm B can plausibly beat A on the winning/breakeven seeds
- Arm D's braking can plausibly help on the losing seeds
- Spread correlates with available decision-room, not fixed offset

---

## Before the Full Experiment

**Checklist:**
- [ ] Weighting formulas fixed to [0, full] range (PREREQUISITE 1) ✓ DONE
- [ ] B2B SaaS model built with viable unit economics
- [ ] Control arm run on 25 seeds
- [ ] Confirm 30-60% profitable seeds (gate passes) or model adjustments needed (gate fails)
- [ ] Identify specific suboptimal decisions the control makes
- [ ] Pre-register hypothesis: Trust-weighting beats equal-weighting on final cash, ≥14/25 seeds
- [ ] Pre-register falsification: B does not beat A in ≥14/25 seeds → hypothesis rejected

**Then and only then:** Run full four-arm experiment with spread analysis.

---

## What Will Be Proven

### If Control Passes Gate (30-60% profitable)
- ✓ Profitable decision-space exists
- ✓ Fair test is possible
- Ready to run Arm B/C/D and measure trust-weighting benefit

### If Spread Analysis Shows Treatment Wins Clustered on Profitable Seeds
- ✓ Trust-weighting correlates with decision-quality
- ✓ Calibration layer shows decision value
- ✓ AgentCo's claim is supported by fair test

### If Spread Analysis Shows Uniform Offset (Like PawDent)
- ✗ Trust-weighting adds noise, not signal
- ✗ Calibration alone doesn't help in this setup
- ✗ Different architecture or better calibration needed

---

## Timeline & Resources

- **Build B2B SaaS harness:** 1-2 hours
- **Run control arm (25 seeds):** 30-45 minutes
- **Gate verification & analysis:** 15 minutes
- **If gate passes: Full four-arm run:** 2-3 hours

**Total time if gate passes:** ~5-6 hours to full result

---

## Final Note

Do not proceed to the full experiment if control shows:
- Uniform failure (0% profitable) → Same broken-system problem as PawDent
- Uniform success (100% profitable) → No decisions matter, no signal possible
- Flat variance across seeds → No decision-space to test

The gate exists to prevent testing calibration's value on a system where decisions don't matter.
