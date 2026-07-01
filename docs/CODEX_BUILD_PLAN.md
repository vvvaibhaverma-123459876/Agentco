# PART B — CODEX END-TO-END PRODUCTION BUILD PLAN

> **Current build status (2026-07-01):** this plan remains the target process and historical build contract. The durable ledger currently reports `67/67 verified (100%)` with the termination predicate met; see `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`. Mission-level claims still distinguish verified evidence-governed operation from partial or unproven long-horizon generality, repeated real-world self-improvement, broad open-domain transfer, and hosted production operations.

## B.0 Codex operating contract (read first, obey always)

1. **Completeness only.** No stub, mock-in-prod, placeholder, `NotImplementedError`, `pass`-only body,
   `TODO`, `FIXME`, "later", commented-out "to be done," or fabricated/simulated result in any runtime
   path. If a thing is in scope, it is built fully and integrated, or it is not marked done.
2. **Integrated only.** A component is not "done" until it is reachable and exercised by the L14
   coordinator through the universal lifecycle (A.5), covered by integration + e2e tests, and emitting
   the required events/audit.
3. **Real only.** Real Postgres, real migrations, real event bus, real secret store, real LLM
   provider, real external resolution source, real vector index. Fixtures exist only inside the test
   suite and only behind `runtime_mode in (offline_fixture, ci_smoke)`; production fails closed if a
   real dependency is missing.
4. **Maintain the ledger.** After every unit of work, update `BUILD_LEDGER.yaml` (B.3) atomically with
   the commit. The ledger is the single source of truth for "what is built / what remains."
5. **Do not stop.** Loop (B.4) until the termination predicate holds. On failure, debug and retry;
   never mark incomplete work as done; never silence a failing gate.
6. **No silent scope change.** Build exactly the ledger. Scope grows only via the explicit `decompose`
   step (B.4), which adds ledger items (additive-only, consistent with A.0 principle 3).
7. **Additive to the civilization.** Never delete a civilization subsystem to make a test pass.

## B.1 Definition of Done (DoD)

**Global DoD — a ledger item is `VERIFIED` only when all hold:**
- code complete, no banned markers (B.2), typed, linted, formatted;
- unit tests + integration tests + (where applicable) e2e slice cover it; coverage ≥ threshold
  (lines ≥ 90% for L0–L6 core, ≥ 80% elsewhere; branch ≥ 75%);
- migrations apply forward cleanly on an empty DB and on the previous schema;
- it emits the required events and writes audit rows in the same transaction;
- it is reachable from the L14 coordinator (reachability gate, B.8) — unless it is itself L0/L1
  bootstrap;
- all constitutional invariants touching it pass (firewall, role-separation, fail-closed);
- observability present (logs/metrics/traces with correlation_id);
- the relevant must-pass suites (B.7) are green;
- the change is committed with the ledger update in the same commit.

**Per-artifact DoD (examples).** A *table*: migration + indexes + constraints + a repository module
with real queries + tests that exercise constraints (e.g. producer≠resolver rejection). A *service*:
real implementation + API (if exposed) + events + audit + tests + wired into the coordinator. A
*state machine*: transition table + guards + illegal-transition rejection test + audit on transition.

## B.2 Anti-stub / anti-simulation enforcement (CI gates)

These run in CI and locally via `make verify`. Any hit is a **release-blocking** failure.

```bash
# 1. Banned markers in runtime (non-test) code
grep -RInE 'TODO|FIXME|XXX|HACK|NotImplementedError|raise NotImplemented|placeholder|stub|mock(?!ito)|simulate|simulated|fake_|dummy|to ?be ?done|later\b' \
  --include='*.ts' --include='*.py' src/ backend/src/ civilization/ \
  | grep -vE '/(tests?|__tests__|fixtures)/' && exit 1 || true

# 2. No simulated reasoning method (grounded in the de-simulate fix)
grep -RInE "method\s*[:=]\s*['\"]simulated['\"]|Simulated answer" src/ backend/src/ civilization/ \
  | grep -vE '/(tests?|fixtures)/' && exit 1 || true

# 3. Empty/stub bodies (python) and throw-not-implemented (ts)
grep -RInE 'def [a-zA-Z_]+\([^)]*\):\s*(\.\.\.|pass)\s*$' --include='*.py' src/ civilization/ && exit 1 || true
grep -RInE 'throw new Error\((["'\''])not implemented' --include='*.ts' backend/src/ && exit 1 || true
```

