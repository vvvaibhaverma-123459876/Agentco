# Remediation 07: Cross-Version Civilization Evaluation

## Scope

Batch 07 executes the first governed paired cross-version comparison:

- Version A baseline: `fb27dc0529d3c5d11480503bfbcf6f2d156f5b04`
- Version B raw candidate: `651794a41513db1e40930f08c253ef261af7c1e7`
- Version C reconciled candidate: `81cd17431f826d9d3cda06b9127758751e44b798`

Version B remains preserved as the raw merge subject. Version C is the dedicated reconciliation commit.

## Reconciliation

Confirmed defect:

- duplicate migration numeric prefix `129` from independently developed longitudinal and civilization branches.

Remediation:

- `backend/src/db/migrate.ts` now stores `content_hash` and `sequence_num` in `schema_migrations`.
- `scripts/verify_migration_identity.py` generates and checks `MIGRATION_IDENTITY_LEDGER`.
- The duplicate `129` prefix has an explicit compatibility contract using full filenames as stable migration IDs.

## Campaign

- Campaign ID: `cross-version-civilization-v1`
- Benchmark registry hash: `3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e`
- Evaluator version: `longitudinal-evaluator-v1`
- Seeds: `101`, `202`, `303`, `404`, `505`
- Cases per seed: `24`
- Executions per subject: `120`

## Results

| Comparison | Paired cases | Improved | Regressed | Unchanged | Mean task-success delta |
|---|---:|---:|---:|---:|---:|
| A vs B | 120 | 5 | 5 | 110 | 0.0000 |
| A vs C | 120 | 5 | 0 | 115 | 0.0417 |
| B vs C | 120 | 5 | 0 | 115 | 0.0417 |

Latency/resource disclosure:

- Version B and C carry the civilization-layer overhead in this deterministic harness: `+2 ms` latency and `+0.1` resource units versus Version A.
- B versus C has no latency/resource delta.

## Civilization Claims

C1-C11 are mostly unit-verified by focused backend tests. C12, C13 and C15 remain not implemented. C14 is partial because hosted staging remains blocked.

## Decision

Decision: `PROMOTION_PROPOSAL` for Version C.

This is not automatic promotion, deployment, hosted evidence, production evidence, weekly evidence or mission-completion proof.

## Remaining Limitations

- The campaign is deterministic local evidence.
- No full hosted staging execution.
- No scheduled weekly observation window.
- No four-week or twelve-week longitudinal evidence.
- Civilization runtime workflows need deeper registered-route and worker-level E2E coverage in a future batch.
