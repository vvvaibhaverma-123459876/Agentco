# Hosted Staging Budget Policy

Batch 05 hosted execution is capped by `HOSTED_STAGING_BUDGET_POLICY.json`.

The policy is intentionally small: maximum 8 hours, estimated infrastructure cost
of 75 USD, provider spend of 5 USD, 20 live LLM requests, 20,000 tokens, and
2,000 load-test requests.

Provisioning must fail closed when the policy is missing, expired, incomplete,
or when cloud billing/quota state cannot be checked. Billing values are
estimates unless the selected provider returns finalized charges for the exact
audit window.

No hosted resource may be created without the required tags:

- `project=agentco`
- `environment=hosted-staging-audit`
- `owner=agentco-audit`
- `managed_by=iac`
- `purpose=batch-05-hosted-staging`
- `production=false`

Current status: `BLOCKED` until a hosted account/project, DNS zone, cloud
identity, and provider credentials are explicitly bound.
