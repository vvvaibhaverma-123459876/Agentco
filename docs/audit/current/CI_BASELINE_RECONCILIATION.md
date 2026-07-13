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