Plus programmatic gates (scripts, not greps):
- **Reachability gate** (B.8): every service in the L9/L8/L12 registries must be reachable from the
  L14 coordinator via a static call-graph + a runtime trace of the e2e slice. Unreachable ⇒ fail.
- **No-fallback-on-protected gate**: in `production` mode, if any protected-surface handler is reached
  while its required service is in fallback, the test fails.
- **Credential key-independence gate**: CI recomputes proof-of-calibration from public ledger rows
  with no signing key and asserts it matches the signed credential.
- **Firewall gate**: the resolution-independence suite (including the three currently-failing Python
  tests) must be green.
- **Sandbox gate**: the 12/12 self-coding breach tests must be green.
- **No-result-fudging gate**: benchmark/eval outcomes are written verbatim even when they falsify a
  hypothesis (honesty rule, grounded in the NSE falsification precedent); a test injects a known-bad
  arm and asserts it is recorded as worse, not "corrected."

## B.3 The Build Ledger (what is built / what remains)

A single machine-readable file at repo root, mirrored into the `migrations`-adjacent DB table
`build_ledger` for runtime introspection. Codex updates it atomically with each commit.

```yaml
# BUILD_LEDGER.yaml — single source of truth for build progress
meta:
  schema_version: 1
  generated_by: codex
  last_updated: 2026-06-26T00:00:00Z
  termination_predicate_met: false
layers:
  L0_runtime_substrate:
    status: in_progress            # not_started | in_progress | done | verified | blocked
    items:
      - id: L0.RuntimeModeManager
        status: verified
        depends_on: []
        artifacts: [src/runtime/mode_manager.ts]
        tests: [tests/runtime/mode_manager.spec.ts]
        events: []
        gates_passed: [lint, unit, integration, no_stub]
        notes: ""
      - id: L0.MigrationRunner
        status: in_progress
        depends_on: [L0.ConfigLoader]
        artifacts: []
        tests: []
        events: []
        gates_passed: []
        blockers: []
  L5_claims_predictions:
    status: not_started
    items:
      - id: L5.SourceIndependenceChecker
        status: not_started
        depends_on: [L1.ActorRegistry, L3.EventLog, L4.EvidenceRegistry]
        acceptance:
          - producer_neq_resolver_enforced_in_db
          - resolution_requires_independent_evidence
          - three_python_independence_tests_green
# ... one block per layer L0..L14 + cross_cutting + capability_engine
rollups:
  total_items: 0
  verified: 0
  in_progress: 0
  not_started: 0
  blocked: 0
  percent_verified: 0.0
gates:
  no_stub: unknown
  reachability: unknown
  firewall: unknown
  sandbox_breach: unknown
  credential_key_independence: unknown
  e2e_civilization_slice: unknown
```

**Ledger rules.**
- Every buildable thing in Part A appears as an `item` with `depends_on`.
- `status` advances only forward to `verified` and only when DoD (B.1) holds; it may move *back* to
  `in_progress`/`blocked` if a gate regresses.
- `rollups` and `gates` are recomputed by `make status` (deterministic from items) — never hand-edited.
- `make remaining` prints the topologically-sorted list of not-yet-`verified` items whose deps are
  satisfied (the work frontier).
- The DB mirror lets the running civilization answer `GET /system/build-status`.

## B.4 The autonomous build loop (do not stop until done)

