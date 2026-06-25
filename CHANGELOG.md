# Changelog

## 0.1.1-dev (2026-06-25)

- Verified RUNNABLE_WITH_FALLBACKS status via post-fix verification run (commit `6b4e27d`)
- Runtime doctor passes in offline_fixture and local_native modes
- Override route auth hardened: unauth→401, wrong scope→403
- Backend 156/182 tests passing; frontend builds cleanly
- Live Postgres schema confirmed (4 core tables)
- Live OpenAI connectivity confirmed (gpt-4o-mini, ~1.2s)
- Explicit fallbacks for Redis/Kafka/Vault/Prometheus/Grafana
- Remaining gaps: north-star benchmark unimplemented, 49/77 services orphaned, no full Docker run

## 0.1.0-rc1-pre

- Aligned public claims around calibration-first civilization infrastructure.
- Added resolution independence enforcement and adversarial calibration tests.
- Hardened Institution Kernel invariants, memory events, and reputation controls.
- Added governed API routes, RBAC, service identity checks, and security docs.
- Added Society, Jurisdiction, Judiciary, Economy, Constitution, Memory, and Lifecycle service layers with focused tests.
- Added civilization operating dashboards backed by typed deterministic data.
- Added an offline civilization constitution demo, offline smoke target, doctor target, and Docker Compose profiles.

No release tag has been created.
