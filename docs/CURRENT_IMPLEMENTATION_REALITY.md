# Current Implementation Reality

**Date:** 2026-06-29  
**Branch:** `fix/runtime-integrity-and-production-honesty`  
**Current build-ledger status:** `18/67 verified (26.87%)`

This document supersedes older completion/prod-readiness claims when they conflict with current tests, `BUILD_LEDGER.yaml`, or reports under `reports/system_run/latest/`.

## Verdict

AgentCo is a runnable local-native research/runtime system with important production guards, not a certified production deployment.

| Verdict area | Status |
|---|---|
| Offline fixture | Runnable when explicitly selected and labeled simulated/offline |
| Local native | Runnable with native Postgres |
| Backend default tier | Passed: `42` suites, `287` tests |
| Production | Not certified |
| Full civilization goal | In progress |

## Verified Since Runtime-Integrity Work

| Layer/item | Verified behavior |
|---|---|
| L1 Identity/authority | Actor registry, authority chain decisions, delegation, public-key lifecycle |
| L2 Resources | Resource ledger reservations and spend guardrail integration |
| L3 Events/audit | Event log, transactional outbox, audit log, internal hash-chain anchors |
| L4 Evidence | Canonical evidence registry writes event/audit provenance |
| L4 Claim grounding | Supported claims require registered evidence and grounded snippets |
| L5 Resolution | Prediction resolution requires `resolution_service`; ordinary user updates are blocked |
| L6 Trust | Resolved predictions create immutable trust-score windows and reputation events |
| L4 Memory promotion | Resolved/scored predictions promote append-only prediction lessons |
| E2E learning slice | Evidence -> grounded claim -> prediction -> resolution -> trust -> memory -> audit/event |
| Source discovery tests | Unit verification is deterministic; production still does live reachability checks |

## Current Real Capabilities

- Native Postgres schema and migrations.
- Backend build and default Jest tier.
- Runtime doctor and mode/fallback reports.
- OpenAI-compatible live path in verifier scripts when credentials are present.
- Event/audit provenance for canonical evidence and learning-loop state changes.
- DB-enforced prediction-ledger resolution firewall.
- Append-only memory promotion for resolved prediction lessons.

## Latest Live OpenAI Evidence

The latest live OpenAI + native Postgres verifier is documented in
`reports/system_run/latest/LIVE_OPENAI_SYSTEM_BEHAVIOR_REPORT.md`.

That run passed the current vendor-risk goal verifier with `mode=live_openai`,
`simulated=false`, DB-backed prediction/audit/event writes, and resolution/scoring.
It proves the narrow live verifier path works; it does not prove full production
readiness, durable cross-domain transfer, or the complete civilization goal.

The latest live cross-domain verifier is documented in
`reports/system_run/latest/live_cross_domain_goal_run.md`. It ran four bounded
synthetic domains with OpenAI and native Postgres persistence:

- `vendor_risk`
- `medical-triage-safe-info`
- `financial-risk-disclosure`
- `code-change-risk-review`

That verifier proves bounded live cross-domain routing/evidence/calibration
checks for the current fixtures. It does not prove open-ended general
intelligence or durable transfer beyond those fixtures.

The latest memory-influence verifier is documented in
`reports/system_run/latest/memory_influence_verification.md`. It creates a real
resolved prediction lesson, retrieves it through `MemoryReader`, injects it into
a later live OpenAI prompt, and validates that the model copies the lesson
marker, escalates, and applies the confidence cap. This proves bounded lesson
reuse for one fixture, not open-ended autonomous self-improvement.

## Partial Or In Progress

- Full L0-L14 architecture: `18/67` verified, many layers remain in progress.
- Source independence scoring and Python independence tests need reconciliation with current actor model.
- Production observability stack, Vault posture, Kafka/Redis real-service path, and Docker production smoke are not recently re-proven.
- Cross-domain transfer has a bounded live verifier and deterministic smoke benchmark, but it is not a demonstrated general-intelligence metric.
- Continuous learning has bounded live lesson-reuse verification, but not long-horizon autonomous improvement measurement.
- Some older services are implemented but not yet proven through the current canonical coordinator path.

## Unsupported Or Future

- Disabled migrations in `backend/src/db/unsupported_migrations/`.
- Durable `review`/`decision` task types without real services.
- Production use with env/local secret fallback.
- Silent fallback to deterministic LLM or mock web adapter in staging/production.
- Treating offline fixture results as real infrastructure evidence.

## Current Must-Pass Commands

```bash
set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"

cd backend
npm run db:migrate
npx tsc --noEmit
npm test -- --runInBand --forceExit
```

Focused current civilization slice:

```bash
cd backend
npx jest tests/civilization-learning-e2e.test.ts \
  tests/claim-grounding.test.ts \
  tests/evidence-registry.test.ts \
  tests/action-loop.test.ts \
  --runInBand --forceExit
```

Runtime checks:

```bash
make doctor
make doctor-offline
make run-best-effort
make verify-resolution-service
```

## Documentation Rule

Historical reports can remain for auditability, but they must not be read as current truth when they claim production completion or full civilization completion. Current truth comes from:

1. `BUILD_LEDGER.yaml`
2. This document
3. Latest verification reports under `reports/system_run/latest/`
4. Actual command output from current tests
