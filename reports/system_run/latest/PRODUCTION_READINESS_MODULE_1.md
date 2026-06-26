# Production Readiness Module 1

Date: 2026-06-26

## Scope

Closed blocker: goal-run audit/event/ledger persistence was file-backed. It is now DB-backed for live runs.

## Result

`COMPLETE_FOR_LOCAL_NATIVE_VERIFICATION`

The live goal-run verifier now:

- pre-registers a UUID prediction in `prediction_ledger`
- writes all verifier events to `event_history`
- writes a hash-chained decision record to `decision_log`
- resolves the prediction through the `resolution_service` DB role
- records DB persistence metadata in `goal_run.json`
- fails rather than silently downgrading live DB-backed runs to file-only output

Offline fixture mode remains file-backed and explicitly simulated.

## Evidence

Commands run:

```text
python3.13 -m pytest tests/test_verify_agentco_goal_run.py runtime/orchestration/tests -q
python3 scripts/verify_openai_connectivity.py
python3 scripts/verify_agentco_goal_run.py
make doctor-production
```

Results:

| Check | Result |
|---|---|
| verifier/orchestration tests | 16 passed |
| OpenAI connectivity | success, `gpt-4o-mini` |
| live goal-run | success, `simulated=false` |
| audit persistence | `db_backed` |
| DB event rows | 11 |
| DB decision-log rows | 1 |
| prediction resolved | true |
| production doctor | fail-closed on secret posture |

Artifacts:

| Artifact | Evidence |
|---|---|
| `reports/system_run/latest/goal_run.json` | includes `db_persistence.prediction_resolved=true` |
| `reports/system_run/latest/performance_summary.json` | includes `db_event_records=11`, `db_decision_log_records=1` |
| `reports/system_run/latest/doctor_report.json` | production services real, blocked only by dev/missing production secrets |

## Remaining Production Blockers

1. Production secret posture is still blocked: `AGENTCO_API_KEY`, `EVENT_BUS_HMAC_KEY`, `EVENT_BUS_SIGNING_KEY`, `JWT_SECRET`, `VAULT_TOKEN`, and test DB secret posture must be real/non-default.
2. Local Vault is dev-mode and must not be claimed as production Vault.
3. Specialist workers still use Flask development serving in tests.
4. North-star benchmark is still deterministic smoke/skeleton, not a real cross-domain generality measurement.
5. Live web/source discovery remains dependent on external APIs and can fail closed.
