# Volume 3 — Runtime Operating System

## 1. Header

| Field | Value |
|---|---|
| Volume | 3 |
| Name | Runtime Operating System |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V2 (Civilization Kernel), V1 (Constitutional Core), V8 (Missions), V16 (Autonomous Evolution), V29 (Infrastructure) |

## 2. Purpose

The Runtime Operating System is the machinery that keeps the civilization *running*:
scheduling ticks, dispatching durable work, publishing events reliably, recovering after
restart, and honoring the kill switch on every loop. Its defining properties are
**exactly-once-effect work sourcing** (leader election + claim-once), **at-least-once
event delivery** (transactional outbox with bounded retry), and **fail-safe halting** (a
run guard consulted at every stage). Mixed status; every present-tense claim cites its
file.

```text
LEADER ELECTION  pg_try_advisory_lock(918273645)   one scheduler ticks at a time
   ▼   (even across restarts; re-running a tick never duplicates work)
SCHEDULER TICK  civilization-scheduler.service.ts / civilization-os.service.ts
   │
DURABLE WORK  durable-execution.service.ts
   │   enqueue → claim (SET status='running' once) → dispatch → complete/fail
   │   kill-switch checked before protected execution (V2 citizenship gate)
   ▼
EVENT DELIVERY  transactional-outbox.service.ts  (event_outbox, mig 083)
   │   relayBatch: SELECT ... FOR UPDATE SKIP LOCKED, attempts++/next_attempt_at
   │   + signed event-bus outbox (event_bus_outbox, mig 128; V32)
   ▼   OutboxWorker.runOnce relays both; Kafka optional
RUN GUARD  run-guard.service.ts  checkHalt / assertCanContinue at every stage
   │   kill switch → autonomy.run_killed ;  budget → autonomy.run_budget_stop
   ▼
RESTART / RECOVERY  advisory lock re-acquired; claimed work resumes idempotently
```

## 3. Definitions

- **Leader election** — the advisory-lock mechanism ensuring a single active ticker
  (`pg_try_advisory_lock`, `civilization-scheduler.service.ts`,
  `civilization-os.service.ts`; `OS_ADVISORY_LOCK_KEY = 918273645`).
- **Scheduler tick** — one bounded coordination cycle
  (`civilization-scheduler.service.ts` `runOnce`; the C12 OS tick).
- **Durable execution** — enqueue/claim/dispatch of workflow tasks with a single
  `claim` transition (`durable-execution.service.ts`).
- **Transactional outbox** — event rows written in the same transaction as state and
  relayed asynchronously (`transactional-outbox.service.ts`, `event_outbox`,
  migration `083`).
- **Relay** — batched publication using `FOR UPDATE SKIP LOCKED` with attempt counting
  and `next_attempt_at` backoff (`relayBatch`).
- **Run guard** — the per-stage halt check honoring kill switch and budget
  (`run-guard.service.ts` `checkHalt`, `assertCanContinue`).
