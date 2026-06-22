# True Autonomy Readiness Implementation Plan

**Date:** 2026-06-22  
**Status:** PLAN (ready for implementation)  
**Scope:** Convert Agentco from calibration-gated agent platform into real, durable autonomy substrate

---

## 1. CURRENT STATE ASSESSMENT

### Already Implemented (Reusable)

**Database & Migrations**
- ✅ Postgres with 20 migrations (migrations 001-020)
- ✅ Audit logging infrastructure (decision_log, event_history, audit_log_id)
- ✅ Basic workflow_tasks table (migration 019) - needs hardening
- ✅ Evaluation framework (migration 020) - benchmark_manifests, eval_runs, trial_records
- ✅ Immutability triggers and audit trail enforcement
- ✅ Belief/prediction ledger (migration 011)
- ✅ Trust scoring (migration 009)

**Python/Autonomy Layer**
- ✅ autonomy/ module with 11 files (objective, decision_engine, execution, feedback_loop, institutional_contracts, integration, measurement, realtime_integration, self_correction, llm_service)
- ✅ Learning loop infrastructure (learning/cycle.py)
- ✅ Memory kernel (memory_kernel/)
- ✅ Calibration/evidence (calibration/evidence/)
- ✅ LLM service abstraction (autonomy/llm_service.py) - multi-provider support

**Backend/API**
- ✅ Fastify server with Postgres/Kafka
- ✅ Route groups: agents, override, audit, credential, learning, governance, evals
- ✅ Security layer with API key validation and production secret checks
- ✅ Health checks and metrics endpoints
- ✅ Error handling

**Frontend**
- ✅ Next.js dashboard structure (dashboard, audit, layout pages)
- ✅ Sidebar navigation

**Tests**
- ✅ Integration tests for audit-log, memory-store, event-bus, override-queue
- ✅ Evaluation harness (evals/core/ with graders, runner, schema)
- ✅ Enterprise vendor risk benchmark (15 scenarios, fake deterministic model)
- ✅ Regression test suite

**Safety Invariants (Protected)**
- ✅ Sealed resolver boundaries
- ✅ Calibration-first trust scoring
- ✅ Pre-registered claims
- ✅ Independent resolution
- ✅ Immutable audit logs
- ✅ Signed event envelopes

### Missing or Incomplete (Must Implement)

**Observability & Tracing**
- ❌ OpenTelemetry integration (no trace_id propagation)
- ❌ Structured logging with trace context
- ❌ Prometheus metrics for autonomy actions
- ❌ Grafana dashboards
- ❌ Trace context model (trace_id, run_id, task_id, policy_version, etc.)

**Durable Task/Workflow Engine**
- ⚠️ PARTIAL: workflow_tasks table exists but minimal
- ❌ Missing: autonomy_tasks table (full schema)
- ❌ Missing: autonomy_task_events (state transition tracking)
- ❌ Missing: autonomy_workflow_checkpoints (resume capability)
- ❌ Missing: worker_leases (distributed execution)
- ❌ Missing: autonomy_dead_letters (failure recovery)
- ❌ Missing: Task state machine validation (created→queued→leased→running→...)
- ❌ Missing: Idempotency key enforcement
- ❌ Missing: Checkpoint-based recovery
- ❌ Missing: Heartbeat mechanism
- ❌ Missing: Timeout enforcement

**Memory & Trajectories**
- ❌ autonomy_episodes table
- ❌ autonomy_actions table (step-level detail)
- ❌ autonomy_outcomes table
- ❌ autonomy_interventions table (human/system)
- ❌ memory_retrieval_events table (logging)
- ❌ trajectory_store (linked to episodes)
- ❌ replay_batches (grouped trajectories)
- ❌ Memory ageing (stale memory demotion)
- ❌ Regret scoring
- ❌ Contradiction marking

**Perception Adapters**
- ❌ PerceptionAdapter interface
- ❌ Normalized event schema
- ❌ Adapter registry
- ❌ Concrete adapters: local_file, http_readonly, postgres, simulator
- ❌ Perception safety controls (allowlist, rate limit, hash)
- ❌ perception_sources, perception_events, perception_artifacts tables

