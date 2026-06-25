# AgentCo Goal Run Verification

- Run ID: `goal-run-20260625T091846Z-b77b2ffe`
- Mode: `live_openai`
- Decision: `escalate`
- Risk: `medium`
- Confidence: `0.6`
- Trusted confidence: `0.4617`
- Passed validation: `True`
- Brier score: `0.16`
- Latency ms: `3451.46`

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

- `prediction_ledger_insert`: ok id=`da0e07f6-cfef-4698-8af5-edbcb4ca678d`
- `prediction_ledger_resolution_update`: ok
- `legacy_prediction_resolution_insert`: ok id=`goal-run-cb915f62b3ab`
- `trust_scores_insert`: ok id=`0a0c5362-6c6b-4551-8532-b15be6641cb8`
- `event_history_insert`: ok id=`37a6e0c5-b664-420b-a6a0-fadb5cc3c879`
- `decision_log_insert`: ok
- `autonomy_audit_events_insert`: ok
- `autonomy_memory_learning_insert`: ok
