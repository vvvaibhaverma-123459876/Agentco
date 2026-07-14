# Canonical Runtime Map — C0 Freeze

Phase C0 decision record for the civilization-layer build. This freezes exactly one canonical production
path per concern (brief §3.1) and records the disposition of every duplicate or legacy implementation.
Machine-readable companion: [`canonical_runtime_map.json`](canonical_runtime_map.json).

Baseline evidence: `docs/audit/current/RUNTIME_COMPONENT_LEDGER.md` and `RUNTIME_REACHABILITY.md`
(structural snapshot `f64ae909…`, remediation-04 batch), regenerable via `make audit-runtime-integration`.

## Canonical paths (one per concern)

| Concern | Canonical implementation | Persistent state | Entry points |
|---|---|---|---|
| Identity | `backend/src/services/identity-authority.service.ts` | `actors`, `agent_identities`, `service_identities`, `actor_key_ring` | `/identity/actors`, `/identity/keys*` |
| Authorization | same service — authority chain decisions | `role_assignments`, `actor_permissions`, `authority_decision_chains` | `/identity/verify`, `/identity/roles/assign` |
| Resource accounting | `backend/src/services/resource-ledger.service.ts` | `civilization_resource_accounts`, `civilization_resource_transactions`, reservations | `/resources/*` |
| Events | `backend/src/services/event-log.service.ts` (canonical hash-chained `event_log` + transactional `event_outbox`) and `backend/src/services/event-bus.service.ts` (signed envelopes, `event_history` + `event_bus_outbox`) | `event_log`, `event_outbox`, `event_history`, `event_bus_outbox` | emitted inside service transactions |
| Event relay | `backend/src/workers/outbox-worker.ts` (drains BOTH outboxes) | — | `npm run agentco:outbox-worker` |
| Audit | `backend/src/services/audit-log.service.ts` (append-only, chain-hashed `decision_log`) | `decision_log` | `appendWithClient` from every canonical writer |
| Evidence | `backend/src/services/evidence-registry.service.ts` | `autonomy_evidence` (+ vector index `101`) | action executor `WEB_SEARCH`/`FETCH_PAGE` |
| Claims | `backend/src/services/action-executor.service.ts` + `claim-grounding.service.ts` | `autonomy_claims` | `GENERATE_CLAIM` action |
| Predictions | `prediction_ledger` (shared schema) via `backend/src/services/resolution-service.service.ts` | `prediction_ledger` (+ chain log) | prediction registration paths |
| Resolution | `resolution-service.service.ts` under the `resolution_service` DB role (write-once, DB-trigger enforced) | resolution columns | authorized service connection only |
| Calibration | Python `calibration/` scoring math + backend `persistent-trust-scorer.service.ts` for durable windows | `trust_scores`, `trust_reputation_ledger` | resolution → scoring pipeline |
| Trust | `persistent-trust-scorer.service.ts`; consumers read latest non-downgraded window | `trust_scores` | domain registry, routing |
| Memory | `memory-promotion-pipeline.service.ts` + `memory-retrieval.service.ts` | `agent_memories` (append-only, trigger-enforced) | promotion after scoring; planner injection |
| Citizens | `backend/src/agent-registry.ts` (actor-backed) + live runtimes: `runtime/base_agent/base_agent_v2.py` (dispatch path) and `agents/autonomy/*` specialists | `actors`, `agent_identities` (+ C2 citizenship tables) | dispatch + `TeamActivationService` spawn |
| Institutions | `backend/src/services/institutions.service.ts` (5 mandatory departments) | `institutions`, `departments` | institution creation path |
| Missions | **NEW in C5** — layered ON TOP of `goal-hierarchy.service.ts`, `durable-execution.service.ts`, `saga-coordinator.service.ts` (no replacement of the task system) | C5 tables | C5 routes + C12 coordinator |
| Governance | `calibration-constitution.service.ts`, `protected-surface-validator.service.ts`, `risk-tier-classifier.service.ts`, `kill-switch.service.ts` (+ C7 proposals/voting/policy enforcement) | constitution/policy/kill-switch tables (027, 097, 098) | `/api/civilization/constitution*`, `/api/civilization/policies*` |
| Judiciary | `judiciary.service.ts` (+ C8 hearings/appeals/enforcement) | judiciary tables (109) | C8 routes |
| Learning | `learner.service.ts`, `regression-test-generator.service.ts`, `skill-library.service.ts`, `candidate-evaluation.service.ts`, `autonomous-promotion.service.ts`; sandbox instrument = Python `selfcoding/` sealed resolver | learning/skill tables (099, 104, 105) | learning routes + C10 |
| Expansion | `domain-registry.service.ts`, `capability-expansion-gate.service.ts`, `proof-of-competence.service.ts`, `generality-metric-tracker.service.ts` (+ C11 proposals/trials/grants/revocations) | 102/103/106/107 tables | C11 routes |
| Civilization coordination | `civilization-runtime.service.ts` + `civilization-scheduler.service.ts` (+ C12 daemon/leader election/routers) | `civilization_coordinator_ticks` | `/api/civilization/runtime/*` |

