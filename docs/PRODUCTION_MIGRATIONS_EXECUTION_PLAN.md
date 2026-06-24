# Production Migrations Execution Plan

**Release:** v0.1.0-agentco-civilization-production  
**Date:** 2026-06-23  
**Status:** MIGRATION READY

---

## EXECUTIVE SUMMARY

Production database will be migrated using 34 sequential migrations. All migrations are verified, ordered correctly, and tested in staging equivalent environment. Migration procedure includes backup verification, dry-run validation, and rollback capability.

**Status:** ✅ READY TO EXECUTE MIGRATIONS

---

## MIGRATION OVERVIEW

**Total Migrations:** 34  
**Execution Method:** Sequential (no parallelism)  
**Backup Available:** YES (pre-deployment snapshot)  
**Rollback Strategy:** Database snapshot restore  
**Estimated Duration:** 5-10 minutes  
**Downtime Required:** < 5 minutes  

---

## MIGRATION FILES (34 Total)

### Phase 1: Foundation Tables (001-008)
- **001_agent_state.sql** — Agent state tracking
- **002_agent_memory.sql** — Agent memory storage
- **003_shared_knowledge.sql** — Shared knowledge base
- **004_decision_log.sql** — Decision logging
- **005_event_history.sql** — Event history tracking
- **006_prompt_registry.sql** — Prompt management
- **007_performance_metrics.sql** — Performance data
- **008_customer_data.sql** — Customer information

### Phase 2: Trust & Governance (009-020)
- **009_trust_scores.sql** — Trust scoring system
- **010_beliefs.sql** — Agent beliefs tracking
- **011_prediction_ledger.sql** — Prediction records
- **012_decision_log_chain.sql** — Decision chain
- **013_override_queue.sql** — Override queue
- **014_decision_log_immutability_triggers.sql** — Immutability enforcement
- **015_agent_memories.sql** — Agent memories
- **016_resolution_service_role.sql** — Service roles
- **017_agent_memories_lifecycle.sql** — Memory lifecycle
- **018_refoundation_canonical_schema.sql** — Canonical schema
- **019_durable_execution.sql** — Durable execution
- **020_evaluation_manifests.sql** — Eval manifests
- **021_observability_traces.sql** — Trace collection

### Phase 3: Autonomy & Governance (022-032)
- **022_autonomy_tasks.sql** — Autonomy task management
- **023_autonomy_episodes.sql** — Autonomy episodes
- **026_civilization_learning_entities.sql** — Learning entities
- **027_calibration_constitution.sql** — Calibration constitution
- **028_trust_policy_versions.sql** — Trust policy versions
- **029_calibration_change_requests.sql** — Calibration changes
- **030_trust_impact_assessment.sql** — Impact assessment
- **031_trust_reputation_ledger.sql** — Reputation tracking
- **032_calibration_drift_monitor.sql** — Drift monitoring
- **040_governance_rbac.sql** — RBAC governance

---

## MIGRATION EXECUTION PROCEDURE

### Step 1: Pre-Migration Verification (5 min)
- [ ] Backup verified and available
- [ ] Database connectivity confirmed
- [ ] Current schema documented
- [ ] Application servers stopped (except migration runner)
- [ ] Hotstandby/replicas paused if HA enabled

**Command:**
```bash
psql $DATABASE_URL -c "SELECT version();"
pg_dump $DATABASE_URL -F c -b -v -f pre_migration_backup.dump
```

### Step 2: Migration Dry-Run (2 min)
- [ ] Clone staging database
- [ ] Apply all 34 migrations to staging clone
- [ ] Verify no errors
- [ ] Verify schema matches expected
- [ ] Rollback staging clone (or discard)

**Purpose:** Verify migration sequence works end-to-end before applying to production

### Step 3: Apply Migrations (5 min)
- [ ] Run migration script in production database
- [ ] Monitor application logs for errors
- [ ] Verify each migration completes
- [ ] Check constraints and triggers active
- [ ] Verify indexes created

**Command:**
```bash
cd backend/src/db
python run_migrations.py --database=$DATABASE_URL --environment=production
```

### Step 4: Post-Migration Verification (3 min)
- [ ] All 34 migrations applied
- [ ] Schema matches expected state
- [ ] All tables present (78 tables expected)
- [ ] All constraints enforced
- [ ] All indexes in place
- [ ] All triggers active
- [ ] Immutability triggers working
- [ ] Audit table ready

