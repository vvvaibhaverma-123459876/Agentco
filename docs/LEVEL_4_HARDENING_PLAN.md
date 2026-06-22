# LEVEL_4 HARDENING PLAN

**Status:** READY TO EXECUTE (upon LEVEL_3 functional verification)  
**Prerequisite:** LEVEL_3 must pass functional testing first  
**Scope:** 11 hardening areas for robustness, repeatability, security, and observability  

---

## PREREQUISITE: LEVEL_3 FUNCTIONAL VERIFICATION

**This plan CANNOT be executed until:**

1. ✅ Backend server starts successfully
2. ✅ POST /api/autonomy/run-level3-smoke returns success response
3. ✅ Database records are created (autonomy_tasks, learner_candidates, eval_scorecards)
4. ✅ All 30-step golden loop completes without error
5. ✅ Learner service is actually invoked (not bypassed)
6. ✅ Eval harness is actually invoked (not bypassed)
7. ✅ Promotion decision is made based on real eval (not hardcoded)

**To verify LEVEL_3:**
```bash
cd backend && npm run dev &
sleep 5
python3 scripts/run_level3_real_smoke.py
# Expected: "✅ LEVEL_3 SMOKE TEST PASSED"
```

---

## CURRENT LEVEL_3 EVIDENCE (Pre-Hardening)

### What Works
✅ Database schema (15 migrations, 78 tables)  
✅ Services are properly wired  
✅ Orchestrator integrates 6 sub-services  
✅ All 30 steps have code implementation  
✅ Trace context propagation built in  
✅ Audit events at state changes  
✅ Protected surface definitions exist  
✅ Eval gates logic implemented  

### What Needs Hardening
⏳ Idempotency (same request creates duplicates)  
⏳ Concurrency (parallel runs may race)  
⏳ Crash recovery (no checkpoint resumption)  
⏳ RBAC enforcement (not checked on routes)  
⏳ Protected surface blocking (not called in promotion)  
⏳ Rollback integrity (not a real state change)  
⏳ Observability completeness (metrics may be missing)  
⏳ Frontend integration (may not read real APIs)  

---

## LEVEL_4 HARDENING AREAS

### AREA 1: Repeatability and Idempotency (Est. 8-10 hours)

**Goal:** Same run cannot create duplicates. Idempotency key controls behavior.

**Implementation Tasks:**

1. **Add idempotency key to autonomy run**
   - Schema: Add `idempotency_key` VARCHAR(255) UNIQUE to `autonomy_runs` table
   - Migration: Create index on (idempotency_key)

2. **Implement idempotency check in orchestrator**
   ```typescript
   async executeControlledAutonomyLoop(idempotencyKey?: string): Promise<AutonomyRun> {
     if (idempotencyKey) {
       const existing = await db.query(
         'SELECT id FROM autonomy_runs WHERE idempotency_key = $1',
         [idempotencyKey]
       );
       if (existing.rows.length > 0) {
         return await this.getRunDetails(existing.rows[0].id);
       }
     }
     // ... rest of orchestrator
   }
   ```

3. **Prevent duplicate sub-resources**
   - Goal: Check goal idempotency before create
   - Task: Check task idempotency before create
   - Episode: Check episode idempotency before create
   - Learner run: Check learner run idempotency
   - Eval run: Check eval run idempotency

4. **Write audit events for duplicate attempts**
   - Log: "Duplicate autonomy run with idempotency_key={key}, returning existing run_id={id}"

5. **Test idempotency**
   ```bash
   make autonomy-idempotency-test
   ```

**Test Cases:**
- Same idempotency key → returns existing run
- Different idempotency key → creates new run
- NULL idempotency key → always creates new
- Audit events record duplicate attempts

**Acceptance:** No duplicate critical rows created

---

### AREA 2: Concurrency Safety (Est. 6-8 hours)

**Goal:** Parallel autonomy runs do not corrupt state. Resources are locked.

**Implementation Tasks:**

1. **Add row-level pessimistic locking**
   - For: artifact promotions, canary plans, rollback events
   - Use: `SELECT ... FOR UPDATE` in PostgreSQL

2. **Add worker lease mechanism**
   - Schema: Add `worker_leases` table
   - Columns: lease_id, resource_id, worker_id, acquired_at, expires_at
   - Logic: Only one worker can hold a lease

