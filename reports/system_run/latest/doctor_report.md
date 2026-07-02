# AgentCo Doctor Report

- Requested mode: `offline_fixture`
- Selected runtime mode: `offline_fixture`
- Can continue: `True`
- Safe next command: `make run-offline-fixture`

| Service | Status | Detail |
|---|---|---|
| `python` | `real` | 3.13.9 |
| `python_dependencies` | `real` | pytest importable |
| `node` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/node |
| `npm` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/npm |
| `backend_build` | `not_required` | build not run in this mode |
| `frontend_build` | `not_required` | build not run in this mode |
| `docker_cli` | `real` | /usr/local/bin/docker |
| `docker_daemon` | `real` | docker daemon reachable |
| `postgres` | `real` | agentco_audit|Zet |
| `migrations` | `real` | ts-node src/db/migrate.ts |
| `core_db_schema` | `real` | prediction_ledger|decision_log|override_queue |
| `redis` | `real` | localhost:6379 |
| `kafka` | `real` | localhost:9092 |
| `vault` | `real` | localhost:8200 |
| `prometheus` | `real` | localhost:9090 |
| `grafana` | `real` | localhost:3005 |
| `openai_env` | `missing` | key_present=False |
| `openai_connectivity` | `not_required` | live check not requested |
| `resolution_service` | `real` | resolution_service |
| `sensitive_route_auth` | `real` | override read route protected |
| `production_secret_posture` | `blocked` | dev-default or missing production secrets: AGENTCO_API_KEY, EVENT_BUS_HMAC_KEY, EVENT_BUS_SIGNING_KEY, JWT_SECRET, VAULT_TOKEN |
| `filesystem_reports` | `real` | /private/tmp/claude-502/-Users-Zet/bf00110a-a95d-44c3-905a-d16dc3207c46/scratchpad/Agentco/reports/system_run/latest |

## Fallbacks Used
- None

## Disabled Capabilities
- `openai_env`
- `production_secret_posture`
