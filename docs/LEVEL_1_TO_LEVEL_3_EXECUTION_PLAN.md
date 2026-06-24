# LEVEL_1 TO LEVEL_3 EXECUTION PLAN

**Date:** 2026-06-22  
**Current Level:** ARCHITECTURE_LEVEL_1 (Isolated Components)  
**Target Level:** ARCHITECTURE_LEVEL_3 (Controlled Autonomy Loop in Sandbox)  
**Overall Current Score:** 25%  
**Target Score After Implementation:** 75%+ (LEVEL_3)

---

## EXECUTIVE SUMMARY

The True Autonomy architecture has well-designed database schemas and some backend services, but lacks critical business logic glue and frontend integration. This plan documents exactly what exists, what's missing, and the build order to achieve LEVEL_3: a real, tested, end-to-end controlled autonomy loop.

---

## PART 1: WHAT ALREADY EXISTS

### Database Schemas (Excellent Design)

**Migrations 021-035: ALL EXIST AND ARE WELL-FORMED**

| Migration | File | Tables | Status |
|-----------|------|--------|--------|
| 021 | observability_traces.sql | observability_traces, trace_spans, trace_metrics, trace_logs, audit_events, autonomous_metrics | ✅ EXISTS |
| 022 | autonomy_tasks.sql | autonomy_tasks, autonomy_leases, autonomy_checkpoints, autonomy_task_heartbeats, autonomy_task_dependencies | ✅ EXISTS |
| 023 | autonomy_episodes.sql | autonomy_episodes, autonomy_actions, autonomy_outcomes, autonomy_episode_rewards, autonomy_episode_metadata, autonomy_memory_refs, autonomy_perception_events | ✅ EXISTS |
| 024 | perception_infrastructure.sql | perception_sources, perception_events, perception_parsing, perception_cache | ✅ EXISTS |
| 025 | autonomy_goals.sql | autonomy_goals, autonomy_goal_constraints, autonomy_goal_risks, autonomy_goal_metrics, autonomy_goal_audit | ✅ EXISTS |
| 026 | autonomy_plans.sql | autonomy_plans, autonomy_plan_steps, autonomy_plan_dependencies, autonomy_plan_resources, autonomy_plan_history | ✅ EXISTS |
| 027 | reward_system.sql | reward_definitions, reward_calculations, reward_history, reward_audit | ✅ EXISTS |
| 028 | eval_harness.sql | eval_suites, eval_cases, eval_runs, eval_results, eval_failures, eval_scorecards | ✅ EXISTS |
| 029 | learner_infrastructure.sql | learner_runs, policy_versions, learner_candidates, replay_training_metrics | ✅ EXISTS |
| 030 | self_modification.sql | self_modification_requests, self_modification_candidates, self_modification_validations, protected_surfaces | ✅ EXISTS |
| 031 | artifact_registry.sql | artifacts, artifact_versions, artifact_signatures, artifact_lineage | ✅ EXISTS |
| 032 | canary_deployment.sql | canary_plans, canary_rollback_events, canary_audit | ✅ EXISTS |
| 033 | rbac.sql | roles, permissions, user_roles, audit_role_changes, rbac_audit, rbac_overrides, rbac_delegation | ✅ EXISTS |
| 034 | policy_control.sql | policy_rules, policy_conditions, policy_exemptions, policy_audit, policy_versions | ✅ EXISTS |
| 035 | simulator_infrastructure.sql | simulator_configs, simulator_runs, simulator_steps, simulator_outcomes, simulator_firewall_logs | ✅ EXISTS |

**Total:** 35+ tables across 15 migrations. All schemas exist and are well-designed.

### Backend Services (Exist But Orphaned)

**Service: task-engine.service.ts (357 lines)**
- Location: `backend/src/services/task-engine.service.ts`
- Class: `TaskEngineService`
- Methods: 15 real implementations
  - createTask, queueTask, leaseTask, startTask, waitForResource
  - resumeTask, completeTask, failTask, cancelTask, getTask
  - saveCheckpoint, loadCheckpoint, heartbeat, releaseLease
  - recoverExpiredLeases, recoverTimedOutTasks
- Status: ✅ Real implementation
- **Problem:** Not called by main application or decision loop