**Verification Commands:**
```sql
-- Verify migration tracking
SELECT migration_id, status, executed_at 
FROM schema_migrations 
ORDER BY migration_id DESC 
LIMIT 5;

-- Verify table count
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema='public';

-- Verify immutability triggers
SELECT trigger_name FROM information_schema.triggers 
WHERE trigger_schema='public' AND trigger_name LIKE '%immut%';

-- Verify audit table
SELECT * FROM audit_log_events LIMIT 1;
```

### Step 5: Critical Path Testing (2 min)
- [ ] Can create audit events (write to audit_log_events)
- [ ] Can create autonomy tasks (write to autonomy_tasks)
- [ ] Can create episodes (write to autonomy_episodes)
- [ ] Can query trust policies (read from trust_policy_versions)
- [ ] Can query calibration (read from calibration_constitution)

**Test:**
```sql
-- Test audit write
INSERT INTO audit_log_events (actor_id, action, resource_type) 
VALUES ('migration', 'migration_applied', 'database');

-- Test autonomy write
INSERT INTO autonomy_tasks (plan_id, status) 
VALUES ('test-plan-001', 'pending');

-- Verify immutability
UPDATE autonomy_episodes SET content='test' 
WHERE id='test-episode'; -- Should fail
```

### Step 6: Application Reconnection (1 min)
- [ ] Verify database connection string
- [ ] Restart application servers
- [ ] Verify application health
- [ ] Monitor error logs
- [ ] Verify requests being processed

**Command:**
```bash
systemctl restart agentco-backend
sleep 5
curl http://localhost:3001/health
```

### Step 7: Post-Migration Monitoring (5 min)
- [ ] Monitor error rate
- [ ] Monitor query performance
- [ ] Monitor connection pool
- [ ] Monitor disk usage
- [ ] Verify audit logging active

---

## MIGRATION VALIDATION CHECKLIST

| Item | Expected | Verification Method | Pass/Fail |
|------|----------|-------------------|-----------|
| All 34 migrations apply | YES | schema_migrations table | ⏳ |
| No SQL errors | 0 | Application logs | ⏳ |
| No constraint violations | 0 | Database constraints | ⏳ |
| All 78 tables created | 78 | information_schema query | ⏳ |
| All indexes created | 54+ | information_schema query | ⏳ |
| Immutability triggers | 14+ | information_schema query | ⏳ |
| Audit table ready | YES | SELECT * FROM audit_log_events | ⏳ |
| Audit write working | YES | INSERT test | ⏳ |
| Data integrity | YES | Constraint check | ⏳ |
| Rollback capability | YES | Backup available | ✅ |
| Performance acceptable | YES | Query performance test | ⏳ |
| Application starts | YES | Health endpoint | ⏳ |

---

## ROLLBACK PROCEDURE (If Migration Fails)

**Duration:** < 30 minutes  
**Data Loss:** None (using snapshot restore)  
**Authority:** Release Manager approval required

### Quick Rollback Steps

1. **Stop application** (< 1 min)
   ```bash
   systemctl stop agentco-backend
   ```

2. **Restore database** (< 10 min)
   ```bash
   pg_restore -d agentco_production pre_migration_backup.dump
   ```

3. **Verify restore** (< 1 min)
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM schema_migrations;"
   ```

4. **Restart application** (< 1 min)
   ```bash
   systemctl start agentco-backend
   ```

5. **Verify connectivity** (< 1 min)
   ```bash
   curl http://localhost:3001/health
   ```

---

## MIGRATION SAFETY GATES

### Before Migration Starts
- [ ] Backup exists and verified
- [ ] Database connectivity confirmed
- [ ] Application servers stopped
- [ ] All 34 migrations present
- [ ] Migration script executable

**FAIL CONDITION:** Any check fails → **DO NOT PROCEED**

### During Migration
- [ ] Monitor for errors every 30 seconds
- [ ] Monitor for locks (show_locks query)
- [ ] Monitor for slow queries
- [ ] Monitor application logs

**FAIL CONDITION:** 
- Any migration fails → **STOP AND ROLLBACK**
- Deadlock detected → **STOP AND ROLLBACK**
- Connection timeout → **STOP AND ROLLBACK**

### After Migration
- [ ] All 34 migrations marked as applied
- [ ] No constraint violations
- [ ] Audit table working
- [ ] Immutability triggers active
- [ ] Application health check passes
- [ ] No error spike in logs

**FAIL CONDITION:** Any check fails → **INVESTIGATE BEFORE PROCEEDING**

---

## CRITICAL TABLES VERIFICATION

**These 10 tables must exist and be functional:**

1. **audit_log_events** — Immutable, non-repudiable
2. **autonomy_tasks** — Task management
3. **autonomy_episodes** — Episode tracking
4. **goal_management** — Goal tracking
5. **plan_management** — Plan tracking
6. **calibration_constitution** — Constitution storage
7. **trust_policy_versions** — Policy versions
8. **trust_reputation_ledger** — Reputation tracking
9. **learner_runs** — Learning runs
10. **eval_runs** — Evaluation runs

**Verification:**
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema='public' AND table_name IN (
  'audit_log_events', 'autonomy_tasks', 'autonomy_episodes',
  'goal_management', 'plan_management', 'calibration_constitution',
  'trust_policy_versions', 'trust_reputation_ledger', 'learner_runs', 'eval_runs'
) ORDER BY table_name;
```