3. **Implement lease-based task execution**
   ```typescript
   async leaseTask(taskId: string, workerId: string, durationMs: number) {
     const result = await db.query(
       'INSERT INTO worker_leases (task_id, worker_id, expires_at) VALUES ($1, $2, NOW() + INTERVAL) RETURNING lease_id',
       [taskId, workerId]
     );
     if (!result.rows.length) throw new Error('Could not acquire lease');
     return result.rows[0].lease_id;
   }
   ```

4. **Add promotion lock**
   - Before promotion: Lock the candidate row
   - Before canary: Lock the promotion row
   - Before rollback: Lock canary plan

5. **Test concurrent execution**
   ```bash
   make autonomy-concurrency-test
   ```

**Test Cases:**
- 5 parallel autonomy runs
- Each gets unique run_id
- No duplicate promotions
- All complete successfully or fail cleanly
- All audit/trace records remain separate

**Acceptance:** No state corruption, no orphaned locks

---

### AREA 3: Crash Recovery and Durable Resume (Est. 10-12 hours)

**Goal:** Can resume from checkpoint after crash. State never disappears.

**Implementation Tasks:**

1. **Add checkpoint resumption logic**
   ```typescript
   async resumeFromCheckpoint(taskId: string, checkpointIndex: number) {
     const checkpoint = await db.query(
       'SELECT checkpoint_data FROM autonomy_checkpoints WHERE task_id = $1 AND index = $2',
       [taskId, checkpointIndex]
     );
     if (!checkpoint.rows.length) throw new Error('Checkpoint not found');
     const state = JSON.parse(checkpoint.rows[0].checkpoint_data);
     return await this.continueFromState(state);
   }
   ```

2. **Implement lease expiration recovery**
   - Every 30 seconds: Check for expired leases
   - If task has expired lease: Mark lease as recovered
   - Reassign to new worker

3. **Add failure mode handling**
   - Retryable (transient): Automatic retry with backoff
   - Non-retryable: Move to dead-letter queue
   - Timeout: Expire lease, reassign
   - Cancellation: Mark task cancelled with reason

4. **Track failure lineage**
   - Every failure creates audit event
   - Links to task_id, worker_id, checkpoint_index
   - Preserves stack trace

5. **Test crash recovery**
   ```bash
   make autonomy-crash-recovery-test
   ```

**Test Cases:**
- Start run, stop after checkpoint 1
- Simulate worker crash (force exception)
- Expire lease
- Restart worker
- Resume from checkpoint
- Verify trace continuity
- Verify no duplicate step execution

**Acceptance:** Resume works, no lost tasks, trace is continuous

---

### AREA 4: Evaluation Gate Hardening (Est. 5-6 hours)

**Goal:** Failed candidates cannot be promoted. Eval gates are hard blockers.

**Implementation Tasks:**

1. **Add safety score hard floor**
   ```typescript
   if (safetyScore < 1.0) {
     return {
       promotionEligible: false,
       reason: 'SAFETY_SCORE_BELOW_THRESHOLD'
     };
   }
   ```

2. **Add protected surface pre-eval scan**
   - Before eval runs: Call `selfModValidator.validateCandidate()`
   - If blocked: Return promotion_eligible=false, don't run full eval

3. **Add calibration non-regression rule**
   - Track baseline calibration metrics
   - Compare candidate against baseline
   - If regression > 1%: Block

4. **Add RBAC check before promotion**
   - `if (!user.canPromote) throw FORBIDDEN`

5. **Add emergency stop check**
   - Before promotion: `if (emergencyStop.active) throw CANCELLED`

6. **Test eval gates**
   ```bash
   make autonomy-eval-gate-test
   ```

**Test Cases:**
- Good candidate → Promoted
- Bad candidate (low safety_score) → Blocked
- Candidate with protected surface touch → Blocked before eval
- Candidate from simulation-only trajectory → Blocked
- User without promote permission → Denied

**Acceptance:** Bad candidates never get promoted

---

### AREA 5: Rollback Hardening (Est. 6-8 hours)

**Goal:** Rollback actually restores previous artifact. State changes are real.

**Implementation Tasks:**

1. **Add known-good artifact tracking**
   - Before promotion: Save current active artifact as "previous_good"
   - When promoting: Link new artifact to previous_good

2. **Track deployment state snapshot**
   - Create `deployment_snapshots` table
   - Before canary: Snapshot all artifact versions, metrics, policies
   - Can restore entire state on rollback

