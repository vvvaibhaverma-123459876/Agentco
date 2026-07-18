# Batch 09B Real-Provider Baseline Report

## Result

| Field | Value |
| --- | --- |
| campaign | `governed-capability-genesis-v6-real-baseline` |
| decision | `HOLD_FOR_MORE_EVIDENCE` |
| execution_attempted | `false` |
| real_provider_execution | `NOT_ATTEMPTED` |
| real_capability_baseline | `NOT_ESTABLISHED` |
| supported_domains | `[]` |
| aggregate_correctness | unavailable |
| hosted_staging | `UNVERIFIED` |
| production_readiness | `UNVERIFIED` |
| capability_improvement | `NOT_CLAIMED` |

## Blocking Preconditions

| Blocker | Evidence |
| --- | --- |
| Post-merge workflow completion not yet fully green at first Batch 09B check | `main` push runs for CI, Clean-Room Audit and Staging Deployment Audit were still `in_progress` for commit `98eb1b9c04604e84770c7bdd286f9bbbfdbec663`. |
| Campaign authorization artifact missing | Repository scan found `schemas/real_provider_campaign_authorization.schema.json` only; no authorization JSON/YAML artifact exists to validate. |
| Authorization cannot bind execution | Without an artifact there is no verified campaign ID, source commit/tree, provider, model, endpoint, case manifest, maximum calls, token budget, cost budget, operator or expiry. |
| Active provider configuration missing | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` and `AGENTCO_PROVIDER_HOST_ALLOWLIST` are not present in the active process environment. |
| Provider preflight invalid | `provider_preflight = invalid_configuration`; failure codes are `missing_model_identifier`, `missing_api_base_url`, `missing_credential_reference`, `missing_provider_host_allowlist`, `invalid_model_identifier`. |

## Counts

| Metric | Value |
| --- | --- |
| planned cases | `24` |
| executed cases | `0` |
| completed cases | `0` |
| failed cases | `0` |
| timed-out cases | `0` |
| denied cases | `0` |
| evidence-unavailable cases | `24` |
| evaluator-unavailable cases | `0` |
| invalid-response cases | `0` |
| infrastructure-failure cases | `0` |
| total tokens | unavailable |
| total cost | unavailable |
| latency statistics | unavailable |

## Non-Claims

This Batch 09B record does not establish real-provider capability, supported domains, aggregate correctness, capability improvement, hosted staging readiness or production readiness. It also does not count dry-run, deterministic, mock or evaluator-generated responses as capability evidence.

## Safe Handling

No live provider call was made. No `code.env` file was sourced. No credential value was read, printed, persisted or committed.