```
INITIALIZE:
  ensure repo, infra (B.5), and BUILD_LEDGER.yaml exist; if ledger missing, GENERATE it from Part A.

LOOP:
  state = load BUILD_LEDGER.yaml
  if termination_predicate(state): write termination_predicate_met=true; STOP.

  frontier = ready_items(state)          # not verified, all depends_on verified, not blocked
  if frontier empty and unverified_items_exist(state):
      # dependency knot or a too-coarse item
      pick the blocking item; DECOMPOSE it into smaller ledger items (additive); continue.

  item = pick(frontier)                  # deterministic: lowest layer, then declared order
  IMPLEMENT item fully (no stub/sim/partial), integrated into the coordinator path.
  WRITE/UPDATE migrations, events, audit, tests, observability.
  RUN gates: make verify  (lint, types, unit, integration, no_stub, layer-specific must-pass)
  if green:
      RUN affected e2e (and the civilization slice if item is integrative)
      if green: set item.status=verified; update rollups/gates; COMMIT (code+ledger together).
      else: record failure in item.blockers; DEBUG; do NOT mark verified; continue.
  else:
      record failing gate in item.blockers; DEBUG; retry (bounded backoff); never mark verified.

  # Safety: never weaken a gate to pass. If a gate looks wrong, open a ledger item to fix the gate
  # with justification; do not disable it.
```

**Termination predicate (all must hold):**
1. every ledger item `status == verified`;
2. all `gates` green: `no_stub, reachability, firewall, sandbox_breach, credential_key_independence,
   e2e_civilization_slice`;
3. reachability == 100% of registered services from the L14 coordinator;
4. the e2e **civilization vertical slice** (B.8) passes end to end against real services;
5. zero banned markers anywhere in runtime code;
6. coverage thresholds met.

**Resume protocol (after any interruption).** The loop is idempotent: on restart, Codex reloads the
ledger, recomputes the frontier, re-runs `make verify` to detect drift, and continues. No in-memory
state is required; the ledger + git history are the durable state.

## B.5 Infrastructure & runtime prerequisites (real, not simulated)

| Concern | Production requirement | Test-only allowance |
|---|---|---|
| Database | Postgres (with pgvector or a real vector DB) | ephemeral Postgres in CI; never SQLite-as-prod |
| Event bus | real broker (Kafka/NATS/Redis Streams) + transactional outbox | file/in-mem bus only in `ci_smoke` |
| Secrets | Vault/KMS | env provider only in local/offline |
| LLM | real provider key | fixture model only in `offline_fixture` |
| Resolution source | real external oracle/source | recorded fixtures only in tests |
| Vector index | real | — |
| Observability | real metrics/trace backend | console exporter in CI |

**Fixtures vs simulation (the bright line).** A *fixture* is recorded/synthetic data used by a test to
exercise real code paths deterministically. *Simulation* is runtime code returning fabricated results
in place of doing the work. Fixtures are allowed in `tests/`; simulation is banned everywhere by B.2.

## B.6 Phased work breakdown (bottom-up; each phase fully done before the next is "verified")

Phases follow the dependency order. Within a phase, Codex still works item-by-item via B.4; a phase is
`verified` only when all its ledger items are `verified` **and** its phase-exit e2e passes. Phases may
overlap where dependencies allow, but no higher-layer item is `verified` before its `depends_on`.

> Each phase below lists: **Deliverables · Migrations · Events · APIs · Integrations · Tests ·
> Phase-exit acceptance.** "Integrations" means the item is wired into the coordinator path even if the
> coordinator itself is finished later (use a thin real driver, not a stub — e.g. a real CLI invoker).

### Phase 0 — L0 Runtime substrate + cross-cutting foundations
- **Deliverables.** RuntimeModeManager, ServiceDoctor, FallbackManager, ConfigLoader, SecretProvider,
  ClockService, MetricsWriter, HealthRegistry, MigrationRunner, FeatureGateService, DeterminismGuard,
  ConnectionPoolManager, GracefulShutdownController, IdempotencyStore. Observability + security
  scaffolding (real backends). `make verify`, `make status`, `make remaining`, BUILD_LEDGER tooling.
- **Migrations.** `migrations`, `idempotency_keys`.
- **APIs.** `/system/health|capabilities|runtime-mode|fallbacks|version|migrations|build-status`.
- **Tests.** mode selection matrix; fail-closed matrix (every fail-closed rule has a test); migration
  forward/again; determinism guard rejects wall-clock in a protected stub-path *test*.
- **Phase-exit.** Server boots in `production` against real Postgres; capability report accurate;
  fail-closed verified; CI gates wired and green.

