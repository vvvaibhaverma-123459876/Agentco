# Production Infrastructure Smoke Report

**Date:** 2026-06-30  
**Branch:** `main`  
**Commit before this report:** `48899c54011ae35513641b6ccefde7551ae5948d`

## Command

```bash
make docker-production-smoke
```

Exit code: `0`

## Result

Docker Desktop was started, then the smoke was run with `.env.production.local`
loaded. Docker/Compose infrastructure started or was already running, and the
production posture gate returned `can_continue=true`.

| Service | Status |
|---|---|
| Postgres | running, healthy |
| Redis | running, healthy |
| Zookeeper | running, healthy |
| Kafka | running, TCP reachable |
| Vault | running, healthy |
| Prometheus | running, healthy |
| Grafana | running, healthy |
| OTel collector | running |

## Production Posture Blockers

Source artifact: `reports/system_run/latest/production_posture_verification.json`

| Check | Status | Detail |
|---|---|---|
| `AGENTCO_API_KEY` | real | present; value suppressed |
| `JWT_SECRET` | real | present; value suppressed |
| `EVENT_BUS_SIGNING_KEY` | real | present; value suppressed |
| `EVENT_BUS_HMAC_KEY` | real | present; value suppressed |
| `DATABASE_URL` | real | present; value suppressed |
| `VAULT_ADDR` | real | present; value suppressed |
| `VAULT_TOKEN` | real | present; value suppressed |
| `SPECIALIST_SHARED_SECRET` | real | present; value suppressed |
| `postgres` | real | tcp reachable at localhost:5432 |
| `redis` | real | tcp reachable at localhost:6379 |
| `kafka` | real | tcp reachable at localhost:9092 |
| `vault` | real | tcp reachable at localhost:8200 |
| `prometheus` | real | tcp reachable at localhost:9090 |
| `grafana` | real | tcp reachable at localhost:3005 |
| `docker_compose` | real | docker compose responded |

## Verdict

AgentCo currently passes the local Docker production-infrastructure smoke with
real local services reachable and production secrets present outside git.

This is a local production-posture smoke, not a certification of hosted
production operations. The desired safety behavior held: the verifier did not
print secret values and would fail closed if required services or secrets were
missing.
