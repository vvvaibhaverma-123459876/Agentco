# Deployment Component Ledger

| Component | Image | Service account | Readiness | Status |
| --- | --- | --- | --- | --- |
| backend | agentco-backend:<commit> | agentco-runtime | /health/ready | verified_deployed_after_audit |
| frontend | agentco-frontend:<commit> | agentco-frontend | /api/health | verified_deployed_after_audit |
| outbox-worker | agentco-backend:<commit> | agentco-worker | not exposed; deployment health by running pod and outbox drain proof | verified_deployed_after_audit |
| migration-job | agentco-backend:<commit> | agentco-migration | job completion | verified_deployed_after_audit |
