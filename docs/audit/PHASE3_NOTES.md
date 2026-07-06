# Phase 3 Notes

## Task 1 — Firewall In-Memory Authority Model

### Direct `validation_status` Writes

Grep command:

```bash
rg -n "validation_status\s*=|SET\s+validation_status|validation_status\s*:\s*str|validation_status\s*TEXT|validation_status\s+VARCHAR|validation_status" --glob '!evals/experiments/**' --glob '!*.csv' --glob '!node_modules/**' --glob '!*__pycache__/**'
```

Meaningful direct write hits:

| File:line | Classification | Finding |
|---|---|---|
| `calibration/firewall/firewall.py:35` | firewall itself | `Belief.validation_status` is a public dataclass field. This is the in-memory hole. |
| `calibration/firewall/firewall.py:85` | firewall itself | Simulation support advances `provisional` to `simulation_supported`. Legitimate transition. |
| `calibration/firewall/firewall.py:171` | firewall itself | `promote_to_reality_validated()` sets `reality_validated`. Legitimate transition. |
| `calibration/firewall/firewall.py:193` | firewall itself | `retire()` sets `retired`. Legitimate transition. |
| `calibration/decay/decay_tracker.py:75` | production code outside firewall | Directly demotes expired `reality_validated` beliefs to `provisional`. Must route through a firewall method. |
| `evals/regression/test_v2_regression.py:408` | test code | Strict xfail probe directly mutates cached status. Must flip to a passing test asserting assignment raises. |
| `synthesis/principle_library/principle_library.py:91` | production code, not Belief | Directly mutates `Principle.validation_status`, a different dataclass. Not part of the firewall `Belief` authority model. |
| `tests/integration/test_resolution_service_role_migration.py:329` | test code, DB layer | Executes raw SQL `SET validation_status = 'reality_validated'` to prove DB trigger rejection. Keep. |

Other hits are reads, dict serialization of `"validation_status": "provisional"`, type declarations, generated reports, docs, or tests asserting status.

### Authority Model

The Python firewall is an in-memory authority for the calibration engine when
`create_calibration_engine()` is called without a DB-backed belief repository.
`RealitySimulationFirewall.__init__()` stores beliefs in `self._beliefs:
dict[str, Belief]`; no code in `calibration/firewall/firewall.py` persists or
rehydrates those objects.

The repository also has a DB-backed authority model for backend/runtime flows:
`backend/src/db/migrations/010_beliefs.sql` creates a `beliefs` table with
`validation_status`, `sim_support_count`, and `reality_prediction_ids`. The same
migration states:

> ONLY promote_to_reality_validated() (called by ResolutionService) may set reality_validated.

and:

> No simulation volume can write reality_validated. Enforced by trigger.

The trigger `enforce_reality_firewall()` blocks SQL updates to
`reality_validated` unless `current_user = 'resolution_service'`.

Conclusion: the DB layer has a role gate for SQL promotion, but Task 1's hole is
in the Python in-memory authority. The correct fix is to make
`Belief.validation_status` read-only from outside the firewall and expose
firewall-owned transition methods. No new DB migration is required for this
specific in-memory hole.

## Task 2 — Durable BaseAgentV2 Audit Writer Investigation

### Existing Audit Infrastructure

Candidate durable audit targets:

| Artifact | Finding |
|---|---|
| `backend/src/db/migrations/004_decision_log.sql` | Creates `decision_log` and says: "This is the legal and governance record of every decision in AgentCo." |
| `backend/src/db/migrations/012_decision_log_chain.sql` | Adds `chain_hash` and `prev_hash`; comment says the table is hash-chained and DB update revocation enforces immutability. |
| `backend/src/db/migrations/014_decision_log_immutability_triggers.sql` | Adds triggers rejecting `UPDATE` and `DELETE`, including table-owner/superuser bypass protection unless triggers are explicitly disabled. |
| `backend/src/services/audit-log.service.ts` | Canonical TS writer. It writes to `decision_log`, computes `prev_hash`/`chain_hash`, and rethrows failures. |
| `agents/core/tools/handlers.py` | Existing Python V1 audit tool also writes to `decision_log`, but with weaker canonical hashing and no writer interface. |
| `backend/src/db/migrations/080_event_log.sql` + `083_transactional_outbox.sql` | Canonical event stream/outbox, but it is a broader event bus rather than the legal/governance decision audit record. |

Decision: `DurableAuditWriter` should write directly to `decision_log` using the
same schema as the TS `AuditLogService`. This avoids a second table, keeps Python
V2 audits visible in the existing governance audit log, and reuses the DB
append-only/hash-chain controls. `event_log`/`event_outbox` remain eventing
infrastructure, not the primary decision audit ledger.

### Fail-Closed Semantics

`BaseAgentV2` currently appends `AuditEntryV2` objects to `self._audit_log`, so
process restart loses audit history. Phase 3 changes this to constructor-injected
`AuditWriter`:

- `DurableAuditWriter`: selected by default when `AGENTCO_TEST_DATABASE_URL` or
  `DATABASE_URL` is configured.
- `InMemoryAuditWriter`: test-only; construction requires an explicit test flag.
- No configured writer: low/medium actions may execute with visible error
  accounting; high/critical actions raise `AuditUnavailableError` before action
  execution.
- For high/critical actions that clear the human-approval gate, durable audit ack
  must be written before the signed action envelope is returned.
