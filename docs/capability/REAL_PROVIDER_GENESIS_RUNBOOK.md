# Real-Provider Genesis Runbook

This runbook is for a future explicitly authorized Batch 09B campaign. Do not use it to perform an unapproved live run.

1. Required environment variables:
   - `OPENAI_API_KEY`
   - `OPENAI_MODEL`
   - `OPENAI_BASE_URL`
   - `AGENTCO_PROVIDER_HOST_ALLOWLIST`
   - optional budget overrides: `AGENTCO_PROVIDER_TOKEN_BUDGET`, `AGENTCO_PROVIDER_MONETARY_BUDGET_USD`, `AGENTCO_PROVIDER_MAX_CALLS`
2. Provision credentials through the approved secret store or local operator environment. Never commit credentials.
3. Set the provider allowlist to the exact provider host. Avoid broad wildcards.
4. Select the model and record the expected model identity.
5. Create a campaign authorization artifact matching the exact source commit and tree.
6. Run configuration preflight:
   - `python3.13 scripts/verify_real_provider_readiness.py --check`
7. Expected preflight output:
   - valid configuration or explicit failure codes;
   - no provider execution unless explicitly authorized;
   - no capability claims.
8. Run dry run:
   - use the readiness report dry-run section;
   - verify `capability_effect = none` and `real_provider_execution = false`.
9. Real run command for a future authorized batch:
   - `make real-capability-genesis-v5`
   - only after authorization and credential checks pass.
10. Monitor live execution:
   - provider calls;
   - retry counts;
   - budget reservation and settlement;
   - timeout terminal states;
   - artifact writes.
11. Budget stop procedure:
   - stop campaign when global call, token or monetary budget reaches the authorized limit.
12. Emergency abort:
   - cancel pending attempts;
   - settle or release all reservations;
   - preserve partial evidence.
13. Evidence collection:
   - archive raw redacted requests and responses;
   - archive evaluator outputs;
   - archive budget ledger and audit references.
14. Artifact verification:
   - run freeze verifier;
   - run artifact verifier;
   - verify semantic hashes.
15. Result interpretation:
   - accepted/rejected/HOLD/invalid decisions are governed by `CAPABILITY_THRESHOLDS.md`.
16. Credential cleanup:
   - clear local shell environment;
   - rotate credentials if leakage is suspected.
17. Incident handling:
   - preserve artifacts;
   - record provider request IDs;
   - open an evidence-integrity finding for any S0/S1 issue.
18. Rerun policy:
   - reruns require disclosure;
   - do not retry until favourable outcomes appear;
   - source-tree or frozen-case changes require new evidence identity.
