# AgentCo Production Readiness

**Current verdict:** not production certified.

AgentCo has several production-oriented controls and verified local-native runtime paths, but it is not ready to be described as production-grade until the remaining production blockers are closed and proven by tests/smoke runs.

## Current Verified Posture

| Area | Status |
|---|---|
| Native Postgres path | Verified locally |
| Backend default tests | Passed: `42` suites, `287` tests |
| Runtime doctor | Implemented |
| Offline fixture mode | Implemented and explicit |
| Production fail-closed guards | Implemented for key provider/secrets paths |
| Resolution-service DB guard | Verified |
| Evidence/claim/trust/memory E2E slice | Verified |

## Not Yet Production Ready

- Real deployment secrets and Vault/KMS posture must be supplied and verified outside git.
- Kafka, Redis, Vault, Prometheus/Grafana, and full Docker production smoke must be rerun and pass with real services.
- Production mode must not rely on env/local secret fallback, deterministic LLM, mock web, in-memory cache, or in-process event bus.
- Source-independence scoring and remaining firewall tests must be reconciled with the current actor model.
- Disabled migrations remain unsupported/future.
- The full L0-L14 build ledger is incomplete: `18/67 verified`.

## Production Gate

Before any production claim, all of the following must pass:

```bash
make doctor-production
make production-posture
make docker-production-smoke
cd backend && npm run build
cd backend && npm test -- --runInBand --forceExit
python3.13 scripts/build_ledger.py status
```

Expected production behavior is fail-closed when critical dependencies or real providers are missing.

## Current Truth Sources

- [BUILD_LEDGER.yaml](BUILD_LEDGER.yaml)
- [docs/CURRENT_IMPLEMENTATION_REALITY.md](docs/CURRENT_IMPLEMENTATION_REALITY.md)
- [reports/system_run/latest/AGENTCO_POST_FIX_VERIFICATION_REPORT.md](reports/system_run/latest/AGENTCO_POST_FIX_VERIFICATION_REPORT.md)
