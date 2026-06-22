# Civilization Calibration & Trust Governance - Migration & Implementation Audit

**Date**: 2026-06-23  
**Status**: 🔴 **CRITICAL ISSUES FOUND - MIGRATION FOUNDATION BROKEN**

---

## EXECUTIVE SUMMARY

The migration infrastructure has **parallel lineages** that conflict, **missing critical tables** referenced by production services, and **fake test targets** that report success without verification.

**Verdict**: Cannot proceed with Civilization Calibration & Trust Governance until Phase 0 (migration cleanup) is complete.

---

## SECTION 1: MIGRATION LINEAGE ANALYSIS

### Discovery: Two Parallel Migration Lineages

**LINEAGE A - Integrated Phases (Comprehensive, 2026 work)**
```
025_goal_management.sql
026_phases_5_8_integrated.sql
027_phases_9_13_integrated.sql
028_civilization_learning_structure.sql
```

Creates 43 tables including:
- ✅ autonomy_goals, autonomy_plans, autonomy_outcomes
- ✅ learner_runs, learner_candidates, replay_batches
- ✅ simulator_runs, simulator_steps, simulator_outcomes
- ✅ eval_suites, eval_runs, eval_scorecards
- ✅ reward_functions, reward_calculations
- ✅ artifact_registry, artifact_signatures, artifact_deployments
- ✅ canary_plans, canary_observations, rollback_events
- ✅ **civilization_entities, civilization_memberships, civilization_learning_events, institutional_knowledge_items, society_disputes, civilization_governance_reviews**

**LINEAGE B - Standalone Phases (Partial, older work)**
```
025_autonomy_goals.sql
026_autonomy_plans.sql
027_reward_system.sql
028_eval_harness.sql
```

Creates only 15 tables:
- ✅ autonomy_goals, autonomy_plans
- ✅ eval_suites, eval_runs, eval_scorecards
- ✅ reward_functions, reward_calculations
- ❌ MISSING: learner_*, simulator_*, artifact_*, canary_*, rollback_*, civilization_*, deployment_snapshots, active_artifacts

### The Conflict

Both lineages define `autonomy_goals`, `autonomy_plans`, `eval_*`, `reward_*` tables.

When migrations run alphabetically, both get applied:
1. **025_autonomy_goals.sql** creates `autonomy_goals` (wins, establishes schema)
2. **025_goal_management.sql** tries to create same table → `IF NOT EXISTS` silently no-ops
3. Later migrations reference columns from one or the other → **schema mismatch failures**

### Service Requirements Analysis

Mapped what each service actually needs:

| Service | Tables Required | Lineage A | Lineage B |
|---------|-----------------|-----------|-----------|
| orchestrator | autonomy_tasks, goals, plans, outcomes, eval_*, reward_* | ✅ All | ✅ Partial (no outcomes in B) |
| learner | learner_*, replay_*, trajectory_store | ✅ Has | ❌ **MISSING** |
| simulator | simulator_*, trajectory_store | ✅ Has | ❌ **MISSING** |
| eval-harness | eval_*, autonomy_*, reward_*, trajectory_store | ✅ Has | ⚠️ Partial |
| rollback | deployment_snapshots, active_artifacts, canary_rollback_events | ❓ Check | ❌ No |
| civilization | civilization_*, institutional_*, society_* | ✅ Has | ❌ **MISSING** |

**Verdict**: **LINEAGE A is the canonical lineage. LINEAGE B is incomplete and must be disabled.**

---

## SECTION 2: MISSING TABLES IN ALL MIGRATIONS

### Critical Finding: Rollback Service Tables Don't Exist

The `rollback.service.ts` references:
- `deployment_snapshots` (line 46 INSERT)
- `active_artifacts` (line 37 SELECT)
- `canary_rollback_events` (assumed in rollback operations)

**Grep Result**: These tables are **not created in ANY migration file**.

```bash
$ grep -r "CREATE TABLE.*deployment_snapshots\|CREATE TABLE.*active_artifacts" backend/src/db/migrations/
# (no output)
```

**Impact**: The rollback service will crash at runtime with `relation "deployment_snapshots" does not exist` when attempting to create a pre-deployment snapshot.

**This breaks**: 
- Phases 9-13 self-improvement canary/rollback
- Civilization calibration trust policy canary/rollback
- Any artifact deployment safeguard

**Required Action**: Create migration to add:
1. `deployment_snapshots` table
2. `active_artifacts` table  
3. `canary_rollback_events` table (if not covered by canary_observations + rollback_events)

---

## SECTION 3: FAKE TEST ANALYSIS

### Fake Targets in Makefile

Found **7 test targets that report success without running actual tests**:

```makefile
autonomy-memory-quality-test:
	@echo "✅ Stale memory demotion and simulation label enforcement verified"

autonomy-observability-test:
	@echo "✅ Metrics recording and 4-signal verification implemented"

autonomy-learner-test:
	python3 -c "print('✅ PHASE 9 learner tests would verify real logic')"

autonomy-simulator-test:
	python3 -c "print('✅ PHASE 10 simulator tests would verify determinism')"
```

Each reports `✅ PASSED` without:
- ❌ Connecting to database
- ❌ Running actual test assertions
- ❌ Querying real tables
- ❌ Verifying real behavior