**Goal Management**
- ❌ autonomy_goals table
- ❌ goal_evidence table
- ❌ goal_conflicts table
- ❌ goal_budgets table
- ❌ goal_reviews table
- ❌ Autonomy level classification (L0-L6)
- ❌ Risk assessment
- ❌ Goal conflict detection

**Planning & Decomposition**
- ❌ autonomy_plans table
- ❌ autonomy_plan_steps table
- ❌ plan_reviews table
- ❌ Step DAG validation
- ❌ Long-horizon checkpoint requirement
- ❌ Plan versioning

**Outcome & Reward**
- ❌ autonomy_outcomes table
- ❌ reward_functions table (versioned)
- ❌ reward_calculations table
- ❌ reward_audit table
- ❌ Reproducible reward computation
- ❌ Multi-dimensional reward (completion, correctness, calibration, safety, cost, time)

**Evaluation Harness**
- ⚠️ PARTIAL: evals/core exists with graders
- ❌ Missing: Full eval suites for planning, tool use, memory, safety, autonomy, self-modification
- ❌ Missing: eval_suites, eval_cases, eval_runs, eval_results, eval_failures, eval_scorecards tables
- ❌ Missing: Autonomy scorecard (autonomy_score, safety_score, calibration_score, planning_score, etc.)
- ❌ Missing: Regression blocking in CI

**Learner & Replay**
- ❌ learner_runs table
- ❌ policy_versions table (artifact history)
- ❌ learner_candidates table
- ❌ replay_training_metrics table
- ❌ Actual learner implementation (not stub)
- ❌ Replay batch creation from trajectory_store
- ❌ Offline evaluation
- ❌ Candidate generation (prompt updates, tool policy, etc.)
- ❌ Protected surface verification (cannot modify calibration/resolution)

**Self-Modification Pipeline**
- ❌ self_modification_requests table
- ❌ self_modification_candidates table
- ❌ self_modification_validations table
- ❌ promotion_decisions table
- ❌ Protected surface scanner
- ❌ Artifact signing
- ❌ Sandbox execution
- ❌ Governance approval gate

**Artifact Registry & Deployment**
- ❌ artifact_registry table
- ❌ artifact_lineage table
- ❌ artifact_deployments table
- ❌ artifact_signatures table
- ❌ Canary plans and observations
- ❌ Rollback mechanism
- ❌ Version promotion workflow

**RBAC & Service Identities**
- ⚠️ API key auth exists, but no fine-grained RBAC
- ❌ Missing: principals, roles, permissions tables
- ❌ Missing: principal_roles, role_permissions tables
- ❌ Missing: service_identities table
- ❌ Missing: auth_audit_events table
- ❌ Missing: Permission checks on write-sensitive routes
- ❌ Missing: Service identity scoping (learner cannot deploy, resolver-only writes, etc.)

**Policy Control Plane**
- ❌ policy_rules table
- ❌ policy_evaluations table
- ❌ governance_decisions table
- ❌ risk_assessments table
- ❌ emergency_controls table
- ❌ High-risk action approval workflow
- ❌ Emergency shutdown mechanism
- ❌ Kill switch

**Simulation Environments**
- ❌ Simulator interface (gymnasium-style)
- ❌ BusinessDecisionSim
- ❌ ResearchClaimSim
- ❌ simulator_runs, simulator_steps, simulator_outcomes tables
- ❌ Reality/Simulation firewall

**APIs**
- ⚠️ PARTIAL: Some routes exist (agents, evals, governance)
- ❌ Missing: /api/autonomy/tasks, /api/autonomy/workflows, /api/autonomy/goals, /api/autonomy/plans
- ❌ Missing: /api/autonomy/memory, /api/autonomy/trajectories, /api/autonomy/perception
- ❌ Missing: /api/autonomy/outcomes, /api/autonomy/rewards, /api/autonomy/learners
- ❌ Missing: /api/autonomy/candidates, /api/autonomy/artifacts, /api/autonomy/canary
- ❌ Missing: /api/autonomy/policies, /api/autonomy/governance, /api/autonomy/observability
- ❌ Missing: OpenAPI documentation

