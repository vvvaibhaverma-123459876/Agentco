# AgentCo

AgentCo is being built as an evidence-governed, calibration-driven AI civilization: a runtime where agents act as bounded citizens, claims require evidence, predictions are pre-registered and independently resolved, trust changes only from scored outcomes, and learning is promoted through audited memory.

This repository is a local production-posture runnable research/runtime system. It is **not a certified hosted production operation** until a real deployment has continuous SLOs, incident response, disaster recovery, backups, monitoring response, and long-running operational evidence.

## Current Verdict

| Area | Current state |
|---|---|
| Build ledger | `67/67 verified (100%)`; termination predicate true |
| Local backend | Runnable against native Postgres with default backend tier passed |
| Release gates | Firewall, sandbox, credential key-independence, reachability, no-stub, no-simulation, and dependency-audit gates passed |
| OpenAI path | Live connectivity, goal-run verifier, and civilization vertical slice have passed when credentials are present |
| Docker/Kafka/Redis/Vault/observability | Local production smoke passed for Postgres, Redis, Kafka, Vault, Prometheus, Grafana, and Docker Compose probes |
| Mission progress | Evidence-governed civilization path verified; long-horizon generality, durable real-world self-improvement, broad open-domain transfer, and hosted production operations remain partial or unproven |
| Production | Local production posture passes; hosted production certification remains unproven |

The source of truth for implementation status is:

- [BUILD_LEDGER.yaml](BUILD_LEDGER.yaml)
- [docs/CURRENT_IMPLEMENTATION_REALITY.md](docs/CURRENT_IMPLEMENTATION_REALITY.md)
- [reports/system_run/latest/mission_progress_verification.md](reports/system_run/latest/mission_progress_verification.md)
- [reports/system_run/latest/PRODUCTION_INFRA_SMOKE_REPORT.md](reports/system_run/latest/PRODUCTION_INFRA_SMOKE_REPORT.md)

Older phase reports are historical artifacts. If they conflict with the build ledger or current implementation reality, treat them as superseded.

## What Is Real Now

- Native Postgres migrations and schema checks.
- Backend Fastify service and frontend build path.
- Runtime doctor and explicit mode/fallback reporting.
- Immutable audit log and canonical event log with transactional outbox.
- Actor identity, authority chains, role/permission checks, public-key lifecycle, and internal hash-chain anchors.
- Resource ledger reservations and spend guardrail integration.
- Canonical evidence registry with event/audit provenance.
- Claim grounding validation: supported claims require registered evidence IDs and support snippets that are token-subsequences of registered evidence.
- Prediction registration and authorized resolution-service path with ordinary-user resolution blocked by DB trigger.
- Persistent trust scoring from resolved predictions into immutable `trust_scores` and reputation events.
- Memory promotion from resolved/scored predictions into append-only `agent_memories`.
- A focused civilization learning E2E slice: evidence -> grounded claim -> prediction -> authorized resolution -> trust score -> memory promotion -> event log -> audit log.
- Deterministic source-discovery unit verification without depending on public internet reachability; production source discovery still probes live URLs.
- L11 conflict judiciary, L12 skill library, L6 proof of competence, L13 capability expansion gate, and VCA promotion loop verified through focused tests.
- L14 coordinator graph/tick API routes, bounded scheduler controls, and reachability checks across the current core service graph.
- Mission progress evidence gate that separates verified claims from partial or unproven long-horizon claims.
- Docker production smoke for local infrastructure services when Docker and configured secrets are available.

## What Is Partial

- AgentCo has not proven progressively more general intelligence over long time horizons.
- It has not proven durable autonomous improvement from repeated real-world operation.
- Broad open-domain transfer remains partial; current evidence is bounded verifier and smoke-benchmark evidence, not proof of general intelligence.
- Hosted production operations are not certified: SLOs, disaster recovery, backups, monitoring response, incident response, and long-running operations evidence remain required.
- Real-world production source discovery still depends on live URL reachability and configured external services.
- Disabled migrations under `backend/src/db/unsupported_migrations/` remain unsupported/future.

## What Is Test-Only Or Simulated

- `MockWebAdapter` is test-only.
- Deterministic LLM/provider fixtures are allowed only in offline/CI/test paths.
- Offline fixture reports and benchmark smoke outputs are not production evidence.
- Fallback cache/event/metrics providers are explicit local/offline fallbacks, not real infrastructure.

Production-like modes must not silently use simulated or fallback providers for protected paths.

## Quick Start: Local Native

Prerequisites:

- Node/npm
- Python 3.13
- Native Postgres reachable via `DATABASE_URL`
- Optional OpenAI-compatible key in `.codex.env` for live LLM verification

```bash
set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"

cd backend
npm install
npm run db:migrate
npx tsc --noEmit
npm test -- --runInBand --forceExit
```

Recent verified backend default result:

```text
42 test suites passed
287 tests passed
1 suite skipped
5 todos
```

## Runtime Doctor

```bash
make doctor
make doctor-offline
make run-best-effort
make run-offline-fixture
```

Production posture is intentionally stricter:

```bash
make doctor-production
make production-posture
```

Production-like startup must fail closed if required real services, secrets, auth, or providers are missing.

## Focused Civilization Learning Slice

The current verified E2E backend slice is covered by:

```bash
cd backend
npx jest tests/civilization-learning-e2e.test.ts --runInBand --forceExit
```

It proves:

```text
registered evidence
grounded supported claim
pre-registered prediction
ordinary DB user cannot resolve
resolution_service role resolves
Brier/log score recorded
trust score inserted
prediction lesson memory promoted
event_log and decision_log records written
```

## Build Ledger

Use the ledger commands to inspect what is verified and what remains:

```bash
python3.13 scripts/build_ledger.py status
python3.13 scripts/build_ledger.py remaining
```

Do not mark a module complete unless real tests prove the actual runtime path. No stubbed, placeholder, or simulated production behavior is accepted.