### Phase 1 — L1 Identity + authority
- **Deliverables.** ActorRegistry, RoleRegistry, PermissionService, ServiceIdentityVerifier, KeyRing,
  DelegationGrant, AuthorityChain, Session/Credential.
- **Migrations.** actors, agent_identities, service_identities, roles, role_assignments, permissions,
  actor_permissions, sessions, credentials, key_rings.
- **Events.** actor.registered, role.assigned.
- **APIs.** identity actors/roles/verify/keys.
- **Tests.** authorization decision matrix; key rotation/revocation; "evidence reviewer cannot resolve
  own claim" decision; keys never logged (log scan test).
- **Phase-exit.** Every subsequent action can resolve a verified actor + authority.

### Phase 2 — L3 Event log + audit (placed early; everything emits)
- **Deliverables.** EventLog, AuditLog, EventBus, OutboxRelay, DeadLetterQueue, EventReplayer,
  HashChainAnchor, ProjectionStore.
- **Migrations.** event_log, audit_log, outbox, dead_letters, projections.
- **Tests.** transactional outbox (state+event atomic); hash-chain integrity + tamper detection;
  replay rebuilds a projection byte-for-byte; DLQ on poison message.
- **Phase-exit.** "If it changes trust/memory/governance/resources/external state, it emits an event"
  is enforced by a trigger + test.

### Phase 3 — L2 Resources + budgets
- **Deliverables.** ResourceLedger, BudgetAllocator, QuotaManager, CostEstimator, TreasuryService,
  RateLimiter, ReservationService, BackpressureController, CostAttribution.
- **Migrations.** resource_accounts, resource_transactions, budgets, reservations.
- **Tests.** reserve→settle/release idempotency; reservation expiry (no leaks); low-trust → smaller
  budget; failure → budget reduction; backpressure sheds non-protected first.
- **Phase-exit.** No action executes without a successful reservation.

### Phase 4 — L4 Evidence + memory
- **Deliverables.** EvidenceRegistry, SourceFingerprintService, ClaimGroundingValidator,
  ProvenanceService, memory records + promotions, real vector index + EmbeddingRecord,
  MemoryReviewPolicy, ContradictionLink.
- **Migrations.** evidence_items, support_snippets, embeddings, memory_records, memory_promotions,
  contradiction_links.
- **Events.** evidence.attached, memory.candidate_created, memory.promoted, memory.rejected.
- **Tests.** grounding rejects non-substring snippets; raw output cannot enter memory directly; vector
  retrieval returns provenance + trust weight; memory needs all six promotion fields.
- **Phase-exit.** Promotion pipeline (observation→claim→evidence→resolution→promotion) enforced.

### Phase 5 — L5 Claims + predictions
- **Deliverables.** ClaimRegistry, PredictionLedger, ResolutionService, SourceIndependenceChecker,
  ClaimGroundingValidator wiring, PreRegistrationGuard, ResolutionScheduler,
  ResolutionEvidenceCollector.
- **Migrations.** claims, prediction_ledger, prediction_resolutions (+ producer≠resolver constraint).
- **Events.** claim.made, claim.grounded, prediction.registered, prediction.resolved.
- **Tests (release-blocking).** producer≠resolver rejected (DB + service); resolution needs
  independent evidence; **the three currently-failing Python independence tests pass**; post-hoc
  prediction rejected; unsupported claim cannot promote to memory.
- **Phase-exit.** Firewall is enforced end to end.

### Phase 6 — L6 Calibration + trust
- **Deliverables.** CalibrationScorer, TrustScorer, ReputationService, CredentialIssuer,
  ProofOfCalibrationService (key-independent recompute), CommitmentChain, StakingOracle, DecayTracker,
  SurpriseRegister, ProofOfCompetenceService (interface; impl completes in Phase 12/15).
- **Migrations.** trust_scores (unique on actor,domain), calibration_scores, proof_credentials,
  commitments.
- **Events.** trust.updated.
- **Tests.** Brier/log/ECE correctness vs known vectors; per-domain (not global) trust; credential
  key-independence gate; surprise fires on high-confidence false; decay ages stale trust.
- **Phase-exit.** Resolved prediction → score → trust → budget/routing adjustment, fully wired.

