# Current Implementation Reality

**Date:** 2026-06-30  
**Branch:** `main`  
**Current build-ledger status:** `67/67 verified (100.0%)`

This document supersedes older completion/prod-readiness claims when they conflict with current tests, `BUILD_LEDGER.yaml`, or reports under `reports/system_run/latest/`.

## Verdict

AgentCo is a runnable local-native research/runtime system with all current build-ledger items verified. It is not a certified production deployment until a real production environment is continuously available and the production posture gate is green at run time.

| Verdict area | Status |
|---|---|
| Offline fixture | Runnable when explicitly selected and labeled simulated/offline |
| Local native | Runnable with native Postgres |
| Backend default tier | Passed: `42` suites, `287` tests |
| No-stub/no-simulation ledger gates | Green: `0` findings in both gates |
| Release safety gates | Firewall, sandbox breach, credential key-independence, and reachability green |
| Dependency audit | Backend and frontend npm audits report `0 vulnerabilities` |
| Local observability compose | Compose config validates; Prometheus, Grafana, and OTel bind sources exist |
| Durable standalone smoke | Shared runtime shutdown closes Kafka producer state and DB pool; smoke exits after attested task |
| Validation connector evidence | Live endpoint success is `EXTERNAL-VALIDATED`; configured failures are `LIVE-UNAVAILABLE`; unconfigured CI remains `FIXTURE` |
| Full Docker startup | Passed locally via `make docker-production-smoke`; Postgres, Redis, Kafka, Vault, Prometheus, Grafana, and Docker Compose probes passed |
| Native migration verifier | Passed with runtime-critical task and civilization-routing schema checks |
| Civilization vertical slice | Passed live local slice with Postgres, Kafka, OpenAI chat/embeddings, `resolution_service`, Reserve recomputation, memory promotion, learner candidate, and coordinator tick |
| Backend L14 runtime tick | Passed focused backend route/service tests; coordinator exposes graph/tick API routes and persists a core service-graph tick to Postgres |
| Backend L14 scheduler | Passed bounded scheduler tests; run-once/start/stop and scheduler API routes are verified |
| Build-ledger tooling | Passed architecture report, frontier, DB sync projection, and backend build-status/readiness tests |
| Runtime mode manager | Passed explicit production capability contract, fallback rejection, doctor reporting, and /system capability/readiness tests |
| Feature gates | Passed runtime-derived feature decisions, env overrides, production fail-closed rules, and /system feature-gate reporting |
| L3 event bus | Passed real Kafka/Postgres publish, event-history persistence, duplicate idempotency, and HMAC envelope tests |
| Determinism guard | Passed backend service/CLI production rejection and Python best-effort offline fallback controls |
| Idempotency store | Passed shared Postgres request-hash replay, conflict rejection, completed-response replay, and event-log lifecycle tests |
| Constitution service | Passed canonical constitution hashing, append-only activation, allowed/prohibited change validation, and protected-surface checks |
| Protected surface enforcer | Passed self-modification candidate scanning, blocked validation persistence, and audit-event recording |
| L10 governance controls | Passed risk-tier classification and kill-switch activation/deactivation with event-log lifecycle records |
| L14 reachability gate | Passed expanded L0-L14 table and route reachability checks for core runtime, identity, resources, events, governance, learning, tasks, institutions, and coordinator trace nodes |
| L12 learning candidate registry | Passed learner replay-batch creation, candidate/artifact persistence, event-log lifecycle records, and no-deployment candidate status checks |
| L7 agent registry | Passed canonical actor/agent identity materialization, route identity exposure, and dispatch task-type rejection |
| L8 durable task execution | Passed registered-agent enforcement, durable health-check execution, audit/provenance persistence, and Python executor validation |
| L8 reasoning service router | Passed real adapter routing with completed durable route-task provenance for service selection |
| L8 action executor | Passed DB-backed action execution, evidence event-log provenance, and grounded claim persistence checks |
| L8 saga coordinator | Passed DB-backed saga execution, ordered step lifecycle, transactional saga event/outbox emission, and compensation marking checks |
| L8 civilization-aware RAG | Passed canonical vector-index retrieval, indexed evidence consensus, external retrieval fallback, and TypeScript checks |
| L9 institution registry | Passed canonical institution actor creation, mandatory department creation, and full work-request/autonomy feedback cycle |
| L9 institution decisions | Passed reputation-weighted voting, governance audit rows, immutable decision-log records, and coalition decision integration |
| L9 core institutions | Passed canonical creation of Production, Verification, Audit, Adversarial, and Improvement departments for each institution |
| L13 domain registry | Passed trust-threshold-gated domain activation, mandatory core-institution checks, event-log/outbox provenance, and TypeScript checks |
| L13 generality metric tracker | Passed active-domain-only metric recording, cross-domain smoke scoring, domains-above-baseline aggregation, event-log/outbox provenance, and TypeScript checks |
| L12 sandbox executor | Passed 12/12 adversarial wall tests for frozen-data writes, resolver import/introspection, escape imports, answer smuggling, and valid resolver usage |
| L12 regression test generator | Passed deterministic learner-candidate regression case generation, idempotency, event-log/outbox provenance, and TypeScript checks |
| L5 claim registry | Passed registered-evidence-only supported claim creation and grounded snippet validation |
| L5 prediction ledger | Passed pre-registered prediction write, ordinary-user resolution block, `resolution_service` update path, and event/audit records |
| L5 source independence | Passed Gate 2 rejection of same-source, derivative, same-group, fixture, simulated, and contradictory evidence before promotion or resolution |
| L4 vector index | Passed registered-evidence-only vector indexing, Postgres cosine retrieval, event-log/outbox provenance, and TypeScript checks |
| L6 calibration scorer | Passed Brier, log score, ECE, over/underconfidence, reliability-bin, horizon-breakdown, and post-hoc exclusion checks |
| L6 proof of calibration | Passed Reserve signed credential, public verification, key-independent recomputation, tamper-evidence, and agent credential integration tests |
| L6 commitment chain | Passed append-only prediction-chain log, chain-head recomputation, and tamper-divergence checks |
| L7 citizen runtime | Passed BaseAgentV2 contract, trusted-confidence, human-approval, DB resource-ledger spend, Reserve credential, and dispatch E2E checks |
| L7 role separation | Passed role-derived authority-chain decisions, protected RBAC/policy surface blocks, ConfigAgent self-modification blocks, and tool-denial audit checks |
| L11 conflict judiciary | Passed contradiction dispute opening, ruling issuance, duplicate-ruling blocking, precedent storage/lookup, and event-log/outbox provenance |
| L12 skill library | Passed versioned skill registration from simulation-trained learner candidates with generated regression coverage |
| L6 proof of competence | Passed threshold-gated proof minting for registered skill regressions with canonical proof hashes |
| L13 capability expansion gate | Passed active-domain/current-skill/proof-required expansion approval with generality metric updates |
| VCA promotion loop | Passed protected-surface scan, competence proof, capability expansion approval, and idempotent promotion persistence |
| Mission progress evidence gate | Passed current evidence aggregation while preserving unproven/partial status for long-horizon generality, repeated real-world improvement, broad open-domain transfer, and hosted production certification |
| Production | Not certified |
| Full civilization goal | Build-ledger complete; production run still depends on live infrastructure and deployment operations |

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
| Runtime schema compatibility | Additive migrations repair legacy `departments.institution_id` drift and expose `agent_task_events` as a canonical view over the existing task event log |
| Civilization/Reserve schema compatibility | Backend migrations now include `prediction_ledger.hardness`, `prediction_ledger.consequence`, and strict `resolution_service` grants required by the canonical civilization verifier |

