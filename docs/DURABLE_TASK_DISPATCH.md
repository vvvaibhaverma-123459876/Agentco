# Durable Task Dispatch

## Implemented

- `backend/src/db/migrations/018_agent_tasks.sql` adds durable `agent_tasks` and append-only `agent_task_events`.
- `backend/src/services/task-dispatch.service.ts` creates, reads, lists, cancels, leases, completes, fails, and dead-letters tasks.
- `backend/src/routes/agents.routes.ts` now dispatches tasks into Postgres instead of an in-memory queue.
- Task status and list endpoints read from the DB.
- `backend/src/workers/task-worker.ts` leases one task and completes it with explicit `executor_mode: durable_placeholder`.

## Tested

- Backend unit tests cover durable insert/event append, DB-backed reads, cancellation, lease query semantics, and absence of `taskQueue` in the agents route.

## Not Implemented

- Real Python runtime execution is not wired into the worker.
- Worker integration with live audit/event bus infrastructure was not run in this pass.
- Postgres integration tests for leasing/retry/dead-letter were not added in this pass.

## Future Work

- Wire the worker to the real Python runtime.
- Add Postgres integration tests for lease reclaim, retries, dead-letter, audit id, and task events.
- Add operational worker process management.

Run current backend tests:

```bash
cd backend && npm test -- task-dispatch.test.ts
```
