# Production Infrastructure Smoke Report

**Date:** 2026-06-29  
**Branch:** `fix/runtime-integrity-and-production-honesty`  
**Commit before this report:** `1e21ce4d132a7fc6c0e761464621ade922490045`

## Command

```bash
make docker-production-smoke
```

Exit code: `2`

## Result

The Docker/Compose infrastructure services started or were already running and
reported healthy:

| Service | Status |
|---|---|
| Postgres | healthy |
| Redis | healthy |
| Zookeeper | healthy |
| Kafka | healthy |
| Vault | healthy |
| Prometheus | healthy |
| Grafana | healthy |

The target still failed because `scripts/verify_production_posture.py` correctly
returned `can_continue=false`.

## Production Posture Blockers

Source artifact: `reports/system_run/latest/production_posture_verification.json`

| Check | Status | Detail |
|---|---|---|
| `AGENTCO_API_KEY` | blocked | missing required production secret |
| `JWT_SECRET` | blocked | missing required production secret |
| `EVENT_BUS_SIGNING_KEY` | blocked | missing required production secret |
| `EVENT_BUS_HMAC_KEY` | blocked | missing required production secret |
| `DATABASE_URL` | blocked | missing required production secret |
| `VAULT_ADDR` | blocked | missing required production secret |
| `VAULT_TOKEN` | blocked | missing required production secret |
| `SPECIALIST_SHARED_SECRET` | blocked | missing required production secret |

## Verdict

Docker/Kafka/Redis/Vault/Prometheus/Grafana are locally reachable as real
services in this run. AgentCo is still not production-runnable because the
production posture gate fails closed on missing production secrets.

This is the desired safety behavior. It is not a runtime bug and should not be
worked around with fake or default production secrets.
