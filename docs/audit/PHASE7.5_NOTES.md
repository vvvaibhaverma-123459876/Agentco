# Phase 7.5 - Release Gate Privilege Correctness

## Task 1 - Teardown intent verdict

Verdict: **(a) Postgres system FK-trigger cleanup convenience**. The failing
teardown disables all triggers on `prediction_ledger` only to delete the e2e
test row after it has been inserted through the legitimate runtime path. It is
not bypassing AgentCo prediction-ledger write-once or ordering triggers.

Failing teardown, `agents/tests/integration/test_agent_dispatch_e2e.py`:

```python
cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL")
cur.execute("DELETE FROM prediction_ledger WHERE producing_agent_id=%s", ("e2e-dispatch-agent",))
cur.execute("ALTER TABLE prediction_ledger ENABLE TRIGGER ALL")
```

The test setup and assertions use the real path:

```python
pid = agent.pre_register_claim(...)
```

The AgentCo prediction-ledger triggers involved are update-only integrity
triggers:

- `backend/src/db/migrations/011_prediction_ledger.sql` creates
  `prediction_ledger_immutability BEFORE UPDATE ON prediction_ledger`.
- `backend/src/db/migrations/095_prediction_ledger_reserve_fields_compatibility.sql`
  creates `trg_reserve_fields_immutable BEFORE UPDATE ON prediction_ledger`.
- `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`
  replaces the same immutability function and still enforces it on update.

Those triggers do not block `DELETE`. The privilege failure comes from
`ALTER TABLE ... DISABLE TRIGGER ALL`, which includes Postgres system RI
constraint triggers. The live FK found in the migration stream is
`backend/src/db/migrations/118_contradictions_and_demotions.sql`:

```sql
prediction_id UUID REFERENCES prediction_ledger(prediction_id)
```

Therefore the fix should use privilege-safe cleanup: delete dependent
`contradictions` rows first, then delete this test's `prediction_ledger` rows.
No trigger disabling is justified for `prediction_ledger`.

## Task 3 - Least-privilege gate findings

Structural fix:

- `scripts/setup_release_gate_role.sql` creates/updates a dedicated
  `agentco_gate` login role.
- The role is explicitly `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION`.
- Grants are limited to `CONNECT`, `USAGE ON SCHEMA public`,
  `SELECT/INSERT/UPDATE/DELETE ON ALL TABLES IN SCHEMA public`, and sequence
  usage/update. It does not receive ownership, superuser, or table-owner-only
  privileges such as disabling system triggers.
- `make release-gate` now separates:
  - `RELEASE_GATE_MIGRATION_DATABASE_URL`: schema-owner/admin DSN for applying
    migrations;
  - `RELEASE_GATE_SETUP_DATABASE_URL`: schema-owner/admin DSN for refreshing
    the gate role grants after migrations;
  - `RELEASE_GATE_DATABASE_URL`: low-privilege DSN used by the Python and
    backend verification suites.

Local setup note: the existing local `agentco` role owns normal app access but
does not have `CREATEROLE`, so it correctly cannot run the role setup script:

```text
ERROR: permission denied to create role
DETAIL: Only roles with the CREATEROLE attribute may create roles.
```

The local admin role is `Zet` (`rolsuper=true`, `rolcreaterole=true`) and was
used only to create/update `agentco_gate`; the gate itself must run as
`agentco_gate`.

Least-privilege gate failures:

- `agents/tests/integration/test_agent_dispatch_e2e.py`: teardown attempted
  table-owner trigger disabling on both `prediction_ledger` and `decision_log`.
  Fixed by ordered FK-safe cleanup for `prediction_ledger` and by leaving
  append-only `decision_log` evidence intact.
- Python destructive schema fixtures under `evals/regression/`, `reserve/tests/`,
  and `tests/civilization/`: fixtures used `AGENTCO_TEST_DATABASE_URL` for
  `DROP TABLE`/migration setup. Fixed by deriving isolated destructive fixture
  databases from `RELEASE_GATE_MIGRATION_DATABASE_URL` when present.
- `runtime/tests/test_spend_guardrail_ledger.py`: applied resource-ledger
  migrations through the app DSN. Fixed by using the migration DSN for setup
  while the ledger under test still uses the app DSN.
- Backend migration helpers in 30+ Jest suites: applied SQL migrations through
  the app `db` pool. Fixed with `backend/tests/support/migration-db.ts`, which
  is fed by `RELEASE_GATE_MIGRATION_DATABASE_URL`; service/runtime queries keep
  using the low-privilege `db` pool.
- Backend cleanup using `TRUNCATE`: ordinary app cleanup in `action-loop` was
  replaced with ordered `DELETE`; append-only/chain fixture resets were moved
  to the migration pool.
- `backend/tests/integration/memory-store.test.ts`: low-privilege app inserts
  hit `agent_memory` RLS. Fixed by adding a role-specific RLS policy for the
  gate role in `scripts/setup_release_gate_role.sql`, rather than granting
  owner/superuser privileges.
- `backend/tests/team-activation.test.ts`: `TRUNCATE` first failed due missing
  app `TRUNCATE`, then `DELETE FROM autonomy_goals` hit the append-only delete
  trigger. Fixed by using migration-pool fixture reset; service writes still use
  the app pool.
- `backend/tests/action-loop.test.ts`: ordered app cleanup initially missed
  `disputes`, whose FK restricts claim deletion. Fixed by deleting `disputes`
  before `autonomy_claims`.
- `backend/tests/civilization-runtime-live-e2e.test.ts`: not a privilege issue;
  full-suite state bleed from a fixed domain let the runtime resolve older
  overdue predictions first. Fixed with a unique domain per test module.
- `backend/tests/action-loop.test.ts`: full backend runs exposed another
  privilege-safe cleanup ordering bug after prior runs left judiciary rows.
  `precedents` references `rulings`, and `rulings` references `disputes`, so
  app-role cleanup now deletes `precedents`, then `rulings`, then `disputes`.
- `backend/tests/institutional-synthesis.test.ts`: not a privilege issue;
  full-suite runs exposed nondeterministic row ordering for contributing claim
  IDs and work-cycle phases. Assertions now compare sets where the contract is
  membership, not order.
- `backend/tests/contradiction-learning-e2e.test.ts`: not a privilege issue;
  retrieval used the shared `autonomy_research` domain and could be outranked by
  old full-suite memories. The test now uses a unique domain tied to its marker.
- Backend Jest open handles: the full suite was green but did not exit because
  Kafka producers remained connected in test environments that publish events.
  Fixed by adding `backend/tests/setup-after-env.ts`, which disconnects the
  Kafka producer after each Jest test file; direct Kafka-producing suites also
  keep explicit cleanup.
