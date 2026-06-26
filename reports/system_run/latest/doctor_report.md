# AgentCo Doctor Report

- Requested mode: `production`
- Selected runtime mode: `production`
- Can continue: `False`
- Safe next command: `make run-best-effort`

| Service | Status | Detail |
|---|---|---|
| `python` | `real` | 3.13.9 |
| `python_dependencies` | `real` | pytest importable |
| `node` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/node |
| `npm` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/npm |
| `backend_build` | `real` | > @agentco/backend@1.0.0 build > tsc |
| `frontend_build` | `real` |  kB ├ ○ /incidents                           554 B          87.9 kB ├ ○ /override                            3.2 kB         90.5 kB ├ ○ /performance                         712 B   |
| `docker_cli` | `real` | /usr/local/bin/docker |
| `docker_daemon` | `real` | docker daemon reachable |
| `postgres` | `real` | agentco|agentco |
| `migrations` | `real` | ts-node src/db/migrate.ts |
| `core_db_schema` | `real` | prediction_ledger|decision_log|override_queue |
| `redis` | `real` | localhost:6379 |
| `kafka` | `real` | localhost:9092 |
| `vault` | `real` | localhost:8200 |
| `prometheus` | `real` | localhost:9090 |
| `grafana` | `real` | localhost:3005 |
| `openai_env` | `real` | key_present=True |
| `openai_connectivity` | `real` | {"latency_ms": 1663, "model": "gpt-4o-mini", "status": "ok", "success": true} |
| `resolution_service` | `real` | resolution_service |
| `sensitive_route_auth` | `real` | override read route protected |
| `production_secret_posture` | `blocked` | dev-default or missing production secrets: AGENTCO_API_KEY, AGENTCO_TEST_DATABASE_URL, EVENT_BUS_HMAC_KEY, EVENT_BUS_SIGNING_KEY, JWT_SECRET, VAULT_TOKEN |
| `filesystem_reports` | `real` | /Users/Zet/Agentco/reports/system_run/latest |

## Fallbacks Used
- None

## Disabled Capabilities
- `production_secret_posture:required_unavailable`
