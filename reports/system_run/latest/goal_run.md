# AgentCo Goal Run Verification

- Run ID: `goal-run-20260625T091055Z-ec7e30f7`
- Mode: `live_openai`
- Decision: `escalate`
- Risk: `medium`
- Confidence: `0.6`
- Trusted confidence: `0.4617`
- Passed validation: `True`
- Brier score: `0.16`
- Latency ms: `4102.07`

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

- `prediction_ledger_insert`: ok id=`dcb484d0-aabe-4cd9-80d9-3449abcb6185`
- `prediction_ledger_resolution_update`: failed error=`ERROR:  LEDGER RESOLUTION VIOLATION: only resolution_service may resolve predictions (current_user=agentco)
CONTEXT:  PL/pgSQL function enforce_prediction_ledger_immutability() line 34 at RAISE`
- `legacy_prediction_resolution_insert`: ok id=`goal-run-d4ebc9be1881`
- `trust_scores_insert`: ok id=`1095999a-d646-4780-a7dd-08edf10d9899`
- `event_history_insert`: ok id=`bab9cb38-61c3-42e9-8e30-7faa1595244d`
- `decision_log_insert`: ok
- `autonomy_audit_events_insert`: ok
- `autonomy_memory_learning_insert`: ok