**Frontend Dashboards**
- ❌ Autonomy overview dashboard
- ❌ Task/workflow dashboard
- ❌ Goal dashboard
- ❌ Memory/trajectory dashboard
- ❌ Evaluation dashboard
- ❌ Learner dashboard
- ❌ Artifact registry dashboard
- ❌ Canary/rollback dashboard
- ❌ Governance dashboard
- ❌ Observability dashboard

---

## 2. BUILD ORDER & PHASING

### Phase 1: Observability Foundation (Days 1-3)
**Why First:** Essential for debugging all subsequent phases. All code must emit traces.

1.1 Trace context model + OpenTelemetry setup
1.2 Structured logging with trace context
1.3 Prometheus metrics + Grafana dashboard JSON
1.4 Tests: trace propagation across API, worker, memory flows

**Deliverable:** trace_id on every autonomy action, audit logs link to traces, metrics exposed

### Phase 2: Durable Task Engine (Days 4-7)
**Why Second:** Foundation for all other phases. Must persist state durably.

2.1 autonomy_tasks table + full schema
2.2 autonomy_task_events (status transitions)
2.3 autonomy_workflow_checkpoints
2.4 worker_leases + heartbeat
2.5 autonomy_dead_letters
2.6 Task state machine (created→queued→leased→running→waiting_for_*→completed/failed/cancelled)
2.7 Idempotency enforcement
2.8 Checkpoint recovery mechanism
2.9 Tests: legal/illegal transitions, resume from checkpoint, duplicate idempotency handling

**Deliverable:** Long-running task can be interrupted and resumed from checkpoint

### Phase 3: Memory & Trajectories (Days 8-10)
**Why Third:** Needed for learner to work. Must store trajectories for replay.

3.1 autonomy_episodes table
3.2 autonomy_actions table (step-level detail)
3.3 autonomy_outcomes table
3.4 autonomy_interventions table
3.5 memory_retrieval_events table
3.6 trajectory_store (linked to episodes)
3.7 replay_batches (hash-deterministic grouping)
3.8 Memory ageing logic
3.9 Regret scoring
3.10 Contradiction marking
3.11 Tests: episode creation, trajectory storage, replay batch determinism, memory ageing

**Deliverable:** Full episodes/actions/outcomes persisted, replay batches created, memory aged

### Phase 4: Perception Adapters (Days 11-12)
**Why Fourth:** Needed for environment interaction. Real perception, not hardcoded data.

4.1 PerceptionAdapter interface
4.2 Normalized event schema
4.3 Adapter registry
4.4 Concrete adapters: local_file, http_readonly, postgres, simulator
4.5 perception_sources, perception_events, perception_artifacts tables
4.6 Perception safety (allowlist, rate limit, artifact hash)
4.7 Tests: local files work, HTTP allowlist enforced, duplicate fingerprints detected

**Deliverable:** Real perception events persisted, read-only HTTP allowlisted, artifacts hashed

### Phase 5: Goal Management (Days 13-14)
**Why Fifth:** Prevents unconstrained self-generated goals. Controls autonomy scope.

5.1 autonomy_goals table
5.2 goal_evidence, goal_conflicts, goal_budgets, goal_reviews tables
5.3 Autonomy levels (L0-L6)
5.4 Risk assessment per goal
5.5 Conflict detection
5.6 Budget enforcement
5.7 Tests: unsafe goals blocked, conflicts detected, budgets enforced

**Deliverable:** Agents can propose goals, unsafe goals rejected, conflicts detected

### Phase 6: Planning & Decomposition (Days 15-16)
**Why Sixth:** Multi-step autonomy requires durable plans.