### Phase 7 — L7 Citizens + roles
- **Deliverables.** AgentRegistry, CapabilityRegistry, ModelRouter, ToolRouter, the citizen runtime
  (BaseAgentV2 re-expressed: pre-register gate, ConfidenceV2, EscalationGate, SpendGuardrail,
  structured_output), citizenship status, institution memberships, earned-autonomy envelope field,
  risk clearance.
- **Migrations.** agents, agent_capabilities (+ memberships, envelope fields).
- **Tests.** role-separation matrix (claim_maker≠resolver, executor≠approver, etc.); a citizen cannot
  act above its risk clearance; pre-register gate blocks claim without prediction.
- **Phase-exit.** All 29 existing roles registered as citizens and acting through the spine.

### Phase 8 — L8 Tasks + execution
- **Deliverables.** TaskDispatcher, TaskEngine, Planner, ActionExecutor, ToolRouter, ModelRouter,
  ReviewRouter, EscalationManager, SagaCoordinator, ReasoningServiceRouter (real
  symbolic/ensemble/rag/bayesian/trustworthiness; fails honestly), ToolMakingService (gated),
  **civilization-aware RAG** (retrieves L4 evidence + L4/L5 promoted memory with the firewall guard
  `dropSameProducer`, weight = status × confidence × trusted_confidence × PoCal).
- **Migrations.** tasks, task_assignments, sagas.
- **Events.** task.created/assigned/completed, decision.made.
- **Tests.** task state machine; reasoning router never returns `method='simulated'` (gate); RAG
  civilization branch retrieves promoted claims, drops same-producer, ranks external-corroboration
  above internal-only; saga compensation on failure.
- **Phase-exit.** A real task runs end to end through plan→execute→claim→evidence→decision→audit.

### Phase 9 — L9 Institutions
- **Deliverables.** InstitutionRegistry + the 8 core institutions + 3 added (Expansion Board, Identity
  Registry, Observability Office), members, decisions.
- **Migrations.** institutions, institution_members, institution_decisions.
- **Events.** institution.created, institution.decision_made.
- **Tests.** institution powers/limits enforced (e.g., Evidence Court cannot change constitution);
  membership-scoped decisions.
- **Phase-exit.** Tasks are routed to and decided by the correct institution.

### Phase 10 — L10 Governance + constitution
- **Deliverables.** ConstitutionService, PolicyEngine, ProtectedSurfaceEnforcer, InvariantValidator,
  SafetyService, RollbackService, ApprovalWorkflow, RiskTierClassifier, EarnedAutonomyController,
  CanaryController, KillSwitch, CircuitBreakerRegistry, TrustedMonitor.
- **Migrations.** protected_surface_requests.
- **Events.** policy.checked, protected_surface.requested/approved/blocked, canary.*, envelope.*,
  killswitch.engaged.
- **Tests.** every protected surface routes through the enforcer (no bypass — static + runtime); Tier 0
  kernel touch always rejected; uncertain tier escalates up; kill-switch halts all autonomous
  promotion; fail-closed on missing approver.
- **Phase-exit.** No protected mutation occurs without a recorded governance decision.

### Phase 11 — L11 Conflict resolution / judiciary
- **Deliverables.** DisputeRegistry, Judiciary, RulingService, AppealsService, PrecedentStore,
  ConflictDetector.
- **Migrations.** disputes, rulings, precedents.
- **Events.** conflict.opened, ruling.issued.
- **Tests.** contradiction auto-opens a dispute; ruling updates memory/trust/policy; precedent reused.
- **Phase-exit.** Contradictions cannot persist unresolved.

### Phase 12 — L12 Learning + improvement (incl. self-coding + skill engine core)
- **Deliverables.** LearningCandidateRegistry, RegressionTestGenerator, BenchmarkRunner, PromotionGate,
  SandboxExecutor (the wall: import blocker, restricted builtins, read-only mounts, interface
  validation), DGMArchive, SkillLibrary + SkillGenerator + CompetenceEvalHarness (held-out/external/
  rotated/protected scorer), ProofOfCompetence impl.
- **Migrations.** learning_candidates, regression_tests, skills, skill_versions, competence_evals,
  dgm_variants.
