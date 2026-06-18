# Civilization Layer — Migration Map

## Infrastructure facts (from repo audit)

| Item | Value |
|---|---|
| Highest backend migration | `014_decision_log_immutability_triggers.sql` |
| Highest reserve migration | `005_prediction_chain.sql` |
| Civilization migration number | `006_civilization.sql` (reserve/migrations/) |
| Migration runner | `npm run db:migrate` → `node -e "require('./dist/db/migrate.js')"` (TS/Node, backend only). Python reserve migrations applied directly in test fixtures via `cur.execute(sql_text)`. |
| Test DB DSN env var | `AGENTCO_TEST_DATABASE_URL` (primary) / `DATABASE_URL` (agents e2e) |
| Default DSN | `postgresql://agentco:password@localhost:5433/agentco?host=/tmp` |
| DB connection pattern | `psycopg2.connect(DSN); conn.autocommit = True` |
| Fixture pattern | module-scope `db()` fixture; drops/creates tables; `yield conn`; teardown drops |
| Base agent class | `BaseAgentV2` in `runtime/base_agent/base_agent_v2.py` |
| Domain model style | Python `@dataclass` (no ORM, no SQLAlchemy) |
| Audit-log trigger pattern | `BEFORE UPDATE OR DELETE … RAISE EXCEPTION '…is append-only…'` |

## Existing file → civilization role → required change

| Existing file | Current responsibility | Civilization role | Required change |
|---|---|---|---|
| `calibration/ledger/prediction_ledger.py` | Stores agent predictions | **Source of agent scores** fed into department/institution propagation | Read-only from civilization layer; no change needed |
| `reserve/scoring/scoring_function.py` | Computes ReserveScore per agent | **Leaf score supplier** for reputation propagation | No change; civilization calls `score_agent()` |
| `reserve/credentials/proof_of_calibration.py` | Issues/verifies credentials | **Verifiable reputation input** at agent level | No change; civilization reads `overall_log_score` from credential |
| `reserve/chain/commitment_chain.py` | Tamper-evident prediction chain | **Foundation gate G3** | No change |
| `runtime/base_agent/base_agent_v2.py` | Agent base class | **Entity that joins departments via `agent_membership_edges`** | Add optional `institution_id` / `department_id` awareness (Phase 7 only) |
| `reserve/migrations/` | Reserve DB schema | **Civilization migrations live here** (same fixture pattern) | Add `006_civilization.sql` |
| `agents/tests/integration/` | Agent e2e tests | **Pattern for civilization e2e test** | Add `tests/e2e/test_institution_operating_loop.py` |

## New directories/files to create

```
civilization/
  __init__.py
  contracts/                        # YAML contract per institution
    engineering.yaml
    security.yaml
  domain/
    __init__.py
    entities.py                     # Institution, Department dataclasses
    membership.py                   # AgentMembershipEdge dataclass
  services/
    __init__.py
    institution_service.py          # create_institution(), factory
    review_service.py               # review state machine
    reputation_service.py           # propagation formula
    governance_service.py           # governance decisions
    memory_service.py               # civilization_memory_events queries
  controls.yaml                     # anti-chaos controls
  reputation_weights.yaml           # department weights

reserve/migrations/
  006_civilization.sql              # all civilization tables

docs/
  SYSTEM_CIVILIZATION.md            # honest capability statement

tests/
  e2e/
    test_institution_operating_loop.py   # Phase 7 end-to-end
  civilization/
    test_migration.py               # T3.1–T3.4
    test_review_state_machine.py    # T5.1–T5.2
    test_reputation_propagation.py  # T5.3–T5.4
    test_governance.py              # Phase 6 tests
    test_contract_validation.py     # Phase 4 tests
```

## Constraints observed (no conflicts found)

- Backend migrations (001–014) are TypeScript/Node-applied; civilization tables go into the same Postgres DB but are applied by the Python fixture pattern (consistent with reserve/ migrations 001–005).
- `prediction_ledger` columns `hardness`, `consequence`, `ed25519_signature` all exist; civilization reads them via `score_agent()`.
- No existing table named `institutions`, `departments`, or `civilization_memory_events` — no collision.
- `decision_log` audit-log service is TypeScript (`backend/src/services/audit-log.service.ts`); governance audit entries are written via Python psycopg2 INSERT directly into `decision_log` (same table, same pattern as audit-log.service.ts rows — compatible).
