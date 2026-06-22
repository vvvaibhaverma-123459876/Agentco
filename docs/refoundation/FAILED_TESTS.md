# Failed / Blocked Tests

Audit date: 2026-06-21.

| Command | Result | Status |
|---|---|---|
| `python3 -m pytest calibration runtime learning synthesis evals/regression -q` | 115 passed earlier in session; later DB-backed tests errored under sandbox localhost denial | **MIXED** |
| `make smoke` before excluding DB-backed ledger tests | 107 passed, 8 Postgres connection errors | **BROKEN environment/infra** |
| `make smoke` after no-infra update | 107 passed; Node checks skipped because `node_modules` missing | **PARTIAL** |
| `npx tsc --noEmit` in `backend` | failed before typecheck: attempted npm registry access for `tsc`; network unavailable | **BROKEN environment/deps** |
| `npx tsc --noEmit` in `frontend` | failed before typecheck: attempted npm registry access for `tsc`; network unavailable | **BROKEN environment/deps** |
| local `backend/node_modules/.bin/tsc` | unavailable | **MISSING deps** |
| local `frontend/node_modules/.bin/tsc` | unavailable | **MISSING deps** |
| `cd backend && ./node_modules/.bin/tsc --noEmit` after `npm ci` | passed | **REAL** |
| `cd frontend && ./node_modules/.bin/tsc --noEmit` after `npm ci` | passed | **REAL** |
| `cd backend && npm run build` | passed | **REAL** |
| `cd frontend && npm run build` | passed with one lint warning in `src/app/audit/page.tsx` | **REAL** |
| `cd frontend && npm run build` after hook fix | not rerun yet | **PENDING** |
| `cd frontend && npm run build` after hook fix | passed without the previous hook warning | **REAL** |
| DB-backed ledger tests after local Postgres approval | 8 passed | **REAL** |
| Gate 3 durable execution smoke | produced attested done task, then was interrupted because KafkaJS kept the process open | **REAL with cleanup caveat** |
| `make master-gate` | passed | **REAL** |