**Service: trajectory-store.service.ts (396 lines)**
- Location: `backend/src/services/trajectory-store.service.ts`
- Class: `TrajectoryStoreService`
- Methods: 10 real implementations
  - createEpisode, recordAction, recordOutcome, recordTrajectoryStep
  - createReplayBatch, getTrajectories, getEpisode
  - markRegret, recordIntervention, getHighRegretEpisodes
- Status: ✅ Real implementation
- **Problem:** Called by autonomy_smoke.py smoke test but not by learner or evaluation harness

**Service: observability.service.ts (216 lines)**
- Location: `backend/src/services/observability.service.ts`
- Class: `ObservabilityService`
- Methods: 8 real implementations
  - beginTrace, endTrace, recordSpan, recordMetric, log, auditEvent
  - getRunTraces, getTraceSpans, computeAutonomyMetrics
- Status: ✅ Real implementation
- **Problem:** Partially integrated; not called from learner/eval

### REST API Routes (Structured But Orphaned)

**Route File: autonomy-tasks.routes.ts (266 lines)**
- Location: `backend/src/routes/autonomy-tasks.routes.ts`
- Endpoints: 10 total
  - `POST /api/autonomy/tasks` - create task
  - `GET /api/autonomy/tasks/:id` - get task
  - `POST /api/autonomy/tasks/:id/queue` - queue task
  - `POST /api/autonomy/tasks/:id/lease` - lease task
  - `POST /api/autonomy/tasks/:id/start` - start task
  - `POST /api/autonomy/tasks/:id/complete` - complete task
  - `POST /api/autonomy/tasks/:id/fail` - fail task
  - `POST /api/autonomy/tasks/:id/cancel` - cancel task
  - `POST /api/autonomy/tasks/:id/checkpoint/save` - save checkpoint
  - `POST /api/autonomy/tasks/:id/checkpoint/load` - load checkpoint
- Imports: taskEngine, trajectoryStore, observability
- Registration: ✅ Registered in server.ts (line 60)
- Status: ✅ Routes exist and are registered
- **Problem:** Frontend does NOT call these routes (0 API calls found in frontend codebase)

### Python Modules (Partial Implementation)

**Module: goal_manager.py**
- Location: `autonomy/goal_manager.py`
- Class: `GoalManager`
- Methods: 10 implementations
  - propose_goal, assess_risk, check_conflicts, approve_goal
  - activate_goal, reject_goal, pause_goal, complete_goal
  - list_active_goals, list_goals_by_agent
- Status: ✅ Real implementation
- **Problem:** Not called by main autonomy loop

**Module: perception_adapter.py**
- Location: `autonomy/perception_adapter.py`
- Classes: PerceptionAdapter (base), LocalFileAdapter, PostgresAdapter, SimulatorAdapter
- Status: ✅ Base class with 3 concrete implementations
- **Problem:** Not integrated into autonomy loop

### Test Infrastructure

**Baseline Tests: 91 PASSING**
- Calibration: 36 tests ✅
- Learning: 14 tests ✅
- Runtime: 41 tests ✅
- **Status:** Original safety invariants appear intact

**Smoke Test: scripts/autonomy_smoke.py**
- Location: `scripts/autonomy_smoke.py` (466 lines)
- Status: ✅ EXISTS and demonstrates end-to-end loop
- **Note:** Uses direct database INSERTS for some steps; does NOT use learner/eval

---

## PART 2: WHAT IS MISSING

### Critical Gap 1: Learner Logic (ZERO IMPLEMENTATION)

**Current State:**
- Migration 029 creates learner tables: learner_runs, policy_versions, learner_candidates, replay_training_metrics
- **NO SERVICE IMPLEMENTS LEARNER LOGIC**
- **NO FILE** generates candidates from replay batches

**Missing Files:**
- `backend/src/services/learner.service.ts` (DOES NOT EXIST)
- `backend/src/services/replay-batch-reader.service.ts` (DOES NOT EXIST)
- `scripts/run_learner.py` (DOES NOT EXIST — referenced in Makefile)

**What Needs Implementation:**
1. Load replay batch from DB
2. Verify trajectory IDs exist
3. Compute baseline metrics from existing policy
4. Generate candidate artifact (heuristic update, prompt update, config update)
5. Hash and sign candidate
6. Store in artifact registry
7. Write learner_run record
8. Write learner_candidate record
9. Prevent deployment (eval must gate promotion)

### Critical Gap 2: Evaluation Harness (ZERO IMPLEMENTATION)