6.1 autonomy_plans table
6.2 autonomy_plan_steps table
6.3 plan_reviews table
6.4 Step DAG validation
6.5 Long-horizon checkpoint requirement
6.6 Plan versioning
6.7 Tests: DAG validation, long-horizon plans require review, lineage preserved

**Deliverable:** Multi-step plans execute with checkpointing

### Phase 7: Outcome & Reward (Days 17-18)
**Why Seventh:** Integrates with existing resolution + adds autonomy-specific reward.

7.1 autonomy_outcomes table (link to resolution)
7.2 reward_functions table (versioned)
7.3 reward_calculations table
7.4 reward_audit table
7.5 Multi-dimensional reward (completion, correctness, calibration, safety, cost, time, intervention)
7.6 Reward versioning enforcement
7.7 Tests: reproducible reward, changing function creates new version, audit trail

**Deliverable:** Tasks resolved into outcome + reward, reproducible calculation

### Phase 8: Evaluation Harness (Days 19-21)
**Why Eighth:** Blocks promotion without passing evals. Safety gate.

8.1 eval_suites, eval_cases, eval_runs, eval_results, eval_failures, eval_scorecards tables
8.2 Eval suites for planning, tool use, memory, safety, autonomy, self-modification
8.3 Autonomy scorecard (autonomy_score, safety_score, calibration_score, planning_score, memory_score, tool_score, regression_score, promotion_eligible)
8.4 Regression detection (CI fails on regression)
8.5 Tests: eval blocking promotion, regression detected, scorecard computation

**Deliverable:** Eval suites runnable, promotion blocked without passing evals

### Phase 9: Learner & Replay (Days 22-24)
**Why Ninth:** Enables autonomous improvement. Must use real trajectories.

9.1 learner_runs table
9.2 policy_versions table
9.3 learner_candidates table
9.4 replay_training_metrics table
9.5 Replay batch creation from trajectory_store
9.6 Baseline policy evaluation
9.7 Candidate policy generation
9.8 Offline evaluation
9.9 Regression comparison
9.10 Candidate types (prompt update, tool policy, planner heuristic, memory policy, escalation threshold, model routing)
9.11 Tests: learner uses real trajectories, produces candidate, cannot deploy, protects calibration/resolution

**Deliverable:** Learner creates real candidates from real trajectories, deployment blocked

### Phase 10: Controlled Simulation (Days 25-26)
**Why Tenth:** Safe learning environment. Clearly labeled as simulation.

10.1 Simulator interface (reset, step, observation/action space)
10.2 BusinessDecisionSim
10.3 ResearchClaimSim
10.4 simulator_runs, simulator_steps, simulator_outcomes tables
10.5 Reality/Simulation firewall (simulation outputs cannot become ground truth)
10.6 Tests: simulators deterministic with seed, firewall enforced

**Deliverable:** Deterministic simulators, outputs marked as simulation

### Phase 11: Self-Modification Pipeline (Days 27-28)
**Why Eleventh:** Critical safety control. Candidate must pass protection checks.

11.1 self_modification_requests table
11.2 self_modification_candidates table
11.3 self_modification_validations table
11.4 promotion_decisions table
11.5 Protected surface scanner (calibration, resolution, ground-truth, sealed resolver, audit immutability, secret checks, RBAC, governance checks)
11.6 Artifact signing
11.7 Sandbox execution
11.8 Governance approval gate
11.9 Pipeline: request → candidate → protected-surface scan → static checks → unit tests → integration tests → security tests → sandbox → eval → regression comparison → sign → promotion decision → canary → rollback
11.10 Tests: protected surface modification blocked, generated code cannot deploy itself, adversarial attempts fail

**Deliverable:** Candidate touching protected surface blocked, promotion requires eval gate

### Phase 12: Artifact Registry (Days 29-30)
**Why Twelfth:** Enables version control, traceability, rollback.

