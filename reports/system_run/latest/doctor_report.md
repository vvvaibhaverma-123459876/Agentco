# AgentCo Doctor Report

- Requested mode: `local_native`
- Selected runtime mode: `local_native`
- Can continue: `True`
- Safe next command: `make run-best-effort`

## Services

| Service | Status | Detail | Remediation |
|---|---|---|---|
| `python` | `real` | 3.13.9 | Use Python 3.13 for AgentCo doctor/tests |
| `python_dependencies` | `real` | pytest importable |  |
| `node` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/node | Install node |
| `npm` | `real` | /Users/Zet/.nvm/versions/node/v24.17.0/bin/npm | Install npm |
| `backend_build` | `real` | > @agentco/backend@1.0.0 build > tsc | Run npm run build |
| `frontend_build` | `real` |  kB ├ ○ /finance                             561 B          87.7 kB ├ ○ /incidents                           554 B          87.7 kB ├ ○ /override                            2.64 kB | Run npm run build |
| `docker_cli` | `real` | /usr/local/bin/docker | Install docker |
| `docker_daemon` | `blocked` | Cannot connect to the Docker daemon at unix:///Users/Zet/.docker/run/docker.sock. Is the docker daemon running? | Start Docker Desktop/daemon or use local_native |
| `docker_compose` | `real` | Docker Compose version v5.1.4 |  |
| `postgres` | `real` | agentco|agentco |  |
| `migration_dependencies` | `real` | pg dependency declared; ts-node runnable (v10.9.2) |  |
| `migrations` | `real` | backend TypeScript migration runner present |  |
| `core_db_schema` | `real` | prediction_ledger|decision_log|event_history|trust_scores |  |
| `redis` | `missing` | localhost:6379 unreachable | Start Redis or use memory cache fallback |
| `kafka` | `missing` | localhost:9092 unreachable | Start Kafka or use in-process event bus fallback |
| `vault` | `missing` | localhost:8200 unreachable | Start Vault or use env secret provider fallback |
| `prometheus` | `missing` | localhost:9090 unreachable | Start Prometheus or use JSON metrics fallback |
| `grafana` | `missing` | localhost:3005 unreachable | Start Grafana or skip dashboard UI |
| `openai_env` | `real` | key_present=True, model=gpt-4o-mini | Set LLM_API_KEY or use offline_fixture |
| `openai_connectivity` | `real` | OpenAI-compatible call succeeded |  |
| `resolution_service` | `real` | resolution_service login works |  |
| `backend_health` | `not_required` | backend not running during doctor |  |
| `sensitive_route_auth` | `real` | static route check passed |  |
| `filesystem_reports` | `real` | /Users/Zet/Desktop/Agentco/reports/system_run/latest |  |

## Fallbacks Used

- `docker_daemon` -> `native_services` (`blocked`)
- `redis` -> `memory_cache` (`missing`)
- `kafka` -> `in_process_event_bus` (`missing`)
- `vault` -> `env_secret_provider` (`missing`)
- `prometheus` -> `json_metrics_writer` (`missing`)
- `grafana` -> `metrics_json_only` (`missing`)

## Disabled Capabilities

- None

## Required Fixes

- None