## Current Real Capabilities

- Native Postgres schema and migrations.
- Native migration verification now checks `agent_tasks`, `agent_task_events`, work-request tables, department institution routing columns, allocation history, and hierarchy columns.
- Backend build and default Jest tier.
- Runtime doctor and mode/fallback reports.
- OpenAI-compatible live path in verifier scripts when credentials are present.
- Event/audit provenance for canonical evidence and learning-loop state changes.
- DB-enforced prediction-ledger resolution firewall.
- Append-only memory promotion for resolved prediction lessons.
- Release-gate verifier for firewall, self-coding sandbox breach tests, and credential key-independence.
- Backend/frontend dependency audit clean at moderate-or-higher severity after targeted upgrades.
- Local Docker Compose observability config for Prometheus, Grafana datasource provisioning, and OTel collector.
- Local Docker startup verification for the compose infrastructure services.
- Durable execution standalone smoke command with shared shutdown cleanup.
- Validation suite live connector separation for configured external endpoints.
- Canonical civilization vertical-slice verifier across reasoning, evidence indexing, prediction, resolution, trust, credential, memory, learning, canary, and coordinator stages.
- Backend L14 runtime graph/tick API routes and reachability tick across core durable-task, institution, constitution, evidence, resolution, trust, memory, learning, and runtime-trace tables.
- Backend L14 bounded scheduler with run-once/start/stop controls and API route coverage.
- Build-ledger architecture report generation with layer rollups, ready frontier, gate findings, DB sync projection, and backend build-status/readiness surfaces.
- Runtime mode classification with explicit production capability contracts for backend providers and Python doctor service checks.
- Feature-gate decisions for live LLM, DB writes, external web, simulated data, self-modification, and civilization scheduler controls.
- Event bus signed envelope publishing to Kafka with idempotent `event_history` persistence and HMAC validation.
- Deterministic provider and offline fixture fallback guards across backend runtime entry points and Python orchestration.
- Shared idempotency store for stable request-hash replay, conflict detection, completed responses, and canonical event-log lifecycle records.
- Calibration constitution service with canonical version integrity, active constitution selection, and protected surface enforcement.
- Protected surface enforcement for self-modification candidates and standalone protected-surface helper checks with audit records.
- Governance risk-tier classifier and kill-switch controls for fail-closed runtime governance.
- Expanded L14 coordinator reachability gate across required tables and route declarations for the core L0-L14 runtime graph.
- Learning candidate registry creates schema-compatible replay batches, learner runs, candidate artifacts, canonical event-log lifecycle records, and ready-for-eval candidates without direct promotion or deployment.
- Agent registry materializes runnable agents into canonical `actors` and `agent_identities`, exposes actor identity state through `/api/agents`, and keeps dispatch gating tied to registered task types.
- Durable task execution enforces registered agents and allowed task types before queue/run, records audit and action-attestation pointers on completed tasks, and keeps the Python executor on the canonical `agent_tasks`/identity-backed path.
- Reasoning service routing records each civilization service invocation as a completed durable task before calling the selected real adapter.
- Action execution persists canonical action rows, registers evidence through the event/audit-backed evidence registry, and only creates supported claims from registered evidence snippets.
- Saga coordination persists saga executions and ordered steps, emits saga lifecycle events through the canonical event log and transactional outbox in the same DB transaction, completes all-success workflows, and marks completed prior steps for compensation when a later step fails.
- Civilization-aware RAG retrieves registered evidence from the canonical Postgres vector index when an embedder is supplied, surfaces indexed evidence as consensus sources, and preserves external Wikipedia/arXiv retrieval as a fallback path.
- Institution registry creates active institution actors before institution rows, provisions mandatory departments, and supports the existing work assignment/autonomy feedback loop.
- Institution decisions persist reputation-weighted votes, governance audit rows, final decisions, and immutable decision-log entries while feeding coalition/reputation workflows.
- Core institutions now have verified mandatory department provisioning through the canonical institution creation path.
- Domain registry activates new domains only when a core institution with all mandatory departments exists and the latest non-downgraded trust score for the domain meets the onboarding threshold.
- Generality metric tracking persists cross-domain benchmark runs only for active registered domains, records per-domain scores, computes domains-above-baseline, and keeps deterministic smoke results labeled as smoke rather than proof of general intelligence.
- Sandbox execution exposes only the sealed resolver scoring API to generated code, blocks forbidden imports and resolver internals, and passed the adversarial wall suite against the read-only frozen NSE data mount.
- Regression test generation derives metric-floor, artifact-integrity, and simulation-guard cases from learner candidate metrics/artifact hashes, persists them idempotently, and emits canonical event/outbox provenance without promoting candidates.
- Claim registry behavior is verified through evidence-backed action execution and token-subsequence grounding checks; unsupported or unregistered evidence claims are blocked.
- Prediction ledger behavior is verified through the civilization learning e2e path from grounded claim to authorized resolution, trust scoring, memory promotion, event log, and audit log.
- Source independence behavior is verified through deterministic source discovery and Python Gate 2 evidence-kernel tests covering circular resolution, derivative mirrors, same-group sources, simulated/fixture evidence, contradiction blocking, and external independent promotion.
- Vector index behavior is verified through canonical registered-evidence embeddings stored as portable Postgres dimension rows, SQL cosine similarity retrieval, and event-log/outbox provenance for each index update.
- Calibration scoring behavior is verified through Python calibration tests that exclude unresolved/post-hoc records and roll up Brier score, log score, ECE, over/underconfidence, reliability bins, and horizon-specific Brier means.
- Proof-of-calibration behavior is verified through the full Reserve suite against an isolated `reserve_test` Postgres database, including credential issuance/persistence, Ed25519/HMAC verification, raw-row recomputation without signing keys, commitment-chain tamper detection, and BaseAgentV2 Reserve credential integration.
- Commitment-chain behavior is verified through Reserve tamper-evidence tests that append resolved predictions into `prediction_chain_log`, recompute the chain head from public ledger rows, block chain-row mutation, and detect altered prediction outcomes or probabilities.
- Citizen runtime behavior is verified through runtime and agent tests covering claim pre-registration, trusted-confidence execution, signed prompt-versioned envelopes, human-approval blocking, resource-ledger-backed LLM spend reservations, Reserve credential participation, and DB/Kafka-backed dispatch.
- Role separation behavior is verified through DB-backed identity authority tests, protected-surface enforcement, ConfigAgent self-modification and permission-change approval gates, and real tool permission denial before handler side effects.

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

