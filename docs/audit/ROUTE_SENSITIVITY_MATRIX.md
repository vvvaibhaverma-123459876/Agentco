# Route Sensitivity Matrix

Generated from active Fastify route registrations in `backend/src/server.ts`, `backend/src/routes/*.ts`, and `backend/src/services/learning.service.ts`. Disabled `*.disabled` route files are not active and are excluded. Fastify's implicit `HEAD` handling follows each `GET` route's classification. CORS preflight must remain detail-free and is not treated as a data route.

## Classification Policy

- `PUBLIC`: health probes only. Liveness exposes process state; readiness/detailed health expose sanitized dependency status without credentials, connection strings, stack traces, audit data, governance data, identity state, resource ledgers, or dashboard state.
- `AUTH-READ`: reads application/system state and requires the configured API key when `AGENTCO_API_KEY` is set.
- `AUTH-WRITE`: mutates state or starts work and requires the configured API key.

Public browser access must not receive a privileged service API key. Browser dashboard requests go through the frontend server-side API proxy, which injects service credentials from server-only environment variables.

## Counts

| classification | routes |
|---|---:|
| PUBLIC | 4 |
| AUTH-READ | 91 |
| AUTH-WRITE | 116 |
| TOTAL | 212 |

## Matrix

| route | method | data exposed | classification | rationale |
|---|---|---|---|---|
| `/api/agents` | GET/HEAD | Agent registry/task/dispatch state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/agents/:id` | GET/HEAD | Agent registry/task/dispatch state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/agents/:id/dispatch` | POST | Agent registry/task/dispatch state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/agents/:id/heartbeat` | GET/HEAD | Agent registry/task/dispatch state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/agents/tasks` | GET/HEAD | Agent registry/task/dispatch state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/agents/tasks/:task_id` | GET/HEAD | Agent registry/task/dispatch state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/audit` | GET/HEAD | Audit trail, trace, or integrity state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/audit/integrity` | GET/HEAD | Audit trail, trace, or integrity state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/action-loop` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/actions` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/allocation/record-decision` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/audit` | GET/HEAD | Audit trail, trace, or integrity state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/candidates` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/candidates/:candidateId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/claims` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/dashboard/overview` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/evals/scorecards` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/evals/scorecards/:scorecardId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/evidence` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/evidence/:evidenceId/share` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/evidence/:sourceEvidenceId/deduplicate` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/goals/:parentGoalId/rollup` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/goals/:parentGoalId/sub-goals` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/goals/:parentSubGoalId/tasks` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/institutions/:institutionId/goal-hierarchy` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/institutions/:institutionId/root-goal` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/observability/traces` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/run-level3-smoke` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/run-level3-smoke/:runId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/runs` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/runs/:runId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/specialist-teams/patterns` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/specialist-teams/record-pattern` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/tasks` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/tasks/:taskId/cancel` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/checkpoint` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/checkpoint/:stepIndex` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/autonomy/tasks/:taskId/complete` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/fail` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/lease` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/queue` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/tasks/:taskId/start` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/work-requests` | POST | Autonomy run/task/candidate/evidence/action state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/autonomy/work-requests/:requestId` | GET/HEAD | Autonomy run/task/candidate/evidence/action state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/assessments` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/assessments/:assessmentId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/assessments/:assessmentId/recommendation` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/batch-update-reputations` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/canary/:canaryId/metric` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/canary/:canaryId/promote` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/canary/:canaryId/rollback` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/canary/start` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/changes/:requestId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/changes/:requestId/approve` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/changes/:requestId/review` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/changes/pending` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/changes/request` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens` | GET/HEAD | Citizenship status/sanction/role/envelope state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/citizens` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/:citizenId` | GET/HEAD | Citizenship status/sanction/role/envelope state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/citizens/:citizenId/envelope` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/:citizenId/roles` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/:citizenId/sanctions` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/:citizenId/suspend` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/:citizenId/transition` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/roles/:eligibilityId/revoke` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/sanctions/:sanctionId/lift` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/citizens/successions` | POST | Citizenship status/sanction/role/envelope state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId` | GET/HEAD | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/coalitions/:coalitionId/activate` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/commitments` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/consensus` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/constitute` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/delegations` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/dissents` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/negotiate` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/proposals` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/settle` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/coalitions/:coalitionId/terminate` | POST | Institution coalition negotiation/consensus/commitment/settlement state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/consistency-check` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/constitution/activate` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/constitution/active` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/constitution/protected-surfaces` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/constitution/validate-change` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/constitution/versions` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/contracts` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/contracts/:contractId/transition` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/departments/:departmentId/specialists` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/drift/:driftId/resolve` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/drift/critical` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/drift/detect` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/drift/unresolved` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/goals/:goalId/lock` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/goals/:goalId/unlock` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/governance/summary` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/health` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/charter` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/deadlock-check` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/deadlock-incidents` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/governance` | GET/HEAD | Society/institution governance/contract state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/jurisdiction` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/limits` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/mandates` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/powers` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/reputation-distribution` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/specialist-assignments` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/institutions/:institutionId/top-performers` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/underperformers` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/:institutionId/work-requests` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/institutions/bootstrap-mandatory` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/:civilizationId/activate` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/:civilizationId/charter` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/:civilizationId/charter/active` | GET/HEAD | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/kernel/:civilizationId/emergency` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/:civilizationId/invariants` | GET/HEAD | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/kernel/:civilizationId/objectives` | GET/HEAD | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/kernel/:civilizationId/objectives` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/:civilizationId/transition` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/bootstrap` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/emergency/:emergencyId/revoke` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/emergency/expire-sweep` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/objectives/:objectiveId/status` | POST | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/kernel/root` | GET/HEAD | Civilization kernel lifecycle/charter/emergency/objective state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/policies` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/policies/:policyId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/policies/:policyId/approve` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/policies/:policyId/review` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/policies/active` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/policies/by-type/:policyType` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/reputation-anomalies/:institutionId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/reputation-trend/:entityId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/reputation/:entityType/:entityId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/reputation/:entityType/:entityId/trust-weight` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/reputation/events` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/reputation/snapshots/:entityType/:entityId` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/runtime/dispatch-tick` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/runtime/graph` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/runtime/reachability-tick` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/runtime/scheduler` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/runtime/scheduler/run-once` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/runtime/scheduler/start` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/runtime/scheduler/stop` | POST | Civilization governance/runtime/reputation/work state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies` | GET/HEAD | Society/institution governance/contract state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/societies` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/:societyId/citizens` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/:societyId/citizens/:citizenId/leave` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/:societyId/institutions` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/:societyId/jurisdictions` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/:societyId/transition` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/bootstrap-defaults` | POST | Society/institution governance/contract state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/civilization/societies/topology` | GET/HEAD | Society/institution governance/contract state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/civilization/status` | GET/HEAD | Civilization governance/runtime/reputation/work state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/credential/:agent_id` | GET/HEAD | Agent credential material or credential lookup | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/audit-trail` | GET/HEAD | Audit trail, trace, or integrity state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/bootstrap` | POST | Governance roles, policy, RBAC, audit, or attestation state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/governance/constitution` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/emergency-freeze` | POST | Governance roles, policy, RBAC, audit, or attestation state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/governance/entities/:entityId/roles` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/permissions` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/policies/:policyId/approve` | POST | Governance roles, policy, RBAC, audit, or attestation state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/governance/roles` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/roles/:entityId/assign` | POST | Governance roles, policy, RBAC, audit, or attestation state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/governance/roles/:entityId/revoke` | POST | Governance roles, policy, RBAC, audit, or attestation state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/governance/status` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/governance/why/:action_id` | GET/HEAD | Governance roles, policy, RBAC, audit, or attestation state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/learning/agent/:agent_id` | GET/HEAD | Learning statistics, signals, proposals, or insights | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/learning/insights` | GET/HEAD | Learning statistics, signals, proposals, or insights | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/learning/proposals/:proposal_id/apply` | POST | Learning statistics, signals, proposals, or insights | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/learning/signal` | POST | Learning statistics, signals, proposals, or insights | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/learning/stats` | GET/HEAD | Learning statistics, signals, proposals, or insights | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/overrides` | GET/HEAD | Human override queue or resolution state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/overrides` | POST | Human override queue or resolution state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/overrides/:request_id/resolve` | POST | Human override queue or resolution state | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/api/overrides/overdue` | GET/HEAD | Human override queue or resolution state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/api/validation/reports` | GET/HEAD | Validation report state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/health` | GET/HEAD | Minimal liveness status and timestamp | PUBLIC | Only public route: liveness probe with no runtime/provider/system state. |
| `/health/detailed` | GET/HEAD | Sanitized dependency health state | PUBLIC | Public dependency probe returns sanitized status only; no credentials, connection strings, stack traces, audit, governance, identity, or dashboard state. |
| `/health/live` | GET/HEAD | Minimal liveness status and timestamp | PUBLIC | Kubernetes liveness probe with no dependency requirement. |
| `/health/ready` | GET/HEAD | Sanitized readiness dependency state | PUBLIC | Kubernetes readiness probe returns sanitized dependency status only. |
| `/health/runtime` | GET/HEAD | Runtime/provider/component health state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/identity/actors` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/delegations/grant` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/keys` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/keys/:keyId/revoke` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/keys/verify-signature` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/permissions/grant` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/roles/assign` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/identity/verify` | POST | Identity, role, delegation, key, or verification mutation | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/metrics` | GET/HEAD | Prometheus/runtime metrics | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/resources/accounts` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/accounts/:accountId` | GET/HEAD | Resource accounts, transactions, reservations, or balances | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/resources/reservations` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/reservations/:reservationId/release` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/reservations/:reservationId/settle` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/reservations/expire` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/transactions/credit` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/resources/transactions/debit` | POST | Resource accounts, transactions, reservations, or balances | AUTH-WRITE | Mutates or triggers backend state; must require API key. |
| `/system/build-status` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/capabilities` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/fallbacks` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/feature-gates` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/health` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/migrations` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/readiness` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/runtime-mode` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/system/version` | GET/HEAD | System mode, build, migration, readiness, or capability state | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |
| `/ws/events` | GET/HEAD | Realtime event stream | AUTH-READ | Exposes non-liveness system/application state; default stance is authenticated read. |

## Uncertain Classifications

None. Routes that look health-like but expose runtime/provider/component/system state beyond sanitized dependency readiness, such as `/health/runtime`, `/system/health`, and `/api/civilization/health`, are intentionally classified `AUTH-READ`.
