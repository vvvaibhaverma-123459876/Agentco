# Production Infrastructure Smoke Report

**Date:** 2026-06-30  
**Branch:** `main`  
**Commit before this report:** `bea00fbf7040fccea80120f3a866d78a6f7f88a9`

## Command

```bash
make docker-production-smoke
```

Exit code: `2`

## Result

The smoke could not start or reuse Docker/Compose infrastructure because the
Docker daemon socket was not reachable:

```text
unable to get image 'postgres:16-alpine': failed to connect to the docker API
at unix:///Users/Zet/.docker/run/docker.sock: connect: no such file or directory
```

After loading `.env.production.local`, `scripts/verify_production_posture.py`
was rerun directly. Production secrets were present and suppressed, but the
runtime infrastructure probes failed because Docker/Compose services were not
running.

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
| `redis` | blocked | tcp unavailable at localhost:6379 |
| `kafka` | blocked | tcp unavailable at localhost:9092 |
| `vault` | blocked | tcp unavailable at localhost:8200 |
| `prometheus` | blocked | tcp unavailable at localhost:9090 |
| `grafana` | blocked | tcp unavailable at localhost:3005 |
| `docker_compose` | blocked | docker compose is unavailable or project is not running |

## Verdict

AgentCo is not currently runnable as a real-world production smoke in this local
environment because Docker/Compose infrastructure is down. This is an external
runtime-state blocker, not a missing-secret blocker and not a code-path success.

The desired safety behavior held: the production posture gate failed closed and
did not print secret values.
