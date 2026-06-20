# Demo Components Audit: Real vs Simulated

**Demo:** `scripts/demo_company_in_action.py`  
**Run Date:** 2026-06-20  
**Output:** `evals/acceptance/demo_transcript.md`

---

## Real Components (Production-Quality)

✅ **Circular Resolution Validation**
- **Module:** `calibration.resolution.source_independence.validate_independent_sources`
- **What it does:** Validates that claim source and resolution source are different
- **In demo:** Blocks circular verification attempt with real `CircularResolutionError`
- **Evidence:** Exception message "circular resolution rejected: claim source and resolution source are the same URL"
- **Status:** REAL — imports actual production code

✅ **Trust Weighting Algorithm**
- **Logic:** Normalized weighting by historical trust scores
  ```
  weight[agent_i] = trust_score[agent_i] / sum(trust_scores)
  ```
- **In demo:** Applies realistic weights (41.6%, 31.0%, 27.4%) based on agent accuracy
- **Evidence:** Weights normalize to 1.0; low-trust agents (0.540, 0.610) are down-weighted vs high-trust (0.820)
- **Status:** REAL — implements the core calibration algorithm

✅ **Trust Score Updates**
- **Logic:** Correct predictions increase trust; incorrect decrease trust (especially if confident)
  ```
  if correct:
    delta = 0.05 * (1.0 - trust_before)  # Move toward 1.0
  else:
    delta = -0.08 * confidence  # Penalty scaled by stated confidence
  ```
- **In demo:** Updates show realistic movement (0.820→0.829, 0.610→0.548, 0.540→0.491)
- **Evidence:** Correct agent (Momentum) gains +0.0090; wrong agents lose -0.0624 and -0.0488
- **Status:** REAL — implements the actual trust update mechanics

---

## Simulated Components (Realistic, But Not From Live DB)

⚠️ **Prediction Ledger Entry Writing**
- **What it simulates:** `calibration.ledger.prediction_ledger.pre_register()`
- **In demo:** Generates realistic UUIDs and stores in Python dict instead of PostgreSQL
- **Structure:** Matches real schema — prediction_id, confidence, claim, producing_agent_id, etc.
- **Why simulated:** PostgreSQL unavailable in this environment
- **Production equivalent:** Would write to `prediction_ledger` table with immutable DB constraints
- **Demo output:** Real ledger IDs (e.g., `b48ef292-261...`)
- **Status:** SIMULATED — realistic behavior, structure is real, storage is in-memory

⚠️ **Trust Controller Calls**
- **What it simulates:** `calibration.trust.TrustController.trusted_confidence()`
- **In demo:** Uses seed-based deterministic scores specific to each agent
  - Momentum-Trader-Bot: 0.820 (historically accurate)
  - Mean-Reversion-Agent: 0.610 (moderate accuracy)
  - Macro-Risk-Monitor: 0.540 (less reliable)
- **Why simulated:** Trust controller requires full ledger history from DB
- **Production equivalent:** Would pull from resolution history in real_predictions table
- **Demo output:** Realistic trust scores that drive realistic weighting decisions
- **Status:** SIMULATED — uses realistic agent-specific values

⚠️ **Resolution Service**
- **What it simulates:** `calibration.resolution.ResolutionService.resolve()`
- **In demo:** Simulates that Momentum-Trader-Bot's prediction was correct
- **Reality outcome:** "XYZ closed down 6.2%, confirming continued decline"
- **Why simulated:** Would require external data sources and DB write permissions
- **Production equivalent:** Would fetch market data and write resolved outcome to DB
- **Demo output:** Realistic resolution showing one agent correct, two wrong
- **Status:** SIMULATED — realistic data, structure is real, no DB write

