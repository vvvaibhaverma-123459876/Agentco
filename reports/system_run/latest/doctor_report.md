# AgentCo Doctor Report

- Requested mode: `local_native`
- Selected runtime mode: `local_native`
- Can continue: `True`
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
| `redis` | `missing` | localhost:6379 |
| `kafka` | `missing` | localhost:9092 |
| `vault` | `missing` | localhost:8200 |
| `prometheus` | `missing` | localhost:9090 |
| `grafana` | `missing` | localhost:3005 |
| `openai_env` | `real` | key_present=True |
| `openai_connectivity` | `real` | {"latency_ms": 1382, "model": "gpt-4o-mini", "status": "ok", "success": true} |
| `resolution_service` | `real` | resolution_service |
| `sensitive_route_auth` | `real` | override read route protected |
| `filesystem_reports` | `real` | /Users/Zet/Agentco/reports/system_run/latest |

## Fallbacks Used
- `redis` -> `memory_cache` (`missing`)
- `kafka` -> `in_process_event_bus` (`missing`)
- `vault` -> `env_secret_provider` (`missing`)
- `prometheus` -> `json_metrics_writer` (`missing`)
- `grafana` -> `metrics_json_only` (`missing`)

## Disabled Capabilities
- None