**Current State:**
- Migration 028 creates eval tables: eval_suites, eval_cases, eval_runs, eval_results, eval_scorecards
- **NO SERVICE RUNS EVALUATIONS**
- **NO FILE** produces scorecards

**Missing Files:**
- `backend/src/services/eval-harness.service.ts` (DOES NOT EXIST)
- `scripts/run_autonomy_eval.py` (DOES NOT EXIST — referenced in Makefile)

**What Needs Implementation:**
1. SafetyEval: protected surface scan, goal validation, authorization checks
2. PlanningEval: step validity, dependency resolution, output schemas
3. MemoryReplayEval: trajectory validity, simulation labels, stale memory detection
4. LearnerCandidateEval: artifact hash, lineage, metric improvement, governance check
5. IntegrationEval: sandbox loop compatibility, calibration preservation
6. Produce eval_results rows
7. Produce eval_scorecard rows
8. **Block promotion if eval fails**
9. **Allow canary only if eval passes**

### Critical Gap 3: Self-Modification Enforcement (ZERO IMPLEMENTATION)

**Current State:**
- Migration 030 creates self-modification tables
- **NO SCANNER CODE**
- **NO VALIDATION LOGIC**

**Missing Files:**
- `backend/src/services/self-modification-validator.service.ts` (DOES NOT EXIST)
- `config/protected_surfaces.yaml` (DOES NOT EXIST)

**What Needs Implementation:**
1. Protected surface manifest (calibration, resolver, audit, RBAC, governance, ground-truth)
2. Scanner service that analyzes candidate diffs
3. Block candidates that touch protected surfaces
4. Write audit event for blocked candidates
5. Tests that prove malicious candidates are blocked

### Critical Gap 4: Frontend Integration (ZERO PAGES, ZERO API CALLS)

**Current State:**
- Backend API routes exist
- **Frontend DOES NOT call them**
- **0 dashboard pages exist**

**Missing:**
- `frontend/src/app/autonomy/` directory (DOES NOT EXIST)
- `frontend/src/lib/api/autonomy.ts` (DOES NOT EXIST)
- Pages:
  - `/autonomy` - overview
  - `/autonomy/tasks` - task management
  - `/autonomy/goals` - goal/plan management
  - `/autonomy/memory` - trajectories and replay
  - `/autonomy/evals` - evaluation results
  - `/autonomy/learner` - candidate history
  - `/autonomy/artifacts` - artifact registry
  - `/autonomy/canary` - deployment status
  - `/autonomy/governance` - policy and overrides
  - `/autonomy/observability` - traces and audit

**What Needs Implementation:**
1. Frontend pages that call backend APIs
2. Real data display (no static arrays)
3. Loading/error/empty states
4. Audit trail display with trace IDs
5. Simulation data labeling

### Critical Gap 5: Main Autonomy Orchestrator (INCOMPLETE)

**Current State:**
- `scripts/autonomy_smoke.py` demonstrates a loop but:
  - Uses direct database INSERTs for some steps
  - Calls task-engine but not learner/eval
  - Does not implement full promoted→canary→rollback flow

**Missing:**
- Production orchestrator service that:
  1. Orchestrates the full loop (perception → goal → task → plan → execute → memory → trajectory → outcome → reward → replay → learner → eval → promotion → canary/rollback)
  2. Uses real services, not INSERT statements
  3. Persists every step
  4. Handles failures gracefully
  5. Carries trace_id and audit context throughout

**Missing Makefile Command:**
- `make autonomy-level3-smoke` (DOES NOT EXIST)

### Critical Gap 6: CLI Scripts (MISSING)

**Current Scripts (Exist):**
- `scripts/autonomy_smoke.py` ✅

**Missing Scripts (Referenced in Makefile):**
- `scripts/run_autonomy_eval.py` ❌
- `scripts/run_simulator.py` ❌
- `scripts/run_learner.py` ❌

**New Scripts Needed:**
- `scripts/run_level3_autonomy_smoke.py` - full end-to-end smoke test
- `scripts/verify_level3_architecture.py` - verification of architecture completeness

---

## PART 3: BUILD ORDER

### Phase 1: Learner Implementation (Enables candidate generation)

1. Create `backend/src/services/learner.service.ts`
   - Load replay batch
   - Compute baseline metrics
   - Generate candidate artifact
   - Store candidate records
   
2. Create `scripts/run_learner.py`
   - Call learner service via API or direct service import
   - Output results to stdout and database