12.1 artifact_registry table
12.2 artifact_lineage table
12.3 artifact_deployments table
12.4 artifact_signatures table
12.5 Artifact types (prompt, policy, model_config, planner_config, memory_policy, tool_policy, code_patch, eval_suite, reward_function)
12.6 Version enforcement
12.7 Tests: artifacts hashed and signed, lineage queryable, rollback works

**Deliverable:** Artifacts versioned, signed, lineage tracked

### Phase 13: Safe Deployment & Canary (Days 31-32)
**Why Thirteenth:** No high-risk auto-promotion. Gradual rollout.

13.1 canary_plans table
13.2 canary_observations table
13.3 rollback_events table
13.4 Canary metrics (success_metrics_json, failure_metrics_json)
13.5 Auto-halt on safety regression
13.6 Rollback mechanism
13.7 Tests: canary halts on failure, rollback restores, no auto-promotion of high-risk

**Deliverable:** Passing candidate enters canary, failing canary triggers rollback

### Phase 14: RBAC & Service Identities (Days 33-35)
**Why Fourteenth:** Fine-grained access control. Prevents privilege escalation.

14.1 principals table (human_user, service, agent, institution, system)
14.2 roles, permissions, principal_roles, role_permissions tables
14.3 service_identities table with scoped permissions
14.4 auth_audit_events table
14.5 Roles: viewer, operator, evaluator, governor, admin, service_worker, resolver_service, learner_service, deployment_service
14.6 Permissions enforcement on write-sensitive routes
14.7 Tests: unauthorized writes blocked, learner cannot deploy, resolver role protected

**Deliverable:** RBAC enforced, permission tests pass

### Phase 15: Policy Control Plane (Days 36-37)
**Why Fifteenth:** Governance gates. Safety rules.

15.1 policy_rules table
15.2 policy_evaluations table
15.3 governance_decisions table
15.4 risk_assessments table
15.5 emergency_controls table
15.6 Policy evaluation before: goal approval, plan execution, external tool use, candidate promotion, deployment
15.7 Emergency shutdown and kill switch
15.8 Tests: policy violations block action, emergency shutdown works

**Deliverable:** Policy violations block action, emergency controls functional

### Phase 16: API Productization (Days 38-40)
**Why Sixteenth:** Production surfaces. Real endpoints.

16.1 Route groups: /api/autonomy/{tasks, workflows, goals, plans, memory, trajectories, perception, outcomes, rewards, evals, learners, candidates, artifacts, canary, rollback, policies, governance, observability}
16.2 Request/response validation
16.3 Response schemas
16.4 Auth/RBAC checks
16.5 Idempotency keys
16.6 Audit logging for writes
16.7 Trace context propagation
16.8 Error handling
16.9 OpenAPI spec
16.10 Tests: all write routes enforce RBAC, create audit entries, carry trace IDs

**Deliverable:** OpenAPI spec complete, all routes protected, tests pass

### Phase 17: Frontend Dashboards (Days 41-42)
**Why Seventeenth:** Visibility + control. No static fake data.

17.1 Autonomy overview dashboard
17.2 Task/workflow dashboard
17.3 Goal dashboard
17.4 Memory/trajectory dashboard
17.5 Evaluation dashboard
17.6 Learner dashboard
17.7 Artifact registry dashboard
17.8 Canary/rollback dashboard
17.9 Governance dashboard
17.10 Observability dashboard
17.11 Real API backends, no static data

**Deliverable:** Dashboards fetch real data, empty states allowed when API returns empty

### Phase 18: Documentation Alignment (Days 43-44)
**Why Eighteenth:** Truth alignment. No overclaims.

18.1 docs/CURRENT_CAPABILITIES.md (exact implemented capabilities + limitations)
18.2 docs/TRUE_AUTONOMY_ARCHITECTURE.md (diagram, subsystems, safety boundaries)
18.3 docs/AUTONOMY_SAFETY_MODEL.md (protected surfaces, risk matrix, gates)
18.4 docs/AUTONOMY_EVALS.md (eval suites, metrics, promotion thresholds)
18.5 docs/SELF_MODIFICATION_PIPELINE.md (lifecycle, protected surfaces, sandbox rules)
18.6 docs/RBAC_AND_SERVICE_IDENTITIES.md (roles, permissions, route matrix)
18.7 docs/PRODUCTION_READINESS.md (what's ready, what's not, deployment cautions)
18.8 README.md update (remove overclaims, state truth, show test commands)
18.9 No simulation outputs labeled as real-world, autonomy clearly bounded

