# Mock and Fallback Isolation Report

Generated during branch `fix/runtime-integrity-and-production-honesty`.

## Backend Runtime Guards

The backend now classifies active providers through `backend/src/runtime-mode.ts`.

| Provider | Real path | Non-real paths | Production-like behavior |
| --- | --- | --- | --- |
| Web adapter | `real_web_adapter` | `mock_web_adapter` | startup fails if mock is selected |
| LLM | `openai_compatible` or configured real provider | `deterministic_llm_fallback`, missing provider | startup fails if fallback/missing in staging/production |
| Secrets | Vault | `env_secret_provider` | startup fails in staging/production |

Production-like means any of:

- `AGENTCO_ENV=production`
- `AGENTCO_ENV=staging`
- `NODE_ENV=production`

## Specialist Shared Secret

`SPECIALIST_SHARED_SECRET` no longer silently falls back to `default-insecure-secret` in staging/production. Backend signing and Python specialist verification both fail closed in production-like environments if the secret is missing or default.

## Runtime Health

The backend exposes:

```text
GET /health/runtime
```

The endpoint returns active runtime mode, provider classifications, and whether fallback/simulated providers are active.

## Durable Task Execution

`scripts/execute_durable_task.py` no longer has synthetic success for `review` or `decision` task types. Those paths now return explicit unsupported errors until real review/decision services are wired.

## Remaining Mock/Demo Code

Known non-production code remains in test, simulation, and disabled-route areas. It must remain isolated from staging/production startup paths and must not be described as production capability.
