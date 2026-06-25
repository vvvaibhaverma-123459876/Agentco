# AgentCo Goal Run Verification

- Run ID: `goal-run-20260625T094154Z-ac2100e8`
- Mode: `simulated_offline`
- Decision: `escalate`
- Risk: `medium`
- Confidence: `0.64`
- Trusted confidence: `0.4925`
- Passed validation: `True`
- Brier score: `0.1296`
- Latency ms: `307.03`

## Validation Checks

- `decision_is_expected`: `True`
- `risk_level_medium`: `True`
- `confidence_in_range`: `True`
- `cites_required_evidence`: `True`
- `all_citations_known`: `True`
- `does_not_confirm_soc2_type2`: `True`
- `does_not_conflate_breach`: `True`
- `requests_soc2`: `True`
- `requests_signed_dpa`: `True`
- `requests_subprocessors`: `True`
- `requires_human_escalation`: `True`
- `passed`: `True`

## Database Trail

- `prediction_ledger_insert`: ok id=`f9ee80d6-fe77-40d9-ae64-f81365f835d8`
- `prediction_ledger_resolution_update`: ok
- `legacy_prediction_resolution_insert`: ok id=`goal-run-92e7f7f68add`
- `trust_scores_insert`: ok id=`29ae87d6-d767-40f5-9aa2-06cc46b84b6d`
- `event_history_insert`: ok id=`5d8e8952-b719-466a-9a09-ed3983f77225`
- `decision_log_insert`: ok
- `autonomy_audit_events_insert`: ok
- `autonomy_memory_learning_insert`: ok
