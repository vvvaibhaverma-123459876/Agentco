# AgentCo Audit Executive Summary

Date: 2026-07-06

## Production Readiness Verdict

AgentCo is **not production-grade today**. It is a **local-native, partially integrated research/runtime system** with several real backend and calibration slices. It is not yet a safe hosted product or a proven autonomous civilization.

## Current Classification

**Prototype plus real local runtime slices.**  
Not merely a scaffold, but not yet a production product.

## Top 10 Risks

1. Status sources conflict: README, current-reality docs, and build ledger disagree.
2. Repo-wide pytest collection fails before tests run.
3. V1 agent governance fails open for audit and human approval.
4. Backend GET endpoints are broadly unauthenticated.
5. V2 agent audit is in-memory unless higher layers persist it.
6. Frontend autonomy health checks the wrong backend route.
7. CI master gate references missing root requirement files.
8. Staging/local infra uses weak credentials and dev-mode services.
9. Disabled routes/migrations imply capabilities that are not active.
10. Hosted production evidence is absent: no SLO, backup, DR, incident, rollback proof.

## Top 10 Missing Systems

1. Single generated source of truth for implementation status.
2. Root-level clean-room bootstrap and Python dependency lock.
3. Route-level read authorization.
4. Durable BaseAgentV2 audit writer.
5. V1 agent retirement or fail-closed governance.
6. Generated frontend API contract from backend routes.
7. Hosted staging/prod operational runbook with evidence.
8. End-to-end UI tests against real backend behavior.
9. Migration baseline/unique-version policy.
10. Longitudinal real-world improvement registry.

## Top 10 Fastest Fixes

1. Fix frontend health check from `/api/health` to `/health`.
2. Add root `pytest.ini` excluding `scripts/` and `archive/` from default collection.
3. Move script DB connections under `if __name__ == "__main__"` or test fixtures.
4. Fix CI master-gate requirement paths.
5. Generate README status from `BUILD_LEDGER.yaml`.
6. Require auth on sensitive GET endpoints.
7. Remove or archive disabled route files from active route directory.
8. Replace staging compose default passwords with required env vars.
9. Add Python lockfile.
10. Add route-contract smoke tests for frontend API clients.

## Recommended Next Engineering Milestone

Make the repo independently runnable and truthfully testable from a clean clone:

- one bootstrap command,
- one authoritative status generator,
- green root test collection,
- backend/frontend type checks,
- route auth contract tests,
- no conflicting readiness claims.

Until that milestone is done, do not market AgentCo as production-ready or as a complete autonomous system.