### Civilization Learning Test

The `test_civilization_learning.py` **appears to be REAL** (has code structure) but was previously identified as **completely fake** — all 14 "checks" are:
```python
checks_passed += 1
print("✅ ...")
```

With **zero database queries** or assertions.

---

## SECTION 4: MIGRATION APPLICATION FAILURES

When attempting clean migration on fresh database:

```
▶️  Applying 026_phases_5_8_integrated.sql...
   column "simulation_derived" does not exist
❌ FAILED
```

**Root Cause**: Migration 026_phases_5_8_integrated.sql tries to:
1. Create `autonomy_goals` (with `simulation_derived` column)
2. But `025_autonomy_goals.sql` already created it without that column
3. `IF NOT EXISTS` silently no-ops
4. Later index creation fails

**This cascades**: 025_autonomy_goals defines different schema than 026_phases_5_8_integrated expects → column mismatches → migration incomplete → no civilization tables → Step 1 verification impossible.

---

## SECTION 5: SCHEMA INCONSISTENCIES

### autonomy_goals Column Mismatch

**025_autonomy_goals.sql defines**:
```sql
source TEXT NOT NULL CHECK (source IN ('agent_proposed', 'perception_derived', 'governance_mandated', 'manual')),
autonomy_level_allowed autonomy_level NOT NULL DEFAULT 'L2',
```

**026_phases_5_8_integrated.sql expects**:
```sql
source TEXT NOT NULL CHECK (source IN ('system', 'agent', 'user', 'simulator')),  -- DIFFERENT!
autonomy_level_allowed autonomy_level,
simulation_derived BOOLEAN DEFAULT false,  -- MISSING in 025_autonomy_goals
```

**orchestrator.service.ts inserts**:
```typescript
source: 'system',  -- This CHECK fails in 025_autonomy_goals!
```

**Verdict**: Services were written against Lineage A schema. Lineage B is incompatible.

---

## SECTION 6: RECOMMENDATIONS - PHASE 0 ACTIONS

### Immediate (Today)

1. **Disable Lineage B migrations**
   ```bash
   mv backend/src/db/migrations/025_autonomy_goals.sql backend/src/db/migrations/025_autonomy_goals.sql.disabled
   mv backend/src/db/migrations/026_autonomy_plans.sql backend/src/db/migrations/026_autonomy_plans.sql.disabled
   mv backend/src/db/migrations/027_reward_system.sql backend/src/db/migrations/027_reward_system.sql.disabled
   mv backend/src/db/migrations/028_eval_harness.sql backend/src/db/migrations/028_eval_harness.sql.disabled
   ```

2. **Create missing rollback tables migration** → `029_rollback_infrastructure.sql`
   - `deployment_snapshots` table
   - `active_artifacts` table
   - `canary_rollback_events` table (or verify rollback_events is sufficient)

3. **Test clean migration**
   ```bash
   DROP DATABASE agentco; CREATE DATABASE agentco;
   npm run db:migrate
   psql -c "\dt" # Verify 43 tables exist, including civilization_*
   ```

4. **Fix civilization learning test** → rewrite to actually query DB
   - Connect to database
   - Run 14 assertions (not just increment counter)
   - Prove civilization entities exist
   - Prove learning events are attributed correctly

### Short-term (This Session)

5. **Disable or rewrite fake test targets in Makefile**
   - Change echo-only targets to real tests
   - Or explicitly mark as `# PLACEHOLDER` and link to real test

6. **Create real test for rollback** (vertical slice)
   - Test rollback tables exist
   - Test deployment_snapshots capture pre-state
   - Test rollback restores previous artifact

---

## SECTION 7: BLOCKERS FOR CIVILIZATION CALIBRATION & TRUST

**Cannot implement Phases 2-12** (calibration constitution, trust policies, impact assessment, etc.) until:

✅ Migration foundation is fixed (Lineage A canonical, Lineage B disabled)  
✅ Missing rollback tables are created  
✅ Fresh migration applies cleanly  
✅ `\dt` shows all 43+ tables exist  
✅ Civilization learning test is rewritten to query DB  
✅ At least one real vertical slice (trust-policy → canary → rollback) works end-to-end  

---

## SECTION 8: FILES TO UPDATE/CREATE

| File | Action | Priority |
|------|--------|----------|
| `025_autonomy_goals.sql` | Disable (add `.disabled`) | CRITICAL |
| `026_autonomy_plans.sql` | Disable (add `.disabled`) | CRITICAL |
| `027_reward_system.sql` | Disable (add `.disabled`) | CRITICAL |
| `028_eval_harness.sql` | Disable (add `.disabled`) | CRITICAL |
| `029_rollback_infrastructure.sql` | Create new | CRITICAL |
| `scripts/test_civilization_learning.py` | Rewrite with DB queries | CRITICAL |
| `Makefile` | Remove/fix fake targets | HIGH |

---

## CONCLUSION

**Status**: 🔴 CRITICAL - MIGRATION FOUNDATION BROKEN

AgentCo cannot proceed with Civilization Calibration & Trust Governance until the migration lineage is consolidated and missing tables are added.

**Next Step**: Execute Phase 0 actions above, then re-run `npm run db:migrate` against fresh database and verify schema.

**Expected Completion**: 1-2 hours for Phase 0 cleanup.
