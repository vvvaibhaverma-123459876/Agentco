# CI Baseline Reconciliation

Batch: 03 runtime architecture and integration  
Base run: `29238640790`  
Base SHA: `b663f7a51ec75e04590b4361c8ef92c323251ef3`

## Failed Jobs

| Job | Result | Root cause | Correction |
| --- | --- | --- | --- |
| Secret scan | Failed | Inline regex matched fixture task IDs such as `task-negative-unsupported` because it searched for `sk-` followed by only 20 URL-safe characters. | Replaced inline shell regex with `scripts/scan_committed_secrets.py`, which requires materially longer OpenAI-key-shaped tokens and excludes documented non-runtime surfaces. |
| Python Agent Tests | Failed | CI ran `cd agents && pytest tests/ ...`, bypassing governed skip/audit setup used by `release-gate`; V2 tests requiring audit writers failed with `AuditUnavailableError`. | CI now runs the governed pytest wrapper from repository root. |
| TypeScript Backend Tests | Failed | CI ran backend tests without Python dependencies and without Kafka, while specialist spawning and Kafka-backed tests are runtime-coupled. | CI now installs Python dependencies, sets `PYTHONPATH`/`AGENTCO_PYTHON`, and provisions Kafka/Zookeeper for backend tests. |
| Release Credibility Gate | Failed | Pull-request checkout used the synthetic merge commit; generated README status was current for branch HEAD but stale for the merge commit. | CI checkout now pins to `${{ github.event.pull_request.head.sha || github.sha }}` so evidence SHA matches the audited branch commit. |

## Evidence Extracted

- `Secret scan` log reported `runtime/evaluation/benchmark.py:57` and `:82` as false-positive secret matches.
- `Python Agent Tests` log reported 18 failures, all rooted in `runtime.base_agent.audit_writer.AuditUnavailableError: No audit writer configured`.
- `TypeScript Backend Tests` log reported specialist spawn failures and Kafka connection failures.
- `Release Credibility Gate` log failed at `README.md status block is stale` while running against PR merge commit `34f56ed...`, not branch HEAD.

Raw logs were downloaded to `/private/tmp/agentco-ci-29238640790/`.

## Local Reproduction

The branch-head checks that replace the divergent CI paths are:

```text
python3.13 scripts/scan_committed_secrets.py --check
python3.13 scripts/verify_pytest_skips.py --report artifacts/ci/python-pytest-report.json --summary-output artifacts/ci/python-pytest-summary.json -- -q
make release-gate
make audit-clean-room
make audit-runtime-integration
```

## Final Conclusion

The base CI failure was a CI-command convergence defect plus one secret-scan false positive, not proof that the clean-room evidence was invalid. Batch 03 keeps general CI active and aligns it with governed verification commands instead of disabling failed jobs.

## Replacement-Run Corrections

The first Batch 03 replacement run on branch `audit/remediation-03-runtime-architecture-integration` exposed three additional CI-only defects:

| Job | Error | Root cause | Correction |
| --- | --- | --- | --- |
| Python Agent Tests | `FileNotFoundError: [Errno 2] No such file or directory: 'rg'` from `scripts/generate_runtime_reachability.py` | The reachability generator assumed ripgrep was installed on the GitHub runner. Local development had `rg`; the runner did not. | `scripts/generate_runtime_reachability.py` now uses `rg` when available and falls back to a Python regex scan over the same active source roots. |
| Python Agent Tests | `SKIP_REASON_MISMATCH` for live Postgres `decision_log` tests | General CI did not provision or migrate PostgreSQL for the Python job, while the governed skip policy correctly treats database-backed tests as runnable when clean local infrastructure is present. | The Python job now provisions PostgreSQL, installs backend migration dependencies, runs migrations, and sets both `DATABASE_URL` and `AGENTCO_TEST_DATABASE_URL`. |
| Release Credibility Gate | `README.md status block is stale` | `actions/checkout` used the default shallow clone. `scripts/generate_status.py` needs `git log -- BUILD_LEDGER.yaml`; with depth `1`, the ledger commit rendered as `unknown`. | CI checkout steps now use `fetch-depth: 0` so history-dependent provenance checks produce the same status block as local verification. |

These were corrected without disabling jobs, adding skips, masking exit codes, or changing release-gate assertions.

The second Batch 03 replacement run exposed two remaining CI-only database
contract defects:

| Job | Error | Root cause | Correction |
| --- | --- | --- | --- |
| Python Agent Tests / Release Credibility Gate | `FATAL: password authentication failed for user "resolution_service"` in `evals/regression/test_pg_ledger_immutability.py` | The test legitimately connects as `resolution_service` with password `test`, but the CI migration command did not set `RESOLUTION_SERVICE_PASSWORD`, so migration `124_prediction_resolution_service_role.sql` created the role with the backend development default password. Clean-room already set this variable, so the defect was CI drift. | General CI now sets `RESOLUTION_SERVICE_PASSWORD=test` anywhere it runs migrations or governed tests against the CI database. |
| Release Credibility Gate | `psycopg2.errors.InsufficientPrivilege: permission denied for schema public` in `runtime/tests/test_runtime_durable_governance_stores.py` | The release gate correctly runs runtime tests as least-privileged role `agentco_gate`, but the durable-store test replayed migration DDL using the runtime DSN instead of treating schema setup as migration/admin work. | The test now first checks whether the runtime governance tables already exist. If schema setup is required, it uses `RELEASE_GATE_MIGRATION_DATABASE_URL` or `RELEASE_GATE_SETUP_DATABASE_URL`; the persistence assertions still run through the runtime DSN. |

These corrections preserve the Phase 7.5 least-privilege split: migration/admin
credentials are used only for schema setup, while runtime tests continue to use
the non-owner role.