- **Outbox worker** — the process relaying both the event-log outbox and the signed
  event-bus outbox (`backend/src/workers/outbox-worker.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V3-INV-001 | Only one scheduler ticks at a time via a Postgres advisory lock, and re-running a tick never duplicates work — even across restarts. | enforced | `backend/src/services/civilization-scheduler.service.ts`, `backend/src/services/civilization-os.service.ts`, `backend/tests/civilization-scheduler.test.ts` |
| V3-INV-002 | A durable task is claimed exactly once (a single status transition to running) before it is dispatched. | enforced | `backend/src/services/durable-execution.service.ts`, `backend/tests/durable-execution-real-tasks.test.ts` |
| V3-INV-003 | Events are published through a transactional outbox written in the same transaction as the state change, so no state change is silently unpublished. | enforced | `backend/src/services/transactional-outbox.service.ts`, `backend/src/db/migrations/083_transactional_outbox.sql`, `backend/tests/outbox-worker.test.ts` |
| V3-INV-004 | Outbox relay sources work with FOR UPDATE SKIP LOCKED and retries failed publications with bounded attempts and backoff. | enforced | `backend/src/services/transactional-outbox.service.ts`, `backend/tests/outbox-worker.test.ts` |
| V3-INV-005 | Every autonomous run stage consults the run guard and halts when the kill switch is engaged or a budget stop is reached. | enforced | `backend/src/services/run-guard.service.ts`, `backend/tests/main-loop-kill-switch.test.ts` |
| V3-INV-006 | The signed event-bus outbox is relayed alongside the event-log outbox, so cross-service events carry integrity. | enforced | `backend/src/workers/outbox-worker.ts`, `backend/src/db/migrations/128_event_bus_outbox.sql`, `backend/tests/event-bus-outbox.test.ts` |
| V3-INV-007 | Task dispatch is idempotent under replay: a completed or in-flight task is not re-executed. | enforced | `backend/src/services/durable-execution.service.ts`, `backend/tests/idempotency-store.test.ts` |
| V3-INV-008 | On restart, in-flight work is recovered or safely re-claimed rather than lost or double-run. | planned | — |
| V3-INV-009 | A poison task that repeatedly fails is dead-lettered rather than retried unboundedly. | planned | — |

## 5. Interfaces

- **Scheduling** — `civilization-scheduler.service.ts` `runOnce`; the OS tick in
  `civilization-os.service.ts`; workers `civilization-scheduler-worker.ts`,
  `task-worker.ts`.
- **Durable work** — `durable-execution.service.ts` (`enqueue`, `get`, `list`, `run`,
  `claim`, `dispatch`).
- **Outbox** — `transactional-outbox.service.ts` (`relayBatch`),
  `backend/src/workers/outbox-worker.ts` (`runOnce` relays log + bus).
- **Halting** — `run-guard.service.ts`, `kill-switch.service.ts` (V1).
- **Supervised runtime** — `supervised-runtime.service.ts`,
  `supervised-free-run.service.ts` (bounded autonomous runs).

## 6. State

- **Outbox (migration `083`):** `event_outbox` (status, `next_attempt_at`, attempts).
- **Signed event bus (migration `128`):** `event_bus_outbox`.
- **Durable tasks:** `workflow_tasks` (durable execution).
- **Idempotency:** idempotency store (`backend/tests/idempotency-store.test.ts`).
- **Leader lock:** Postgres advisory lock `918273645` (no table; a runtime lock).
- **Halt signals:** kill-switch state (V1), budget state (V7).

## 7. Failure modes and responses

- **Split-brain scheduling** — the advisory lock guarantees a single active ticker, and
  re-running a tick is idempotent (V3-INV-001); a second scheduler simply fails to
  acquire the lock.
- **Lost events** — the transactional outbox writes the event in the state transaction
  and relays later, so a crash between state and publish cannot lose the event
  (V3-INV-003); relay is at-least-once with SKIP LOCKED and backoff (V3-INV-004).
- **Double execution** — a task is claimed with a single status transition and dispatch
  is idempotent under replay (V3-INV-002, V3-INV-007).
- **Runaway loop** — the run guard halts on kill switch or budget at every stage
  (V3-INV-005); the halt event is emitted even if other logging fails.
- **Lost in-flight work on restart** — recovery/re-claim of interrupted tasks is not yet
  an enforced invariant (V3-INV-008 planned; open question 1).
- **Poison tasks** — unbounded retry of a permanently failing task is not yet
  dead-lettered (V3-INV-009 planned; open question 2).

## 8. Verification obligations

Existing and green today: `backend/tests/civilization-scheduler.test.ts` (leader
election, idempotent tick), `backend/tests/durable-execution-real-tasks.test.ts`,
`backend/tests/outbox-worker.test.ts`, `backend/tests/event-bus-outbox.test.ts`,
`backend/tests/main-loop-kill-switch.test.ts`, `backend/tests/kill-switch.test.ts`,
`backend/tests/idempotency-store.test.ts`.

Must exist before the planned invariants flip: a restart-recovery test proving in-flight
work is re-claimed exactly once (V3-INV-008), and a dead-letter test for poison tasks
(V3-INV-009).

## 9. Implementation mapping

- `backend/src/services/civilization-scheduler.service.ts`,
  `backend/src/services/civilization-os.service.ts` — leader-elected ticking.
- `backend/src/services/durable-execution.service.ts` — durable task lifecycle.
- `backend/src/services/transactional-outbox.service.ts` — outbox relay.
- `backend/src/workers/outbox-worker.ts`, `task-worker.ts`,
  `civilization-scheduler-worker.ts` — the worker processes.
- `backend/src/services/run-guard.service.ts`, `kill-switch.service.ts` — halting.
- `backend/src/services/supervised-runtime.service.ts`,
  `supervised-free-run.service.ts` — bounded runs.
- Migrations: `083` (outbox), `128` (signed event bus).

## 10. Open questions

1. **Restart recovery is not proven.** The advisory lock ensures a single leader and
   claimed work is idempotent, but a test proving interrupted in-flight tasks are
   re-claimed exactly once after a crash is missing (V3-INV-008 planned). Scenario G
   (restart & replay) exercises replay at the civilization level; the durable-task
   recovery guarantee needs its own invariant.
2. **No dead-letter path.** A permanently failing task has bounded outbox retry, but a
   poison *task* (as opposed to a poison event) is not dead-lettered (V3-INV-009).
3. **Dual outbox.** The event-log outbox (migration `083`) and the signed event-bus
   outbox (migration `128`) are relayed together but remain two mechanisms; the frozen
   decision to keep both is recorded in `docs/civilization/CANONICAL_RUNTIME_MAP.md` (D2),
   and whether they converge is a Volume 19 (Structural Evolution) question.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 14) | Bind leader-elected scheduling, durable exactly-once-effect work, at-least-once transactional-outbox delivery, and kill-switch-honoring run guards into one citable runtime OS — the machinery that keeps the kernel (V2) alive and recoverable. |
