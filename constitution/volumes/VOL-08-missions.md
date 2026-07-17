# Volume 8 — Missions

## 1. Header

| Field | Value |
|---|---|
| Volume | 8 |
| Name | Missions |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V11 (Trust & Calibration), V7 (Civilization Economy), V12 (Governance), V6 (Institutions) |

## 2. Purpose

Missions are how AgentCo turns objectives into audited work. This volume defines the work
hierarchy — objective → goal → mission → workstream → task → action → evidence →
settlement — and the rule that makes it trustworthy: **a mission completes only when every
completion gate is satisfied, fail-closed, with an attestation written in the same
transaction as the state change.** Work cannot declare its own success. Descriptive tier:
every normative sentence cites the enforcing file or test.

The work decomposition and its gates:

```text
STRATEGIC GOAL         strategic_goals        (mission.service.ts createStrategicGoal)
   │  createMission — policy enforcement checked at creation (assertAllowed)
   ▼
MISSION                missions               state machine, DB-guarded transitions
   │                                          proposed→triaged→approved→funded→planned
   │                                          →assigned→executing→evaluating→completed
   ├─ WORKSTREAM        workstreams            required vs optional
   │     └─ TASK        mission_tasks
   │           └─ ACTION ATTEMPT  mission_action_attempts  (action-executor.service.ts)
   │                 └─ EVIDENCE   mission_evidence_bundle  (links V9 evidence)
   ▼
COMPLETION GATE (fail-closed, ALL required):
   required workstreams complete · evidence linked · settlement recorded
   · audit records present · outcome recorded · status == 'evaluating'
   ▼
ATTESTATION            mission_attestations   (hash bundle, written in-transaction)
   ▼
SETTLEMENT             mission_settlements    (V7 economy)
```

## 3. Definitions

- **Strategic goal** — a top-level objective a mission serves
  (`strategic_goals`, migration `133`).
- **Mission** — a unit of governed work with a lifecycle state machine
  (`missions`; `backend/src/services/mission.service.ts`).
- **Workstream** — a required or optional branch of a mission
  (`workstreams`); a mission is not complete while any *required* workstream is open.
- **Task** — a unit within a workstream (`mission_tasks`).
- **Action attempt** — a single executor action toward a task, recorded win or lose
  (`mission_action_attempts`; `backend/src/services/action-executor.service.ts`).
- **Evidence bundle** — the link between a mission and registered V9 evidence
  (`mission_evidence_bundle`).
- **Completion readiness** — the fail-closed predicate over the five gates
  (`completionReadiness` in `mission.service.ts`).
- **Attestation** — a hashed bundle of the mission's completion state, written inside the
  completion transaction (`mission_attestations`, `writeAttestationWithClient`).
- **Settlement** — the economic close-out of a mission (`mission_settlements`; Volume 7).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V8-INV-001 | A mission completes only when required workstreams are complete and evidence, settlement, audit records, and an outcome all exist; otherwise completion fails closed. | enforced | `backend/src/services/mission.service.ts`, `backend/tests/missions.test.ts` |
| V8-INV-002 | A mission can be completed only from the `evaluating` state, and completion writes a mission attestation in the same transaction as the state transition. | enforced | `backend/src/services/mission.service.ts`, `backend/tests/missions.test.ts` |
| V8-INV-003 | Mission status changes only through the mission service's authorized transition path; direct database updates to status are rejected by trigger. | enforced | `backend/src/db/migrations/133_missions.sql`, `backend/tests/missions.test.ts` |
| V8-INV-004 | An archived mission is immutable, and mission identity columns cannot be altered after creation. | enforced | `backend/src/db/migrations/133_missions.sql` |
| V8-INV-005 | Mission creation is checked against enforceable runtime policy before the mission exists. | enforced | `backend/src/services/mission.service.ts`, `backend/src/services/policy-enforcement.service.ts` |
| V8-INV-006 | Every mission state transition is appended to an append-only transition log. | enforced | `backend/src/db/migrations/133_missions.sql` |
| V8-INV-007 | Executor actions that fetch the web pass the SSRF/URL-safety guard, and each action attempt is recorded whether it succeeds or fails. | enforced | `backend/src/services/action-executor.service.ts`, `backend/tests/action-loop.test.ts` |
| V8-INV-008 | A mission's resource reservations are settled or released on completion or abandonment, with no orphaned reservations. | planned | — |
| V8-INV-009 | Every required workstream traces to at least one piece of grounded evidence, not merely to a completion flag. | planned | — |

## 5. Interfaces

- **Mission lifecycle** — `mission.service.ts`: `createStrategicGoal`, `createMission`
  (policy-gated), `transitionMission`, `addWorkstream`, `addTask`,
  `recordActionAttempt`, `completeWorkstream`, `linkEvidence`, `recordSettlement`,
  `recordOutcome`, `completionReadiness`, `completeMission`, `settleMission`,
  `getMission`, `getAttestation`.
- **Goal formation and sourcing** — `goal-formation.service.ts`,
  `goal-manager.service.ts`, `goal-hierarchy.service.ts`,
  `goal-source-discovery.service.ts`.
