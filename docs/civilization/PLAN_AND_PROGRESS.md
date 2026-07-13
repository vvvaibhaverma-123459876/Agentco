# Civilization Layer Build — Plan and Progress

Live status for the civilization-layer build (brief: complete production-grade civilization layer, phases C0–C15).
Machine-readable state: [`CIVILIZATION_BUILD_LEDGER.yaml`](../../CIVILIZATION_BUILD_LEDGER.yaml). This document is updated at every phase boundary and meaningful checkpoint.

## Current state

| Field | Value |
|---|---|
| Branch | `feature/civilization-layer` |
| Base commit | `997e66ce700e0c93896f13f7d6f559d0a50b15dd` (GitHub main, PRs #21–#23 merged) |
| Current phase | **C2 — citizenry** (integrated; full regression running) |
| Current item | C2 regression → verify; next: C3 societies + institutions |
| Completion gate | `termination_predicate_met: false` — 9/52 verified, 5 integrated |
| Test results | baseline 101 suites green; post-C1: 102 suites / 665 tests green (incl. route-auth 178); C1 kernel 8/8; C2 citizenship 7/7 |
| Migration state | 129_civilization_kernel + 130_citizenship applied cleanly on the isolated empty-DB stack |
| Known blockers | none |
| Next executable action | C2 full regression → commit; C3: societies schema (131) + institution charters/mandates/contracts + 10 mandatory institutions seed |

## Environment decisions (recorded)

- Build runs in a dedicated clone at `/Users/Zet/agentco-build/Agentco`. The operator's live tree (`/Users/Zet/Agentco`) is never touched; their local-only commit `f1591df` (CI evidence binding) is noted for later merge if pushed.
- All infra for this build is **isolated**: dedicated container names (`agentco-build-*`) and ports (Postgres 5544; Kafka 9192 when needed) so the operator's own `agentco-*` containers and volumes are never shared or disturbed. Rationale: backend tests mutate schema/data; sharing the operator's DB would corrupt their work.
- Commits are checkpointed on the build branch; **no push** without explicit operator authorization (brief §17).
- GNU Make on this host is 3.81; Makefile changes must stay 3.81-compatible.

## Phase status

| Phase | Status | Notes |
|---|---|---|
| C0 canonical runtime freeze | **VERIFIED** | canonical map + D1–D10 dispositions; env + reachability baselines green |
| C1 civilization kernel | **VERIFIED** | migration 129; kernel service + bootstrap + routes; 8/8 tests; full suite green |
| C2 citizenry | INTEGRATED | migration 130; gate wired into durable-execution + specialist spawn; 7/7 tests; regression running |
| C3 societies + institutions | not started | |
| C4 coalitions | not started | |
| C5 objectives/goals/missions | not started | |
| C6 economy | not started | |
| C7 governance | not started | |
| C8 judiciary | not started | |
| C9 collective epistemics | not started | |
| C10 learning + safe evolution | not started | |
| C11 capability/domain expansion | not started | |
| C12 civilization operating system | not started | |
| C13 operator plane | not started | |
| C14 reliability/security/deployment | not started | |
| C15 completion proof | not started | |

## Foundation facts (from pre-build inspection, 2026-07-13)

- Canonical runtime confirmed: TypeScript Fastify backend (`backend/src`), PostgreSQL via `backend/src/db/migrate.ts` (filename-ordered transactional SQL, `schema_migrations` tracking), canonical `event_log` + `decision_log` + transactional outbox (`event_outbox`, plus signed event-bus outbox via migration 128), Kafka relay via `backend/src/workers/outbox-worker.ts`.
- Existing L0–L14 substrate per `BUILD_LEDGER.yaml` (68/71 verified at base commit): identity/authority (079/084/085/086), resource ledger + reservations (081/082), evidence registry (088), prediction ledger + resolution_service role, trust scoring, judiciary (109), learning candidate registry + regression generator (104), skill library (105), proof of competence (106), capability expansion gate (107), skill promotion loop (108), domain registry (102), generality tracker (103), civilization runtime + bounded scheduler routes.
- Existing partially-built civilization pieces to extend (not duplicate): `coalition-formation.service.ts`, `deadlock-detector.service.ts`, `institutions.service.ts` (5-department creation), `institution-work-assignment`, `goal-hierarchy`, `civilization-runtime/scheduler` services.
- Known defects to fix during build (from prior audit + own inspection): echo-only fake-success Make targets (`autonomy-memory-quality-test`, `autonomy-observability-test`), broken `autonomy-phases-9-13-full-test` (missing dependency target), Python civilization stack (`civilization/`) duplicating backend semantics (C0 disposition decision pending).

## Checkpoint log

- 2026-07-13 — Branch created from 997e66ce. Ledger (52 items, C0–C15) and this plan created. C0 inventory + environment baseline started.
- 2026-07-13 — C0 verified (canonical map D1–D10; baseline: 117 migrations empty-DB, tsc, 101 suites green). C1 implemented+committed (b693aaf): kernel migration 129, service, bootstrap, routes, 8/8 tests. Route-auth matrix regression caught missing classifications → matrix extended 157→171 (d296a00); full suite green (102 suites / 665 tests). Learned: never pipe test commands through tail — exit codes must come from the test runner.
- 2026-07-14 — C2 integrated: migration 130 (citizens/sanctions/roles/envelopes/successions with guards; institutions.id is VARCHAR — FK matched), citizenship service, gate wired into durable-execution (enqueue+run) and team-activation spawn (with trust-linked budget scaling), 11 routes (matrix 171→182), 7/7 focused tests. Full regression running.
