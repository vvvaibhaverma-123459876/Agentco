# Launch Readiness Status

Status: not ready for v0.1.0-rc1 tag.

## Commands Run

- `make doctor` - passed.
- `make smoke` - passed offline.
- `make demo` - passed offline and exported `examples/civilization_constitution_demo/artifacts/audit_package.json`.
- `make migrate` - passed, 30 migrations applied.
- `make dev-minimal` - initially blocked by sandbox Docker socket access, then passed with approval; Postgres profile running and migrations applied.
- `docker compose --profile dev up -d zookeeper kafka` - passed with approval for backend event-bus integration tests.
- `docker compose --profile minimal config --services` - passed, returned `postgres`; Docker warned the top-level `version` key is obsolete.
- `cd backend && npm test && npm run build` - failed once in sandbox because Node could not connect to localhost services; passed after Docker services were running and localhost access was approved:
  - backend Jest: 42 passed
  - backend build: passed
- `cd frontend && npm test && npm run build` - passed:
  - dashboard surface check passed
  - frontend build passed with existing hook dependency warning
- `make test` - passed after expanding the target to include backend build and frontend test:
  - Python: 280 passed
  - migrations: 30 applied
  - backend Jest: 42 passed
  - backend build: passed
  - frontend test: passed
  - frontend build: passed

## Known Blockers

- GitHub Actions has been configured but not observed on the remote CI service in this run.
- Live end-to-end Society/Civilization orchestration is not fully bound to persisted backend APIs.
- Frontend civilization dashboards use deterministic mock data.
- Backend Jest emits an existing worker shutdown warning.
- Frontend build emits an existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Docker Compose emits an obsolete top-level `version` warning.

## Shipped Capabilities

- Calibration ledger, independence checks, trust scoring, audit traces, and recomputable credentials.
- Institution Kernel hardening and calibrated reputation propagation tests.
- Governed API/RBAC route boundaries.
- Society, jurisdiction, dispute, economy, constitution, memory, and lifecycle service layers with tests.
- Offline smoke and offline civilization constitution demo.
- CI workflow configured to run offline gates, migrations, Python tests, backend tests/build, frontend tests/build, and full `make test` without paid LLM keys.

## Experimental Capabilities

- Civilization dashboards backed by deterministic mock data.
- Demo propagation from trust into institution/society/economy/memory fixtures.
- Compose profiles for local run modes.

## Future Capabilities

- Live Society/Civilization orchestration through durable APIs.
- Full constitutional governance identity/quorum process.
- Production deployment hardening and observability.
