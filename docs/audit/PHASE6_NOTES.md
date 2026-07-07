# Phase 6 Notes — V1 Retirement and Post-Merge Verification

## Task 1 — Chain Seam Verification

Verdict: full-chain verification recomputes historical `decision_log` entry hashes, and versioned verification was needed for the Phase 5 canonicalization seam.

What the verifier does:

- `backend/src/services/audit-log.service.ts::verifyChainIntegrity()` selects all rows with 64-character hex `chain_hash` and `prev_hash`.
- It walks oldest to newest (`ORDER BY timestamp ASC, log_id ASC`).
- It recomputes each row hash as `SHA-256(prev_hash || serialized_row_content)` and compares it with the stored `chain_hash`.

Phase 5 already accepted two serialization buckets:

- `v2.sorted-json`: sorted-key compact JSON, the current TypeScript/Python writer contract.
- `v1.ts-insertion-json`: TypeScript `JSON.stringify(fields)` insertion order, the pre-Phase-5 TypeScript writer contract.

Phase 6 added the missing legacy Python bucket:

- `v1.python-insertion-json`: Python insertion-order compact JSON with the original `datetime.now(timezone.utc).isoformat()` timestamp shape.

Implementation note: the verifier now selects `timestamp::text AS timestamp_text`. That preserves Postgres microseconds, which JavaScript `Date` would otherwise truncate to milliseconds. The Python legacy timestamp is reconstructed from Postgres text before hashing.

Verification:

```text
npm test -- audit-chain-cross-writer.test.ts --runInBand
PASS tests/audit-chain-cross-writer.test.ts
  ✓ verifier accepts legacy Python insertion-order rows across the canonicalization seam
  ✓ TS -> Python -> TS entries verify as one chain
```

Full local chain probe:

```json
{
  "span": {
    "count": 2790,
    "min_ts": "2026-07-05 10:28:35.455+05:30",
    "max_ts": "2026-07-07 09:12:54.679+05:30"
  },
  "verification": {
    "valid": true
  }
}
```

## Task 2 — Suite Delta Accounting

Baseline compared: `7f89f10` (`fix(auth): phase4 remove method-based preflight bypass`), the commit immediately before the Phase 5 merge stack.

Commands:

```text
python3.13 -m pytest -q --junitxml=/private/tmp/agentco-pre-phase5-pytest.xml
python3.13 -m pytest -q --junitxml=/private/tmp/agentco-current-pytest.xml
```

Observed counts in this environment:

| run | passed | skipped | failed | errors |
|---|---:|---:|---:|---:|
| pre-Phase-5 `7f89f10` | 511 | 39 | 6 | 16 |
| Phase 6 after reserve DSN fix | 511 | 43 | 6 | 1 |

Note: the prompt remembered `492/47/10/23 -> 512/39/5/16`. The rerun on July 7, 2026 did not reproduce those exact counts. In both old and new runs, `tests/test_specialist_agent.py::TestResearcherAgent::test_fetch_page_action` failed because the page fetch returned `failed`, so it is not a Phase 5/6 delta in this environment.

Changed test states:

| test id | old -> new | cause |
|---|---|---|
| `reserve/tests/test_agent_reserve_integration.py::test_agent_earns_reserve_credential_from_real_predictions` | error -> not-collected | env / DSN guard fix: module now skips before `psycopg2.connect(None)` can default to OS database |
| `reserve/tests/test_oracle_layer.py::test_oracle_resolves_prediction_and_records_standing` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_oracle_layer.py::test_higher_authority_oracle_contradicts_lower` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_oracle_layer.py::test_mechanical_ground_truth_contradicts_oracle_and_docks_standing` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_oracle_layer.py::test_unqualified_agent_cannot_act_as_oracle` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_oracle_layer.py::test_write_trace` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_proof_of_calibration.py::test_deterministic_scoring_recomputes_identically` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_proof_of_calibration.py::test_two_agents_with_different_track_records_produce_different_credentials` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_proof_of_calibration.py::test_fresh_agent_has_neutral_low_standing` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_proof_of_calibration.py::test_write_trace` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_staking_and_decisions.py::test_weighted_decision_follows_credential_weight` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_staking_and_decisions.py::test_sybil_identities_have_zero_weight` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_staking_and_decisions.py::test_stake_is_write_once` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_staking_and_decisions.py::test_collusion_resistance_property_audit_values` | error -> not-collected | env / DSN guard fix |
| `reserve/tests/test_staking_and_decisions.py::test_write_trace` | error -> not-collected | env / DSN guard fix |
| `reserve.tests.test_agent_reserve_integration` | not-collected -> skipped | env / DSN guard fix: module-level skip with explicit message |
| `reserve.tests.test_oracle_layer` | not-collected -> skipped | env / DSN guard fix: module-level skip with explicit message |
| `reserve.tests.test_proof_of_calibration` | not-collected -> skipped | env / DSN guard fix: module-level skip with explicit message |
| `reserve.tests.test_staking_and_decisions` | not-collected -> skipped | env / DSN guard fix: module-level skip with explicit message |

Unknown entries: 0.

Reserve DSN finding and fix:

- Finding: four reserve live-service modules caught isolation/connectivity failures by setting `DSN = None`, then later called `psycopg2.connect(DSN)`. Libpq treats `None` like no DSN and falls back to defaults, including the OS username database (`Zet` locally).
- Fix: `reserve/tests/dsn.py::reserve_test_dsn()` centralizes reserve DSN resolution. It returns an isolated explicit DSN or raises a clear refusal before any test can call `psycopg2.connect(None)`.
- The affected modules now skip at module collection with that explicit reason when reserve Postgres is unavailable.

Verification:

```text
python3.13 -m pytest reserve/tests/test_agent_reserve_integration.py reserve/tests/test_oracle_layer.py reserve/tests/test_proof_of_calibration.py reserve/tests/test_staking_and_decisions.py -q
4 skipped in 0.06s
```