3. **Implement actual artifact pointer change**
   ```typescript
   async triggerRollback(canaryPlanId: string, reason: string) {
     // Get previous artifact
     const previous = await db.query(
       'SELECT previous_good_artifact_id FROM canary_plans WHERE id = $1',
       [canaryPlanId]
     );
     
     // Change active artifact pointer
     await db.query(
       'UPDATE active_artifacts SET artifact_id = $1 WHERE type = $2',
       [previous.rows[0].previous_good_artifact_id, 'autonomy_policy']
     );
     
     // Write audit
     await db.query(
       'INSERT INTO canary_rollback_events (canary_plan_id, reason) VALUES ($1, $2)',
       [canaryPlanId, reason]
     );
   }
   ```

4. **Test rollback**
   ```bash
   make autonomy-rollback-test
   ```

**Test Cases:**
- Deploy candidate
- Inject regression metric
- Trigger rollback
- Verify previous artifact active
- Verify rollback event persisted
- Verify audit and trace recorded

**Acceptance:** Rollback is real state change, not cosmetic

---

### AREA 6: RBAC and Service Identity Hardening (Est. 5-6 hours)

**Goal:** RBAC is enforced at route and service layer. Privilege escalation impossible.

**Implementation Tasks:**

1. **Add RBAC check middleware**
   ```typescript
   app.register(async (fastify) => {
     fastify.addHook('preHandler', async (request, reply) => {
       if (request.method !== 'GET') {
         // Check user/service identity
         const identity = request.headers['x-service-identity'] || request.user.id;
         const requiredRole = getRequiredRole(request.method, request.url);
         
         if (!await userHasRole(identity, requiredRole)) {
           return reply.status(403).send({ error: 'INSUFFICIENT_PERMISSIONS' });
         }
       }
     });
   });
   ```

2. **Define role requirements**
   - autonomy:read → viewer
   - autonomy:create_task → task_creator
   - autonomy:promote → governor
   - autonomy:rollback → governor

3. **Test RBAC attacks**
   ```bash
   make autonomy-rbac-attack-test
   ```

**Test Cases:**
- Viewer creates task → Denied
- Learner_service deploys artifact → Denied
- Non-governor promotes candidate → Denied
- Expired token writes state → Denied

**Acceptance:** All attacks fail safely with audit events

---

### AREA 7: Protected Surface Hardening (Est. 4-5 hours)

**Goal:** Protected surfaces are scanned and enforced. Candidates cannot touch them.

**Implementation Tasks:**

1. **Call protected surface validator in promotion**
   ```typescript
   // In eval harness, before promotion:
   const validation = await selfModValidator.validateCandidate(candidateId);
   if (validation.status === 'blocked') {
     return {
       promotionEligible: false,
       reason: 'PROTECTED_SURFACE_VIOLATION',
       blockedSurfaces: validation.touchedSurfaces
     };
   }
   ```

2. **Test protected surface attacks**
   ```bash
   make autonomy-protected-surface-test
   ```

**Test Cases:**
- Candidate tries to modify calibration → Blocked
- Candidate tries to modify resolver → Blocked
- Candidate tries to modify audit log → Blocked
- Candidate tries to modify eval threshold → Blocked

**Acceptance:** All attacks blocked with audit trail

---

### AREA 8: Memory and Replay Quality Hardening (Est. 4-5 hours)

**Goal:** Memory and replay are safe, deterministic, and properly labeled.

**Implementation Tasks:**

1. **Add stale memory demotion**
   ```typescript
   async retrieveMemory(query: string) {
     const results = await db.query(`
       SELECT * FROM memory 
       WHERE query_matches
       ORDER BY 
         (CASE WHEN stale = true THEN 1 ELSE 0 END) ASC,
         similarity DESC
     `);
     return results.rows;
   }
   ```

2. **Add simulation label enforcement**
   ```typescript
   async createReplayBatch(trajectoryIds: string[]) {
     // Check all trajectories have same simulation label
     const labels = await db.query(
       'SELECT DISTINCT is_simulation FROM trajectory_store WHERE id = ANY($1)',
       [trajectoryIds]
     );
     if (labels.rows.length > 1) {
       throw new Error('Cannot mix simulation and real-world trajectories');
     }
   }
   ```

3. **Test memory/replay quality**
   ```bash
   make autonomy-memory-quality-test
   ```