- **Execution loop** — `autonomy-orchestrator.service.ts`, `autonomy-run.service.ts`,
  `action-executor.service.ts`, `task-engine.service.ts`.
- **Routes** — mission and goal-hierarchy HTTP routes (classified in the route
  sensitivity matrix, V32).

## 6. State

- **Mission tables (migration `133`):** `strategic_goals`, `missions`,
  `mission_dependencies`, `mission_state_transitions` (append-only), `workstreams`,
  `mission_tasks`, `mission_action_attempts`, `mission_evidence_bundle`,
  `mission_outcomes`, `mission_settlements`, `mission_attestations` (one per mission).
- **Goal/hierarchy tables:** migrations `025`, `054` (goal hierarchies, evidence
  deduplication, cross-institutional evidence access).
- **Action loop tables:** `autonomy_evidence` and action records (migration `050`).

## 7. Failure modes and responses

- **Self-declared success** — `completeMission` calls `completionReadiness` first and
  throws `409` with the blocking list if any gate is unmet
  (`mission.service.ts`); the five gates are required workstreams, evidence, settlement,
  audit, and outcome.
- **Out-of-order completion** — completion requires `status == 'evaluating'`; any other
  state throws `409` (V8-INV-002).
- **Bypassing the service** — the `mission_status_guard` trigger rejects any status
  change unless `civilization.mission_transition_authorized` is set (only the service
  sets it), and freezes identity columns and archived missions (migration `133`).
- **Hostile fetch during execution** — the action executor validates URLs through the
  V32 SSRF guard before fetching (`action-executor.service.ts` `handleFetchPage`,
  `inputValidator.validateUrl`), and records every attempt.
- **Orphaned reservations** — settlement/release completeness on abandonment is not yet
  an enforced invariant (V8-INV-008 planned; open question 1), an economy (V7) seam.
- **Flag-only completion** — a workstream marked complete without traced evidence is
  currently possible; V8-INV-009 (planned) would require evidence per required
  workstream, not just a mission-level bundle (open question 2).

## 8. Verification obligations

Existing and green today: `backend/tests/missions.test.ts` (creation policy gate,
fail-closed completion, evaluating-state requirement, attestation, transition guard),
`backend/tests/action-loop.test.ts` (executor loop + SSRF guard + attempt recording),
`backend/tests/autonomy-run-reuse.test.ts`,
`backend/tests/bounded-goal-formation-e2e.test.ts`,
`backend/tests/goal-formation-supervised-free-run.test.ts`,
`backend/tests/goal-relevant-source-discovery-e2e.test.ts`.

Must exist before the planned invariants flip: a reservation settle/release completeness
test on abandonment (V8-INV-008), and an evidence-per-required-workstream test
(V8-INV-009).

## 9. Implementation mapping

- `backend/src/services/mission.service.ts` — the mission lifecycle, completion gate,
  attestation bundle, settlement.
- `backend/src/db/migrations/133_missions.sql` — schema, state CHECK constraints,
  `mission_status_guard` trigger, append-only transitions.
- `backend/src/services/action-executor.service.ts` — action handlers (web search,
  fetch with SSRF guard, extract evidence, generate claim, update memory, evaluate
  progress, spawn specialist), attempt recording.
- `backend/src/services/autonomy-orchestrator.service.ts`,
  `backend/src/services/autonomy-run.service.ts`,
  `backend/src/services/task-engine.service.ts` — the run/orchestration loop.
- `backend/src/services/goal-formation.service.ts`,
  `backend/src/services/goal-manager.service.ts`,
  `backend/src/services/goal-hierarchy.service.ts`,
  `backend/src/services/goal-source-discovery.service.ts` — goal formation and sourcing.
- `backend/src/services/policy-enforcement.service.ts` — the creation-time policy gate
  (Volume 12).

## 10. Open questions

1. **Reservation lifecycle on abandonment.** Completion records a settlement, but nothing
   yet proves that an *abandoned* mission releases its economic reservations
   (V8-INV-008 planned). This is the V7 (Economy) seam; the invariant belongs here but
   the mechanism spans both volumes.
2. **Evidence granularity.** The completion gate requires a mission-level evidence
   bundle, not evidence per required workstream; a workstream can be flagged complete
   without its own grounded evidence (V8-INV-009 planned).
3. **Two goal lineages.** `strategic_goals` (migration `133`) and the older goal
   hierarchy (`025`/`054`) both model goals; which is canonical for new missions should
   be frozen (a Volume 2 canonical-runtime concern) so orchestration reads one tree.
4. **Audit detection is string-matched.** `completionReadiness` detects audit records via
   `decision_log.input_summary LIKE '%mission <id>%'` (`mission.service.ts`); a
   structured mission→decision link would be more robust than substring matching.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 6) | Bind the objective→goal→mission→task→action→evidence→settlement chain and its fail-closed completion gate into one citable work system, since Knowledge (V9) and Trust (V11) feed it and Economy (V7) settles it. |
