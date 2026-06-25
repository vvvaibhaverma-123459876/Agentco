# Civilization Free-Run Runtime

Last updated: 2026-06-25

## What Is Real

The backend has a goal-less free-run vertical slice:

```bash
cd backend
DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npx ts-node scripts/civilization-free-run.ts --mode fixture
```

The runtime executes:

1. self-assessment from a real Postgres health snapshot
2. internal goal creation with `source = perception_derived`
3. society agenda persistence in `autonomy_memory`
4. agenda-driven bounded task execution
5. grounded claim creation
6. active contradiction detection
7. governance-bound agent spawn proposal
8. governance-bound self-improvement proposal
9. pending human-review override requests for those proposals
10. promotion gate
11. prediction registration
12. report artifacts under `audit_artifacts/civilization_free_run/<run_id>/`

The society agenda is not just a note: it carries `societyId`, `institutionId`, `taskType`, and `executionDomain`, and fixture bounded execution consumes that route. Calibration agendas produce evidence-promotion work; research agendas produce research-ingestion work.

Contradiction detection is now an active free-run stage. New claims are compared against recent stored claims for direct polarity conflicts over the same normalized proposition. When a conflict is found, the new claim is marked `contradicted`, `contradicted_by` / `contradicts` links are persisted on the real `autonomy_claims` rows, and promotion blocks the contradicted claim.

Agent spawning is proposal-only in the free-run pass. The runtime maps agenda and contradiction needs to registered specialist roles, copies the role's real default budget from `SPECIALIST_ROLES`, persists an `agent_spawn_proposal` in `autonomy_memory`, writes `agent_spawn_proposals.jsonl`, and does not activate a subprocess or write `autonomy_team_activations`.

Self-improvement is also proposal-only. The free-run pass records a structured `self_improvement_proposal` with affected files, expected improvement, tests to pass, rollback plan, risk level, and protected-surface scan results from `ProtectedSurfaceEnforcerService`. It writes `self_improvement_proposals.jsonl`; it does not edit code, create deployable candidates, or promote changes.

Self-assessment now computes a health snapshot from deployed tables instead of only counting claims. The snapshot includes total claims/evidence, supported/promoted backlog, unresolved contradiction links, overdue unresolved Phase 0b predictions, and weak domains with multiple claims but no promoted knowledge. The chosen internal goal is derived from those signals, and the report records the snapshot in `civilization_report.md`, `events.jsonl`, and `report.json`.

Proposal review is connected to the existing human override queue. Agent-spawn proposals enqueue `agent_upgrade` requests and self-improvement proposals enqueue `config_change` requests in `override_queue`. They remain `pending`, have no `approval_token`, and carry `blocked_until_approved = true` in context. The free-run does not consume approvals, activate specialists, generate candidates, or apply code changes.

Approval consumption now has a preflight gate. `assessGovernanceApprovalReadiness()` requires a matching approved `override_queue` row, the exact approval token, and a completed `eval_scorecards` row with `promotion_eligible = true`. It writes a `governance_approval_preflight` audit record to `autonomy_memory` and returns `ready` or a structured blocked reason. It does not execute the queued action.

Approved agent-spawn proposals can now run one bounded specialist lifecycle after the preflight returns `ready`. `executeApprovedAgentSpawn()` starts the real Python specialist subprocess through `TeamActivationService`, sends one signed `evaluate_progress` action over HTTP, terminates the process, updates `autonomy_team_activations`, and writes an `approved_agent_spawn_execution` audit record. The included specialist runtime is a stdlib HTTP server under `backend/agents/autonomy/` for the free-run roles. It does not promote artifacts.

Approved self-improvement proposals can now become sandbox-validated learner candidates after the same approval-token/eval preflight returns `ready`. `executeApprovedSelfImprovementCandidate()` creates a real `artifacts` row, immutable `autonomy_episodes` + `trajectory_store` evidence, `replay_batches`, a completed `learner_runs` row, an evaluated `learner_candidates` row, a sandbox `eval_runs`/`eval_scorecards` record, and an `approved_self_improvement_candidate_execution` audit record. The candidate is deliberately not promoted: `learner_candidates.status = 'evaluated'`, `promoted_at IS NULL`, sandbox feedback has `promotion_allowed = false`, and the sandbox scorecard has `promotion_eligible = false`.

Sandbox-validated self-improvement candidates now have a separate human-governed promotion path. `enqueueSelfImprovementPromotionRequest()` creates a new pending `override_queue` row for an evaluated candidate with a tested, non-simulation artifact and passed sandbox feedback. `executeApprovedSelfImprovementPromotion()` requires that separate approval token plus a completed promotion-eligible eval before marking `learner_candidates.status = 'promoted'`, setting `promoted_at`, marking the `artifacts` row `promoted`, and writing an `approved_self_improvement_promotion_execution` audit record. This still does not deploy artifacts or modify source files; the active deployment/rollback tables are not present in the active schema.

## How It Is Tested

```bash
cd backend
RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npx jest tests/integration/civilization-free-run.test.ts --runInBand --forceExit
```

The integration test uses real Postgres and asserts that:

- the run starts without a user goal
- the internal goal is persisted as perception-derived
- the society agenda is persisted
- the health snapshot detects unresolved contradictions, stale predictions, and weak domains from real Postgres state
- the agenda route drives the bounded task objective and claim content
- direct contradictions are detected and persisted before promotion
- agent spawn proposals are persisted with governance review required and bounded budgets
- proposal creation does not activate specialists
- self-improvement proposals include affected files, tests, rollback plan, and protected-surface scan
- proposal review requests are persisted in `override_queue` as pending, unapproved, blocked actions
- approval-token preflight blocks pending requests, missing evals, and non-eligible scorecards, then returns ready only for approved requests with a promotion-eligible eval
- ready agent-spawn approvals start a real specialist subprocess, execute one signed bounded action, terminate it, and persist a completed `autonomy_team_activations` row
- ready self-improvement approvals create a sandbox-validated learner candidate backed by artifact, trajectory, replay batch, learner run, candidate, sandbox eval, and audit-memory rows without promotion
- sandbox-validated candidate promotion requires a second pending override, blocks on a non-eligible eval, and only promotes the real candidate/artifact rows after a separate approval plus promotion-eligible eval
- grounded claims can be promoted
- ungrounded claims are blocked
- prediction registration is attempted
- report, event, claim, contradiction, agent-spawn-proposal, self-improvement-proposal, and governance-queue artifacts are written

## Still Partial

This is not the full civilization objective yet.

- self-assessment is still single-pass; it does not yet compare trends across runs or apply learned severity thresholds
- society agendas are persisted records, not a complete society scheduler
- contradiction detection is conservative and direct-pattern based; it does not yet do semantic contradiction discovery with retrieval or LLM adjudication
- agent spawn proposals can execute one bounded approved lifecycle; they are not yet connected to longer task delegation or result promotion
- self-improvement proposals have approval-token/eval preflight, candidate generation, sandbox validation, and a separate human-governed candidate/artifact promotion path, but they are not connected to deployment, rollback, or source-code modification
- `read_only_web` depends on the external arXiv/LLM path and remains environment-limited

Next integrated increments should deepen the candidate evaluator with richer replay/regression checks or add active artifact deployment/rollback tables before any deployable self-modification path. Do not enable autonomous code modification.
