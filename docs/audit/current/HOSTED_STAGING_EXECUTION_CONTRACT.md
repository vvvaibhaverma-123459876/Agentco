# Hosted Staging Execution Contract

Batch 05 is **BLOCKED** in this environment.

Reason: no hosted cloud CLI (`aws`, `gcloud`, `az`) or IaC tool
(`terraform`, `tofu`, `pulumi`) is installed, and no hosted staging
account/project, DNS zone, workload identity, state backend, or bounded provider
credentials are bound to the repository.

Existing deployment assets are Helm/Kubernetes oriented and Batch 04 has
local-real Kind evidence. That evidence does not satisfy hosted staging.

Required hosted contract before any resource creation:

- Dedicated non-production cloud account/project/subscription.
- IaC state location with protected access.
- Hosted Kubernetes or equivalent managed compute.
- Hosted container registry.
- Managed PostgreSQL, Redis, and Kafka-compatible broker.
- Hosted secret manager and workload identity.
- Dedicated staging DNS hostname and valid TLS certificate.
- Hosted logs, metrics, traces, and alert delivery.
- Bounded live OpenAI-compatible provider credentials.
- Budget and cleanup ownership from `HOSTED_STAGING_BUDGET_POLICY.json`.

Current evidence classification: `UNVERIFIED_EXTERNAL_DEPENDENCY`.