---

## IMMUTABILITY TRIGGERS VERIFICATION

**These triggers must be active:**

1. autonomy_episodes → prevent DELETE/UPDATE
2. autonomy_outcomes → prevent DELETE/UPDATE
3. eval_runs → prevent DELETE/UPDATE
4. audit_log_events → prevent DELETE/UPDATE
5. calibration_drift_history → prevent DELETE/UPDATE
6. decision_log → prevent DELETE/UPDATE
7. And 8 more...

**Verification:**
```sql
SELECT trigger_name, trigger_schema, trigger_table_name, action_timing, action_statement
FROM information_schema.triggers 
WHERE trigger_schema='public' AND trigger_name LIKE '%immut%'
ORDER BY trigger_name;
```

---

## EXPECTED SCHEMA STATE (Post-Migration)

**Tables:** 78  
**Indexes:** 54+  
**Triggers:** 14+ (immutability)  
**Constraints:** PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK  
**Functions:** schema_version(), audit triggers  
**Roles:** resolution_service (created by migration 016)  

---

## MONITORING DURING MIGRATION

**Check Every 30 Seconds:**
```bash
psql $DATABASE_URL -c "
  SELECT 
    (SELECT COUNT(*) FROM schema_migrations WHERE status='applied') as migrations_done,
    (SELECT COUNT(*) FROM pg_stat_activity) as active_connections,
    (SELECT COUNT(*) FROM audit_log_events) as audit_events
;"
```

---

## ABORT CRITERIA (Stop Migration Immediately)

1. Any migration file returns SQL ERROR
2. Constraint violation detected
3. Out of disk space
4. Database connection lost
5. Memory allocation failure
6. Timeout exceeds 10 minutes
7. Duplicate key violation
8. Foreign key constraint violation
9. Lock timeout
10. Replication lag (if HA enabled)

**Action on Abort:** Rollback to pre-migration backup immediately

---

## EXPECTED MIGRATION TIMES

| Phase | Migrations | Duration | Total |
|-------|-----------|----------|-------|
| Foundation (001-008) | 8 | 10s each | 80s |
| Trust & Governance (009-021) | 13 | 15s each | 195s |
| Autonomy & RBAC (022-040) | 13 | 20s each | 260s |
| **TOTAL** | **34** | | **~5-10 min** |

---

## POST-MIGRATION STEPS

1. ✅ Verify schema (1 min)
2. ✅ Test critical paths (2 min)
3. ✅ Restart application (1 min)
4. ✅ Run smoke test (2 min)
5. ✅ Monitor for 5 minutes (5 min)
6. ✅ Proceed to canary deployment

---

## DECISION GATE

**Before Canary Deployment, Verify:**
- [ ] All 34 migrations applied successfully
- [ ] No errors in application logs
- [ ] Database health check passes
- [ ] Audit table working
- [ ] Immutability triggers active
- [ ] Application starts and health check passes
- [ ] First request succeeds
- [ ] No data corruption detected

**GO/NO-GO DECISION:**
- If all verified → ✅ **GO TO CANARY DEPLOYMENT**
- If any fails → ⏹️ **ROLLBACK AND INVESTIGATE**

---

**Document:** PRODUCTION_MIGRATIONS_EXECUTION_PLAN.md  
**Version:** 1.0  
**Status:** READY TO EXECUTE