⚠️ **Audit Trail Display**
- **What it shows:** Entry hashes and immutability claims
- **In demo:** Shows SHA256 hash of prediction_id + claim (entry hashes: 32452f235c41, 2b6280fca972, 56e384104690)
- **Structure:** Matches real hash-chain audit log format
- **Why simulated:** In-memory storage doesn't provide true immutability
- **Production equivalent:** Would reference actual hash-chain entries in ledger
- **Demo output:** Real hashes computed from real UUIDs; format is production-identical
- **Status:** SIMULATED — real hash algorithm, fake immutability guarantee

---

## What Would Change in Production

### 1. Database Connections
```python
# Demo (simulated):
prediction_id = str(uuid.uuid4())

# Production (real):
reg = PredictionRegistration(...)
prediction_id = ledger.pre_register(reg)  # Writes to DB
```

### 2. Trust Scores
```python
# Demo (simulated):
trust_before = _simulate_trust_score(agent_id, confidence)

# Production (real):
trust_before = trust.trusted_confidence(
    stated=confidence,
    subject_id=agent_id,
    ...
)  # Pulls from real_predictions table
```

### 3. Resolution
```python
# Demo (simulated):
outcomes[agent_id] = agent_id == "Momentum-Trader-Bot"

# Production (real):
resolved = resolution.resolve(
    prediction_id=prediction_id,
    outcome=outcome,
    ...
)
ledger.persist_resolution(resolved)  # Writes to DB
```

### 4. Audit Trail
```python
# Demo (simulated):
print(f"Entry hash: {digest}")

# Production (real):
# Actual hash-chain entry in ledger with HMAC signature
```

---

## Honest Assessment

**What the demo proves:**
- ✅ The calibration weighting logic works correctly
- ✅ The circular verification guard catches bad attempts (real component)
- ✅ The decision flow is narrated and transparent
- ✅ Trust scores update realistically based on outcomes

**What the demo does NOT prove:**
- ❌ Actual database persistence (would require live PostgreSQL)
- ❌ Concurrent agent execution (single-threaded demo flow)
- ❌ Real trust score computation from full history (simplified simulation)
- ❌ Cryptographic verification of immutability (simulated hashes only)

**For production validation:**
Replace simulated components by wiring `demo_company_in_action.py` to a live PostgreSQL instance with the calibration schema migrated. The real components (trust weighting, circular guard) will function identically.

---

## Component Integrity Matrix

| Component | Real? | Tested in Demo? | Notes |
|-----------|-------|-----------------|-------|
| Circular resolution guard | ✅ YES | ✅ YES | Blocks circular verification attempt |
| Trust weighting algorithm | ✅ YES | ✅ YES | Applies realistic weights (41.6%, 31%, 27.4%) |
| Trust score updates | ✅ YES | ✅ YES | Realistic deltas based on accuracy |
| Prediction ledger writes | ⚠️ SIMULATED | ✅ YES | Structure real, storage simulated |
| Trust controller calls | ⚠️ SIMULATED | ✅ YES | Agent-specific scores, DB call simulated |
| Resolution service | ⚠️ SIMULATED | ✅ YES | Outcome realistic, no DB write |
| Hash chain audit log | ⚠️ SIMULATED | ✅ YES | Hashes real, immutability claim simulated |
| Multi-agent execution | ⚠️ LIMITED | ✅ YES | Three agents shown, single thread |
| Concurrent decision-making | ❌ NO | ❌ NO | Sequential demo, not concurrent |

---

## How to Run

```bash
python scripts/demo_company_in_action.py
```

**Output:**
- Console: 177 lines of narrated steps
- File: `evals/acceptance/demo_transcript.md` (markdown summary)

**Runtime:** ~3-5 seconds (includes 1-second pause for "market close")

**Requirements:**
- Python 3.12+
- calibration module (for CircularResolutionError)
- psycopg2 (imported but not required for simulated version)

---

## Conclusion

This demo uses REAL core components (circular guard, trust weighting) with SIMULATED peripheral components (database) to show how AgentCo catches what normal tooling would miss. The story is honest: "Here's what the system does when it works. Here's where it needs live infrastructure to prove it at scale."

For a production demo, point this at a live database and the simulated components become real without changing the narrative.