- **Events.** learning.candidate_created, skill.promoted, skill.rolled_back.
- **Tests (release-blocking).** the 12 sandbox breach tests pass; failure→regression test generated;
  competence eval is producer≠resolver and rotated; no-result-fudging gate.
- **Phase-exit.** A learned lesson becomes a regression test and (if it improves metrics) a promoted
  skill — only via the gate.

### Phase 13 — L13 Expansion + domain onboarding
- **Deliverables.** DomainRegistry, DomainRiskReviewer, CapabilityExpansionGate,
  GeneralityMetricTracker.
- **Migrations.** domain_registry, generality_metrics, benchmarks, benchmark_runs.
- **Events.** domain.approved.
- **Tests.** domain cannot onboard without passing its benchmark + having enough trusted citizens;
  generality metric increments only on verified competence beating baseline.
- **Phase-exit.** New domains enter only after proof; generality is measured over time.

### Phase 14 — L14 Coordinator (continuous)
- **Deliverables.** CivilizationRuntime, CivilizationOrchestrator, InstitutionRouter, GovernanceRouter,
  LearningRouter, EventRouter, Scheduler (continuous daemon), WorkSourcer (external + self-assessment),
  LoopSupervisor, GeneralityReporter.
- **Tests.** continuous loop runs N ticks against real services; self-assessment produces internal
  goals; **only** `tier==1 ∧ within_envelope ∧ gate ∧ clean_canary` closes autonomously; everything
  else queues to humans; kill-switch + backpressure honored.
- **Phase-exit.** The single-pass free-run is fully replaced by a continuous, supervised coordinator.

### Phase 15 — Capability-growth engine completion (VCA)
- Tie L12 SkillLibrary + L6 ProofOfCompetence + L13 GeneralityMetric + L10 Tier-1 auto-approval into
  the closed self-evolution loop (Part-11 design). **Tests:** a skill is proposed, passes the eval
  gate, canaries clean, promotes autonomously, mints PoC, widens the envelope; a deliberately-bad
  skill canaries-breaches, auto-rolls-back, contracts the envelope.

### Phase 16 — Full E2E integration + hardening
- **Reachability == 100%** from the coordinator (orphaned-services gate). **Civilization vertical
  slice** (B.8) green against real services. Load/chaos tests (broker down → DLQ + recovery; DB
  failover; replay rebuilds projections). Security review (scopes, keys, PII). Observability complete
  (dashboards, SLOs, alerts). Then `termination_predicate_met = true`.

## B.7 Testing strategy (must-pass suites)

- **Unit** — pure logic (scoring vectors, state-machine guards).
- **Integration** — service + real DB + real bus; constraints enforced (producer≠resolver,
  audit-in-same-tx).
- **Contract** — every API has request/response contract tests; events have schema tests.
- **Property-based** — calibration math, idempotency, reservation conservation (no resource created
  or destroyed).
- **Adversarial / security** — sandbox breach (12+), prompt-injection on tool/RAG inputs, scope
  escalation attempts, tamper attempts on the hash chain.
- **E2E** — the civilization vertical slice (B.8) and the closed self-evolution loop (Phase 15).
- **Chaos / resilience** — broker outage, DB failover, replay recovery, kill-switch.
- **Release-blocking gates** (recap): no_stub, no_simulation, reachability=100%, firewall (incl. the 3
  Python tests), sandbox_breach, credential_key_independence, no_result_fudging, e2e slice, coverage.

## B.8 Integration mandate (civilization is essential everywhere)

- **Reachability gate.** Build a static call graph from the L14 coordinator + capture a runtime trace
  of the vertical slice. Every registered service (L8 tools, L9 institutions, L12 instruments) must
  appear. Anything unreachable is `blocked` in the ledger, not `verified`. (Directly retires the
  49/77-orphaned condition.)
- **Spine-traversal gate.** Each action type has a test asserting it traversed the universal lifecycle
  (A.5): identity→role→institution→budget→evidence→claim/prediction→constitution→decision→audit→
  resolution→trust→memory→learning. Missing a stage ⇒ fail.
