# AgentCo Goal Run Verification

- Run ID: `goal-run-20260625T093328Z-93004d14`
- Mode: `live_openai`
- Decision: `escalate`
- Risk: `medium`
- Confidence: `0.6`
- Trusted confidence: `0.4617`
- Passed validation: `True`
- Brier score: `0.16`
- Latency ms: `2864.52`

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

- `prediction_ledger_insert`: ok id=`20c2a420-188b-4294-bb7e-da387bf3739a`
- `prediction_ledger_resolution_update`: ok
- `legacy_prediction_resolution_insert`: ok id=`goal-run-3faf9854a807`
- `trust_scores_insert`: ok id=`ba02ebfc-15ce-4321-a977-1ee73413ba1a`
- `event_history_insert`: ok id=`392ef4df-7b8f-441b-95ca-89717ec7cfbb`
- `decision_log_insert`: ok
- `autonomy_audit_events_insert`: ok
- `autonomy_memory_learning_insert`: ok
