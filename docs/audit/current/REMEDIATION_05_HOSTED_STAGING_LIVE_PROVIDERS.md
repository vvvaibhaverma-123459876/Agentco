# Remediation 05 Hosted Staging Live Providers

Status: `BLOCKED`.

## Scope

Batch 05 is intended to deploy AgentCo to a real hosted staging environment and
exercise managed infrastructure, real DNS/TLS, external alert delivery, bounded
live provider calls, backup/restore, load, autoscaling, rollback, drift, and
hosted security checks.

## Current Execution Result

Hosted execution has not started. The local environment lacks:

- supported cloud CLI (`aws`, `gcloud`, or `az`);
- IaC tool (`terraform`, `tofu`, or `pulumi`);
- dedicated staging account/project/subscription binding;
- remote/protected IaC state backend;
- DNS zone or delegated staging hostname;
- hosted secret-manager/workload-identity binding;
- bounded live provider credentials;
- non-production external alert destination.

## Controls Added

- `HOSTED_STAGING_EXECUTION_CONTRACT.*`
- `HOSTED_STAGING_BUDGET_POLICY.*`
- `scripts/verify_hosted_staging_budget.py`
- `scripts/hosted_staging_audit.py`
- fail-closed Make targets:
  - `hosted-staging-plan`
  - `hosted-staging-apply`
  - `audit-hosted-staging`
  - `hosted-staging-destroy`
- manual `.github/workflows/hosted-staging-audit.yml`

## Evidence Classification

Current classification: `UNVERIFIED_EXTERNAL_DEPENDENCY`.

No production readiness, hosted staging readiness, hosted production proof, or
live-provider verification is claimed.

## Required Next Step

Provide a dedicated hosted staging account/project, DNS control, IaC state
backend, workload identity, registry access, cloud billing/quota read access,
and bounded provider credentials. Then rerun:

```bash
make hosted-staging-plan
make hosted-staging-apply
make audit-hosted-staging
```

## Cleanup

If hosted resources are ever provisioned, `make hosted-staging-destroy` must be
run unless a bounded retention decision with owner, cost, expiry, and cleanup
deadline is committed to the hosted evidence artifact.
