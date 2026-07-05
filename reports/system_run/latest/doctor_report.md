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
| `docker_daemon` | `blocked` | failed to connect to the docker API at unix:///Users/Zet/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/Zet/.docker/run/docker |
| `postgres` | `real` | agentco|agentco |
| `migrations` | `real` | ts-node src/db/migrate.ts |
| `core_db_schema` | `real` | prediction_ledger|decision_log|override_queue |
| `redis` | `missing` | localhost:6379 |
| `kafka` | `missing` | localhost:9092 |
| `vault` | `missing` | localhost:8200 |
| `prometheus` | `missing` | localhost:9090 |
| `grafana` | `missing` | localhost:3005 |
| `openai_env` | `real` | key_present=True |
| `openai_connectivity` | `not_required` | live check not requested |
| `resolution_service` | `real` | resolution_service |
| `sensitive_route_auth` | `real` | override read route protected |
| `production_secret_posture` | `blocked` | dev-default or missing production secrets: AGENTCO_API_KEY, AGENTCO_TEST_DATABASE_URL, DATABASE_URL, EVENT_BUS_HMAC_KEY, EVENT_BUS_SIGNING_KEY, JWT_SECRET, VAULT_TOKEN |
| `filesystem_reports` | `real` | /Users/Zet/Agentco/reports/system_run/latest |

## Fallbacks Used
- `redis` -> `memory_cache` (`missing`)
- `kafka` -> `file_event_log` (`missing`)
- `vault` -> `env_secret_provider` (`missing`)
- `prometheus` -> `json_metrics_writer` (`missing`)
- `grafana` -> `metrics_json_only` (`missing`)

## Disabled Capabilities
- `docker_daemon`
- `production_secret_posture`