The latest mission progress verifier is documented in
`reports/system_run/latest/mission_progress_verification.md`. It ties the project
mission to explicit evidence claims and intentionally keeps long-horizon
generality, repeated real-world autonomous improvement, broad open-domain
transfer, and hosted production operations as partial/unproven until the required
longitudinal or hosted evidence exists.

The latest Docker production-infrastructure smoke is documented in
`reports/system_run/latest/PRODUCTION_INFRA_SMOKE_REPORT.md`. On 2026-06-30,
Docker Desktop was started, `.env.production.local` was loaded, production
secrets were present with values suppressed, and Postgres, Redis, Kafka, Vault,
Prometheus, Grafana, and Docker Compose probes passed. The posture gate returned
`can_continue=true`.

## Partial Or In Progress

- Full L0-L14 build ledger: `67/67` verified; current work shifts from build completion to production operation hardening.
- Source independence scoring and Python independence tests are verified in the current ledger through deterministic source discovery and Gate 2 evidence-kernel tests, but broader live-source diversity remains an operational measurement target.
- Production observability stack, Vault, Kafka, Redis, and Docker services pass the latest local production posture smoke; hosted production operations still require deployment-specific SLO, backup, DR, and monitoring evidence.
- Cross-domain transfer has a bounded live verifier and deterministic smoke benchmark, but it is not a demonstrated general-intelligence metric.
- Continuous learning has bounded live lesson-reuse verification, but not long-horizon autonomous improvement measurement.
- Some older services are implemented but not yet proven through the current canonical coordinator path.
- Release-gate reachability is green for required backend route clusters and L14 runtime reachability endpoints; it still does not prove every disabled/legacy route or every internal behavior path.
- The canonical civilization vertical slice and L14 reachability graph are verified, but long-running production behavior still needs durable multi-society runtime traces and repeated operational evidence.

## Unsupported Or Future

- Disabled migrations in `backend/src/db/unsupported_migrations/`.
- Durable `review`/`decision` task types without real services.
- Production use with env/local secret fallback.
- Production startup without required deployment secrets.
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

Migration contract check:

```bash
make verify-migrations-native
python3.13 -m pytest tests/test_verify_migrations_native.py -q
```

Release gate check:

```bash
make release-gates
python3.13 -m pytest tests/test_verify_release_gates.py reserve/tests/test_key_independence_safe.py -q
```

Mission progress evidence check:

```bash
make mission-progress
python3.13 -m pytest tests/test_verify_mission_progress.py -q
```

Focused current civilization slice:

```bash
python3.13 scripts/verify_civilization_vertical_slice.py --update-ledger

cd backend
npm test -- tests/civilization-runtime-reachability.test.ts --runInBand --forceExit
npm test -- tests/civilization-runtime-routes.test.ts --runInBand --forceExit
npm test -- tests/civilization-scheduler.test.ts --runInBand --forceExit

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