- **The civilization vertical slice (the canonical e2e):**
  ```
  Human submits task → task created → citizen assigned (role-separated)
   → citizen makes claim (requires evidence) → prediction pre-registered
   → budget reserved → action executed (real reasoning, civilization-aware RAG)
   → decision produced → audit event written (same tx)
   → independent resolver resolves prediction (producer≠resolver)
   → calibration scored → per-domain trust updated → credential minted (recomputable)
   → Evidence Court reviews memory candidate → memory promoted only if reality-validated
   → learning candidate created → (Tier-1) skill canaried + promoted | (else) queued to human
   → generality metric updated → coordinator ticks
  ```
  This slice must pass against real Postgres, real bus, real LLM, real resolver, real vector index.

## B.9 Observability, security, rollback, migrations

- **Observability.** Structured logs with `correlation_id`/`causation_id`; RED/USE metrics per service;
  distributed traces across the spine; dashboards built from L3 projections; SLOs + alerts on
  firewall violations, fallback-on-protected, queue depth, canary breach rate.
- **Security.** Ed25519 signing of events/credentials; key rotation/revocation; least-privilege scopes;
  secrets only via SecretProvider; PII tagging + access control; no keys/secrets in logs (scanned).
- **Rollback.** RollbackService + DGMArchive enable instant revert of any promoted skill/self-mod;
  canary auto-rollback on breach; envelope contracts on anomaly.
- **Migrations.** forward-only, versioned, transactional; CI applies on empty + previous schema;
  destructive changes require an explicit, reviewed governance decision (policy_change surface).

## B.10 Milestones & exit criteria

| Milestone | Exit criterion |
|---|---|
| M0 Foundations | Phases 0–3 verified; boots on real infra; events + audit + budgets enforced |
| M1 Truth backbone | Phases 4–6 verified; evidence→claim→prediction→resolution→trust firewall green |
| M2 Society | Phases 7–11 verified; citizens, tasks, institutions, governance, judiciary live |
| M3 Improvement | Phases 12–13 verified; safe learning, self-coding, expansion, generality metric |
| M4 Continuous | Phase 14 verified; single-pass replaced by supervised continuous coordinator |
| M5 Capability | Phase 15 verified; closed self-evolution loop with Tier-1 auto-approval + rollback |
| M6 Done | Phase 16: reachability=100%, vertical slice green, all gates green, ledger 100% verified, `termination_predicate_met=true` |

## Appendix A — Repository layout (target)

```
civilization/
  runtime/ identity/ resources/ events/ evidence/ claims/ trust/ agents/ tasks/
  institutions/ governance/ disputes/ learning/ expansion/ coordinator/
  cross_cutting/ (observability/ security/ messaging/ migrations/)
backend/src/  (HTTP surface, route clusters → all reachable from coordinator)
tests/        (unit/ integration/ contract/ adversarial/ e2e/ chaos/ fixtures/)
docs/         (CIVILIZATION_ARCHITECTURE.md, CODEX_BUILD_PLAN.md)
BUILD_LEDGER.yaml
Makefile      (verify, status, remaining, slice, migrate)
```

## Appendix B — `make` targets (developer + Codex interface)

```
make verify     # lint + types + unit + integration + all release-blocking gates
make status     # recompute rollups/gates from BUILD_LEDGER.yaml; print progress
make remaining  # topo-sorted ready work frontier
make slice      # run the civilization vertical slice e2e against real services
make migrate    # apply forward migrations
make reachability  # static + runtime reachability report from the coordinator
```

## Appendix C — Acceptance summary (the one-line test of "done")

> The civilization boots on real infrastructure; a real human task flows through identity, role,
> institution, budget, evidence, claim, pre-registered prediction, real (never simulated) execution
> with civilization-aware retrieval, constitutional checks, audited decision, independent resolution,
> calibration-scored per-domain trust, recomputable credential, reality-gated memory promotion, and a
> learning candidate that — only if Tier 1, gated, and clean-canaried — promotes a new skill
> autonomously and widens the earned-autonomy envelope, with the generality metric ticking up; every
> registered service is reachable from the coordinator; every release-blocking gate is green; and
> `BUILD_LEDGER.yaml` reports 100% verified with `termination_predicate_met: true`.

*End of document.*