3. Add integration tests for learner

**Dependency:** Replay batch must exist (created by trajectories service)  
**Unblocks:** Evaluation harness

### Phase 2: Evaluation Harness (Enables promotion gating)

1. Create `backend/src/services/eval-harness.service.ts`
   - Implement 5 eval suite runners
   - Produce eval_results
   - Produce eval_scorecard
   - Enforce promotion blocks
   
2. Create `scripts/run_autonomy_eval.py`
   - Call eval harness
   - Output results
   
3. Add integration tests for eval

**Dependency:** Learner must exist and produce candidates  
**Unblocks:** Self-modification enforcement, main orchestrator

### Phase 3: Self-Modification Enforcement (Enables safety gating)

1. Create `config/protected_surfaces.yaml`
   - List protected files/symbols
   
2. Create `backend/src/services/self-modification-validator.service.ts`
   - Scan candidate artifacts
   - Block unsafe modifications
   - Write audit events
   
3. Integrate with eval harness
   - Protected surface check is part of SafetyEval
   
4. Add security tests
   - Prove malicious candidates are blocked

**Dependency:** Eval harness must be callable  
**Unblocks:** Main orchestrator

### Phase 4: Main Autonomy Orchestrator (Enables end-to-end loop)

1. Create `backend/src/services/autonomy-orchestrator.service.ts`
   - Orchestrate full loop (20 steps)
   - Use real services, not INSERT statements
   - Persist every step
   - Carry trace context
   
2. Create `/api/autonomy/run-level3-smoke` endpoint
   - Trigger orchestrator
   - Return run_id and status
   
3. Create `scripts/run_level3_autonomy_smoke.py`
   - Call orchestrator endpoint
   - Wait for completion
   - Verify persisted records
   
4. Add to Makefile:
   ```
   make autonomy-level3-smoke
   ```

**Dependency:** Learner, eval, self-mod must all be implemented  
**Unblocks:** Frontend integration, final smoke test

### Phase 5: Frontend Integration (Enables user interaction)

1. Create `frontend/src/lib/api/autonomy.ts`
   - API client for autonomy endpoints
   
2. Create `frontend/src/app/autonomy/` pages
   - Overview, tasks, goals, memory, evals, learner, artifacts, canary, governance, observability
   
3. Each page must:
   - Call real backend API
   - Display real data
   - Show loading/error/empty states
   - Show simulation labels where appropriate
   
4. Add frontend tests

**Dependency:** All backend services and APIs must exist  
**Unblocks:** User-facing autonomy system

### Phase 6: Final Smoke Test & Validation

1. Create `tests/integration/test_level3_autonomy_loop.py`
   - Full end-to-end test
   - Verify all persisted records
   - Verify learner output
   - Verify eval scorecard
   - Verify promotion blocking
   - Verify rollback
   
2. Create `scripts/verify_level3_architecture.py`
   - Check services exist
   - Check routes are wired
   - Check DB schema
   - Check CLI scripts
   - Check frontend pages
   
3. Add to Makefile:
   ```
   make autonomy-level3-test
   ```

**Dependency:** All previous phases complete

---

## PART 4: ACCEPTANCE CRITERIA

### Acceptance Test: make autonomy-level3-smoke

**MUST PRODUCE:**
- ✅ persisted autonomy_task
- ✅ persisted autonomy_plan with steps
- ✅ persisted autonomy_episodes
- ✅ persisted autonomy_actions
- ✅ persisted autonomy_outcomes
- ✅ persisted autonomy_episode_rewards
- ✅ persisted trajectory rows
- ✅ persisted reward_calculation rows
- ✅ persisted replay_batch
- ✅ persisted learner_run
- ✅ persisted learner_candidate
- ✅ persisted artifact row
- ✅ persisted eval_run
- ✅ persisted eval_results
- ✅ persisted eval_scorecard
- ✅ persisted audit_events
- ✅ persisted trace_ids in observability_traces
- ✅ promotion decision (blocked or canary-eligible)
- ✅ canary_plan (if allowed)
- ✅ canary_rollback_event (forced regression case)

**MUST NOT HAVE:**
- ❌ hardcoded pass/fail
- ❌ fake candidate
- ❌ fake eval scorecard
- ❌ simulation data promoted as real-world truth
- ❌ missing trace_id
- ❌ missing audit_event
- ❌ missing service call

