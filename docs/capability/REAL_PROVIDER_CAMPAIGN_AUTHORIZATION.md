# Real-Provider Campaign Authorization

Real-provider Genesis execution requires a machine-verifiable authorization artifact before the first provider call. The schema is `schemas/real_provider_campaign_authorization.schema.json`.

Required bindings:

| Field | Requirement |
| --- | --- |
| `campaign_id` | Must equal `governed-capability-genesis-v5`. |
| `source_commit` | Must equal the exact execution commit. |
| `source_tree` | Must equal the exact execution tree. |
| `protocol_version` | Must reference accepted Protocol V3. |
| `genesis_version` | Must reference Genesis V5. |
| `provider`, `model`, `endpoint` | Must match validated provider configuration. |
| `maximum_calls`, `maximum_tokens`, `maximum_cost_usd` | Must not exceed configured campaign budgets. |
| `authorization_expiry` | Must be in the future at execution time. |
| `approved_evidence_destination` | Must identify the immutable artifact destination. |

Execution fails closed when authorization is missing, expired, malformed, unsigned when signing is required, for another commit, for another model, for another endpoint, or over budget.

Non-claims that must be included:

- protocol readiness is not real capability evidence;
- deterministic or mock responses cannot establish capability;
- hosted staging remains unverified;
- production readiness remains unverified;
- a HOLD decision is neither success nor failure.