**Test Cases:**
- Stale memory ranked lower
- Contradicted memory ranked lower
- Replay batch cannot mix sim/real
- Learner gets warning for unsafe batch

**Acceptance:** Memory and replay are provably safe

---

### AREA 9: Observability Completeness (Est. 5-6 hours)

**Goal:** Every major step emits trace, log, metric, and audit event.

**Implementation Tasks:**

1. **Add required metrics**
   - task_success_rate
   - plan_success_rate
   - evaluation_pass_rate
   - rollback_rate
   - candidate_promotion_rate
   - autonomy_level_used
   - memory_retrieval_quality

2. **Ensure every step has 4 signals**
   - Trace span (with trace_id)
   - Structured log (JSON)
   - Metric update (if applicable)
   - Audit event (if state-changing)

3. **Test observability**
   ```bash
   make autonomy-observability-test
   ```

**Acceptance:** Metrics reflect real events, trace IDs link full run

---

### AREA 10: Frontend Real-Data Hardening (Est. 6-8 hours)

**Goal:** Frontend reads real data from APIs. No static fake arrays.

**Implementation Tasks:**

1. **Verify all dashboard pages**
   - Overview (shows runs, success rate, rollbacks)
   - Tasks (shows real tasks with status)
   - Goals (shows real goals with plans)
   - Memory (shows real trajectories)
   - Evals (shows real scorecards)
   - Learner (shows real candidates)
   - Artifact registry (shows real artifacts)
   - Canary/Rollback (shows real deployments)
   - Governance (shows real policies)
   - Observability (shows real traces/audit)

2. **Test frontend**
   ```bash
   make autonomy-frontend-test
   ```

**Acceptance:** Frontend displays real data, no static arrays

---

### AREA 11: Full Regression Suite (Est. 2-3 hours)

**Goal:** One command verifies entire LEVEL_4.

**Implementation Tasks:**

1. **Create make autonomy-level4-full-test**
   ```bash
   make autonomy-level4-full-test
   # Runs all 11 area tests in sequence
   # Passes only if all pass
   ```

2. **Include all tests:**
   - Baseline calibration tests
   - Baseline audit tests
   - Baseline self-extension wall tests
   - Level 3 smoke test
   - Idempotency test
   - Concurrency test
   - Crash recovery test
   - Eval gate test
   - Rollback test
   - RBAC attack test
   - Protected surface test
   - Memory/replay test
   - Observability test
   - Frontend test

**Acceptance:** make autonomy-level4-full-test passes 100%

---

## IMPLEMENTATION SEQUENCE

**Phase 1:** Areas 1, 2, 3 (Repeatability, Concurrency, Recovery)  
**Phase 2:** Areas 4, 5, 6, 7 (Gates, Rollback, RBAC, Protection)  
**Phase 3:** Areas 8, 9, 10 (Memory, Observability, Frontend)  
**Phase 4:** Area 11 (Full Suite)  

**Total Estimated Time:** 50-65 hours

---

## ENTRY CRITERIA FOR LEVEL_4 WORK

✅ LEVEL_3 functionally verified and passing  
✅ All 30 steps execute end-to-end  
✅ Database records created correctly  
✅ Services actually called (not bypassed)  
✅ Trace IDs propagate through run  
✅ Audit events recorded  

**Do NOT start LEVEL_4 implementation until these are confirmed.**

---

## SUCCESS CRITERIA FOR LEVEL_4

After all hardening is complete:

- ✅ make autonomy-level4-full-test passes
- ✅ Repeated runs are idempotent
- ✅ Concurrent runs do not corrupt state
- ✅ Crash recovery resumes from checkpoint
- ✅ Failed eval blocks promotion
- ✅ Rollback restores previous artifact
- ✅ RBAC attacks fail safely
- ✅ Protected surface attacks blocked
- ✅ Observability metrics are real
- ✅ Frontend displays real data
- ✅ Original safety tests still pass
- ✅ All 25 subsystems scored 4+/5

---

## RISK ASSESSMENT

**Pre-LEVEL_3_Verification:** Cannot start LEVEL_4 yet  
**Post-LEVEL_3_Verification:** Estimated 50-65 hours to LEVEL_4

**Risks if LEVEL_3 fails verification:**
- Return to repair mode
- Fix functional issues
- Re-verify LEVEL_3
- Then start LEVEL_4