### Acceptance Test: make autonomy-level3-test

**MUST PASS:**
- ✅ All 91 baseline tests still pass
- ✅ `test_level3_autonomy_loop.py` passes
- ✅ Learner tests pass
- ✅ Eval harness tests pass
- ✅ Self-modification blocking tests pass
- ✅ API route tests pass
- ✅ Frontend build passes

### Acceptance Test: Baseline Preservation

**MUST STILL PASS:**
- ✅ Calibration tests (36)
- ✅ Learning tests (14)
- ✅ Runtime tests (41)
- ✅ All 91 baseline tests

---

## PART 5: FILES TO CREATE/MODIFY

### New Files to Create

**Backend Services:**
- `backend/src/services/learner.service.ts` (200-300 lines)
- `backend/src/services/eval-harness.service.ts` (400-500 lines)
- `backend/src/services/self-modification-validator.service.ts` (300-400 lines)
- `backend/src/services/autonomy-orchestrator.service.ts` (500-700 lines)

**Backend Routes:**
- Add `/api/autonomy/learner/*` routes
- Add `/api/autonomy/evals/*` routes
- Add `/api/autonomy/candidates/*` routes
- Add `/api/autonomy/run-level3-smoke` endpoint

**CLI Scripts:**
- `scripts/run_learner.py` (100-150 lines)
- `scripts/run_autonomy_eval.py` (100-150 lines)
- `scripts/run_level3_autonomy_smoke.py` (100-150 lines)
- `scripts/verify_level3_architecture.py` (150-200 lines)

**Configuration:**
- `config/protected_surfaces.yaml` (50-100 lines)

**Tests:**
- `tests/integration/test_level3_autonomy_loop.py` (500-700 lines)
- Unit tests for learner, eval, self-mod services

**Frontend:**
- `frontend/src/lib/api/autonomy.ts` (200-300 lines)
- `frontend/src/app/autonomy/page.tsx` (Overview page)
- `frontend/src/app/autonomy/tasks/page.tsx`
- `frontend/src/app/autonomy/goals/page.tsx`
- `frontend/src/app/autonomy/memory/page.tsx`
- `frontend/src/app/autonomy/evals/page.tsx`
- `frontend/src/app/autonomy/learner/page.tsx`
- `frontend/src/app/autonomy/artifacts/page.tsx`
- `frontend/src/app/autonomy/canary/page.tsx`
- `frontend/src/app/autonomy/governance/page.tsx`
- `frontend/src/app/autonomy/observability/page.tsx`

**Documentation:**
- Update `docs/LEVEL_3_AUTONOMY_VALIDATION_REPORT.md`

### Files to Modify

**Backend:**
- `backend/src/server.ts` - register new routes
- `Makefile` - add autonomy-level3-smoke and autonomy-level3-test commands

**Scripts:**
- `scripts/autonomy_smoke.py` - may need updates to use services instead of INSERT

---

## PART 6: RISK ASSESSMENT

### Low Risk
- ✅ Adding new services (not touching existing ones)
- ✅ Adding new routes (registry is already extensible)
- ✅ Adding new frontend pages (isolated)
- ✅ Adding new CLI scripts (isolated)

### Medium Risk
- ⚠️ Integrating learner/eval into smoke test (must preserve test behavior)
- ⚠️ Modifying autonomy_smoke.py to use services instead of INSERT

### Mitigation
- Preserve all 91 baseline tests
- Add new tests incrementally
- Verify each phase before moving to next

---

## SUMMARY

| Phase | Component | Status | Effort | Risk |
|-------|-----------|--------|--------|------|
| 1 | Learner Service | ❌ TODO | 4-6h | LOW |
| 2 | Eval Harness | ❌ TODO | 4-6h | LOW |
| 3 | Self-Modification | ❌ TODO | 3-4h | MED |
| 4 | Main Orchestrator | ❌ TODO | 4-6h | MED |
| 5 | Frontend Pages | ❌ TODO | 6-8h | LOW |
| 6 | Final Tests | ❌ TODO | 3-4h | LOW |
| **TOTAL** | | | **25-35h** | **MED** |

**Expected Outcome After Completion:**
- Architecture Level 3: Controlled autonomy loop works in sandbox domains
- Overall Score: 75%+
- Command: `make autonomy-level3-smoke` produces real persisted evidence
- All 91 baseline tests still passing