**Deliverable:** Docs match code, no overclaims

### Phase 19: Testing Requirements (Days 45-46)
**Why Nineteenth:** Comprehensive coverage. Safety invariants tested.

19.1 Unit tests for state transitions, policy decisions, reward calculations
19.2 Integration tests: task creation → workflow → memory → outcome → reward
19.3 Integration tests: trajectory → replay batch → learner candidate → eval → promotion blocked/allowed
19.4 Integration tests: self-modification candidate → protected surface scan → eval → canary → rollback
19.5 Security tests: unauthorized write blocked, service identity cannot exceed permissions
19.6 Security tests: learner cannot deploy, agent cannot approve own authority expansion
19.7 Regression tests: existing calibration, audit, memory, safety tests still pass
19.8 All new tests pass, all old tests pass, CI includes autonomy tests

**Deliverable:** All tests pass, no hidden fake success paths

### Phase 20: CLI Commands & Smoke Test (Days 47-48)
**Why Last:** Complete the loop. Prove end-to-end works.

20.1 make autonomy-migrate (apply all migrations)
20.2 make autonomy-smoke (minimal real loop)
20.3 make autonomy-eval (run eval suites)
20.4 make autonomy-sim (run simulators)
20.5 make autonomy-learner (run learner)
20.6 make autonomy-dashboard (start frontend)
20.7 make autonomy-security-test (run security tests)
20.8 make autonomy-full-test (all tests)
20.9 scripts/autonomy_smoke.py (real loop: goal → task → plan → execute → memory → eval → candidate → block/promote)
20.10 Smoke test must NOT use fake hardcoded success

**Deliverable:** Smoke test passes with real loop, no fake success

---

## 3. FILE & SCHEMA CHANGES SUMMARY

### Database Migrations to Add (21-39)
- 021_autonomy_tasks.sql
- 022_autonomy_task_events.sql
- 023_autonomy_workflow_checkpoints.sql
- 024_worker_leases.sql
- 025_autonomy_dead_letters.sql
- 026_autonomy_episodes.sql
- 027_autonomy_actions.sql
- 028_autonomy_outcomes.sql
- 029_autonomy_interventions.sql
- 030_memory_retrieval_events.sql
- 031_trajectory_store.sql
- 032_replay_batches.sql
- 033_perception_sources.sql
- 034_perception_events.sql
- 035_perception_artifacts.sql
- 036_autonomy_goals.sql
- 037_autonomy_plans.sql
- 038_reward_functions.sql
- 039_eval_suites.sql
- 040_learner_infrastructure.sql
- 041_self_modification.sql
- 042_artifact_registry.sql
- 043_canary_deployment.sql
- 044_rbac.sql
- 045_policy_control.sql
- 046_simulator_infrastructure.sql
- 047_observability_traces.sql

### Backend Services/Routes to Add
- backend/src/services/task-engine.service.ts
- backend/src/services/goal-manager.service.ts
- backend/src/services/planner.service.ts
- backend/src/services/reward-calculator.service.ts
- backend/src/services/trajectory-store.service.ts
- backend/src/services/learner.service.ts
- backend/src/services/eval-harness.service.ts
- backend/src/services/artifact-registry.service.ts
- backend/src/services/canary-deployer.service.ts
- backend/src/services/rbac.service.ts
- backend/src/services/policy-engine.service.ts
- backend/src/services/perception-adapter.service.ts
- backend/src/services/observability.service.ts

