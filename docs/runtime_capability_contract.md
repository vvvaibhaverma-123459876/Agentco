# AgentCo Runtime Capability Contract

This contract defines how AgentCo behaves when runtime dependencies are present,
missing, degraded, or replaced by explicit fallbacks.

## Terms

| Term | Meaning |
|---|---|
| `real` | Backed by the real service or real persisted database path. |
| `partial` | Some real behavior exists, but important paths are unavailable or unverified. |
| `fallback` | A declared substitute is active and visible in reports. |
| `simulated` | Deterministic or fake behavior; never presented as real infrastructure. |
| `blocked` | Required dependency or safety boundary prevents capability execution. |

## Runtime Modes

| Mode | Purpose |
|---|---|
| `production` | Real services, real secrets, no silent fallback, fail closed. |
| `local_full` | Docker Compose preferred, real Postgres expected, optional infra may degrade with explicit report. |
| `local_native` | Native Postgres allowed; Docker not required; Kafka/Redis/Vault/metrics can fall back. |
| `offline_fixture` | Deterministic, no external services required, file-backed reports required. |
| `ci_smoke` | Fast deterministic CI checks, no secrets or external services. |
| `degraded` | Automatically selected when noncritical services are missing; governance-sensitive paths fail closed. |

## Dependency Contract

| Capability | Required for production | Local fallback | Offline fallback | Fail-closed? |
|---|---|---|---|---|
| Postgres | yes | native Postgres | file-backed smoke ledger | yes for production |
| Core DB schema | yes | migrations via backend TS runner | not required | yes for DB writes |
| Kafka | preferred | in-process event bus | file event log | no |
| Redis | no | memory cache | memory cache | no |
| Vault | yes in production | env/local secret provider | env/local secret provider | yes for production |
| Prometheus | preferred | JSON metrics writer | JSON metrics writer | no |
| Grafana | preferred | skip UI, keep metrics JSON | skip UI | no |
| OpenAI/LLM | deployment-dependent | disabled live LLM if missing | deterministic fake LLM | no for offline, yes for production if required by workload |
| Resolution service | yes for ledger scoring | service DB URL or disable primary resolution | disabled | yes for scoring |
| Auth middleware | yes | no fallback | no fallback | yes |
| Filesystem reports | yes | local reports directory | local reports directory | yes |

## Required Behavior

- Fallbacks must be explicit in `doctor_report.json` and `doctor_report.md`.
- Fallbacks cannot be used silently in production.
- Fallbacks cannot bypass auth, governance, resolution-service, or immutable ledger boundaries.
- Missing `resolution_service` disables primary ledger resolution; it must not trigger unauthorized updates through the app DB user.
- Missing OpenAI may use a deterministic fake LLM only in `offline_fixture` or `ci_smoke`.
- Missing Postgres may use a file-backed smoke ledger only in `offline_fixture` or `ci_smoke`.
- Docker absence should select `local_native` when native Postgres is healthy.
- Security-sensitive routes are never downgraded by degraded mode.

## Verified Runtime State — 2026-06-25

**Runnability verdict:** `RUNNABLE_WITH_FALLBACKS`

| Service | Observed status | Fallback active |
|---|---|---|
| Postgres | `real` — 4 core tables live | — |
| Migrations | `real` — doctor confirms up-to-date | — |
| Redis | `missing` | memory_cache |
| Kafka | `missing` | file_event_log |
| Vault | `missing` | env_secret_provider |
| Prometheus | `missing` | json_metrics_writer |
| Grafana | `missing` | metrics_json_only |
| OpenAI/LLM | `real` — gpt-4o-mini, ~1.2s latency | — |
| Resolution service | `real` — doctor login verified | — |
| Auth middleware | `real` — 401/403 gates verified | — |
| Docker daemon | not required for local_native mode | — |

**Doctor output:** `can_continue=true`, `required_fixes=[]`, `disabled_capabilities=[]`

**Modes verified:** `offline_fixture` (make run-offline-fixture ✅), `local_native` (make run-best-effort ✅)

**Not yet verified:** `production` mode (requires Redis/Kafka/Vault/Prometheus all live + Docker Compose up)