## Duplicate / legacy disposition table

| # | Duplicate or legacy path | Decision | Rationale / action |
|---|---|---|---|
| D1 | Python `civilization/` stack (governance_service, reputation, institutions in Python; reserve-migration schema) | **LEGACY — quarantined, do-not-extend** | Already isolated: its destructive fixtures run only in sibling `<db>_pyciv` databases (`pg_test_isolation.py`). Backend `institutions.service.ts` is canonical. No new callers; C3 extends backend only. Python tests retained as historical coverage of the legacy layer. |
| D2 | Dual outbox stores: `event_outbox` (canonical event_log relay) + `event_bus_outbox` (signed envelope relay, migration 128) — prior finding RTI-002 | **KEEP BOTH, documented split, single relay** | Different payload contracts (canonical state events vs HMAC-signed bus envelopes); one worker (`outbox-worker.ts`) drains both. No second event store is introduced by this build; C14 revisits convergence with replay tests. |
| D3 | `governance-rbac.service.ts` (autonomy-surface RBAC) vs `identity-authority.service.ts` | **BOUNDARY DOCUMENTED** | governance-rbac guards autonomy dashboard/level-3 surfaces; identity-authority is the civilization authority model. C2 citizenship gate builds on identity-authority only. |
| D4 | `dashboard/src` (stand-alone calibration dashboard stub) | **LEGACY — archive candidate in C13** | Operator plane is `frontend/` (Next.js). Not registered in any runtime; C13 decides archive vs delete with tests. |
| D5 | `backend/src/routes/*.disabled` + `backend/src/db/unsupported_migrations/*.disabled` | **REMAIN DISABLED** | C5/C7/C11 build fresh, forward-numbered migrations (129+) and new routes instead of re-enabling stale disabled surfaces. Disabled files stay inert. |
| D6 | `archive/agents_v1` (V1 department agents) | **ALREADY ARCHIVED** (Phase 6) | No action; remaining live V1 surface is the autonomy specialist spawn path, which is the governed adapter. |
| D7 | Python `runtime/base_agent/spend_ledger.py` writing L2/L3 tables directly | **ACCEPTED EXCEPTION (governed direct-DB adapter)** | Existing verified path (L2.SpendGuardrailIntegration) emitting the canonical decision_log hash format; fails closed. Revisit in C6 (economy hardening) whether to route through backend API; documented here per brief §3.2. |
| D8 | `memory_kernel/` (thin Python memory layer) | **LEGACY — do-not-extend** | `agent_memories` via backend promotion pipeline is canonical. |
| D9 | Echo-only Make targets (`autonomy-memory-quality-test`, `autonomy-observability-test`) + `autonomy-phases-9-13-full-test` referencing nonexistent `autonomy-phases-5-8-full-test` | **FIX IN C14** | Fake-success surfaces; replaced with real commands (or retired with exit 2 like `production-release-gate`) during reliability hardening, kept in the ledger so it cannot be forgotten. |
| D10 | Frontend `frontend/src/lib/api/*` hand-written client vs backend routes | **C13 CONTRACT WORK** | Operator-plane phase adds/aligns clients for new civilization APIs; no second API surface. |

## Python specialist boundary (brief §3.2)

Python specialists (`agents/autonomy/*`, `BaseAgentV2` dispatch) reach canonical state through:
1. the `TeamActivationService` spawn adapter (`python3.13 -m agents.autonomy.<role>`) with budgets and role whitelist;
2. the durable-execution dispatch path (registered agents, allowed task types);
3. the documented D7 exception (spend ledger).

C2 adds the citizenship/eligibility gate to (1) and (2). Any other Python write path to canonical
civilization tables found during the build is a defect to fix, not a pattern to extend.