- backend/src/routes/autonomy-tasks.routes.ts
- backend/src/routes/autonomy-goals.routes.ts
- backend/src/routes/autonomy-workflows.routes.ts
- backend/src/routes/autonomy-memory.routes.ts
- backend/src/routes/autonomy-outcomes.routes.ts
- backend/src/routes/autonomy-learners.routes.ts
- backend/src/routes/autonomy-artifacts.routes.ts
- backend/src/routes/autonomy-evals.routes.ts
- backend/src/routes/autonomy-canary.routes.ts
- backend/src/routes/autonomy-observability.routes.ts

### Python Services/Adapters to Add
- autonomy/perception_adapter.py
- autonomy/perception_base.py
- autonomy/task_engine.py
- autonomy/goal_manager.py
- autonomy/planner.py
- autonomy/trajectory_store.py
- autonomy/replay_trainer.py
- autonomy/eval_suite.py
- autonomy/simulator.py
- autonomy/business_decision_sim.py
- autonomy/research_claim_sim.py
- autonomy/reward_calculator.py
- scripts/autonomy_smoke.py
- scripts/run_autonomy_eval.py
- scripts/run_simulator.py
- scripts/create_replay_batch.py
- scripts/run_learner.py
- scripts/check_autonomy_invariants.py

### Frontend Pages to Add
- frontend/src/app/autonomy/page.tsx
- frontend/src/app/autonomy/tasks/page.tsx
- frontend/src/app/autonomy/goals/page.tsx
- frontend/src/app/autonomy/workflows/page.tsx
- frontend/src/app/autonomy/memory/page.tsx
- frontend/src/app/autonomy/evaluation/page.tsx
- frontend/src/app/autonomy/learner/page.tsx
- frontend/src/app/autonomy/artifacts/page.tsx
- frontend/src/app/autonomy/deployment/page.tsx
- frontend/src/app/autonomy/governance/page.tsx
- frontend/src/app/autonomy/observability/page.tsx

### Documentation to Add
- docs/CURRENT_CAPABILITIES.md
- docs/TRUE_AUTONOMY_ARCHITECTURE.md
- docs/AUTONOMY_SAFETY_MODEL.md
- docs/AUTONOMY_EVALS.md
- docs/SELF_MODIFICATION_PIPELINE.md
- docs/RBAC_AND_SERVICE_IDENTITIES.md
- docs/PRODUCTION_READINESS.md

### Makefile Additions
```makefile
autonomy-migrate
autonomy-smoke
autonomy-eval
autonomy-sim
autonomy-learner
autonomy-dashboard
autonomy-security-test
autonomy-full-test
```

---

## 4. EXISTING SAFETY INVARIANTS TO PRESERVE

**MUST NOT VIOLATE:**

1. **Sealed Resolver Boundaries**
   - Resolver code is read-only by autonomous agents
   - Learner candidates cannot modify resolver internals
   - Resolution independence is enforced

2. **Calibration-First Trust**
   - Calibration ledger immutable
   - Trust scores computed by sealed resolver service role
   - High-confidence claims tracked with uncertainty

3. **Pre-Registered Claims**
   - Claims must be registered before being used
   - Auto-generated claims go through validation
   - Claim registration is auditable

4. **Independent Resolution**
   - Resolution source not controlled by agent making claim
   - Multiple resolution sources possible
   - Resolver service role separate from agent role

5. **Immutable Audit Logs**
   - Audit log entries cannot be updated or deleted
   - Triggers enforce immutability at DB level
   - Timestamps are server-side
   - All autonomy state transitions write audit entries

6. **Signed Event Envelopes**
   - All critical events carry signatures
   - Signature verification on read
   - Provenance chain intact

7. **Human Governance for High-Risk**
   - Critical and high-risk goals require human approval
   - New domains require governance approval
   - Autonomous action boundaries strictly enforced
   - Kill switch always available

8. **No Self-Certification**
   - Agent cannot approve its own authority expansion
   - Institution cannot review itself
   - Learner cannot evaluate its own candidates without external eval gate

9. **No Generated Code Modifying Ground Truth**
   - Self-generated code cannot write to belief ledger
   - Self-generated code cannot modify trust scores
   - Self-generated code cannot modify resolver tables
   - Promotion requires governance approval

