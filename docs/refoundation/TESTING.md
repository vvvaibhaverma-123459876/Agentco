# Testing

Status: **PARTIAL**.

## Current Commands

```bash
python3 -m pytest calibration runtime learning synthesis evals/regression -q
```

Observed 2026-06-21 before sandbox DB denial: **115 passed**.

```bash
make smoke
```

Runs the no-infra Python smoke slice and TypeScript checks when `node_modules` exists. The smoke target intentionally excludes DB-backed Postgres ledger tests; those belong in the real-infrastructure gate.

Observed 2026-06-21 after Gates 15-17 additions: **139 passed** and backend/frontend TypeScript checks passed.

```bash
cd backend && npm run build
cd frontend && npm run build
```

Observed 2026-06-21: both builds passed. The previous frontend hook warning in `src/app/audit/page.tsx` is fixed.

```bash
python3 -m pytest evals/regression/test_pg_ledger_immutability.py evals/regression/test_pg_ledger_persistence.py -q
```

Runs the Postgres ledger persistence/immutability checks when local DB access is available.

## Blocked In This Sandbox

Initial backend and frontend TypeScript checks could not run because `node_modules` was missing and network access to npm was restricted. After approved `npm ci`, both TypeScript checks passed.

Postgres ledger tests passed after approved local-Postgres access:

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco \
  python3 -m pytest evals/regression/test_pg_ledger_immutability.py evals/regression/test_pg_ledger_persistence.py -q
```

Durable execution smoke against local Postgres produced `status=done`, `kind=health_check_result`, and `attested=true`. The process was interrupted after output because KafkaJS kept a producer handle open.

Full master gate:

```bash
make master-gate
```

Observed 2026-06-21: passed. It ran smoke tests, validation report generation, backend build, and frontend build.

## Future Gate Commands

Gates 0-17 are wired into the deterministic repo master gate. Live third-party benchmark connectors remain future hardening.
