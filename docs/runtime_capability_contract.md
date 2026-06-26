# AgentCo Runtime Capability Contract

AgentCo must report the difference between real infrastructure, explicit fallback behavior, simulated data, and blocked capabilities. Fallbacks are allowed only when they preserve governance boundaries and are visible in reports.

Production-like mode is any of:

- `AGENTCO_ENV=production`
- `AGENTCO_ENV=staging`
- `NODE_ENV=production`

In production-like mode, startup must fail closed if simulated, mock, unsupported, or local fallback providers are selected.

## Status Terms

| Term | Meaning |
|---|---|
| `real` | A live dependency or real code path was verified by command or probe. |
| `partial` | Some parts work, but a required dependency or proof path is incomplete. |
| `fallback` | A declared replacement adapter is active and reported. |
| `simulated` | Deterministic or fake data/model behavior; never production evidence. |
| `blocked` | The dependency or proof path is unavailable, but failure is clear and safe. |
| `broken` | The dependency exists or was attempted but failed unexpectedly. |
| `missing` | The dependency/configuration is absent. |

## Capability Matrix

| Capability | Required for production | Local fallback | Offline fallback | Fail-closed? |
|---|---:|---|---|---:|
| Postgres | yes | native Postgres | file-backed smoke ledger | yes for production |
| Core migrations/schema | yes | existing schema accepted if complete | skipped and reported | yes for production/local DB writes |
| Kafka | preferred | in-process event bus | file event log | no |
| Redis | no | memory cache | memory cache | no |
| Vault | yes | env/local secret provider | env/local secret provider | yes for production |
| Prometheus/Grafana | preferred | JSON metrics artifact | JSON metrics artifact | no |
| OpenAI/LLM | deployment-dependent | live if key exists; otherwise disabled | deterministic fake LLM | fake forbidden outside offline/CI |
| Resolution service | yes for ledger scoring | service DB URL if configured | disabled | yes for scoring |
| Auth middleware | yes | no fallback | no fallback | yes |
| Reports/results filesystem | yes | local reports directory | local reports directory | yes |

## Runtime Modes

| Mode | Purpose | External services | Simulated data |
|---|---|---|---|
| `production` | Real deployment path with governance fail-closed. | Required critical services. | Forbidden. |
| `local_full` | Docker-backed local stack when available. | Postgres required; Kafka/Redis/Vault preferred. | Forbidden. |
| `local_native` | Developer mode with native Postgres and explicit fallbacks. | Native Postgres required. | Forbidden. |
| `offline_fixture` | Deterministic local verification without external services. | None required. | Allowed and labeled. |
| `ci_smoke` | Fast CI-safe deterministic checks. | None required. | Allowed and labeled. |
| `degraded` | Automatic fallback when noncritical services are missing. | Critical governance paths still fail closed. | Forbidden unless switched to offline/CI. |

## Failure Behavior

| Dependency failure | Expected behavior |
|---|---|
| Docker unavailable | Use `local_native` if native Postgres is healthy; otherwise use explicit offline fixture when requested. |
| Kafka unavailable | Use in-process event bus outside production; report event streaming as fallback. |
| Redis unavailable | Use memory cache outside production; report cache persistence as disabled. |
| Vault unavailable | Use env/local secrets outside production; production fails closed. |
| Prometheus/Grafana unavailable | Write JSON metrics artifacts and skip dashboard UI. |
| OpenAI key missing | Use deterministic fake LLM only in `offline_fixture` or `ci_smoke`; disable live intelligence otherwise. |
| Postgres unavailable | Production/local native fail closed; offline/CI may use file-backed smoke ledger marked simulated. |
| Resolution-service credentials missing | Disable primary ledger resolution; keep unauthorized-resolution guard checks. |
| Auth middleware missing | Fail closed in every mode. |

## Backend Provider Guard

The backend exposes active provider metadata at:

```text
GET /health/runtime
```

Provider classifications:

| Provider | Real | Fallback/simulated | Production-like behavior |
|---|---|---|---|
| Web adapter | `real_web_adapter` | `mock_web_adapter` | startup fails |
| LLM | configured real provider | `deterministic_llm_fallback` or missing provider | startup fails |
| Secrets | Vault | env/local secret provider | startup fails |

Test and development may use non-real providers only when those providers are explicitly reported and never represented as production infrastructure.