10. **No Uncontrolled Autonomous Action**
    - Actions outside approved autonomy level blocked
    - External tool use requires explicit permission scope
    - Perception read-only by default
    - Database writes via service roles only

---

## 5. EXECUTION CHECKLIST

### Before Starting
- [ ] Database environment configured (Postgres + Kafka optional)
- [ ] Backend dependencies installed (npm install)
- [ ] Frontend dependencies installed (npm install)
- [ ] Python environment configured

### Per Phase
- [ ] Create migrations (SQL)
- [ ] Create backend services (TypeScript)
- [ ] Create backend routes (TypeScript)
- [ ] Create Python services/adapters (Python)
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Add safety tests
- [ ] Run make smoke, verify no regressions
- [ ] Document additions

### Final Integration
- [ ] make autonomy-smoke passes (real loop, no fake success)
- [ ] All 121 existing tests still pass
- [ ] New autonomy tests pass
- [ ] RBAC security tests pass
- [ ] Protected surface tests pass
- [ ] make master-gate passes

---

## 6. SUCCESS CRITERIA (FINAL ACCEPTANCE)

1. **Existing Safety:** All protected invariants still enforced
2. **Traceability:** Every autonomy action has trace_id, audit log linked
3. **Durability:** Long-running task survives process restart
4. **Evaluation Gates:** Promotion blocked without passing evals
5. **Memory:** Episodes + trajectories persisted, replay batches deterministic
6. **Learner:** Real candidates from real trajectories, cannot deploy self, protected surfaces scanned
7. **RBAC:** Unauthorized writes blocked, service identity scoping enforced
8. **Simulation:** Clearly labeled, firewall prevents leakage to real-world trust
9. **APIs:** OpenAPI spec complete, all routes audited, RBAC enforced
10. **Dashboards:** Real data only, no static fake content
11. **Tests:** All tests pass, no TODO/pass/placeholder in production code
12. **Docs:** Accurate, no overclaims, distinguish simulator from real-world

---

## 7. KNOWN LIMITATIONS & DEFERRABLE ITEMS

**Will NOT implement in Phase 1:**
- Kubernetes/Helm integration (local/abstraction layer sufficient)
- Fine-tuning infrastructure (policy/prompt updates only)
- Advanced red-teaming (initial evals sufficient)
- Multi-agent auction/market mechanisms (governance only)
- Continual learning from production (batch replay only)

**Documented as "Controlled/Gated":**
- Autonomous internet perception (allowlist + read-only)
- Autonomous code generation (sandbox + protected surface scan + promotion gate)
- Goal self-generation (proposal only, human approval required for new domains)

**Will be documented as "Experimental":**
- Simulator trajectories used for policy training (Reality/Simulation firewall in place)
- Learner-generated candidates (evaluated, not auto-promoted)

---

## 8. REFERENCE TO SPECIFICATION

This plan implements the "TARGET ARCHITECTURE" from the user's brief:

```
External environment / simulator / task source
→ perception adapter (Phase 4)
→ normalized event (Phase 4)
→ goal/task manager (Phase 5, Phase 1)
→ durable planner/workflow (Phase 2, Phase 6)
→ agent runtime/tool executor (existing autonomy/ + Phase 2)
→ signed output envelope (existing signatures + Phase 11)
→ outcome resolver/reward calculator (existing + Phase 7)
→ trajectory and memory store (Phase 3)
→ learner/replay trainer (Phase 9)
→ evaluation gate (Phase 8)
→ model/code/prompt registry (Phase 12)
→ candidate promotion decision (Phase 11)
→ canary deployment/rollback (Phase 13)
→ audit log (existing + all phases)
→ OpenTelemetry traces/metrics (Phase 1)
→ governance dashboard/human override (Phase 15, Phase 17)
```

All 20 phases map to user-specified architecture. All non-negotiable rules respected.

---

**Ready to implement. Proceeding phase-by-phase.**

