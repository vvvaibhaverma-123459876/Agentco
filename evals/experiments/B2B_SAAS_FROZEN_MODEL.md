# B2B SaaS Business Model — FROZEN ARTIFACT

**Status:** This artifact is committed BEFORE wiring in agents.  
**Purpose:** Fix business model and control policy independently, to prevent co-design bias.  
**Commit Hash:** [TO BE FILLED WHEN COMMITTED, before any agent implementation]

**Independence Guarantee:** Business model, unit economics, oracle response surface, and control policy suboptimality are all chosen WITHOUT reference to what agents will predict. Agent forecast accuracy will emerge from the simulation naturally.

---

## Business Model Specification

### Product & Unit Economics

**Product:** B2B SaaS, $99/month per customer

**Cost Structure:**
- **COGS:** $20/customer/month (hosting, support, payment processing)
- **Fixed Costs (scale-aware):**
  - 0-50 customers: $3,000/month
  - 51-150 customers: $5,000/month
  - 151+ customers: $8,000/month

**Unit Economics Formula:**
```
LTV = ARPU × (1 / (churn_rate + discount_rate))
      where ARPU = $99 × (1 - refund_rate)
      
CAC = Monthly_Ad_Spend / New_Customers_Acquired

Profitability = Gross_Margin > (Fixed_Costs + Ad_Spend)
```

**Profitability Region:**
- Profitable: LTV > 3.5 × CAC, cash burn < $20k/month
- Breakeven: LTV ≈ 3 × CAC, cash burn ≈ $0
- Unprofitable: LTV < 2.5 × CAC, cash burn > $20k/month

---

## Market Oracle (Deterministic Response Surface)

**Seed-Dependent Market Conditions (Fixed):**

Each of 25 seeds generates a market with specific:
- Base demand elasticity (how many customers at given price/quality)
- Churn sensitivity to quality/support (if company cuts corners, churn rises)
- CAC trajectory (early/late market dynamics)
- Competitive pressure (when does it peak)

**Oracle Input:** Decisions (spend, price, quality investment, support level)  
**Oracle Output:** Actual customers, churn, CAC, retention

**Determinism:** Same seed + same decisions → same market outcome, always.  
Same seed + different decisions → different outcome (expected).

**Mathematical Form:**
```
new_customers = f(ad_spend, price, market_seed, month)
churn = g(quality_investment, support_level, market_seed)
retention_ltv = h(churn, arpu, discount_rate)
```

Functions f, g, h are fixed and deterministic, not hand-tuned to agent strengths.

---

## Control Policy (Intentionally Suboptimal)

### Why This Policy is Suboptimal (Independent Reasoning)

**The control policy is designed to be:**
1. **Inflexible:** Fixed spending formula regardless of market conditions
2. **Non-adaptive:** Never adjusts price based on demand signals
3. **Risky:** Doesn't invest in retention (highest-ROI lever)

**Independent Justification (NOT based on what agents will predict):**

- **Fixed ad spend is suboptimal because:**
  Real businesses adjust spend based on CAC trajectories.
  Leaving spend fixed on months when CAC is rising wastes capital.
  A smart business would cut when CAC > LTV risk threshold.
  Control misses this optimization.

- **Fixed pricing is suboptimal because:**
  Real businesses test pricing based on demand.
  If customers show strong willingness-to-pay, not raising price leaves margin on table.
  If churn spikes, raising price often signals scarcity/value (real B2B behavior).
  Control never adjusts.

- **No retention investment is suboptimal because:**
  Churn is the biggest threat to SaaS profitability.
  ROI on retention spend is 3-5x (invest $1k, save $3-5k LTV).
  Control saves $1k operationally but loses $3-5k LTV.
  Basic finance says this is backward.

**This suboptimality is generic to "naive SaaS operations," not designed around specific agent strengths.**

---

### The Control Policy (Fixed, Committed Here)

**Ad Spend Schedule** (no adjustment for CAC or market conditions):
- Months 1-6: $3,000/month
- Months 7-18: $5,000/month
- Months 19-36: $6,000/month

**Pricing** (fixed, never adjusted):
- All 36 months: $99/month

**Churn Management** (no CS investment):
- No additional support spending
- Result: 6-8% baseline churn (worse than invested competitor)

**Quality Investment** (minimal):
- $500/month (maintenance-level only)

**Rationale (Generic SaaS Anti-Pattern):**
"Run lean, don't experiment with pricing/retention." This is a textbook bad strategy, independent of any specific agent.

---

## 36-Month Deterministic Timeline

**Key Market Events (Programmed, Fixed):**

- **Months 1-6:** Early market (low CAC ~$25, 40% willing-to-pay at $99)
- **Months 7-12:** Market expansion (CAC rises ~$35, competition appears)
- **Months 13-18:** Competitive pressure (CAC ~$40-45, churn sensitivity increases)
- **Months 19-24:** Market maturity (CAC peaks ~$50, price wars, retention critical)
- **Months 25-36:** Consolidation (CAC stabilizes ~$45, profitable businesses thrive)

**Seed Variation (25 predetermined):**
Each seed gets a unique market curve within this timeline:
- Some seeds: more favorable early churn, easier growth
- Some seeds: harsh early market, high CAC from month 1
- Spread: 30-60% of seeds naturally profitable under control policy
  (due to market luck, not decision quality)

---

## Expected Outcomes Under Control Policy Alone

**Predicted Distribution (25 Seeds):**
- 8-10 seeds (32-40%): Profitable ($50-150k final cash)
- 5-6 seeds (20-24%): Breakeven ($-10k to +10k final cash)
- 9-10 seeds (36-40%): Loss ($-50k to -150k final cash)

**Why Mixed Outcomes:**
- Easy markets (low CAC, low churn): Control policy is "good enough"
- Hard markets (high CAC, high churn): Control policy's inflexibility hurts

**Variance (High):**
- SD across seeds: ~$120k-150k
- This variance indicates decisions matter (test is valid)

---

## Agent Forecasts (TO BE WIRED IN NEXT)

**Placeholder:** Agent forecast accuracy will emerge from simulation naturally.

**NOT predetermined:** We will NOT hand-set agents to be good at predicting exactly where control is bad.

**Agents will forecast:**
- Growth Marketer: "What will CAC be?"
- Finance Controller: "Will we hit revenue targets?"
- Operations: "Will churn exceed targets?"
- Product: "Will quality investment ROI justify spend?"

**Their accuracy will depend on:** How well their heuristics match this oracle (unknown until we run it).

---

## Independence Certification

This model is frozen and committed at git hash: **[COMMIT HASH BEFORE AGENTS]**

**Certified Independent:**
- ✓ Unit economics fixed before agents exist
- ✓ Oracle response surface fixed before agents' predictions
- ✓ Control policy suboptimality chosen for generic reasons
- ✓ No reference to what agents will predict
- ✓ Market conditions programmed before seeing agent heuristics

**This ensures:** Any "trust-weighting wins" on this business will reflect calibration helping decisions, not co-design bias.

---

## Notes for Implementation

**When wiring agents:**
1. Create forecast functions that generate agent predictions
2. Run simulation with agents predicting and oracle resolving
3. Agent accuracy (hit rate on claims) will be determined by how their heuristics match actual market outcomes
4. Do NOT tune agent parameters to match this model's structure
5. Do NOT adjust oracle based on agent predictions

**The test is valid if and only if:** Agents' forecasts emerge naturally from their heuristics, not from tuning to the known business structure.
