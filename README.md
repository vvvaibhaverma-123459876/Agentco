# Agentco

Agentco is an evidence-governed control plane for autonomous systems: if an agent acts through Agentco, you can inspect the policy that governed it, the evidence it relied on, the calibration record behind its confidence, the attested environment it ran in, and the exact conditions under which it was permitted to affect the world.

## Status

Agentco is under refoundation. Claims in this repository use explicit status labels:

- **REAL**: implemented and proven by passing tests on real or external evidence.
- **FIXTURE**: implemented and proven only against internally-authored deterministic fixtures.
- **EXTERNAL-VALIDATED**: proven against an external benchmark or independent ground truth the repo did not author.
- **PARTIAL**: partially implemented; the implemented slice is specified.
- **FACADE**: named or scaffolded but not functional.
- **BROKEN / MISSING / DEPRECATED**: self-explanatory.

The long-range R&D vision is kept separately in [NORTH_STAR.md](docs/refoundation/NORTH_STAR.md). Product surfaces should only claim capabilities proven by tests.

## Current Proven Surface

| Capability | Status | Proof |
|---|---|---|
| Calibration, trusted confidence, reality firewall, learning-loop regression slice | **FIXTURE** | `python3 -m pytest calibration runtime learning synthesis evals/regression -q` |
| Backend audit log, event bus, memory store, override queue services | **PARTIAL** | `backend/tests/integration/*` require local Postgres/Kafka setup |
| Frontend operator dashboard | **PARTIAL** | Next.js source exists; dependency install required before TS/build verification |
| Durable execution, external attestation, canonical source independence, full governance DSL | **MISSING** | Tracked in [IMPLEMENTATION_MATRIX.md](docs/refoundation/IMPLEMENTATION_MATRIX.md) |

## Local Development

```bash
make dev
make smoke
```

`make dev` installs frontend/backend dependencies and starts local infrastructure. `make smoke` runs the local Python smoke slice and checks backend/frontend type surfaces when dependencies are installed.

For write-auth testing, set the same key in backend and frontend:

```bash
export AGENTCO_API_KEY=dev-agentco-key
export NEXT_PUBLIC_AGENTCO_API_KEY=dev-agentco-key
```

When `AGENTCO_API_KEY` is unset, backend write-auth is disabled for local bring-up.

## Architecture and Refoundation Docs

- [True North](docs/refoundation/AGENTCO_TRUE_NORTH.md)
- [Current State Audit](docs/refoundation/CURRENT_STATE_AUDIT.md)
- [Implementation Matrix](docs/refoundation/IMPLEMENTATION_MATRIX.md)
- [Build Plan](docs/refoundation/BUILD_PLAN.md)
- [Layer Contracts](docs/refoundation/LAYER_CONTRACTS.md)
- [Repo Truth Ledger](docs/refoundation/REPO_TRUTH_LEDGER.md)
- [Validation Plan](docs/refoundation/VALIDATION_PLAN.md)
- [Testing](docs/refoundation/TESTING.md)
- [Session Handoff](docs/refoundation/SESSION_HANDOFF.md)
