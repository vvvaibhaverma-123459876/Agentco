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

Pending full gate run.
