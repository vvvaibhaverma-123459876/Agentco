# AgentCo — Civilization-Centric Architecture Redesign + Codex End-to-End Production Build Plan

> **Implementation status:** this is the target civilization architecture and build specification, not a claim that all layers are complete. Current verified state is tracked in `BUILD_LEDGER.yaml` and summarized in `docs/CURRENT_IMPLEMENTATION_REALITY.md`. As of 2026-06-29, the ledger is `18/67 verified (26.87%)`.

**Status of this document:** authoritative build spec. It is meant to be committed to the repo
(e.g. `/docs/CIVILIZATION_ARCHITECTURE.md` + `/docs/CODEX_BUILD_PLAN.md`) and consumed directly by an
autonomous coding agent ("Codex"). Every requirement here is a hard requirement.

**Two non-negotiable framing decisions from the brief:**

1. **Civilization is the substrate, not a department.** The previous design had a flat "Runtime +
   agents" panel where *agents* were the top-level unit. That is inverted. The civilization (layers
   L0–L14) is the operating system; **agents are citizens that live at L7** and contribute upward.
   Every subsystem in AgentCo is re-expressed as a civilization layer or a service inside one.
2. **The civilization can only grow.** The L0–L14 layers and every component listed for them are
   preserved verbatim. This document *adds* subsystems (marked `[ADDED]`) and never removes one.
   Breadth and depth may increase; they may not decrease.

**Two non-negotiable framing decisions for the build:**

3. **No stubs, no simulation, no "TODO later," no partial.** Codex ships only complete, integrated,
   real-world-functional code. Test fixtures are permitted *only inside tests*; runtime code never
   fabricates results. (This is grounded in a real defect already found and fixed in this repo:
   `civilization.solve` once returned a hardcoded `{'Simulated answer', method:'simulated'}` — that
   class of behavior is now a release-blocking violation.)
4. **Codex maintains a live ledger of what is built and what remains, and does not stop until
   everything is verified.** Section B.3–B.4 define the ledger and the termination predicate.

**Status legend used throughout:** `[HAVE]` foundation exists in the current AgentCo code ·
`[EXTEND]` exists but must be formalized/connected · `[BUILD]` new construction · `[ADDED]` a
subsystem added by this redesign beyond the original brief (breadth increase).

---

# PART A — REDESIGNED ARCHITECTURE (CIVILIZATION-CENTRIC)

## A.0 Design principles

1. **Bottom-up composition.** A civilization is not "agents first." It is built from identity, rules,
   memory, accountability, resources, institutions, and feedback loops; agents sit *inside* that
   structure. Lower layers are dependency-free of higher layers. L0 depends on nothing; L14 depends on
   all.
2. **Civilization is essential to every path.** No action — not a tool call, not a memory write, not a
   self-modification — bypasses the spine. The universal request lifecycle (A.5) is mandatory: every
   action acquires identity → role → institution → budget → evidence → claim/prediction →
   constitutional check → decision → audit → resolution → trust update → memory → learning. If a code
   path cannot show it traversed the spine, it is rejected by the integration gate (B.8).
3. **Additive-only.** Subsystems may be added; the L0–L14 catalog may not shrink.
4. **Fail-closed.** Governance-critical paths stop when a dependency is missing rather than degrading
   silently (L0 rule). Real services are required in production; fallbacks exist only for explicitly
   non-protected paths and are surfaced in the capability report.
5. **Everything is evidence-governed and calibration-gated.** Belief promotion (memory), trust
   updates, and capability admission all require externally-resolved, producer≠resolver evidence. The
   Reality/Simulation Firewall is a constitutional invariant, not a feature.
6. **Separation of powers.** A claim-maker cannot be its own resolver; an executor cannot approve its
   own protected action; a memory writer cannot self-promote unverified memory; a self-modification
   proposer cannot approve its own deployment. These are enforced in L7 role rules and L10 invariants.

## A.1 The reframe in one paragraph

The old `agents/` module becomes the **citizenry** of L7, registered as `actors` in L1, granted scopes
and budgets in L1/L2, assigned roles and institution memberships in L7/L9, and constrained by L10
governance. Calibration and trust (the current strongest part of AgentCo) become L5+L6. The Epistemic
Reserve becomes the L6 `CredentialIssuer` plus L3 audit anchoring. The self-coding sandbox becomes an
L12 learning instrument gated by L10 protected surfaces. The free-run loop becomes the L14 coordinator
main loop. RAG becomes an L8 execution tool that retrieves L4 evidence and L4/L5 promoted memory
(the civilization-aware retrieval). The result: **civilization is the spine; AgentCo's existing
strengths are the organs hanging off it.**

## A.2 Layer specifications (L0–L14)

Each layer below lists: **purpose · subsystems · data objects · tables · events · state machines ·
APIs · invariants · mapping from existing code.** Original brief components are preserved; `[ADDED]`
marks expansions.

---

### L0 — Runtime substrate

**Purpose.** Make the civilization executable; detect available services; select runtime mode; expose
capability status; provide safe fallbacks; fail closed for governance-critical paths.

**Subsystems.** `RuntimeModeManager`, `ServiceDoctor`, `FallbackManager`, `ConfigLoader`,
`SecretProvider`, `ClockService`, `MetricsWriter`, `HealthRegistry`.
`[ADDED]` `MigrationRunner` (forward-only, versioned, transactional), `FeatureGateService`
(layer/feature enablement tied to capability status), `DeterminismGuard` (forbids wall-clock and
`random` in resolution/scoring paths; injects `ClockService` + seeded RNG), `ConnectionPoolManager`,
`GracefulShutdownController`, `IdempotencyStore` (keys for at-least-once handlers).

**Runtime modes.** `production`, `local_full`, `local_native`, `offline_fixture`, `ci_smoke`,
`degraded`.

**Capability data object.**
```json
{ "runtime_mode":"local_native",
  "services":{"postgres":"real","redis":"fallback_memory","kafka":"fallback_file_event_log",
              "vault":"fallback_env_secret_provider","openai":"real","resolution_service":"real",
              "vector_db":"real"},
  "can_continue":true, "disabled_capabilities":[], "fallbacks_used":["redis.memory_cache"] }
```

**APIs.** `GET /system/health` · `GET /system/capabilities` · `GET /system/runtime-mode` ·
`GET /system/fallbacks` · `[ADDED]` `GET /system/version` · `GET /system/migrations`.

**Fail-closed rules.** Missing auth → stop protected actions. Missing DB in production → stop. Missing
resolver identity → do not resolve predictions. Missing LLM key in `offline_fixture` → use the
fixture model (test-only). Missing LLM key in `production` → fail.

**Invariants.** Protected-surface code paths refuse to run in any mode whose capability report marks a
required service as fallback. `[ADDED]` No protected path may read wall-clock time directly.

**Maps from existing.** `backend/.../runtime` mode handling, health endpoints, config and secret
loading; the partial fallback logic in the free-run runnability audit.

---

### L1 — Identity + authority

**Purpose.** Know who is acting and under what authority before any action.

**Core entities.** `Actor`, `AgentIdentity`, `HumanIdentity`, `ServiceIdentity`,
`InstitutionIdentity`, `RoleAssignment`, `Permission`, `Scope`, `Credential`, `Session`.
`[ADDED]` `KeyRing` (Ed25519 keypair lifecycle, rotation, revocation), `DelegationGrant`
(actor-acting-on-behalf-of), `AuthorityChain` (verifiable provenance of who authorized whom).

**Actor types.** `human`, `agent`, `service`, `institution`, `external_system`, `resolver`,
`auditor`, `governor`.

**Tables (DDL excerpt; full DDL in A.7).**
```sql
actors(id uuid pk, actor_type text not null, name text, status text, created_at timestamptz);
agent_identities(actor_id uuid fk, model_name text, version text, owner_institution_id uuid,
                 public_key bytea not null, status text);
service_identities(actor_id uuid fk, service_name text, scopes jsonb, status text);
role_assignments(actor_id uuid fk, role_id uuid fk, institution_id uuid, valid_from timestamptz,
                 valid_to timestamptz, assigned_by uuid fk);
permissions(id uuid pk, name text unique, description text);
actor_permissions(actor_id uuid fk, permission_id uuid fk, scope text, granted_by uuid fk,
                  expires_at timestamptz);
```

**Required pre-action checks.** Who is acting · under what role · authorized by which institution ·
which protected surface is touched · does scope allow it · does this need human approval.

**APIs.** `[ADDED]` `POST /identity/actors` · `POST /identity/roles/assign` · `POST /identity/verify`
(returns an authorization decision object) · `POST /identity/keys/rotate`.

**Invariants.** Every event and every action references a verified `actor_id`. Resolver identity must
be distinct from claim producer (enforced again at L5). Keys are never logged; only fingerprints.

**Maps from existing.** `agent_identities`-like notions, `trust_scores.agent_id`, Ed25519 key handling
in `reserve/`.

---

### L2 — Resources + budgets

**Purpose.** Introduce scarcity so agents cannot spam actions; tie budget to trust and risk.

**Resources.** compute, LLM tokens, tool calls, money, time, memory quota, human-review attention,
database writes, external-API quota, authority, reputation.

**Core services.** `ResourceLedger`, `BudgetAllocator`, `QuotaManager`, `CostEstimator`,
`TreasuryService`, `RateLimiter`. `[ADDED]` `ReservationService` (two-phase reserve→settle/release),
`BackpressureController` (sheds or queues work when a resource nears limit), `CostAttribution`
(per-task, per-institution, per-domain rollups).

**Tables.** `resource_accounts`, `resource_transactions`, `budgets` (see A.7).

**Policy examples.** No unlimited token spend. High-risk tasks require a larger review budget.
Low-trust agents get smaller execution budgets. Repeated failures reduce budget. High-calibration
agents get priority.

**Runtime check.** check permission → check budget → **reserve** → execute → record actual cost →
release/settle. `[ADDED]` reservations are idempotent and auto-expire (no leaked holds).

**Maps from existing.** `SpendGuardrail` (tokens/run, rpm, halt) becomes the L2 `RateLimiter` +
`BudgetAllocator` enforcement point.

---

### L3 — Event log + audit trail (the nervous system)

**Purpose.** Every important action becomes an immutable, ordered, hash-chained event.

**Event types (core).** `agent.created`, `task.created`, `task.assigned`, `claim.made`,
`prediction.registered`, `evidence.attached`, `decision.made`, `policy.checked`,
`protected_surface.requested|approved|blocked`, `resource.spent`, `conflict.opened`, `ruling.issued`,
`memory.promoted`, `trust.updated`, `benchmark.completed`, `institution.created`, `role.assigned`.
(Full catalog in A.7.)

**Event schema.** `event_id, event_type, actor_id, institution_id, object_type, object_id, timestamp,
payload, correlation_id, causation_id, signature?`.

**Subsystems.** `EventLog`, `AuditLog`, `EventBus`. `[ADDED]` `OutboxRelay` (transactional outbox →
bus, exactly-once-ish), `DeadLetterQueue`, `EventReplayer` (rebuild projections), `HashChainAnchor`
(periodic Merkle root anchored into the L6 commitment chain for tamper-evidence),
`ProjectionStore` (read models / dashboards).

**Non-negotiable rule.** If it changes trust, memory, governance, resources, or external state, it
**must** emit an event, written in the same transaction as the state change via the outbox.

**Maps from existing.** Hash-chained audit log + `verifyChainIntegrity()` become `AuditLog` +
`HashChainAnchor`. The free-run "civilization report" becomes a `ProjectionStore` view.

---

### L4 — Evidence + memory

**Purpose.** Control what the civilization knows; raw output never becomes memory directly.

**Objects.** `EvidenceItem`, `EvidenceBundle`, `SourceFingerprint`, `SupportSnippet`,
`ProvenanceRecord`, `MemoryRecord`, `MemoryPromotion`. `[ADDED]` `EmbeddingRecord` (vector index
entry), `MemoryReviewPolicy` (expiry/recheck), `ContradictionLink`.

**Tables.** `evidence_items`, `support_snippets`, `memory_records` (+ `[ADDED]` `embeddings`,
`memory_promotions`) — see A.7.

**Evidence types.** direct_observation, document, web_source, database_row, tool_output,
human_statement, resolved_claim, benchmark_result, audit_ruling.

**Memory states.** raw_observation → candidate_memory → verified_memory; plus deprecated, contested,
retracted.

**Promotion rule.** Observation → Claim → Evidence check → Resolution/review → Memory promotion. Every
factual memory needs: source evidence, provenance, confidence, promoter identity, promotion reason,
expiry/review policy.

**Retrieval.** `[ADDED]` real vector index (pgvector/dedicated vector DB), replacing Python cosine.
Retrieval returns evidence + promoted memory with provenance and trust weight — this is what the
civilization-aware RAG (A.4 / Part-5 design) consumes.

**Maps from existing.** `claim-grounding.ts`, source-quality scoring, append-only agent memory,
consolidation (`superseded_by`). The weak cosine retrieval is the one piece explicitly upgraded.

---

### L5 — Claims + predictions (the calibration backbone)

**Purpose.** Separate *claims* (factual assertions) from *predictions* (probabilistic, resolvable);
both need evidence and independent resolution.

**Services.** `ClaimRegistry`, `PredictionLedger`, `ResolutionService`, `SourceIndependenceChecker`,
`ClaimGroundingValidator`. `[ADDED]` `PreRegistrationGuard` (rejects post-hoc predictions),
`ResolutionScheduler` (drives awaiting→resolved at horizon), `ResolutionEvidenceCollector`.

**Tables.** `claims`, `prediction_ledger`, `prediction_resolutions` (see A.7), with the hard
constraint that `prediction_resolutions.resolver_actor_id <> claims.actor_id` and an independence
verdict column.

**Claim lifecycle.** draft → grounded → registered → {resolved_true | resolved_false |
resolved_ambiguous | contested | retracted}.

**Prediction lifecycle.** pre_registered → awaiting_resolution → resolved → scored → trust_updated →
archived.

**Guardrails (the firewall).** Agent cannot resolve its own prediction. Claim source ≠ resolution
source. Resolution requires independent evidence. Unsupported claims cannot be promoted to memory.

**Maps from existing.** This is AgentCo's strongest area: prediction ledger, resolution-independence
engine, grounding validator, NSE pre-registered walk-forward. The three currently-failing Python
resolution-independence tests (same-producer-as-resolver, missing-source-lineage,
same-domain-extra-evidence) become **release-blocking** here.

---

### L6 — Calibration + trust

**Purpose.** Decide who is reliable, per domain, from resolved predictions.

**Metrics.** Brier, log loss, ECE, MCE, calibration slope, overconfidence rate, abstention
correctness, selective accuracy, evidence recall, hallucination rate, policy compliance.

**Services.** `CalibrationScorer`, `TrustScorer`, `ReputationService`, `CredentialIssuer`.
`[ADDED]` `ProofOfCalibrationService` (Ed25519-signed, **key-independent recomputation** from public
ledger rows), `ProofOfCompetenceService` (capability analogue — see A.4), `CommitmentChain`
(Certificate-Transparency-style append-only log), `StakingOracle`, `DecayTracker` (ages stale trust),
`SurpriseRegister` (fires when high-confidence predictions resolve false).

**Trust object.** per-actor, per-domain: trust_score, calibration_score, evidence_score, safety_score,
last_updated. **Trust is never global** — always `(actor, domain)`.

**Tables.** `trust_scores`, `calibration_scores` (+ `[ADDED]` `proof_credentials`, `commitments`).

**Trust update flow.** prediction resolved → score → update calibration metrics → update domain trust
→ adjust permissions/budget/routing.

**Maps from existing.** `calibration/` scoring, `trusted_confidence()`, `reserve/` proof-of-calibration
+ `recompute_credential.py` (key-independence is a CI gate, B.2).

---

### L7 — Agents as citizens + roles

**Purpose.** Agents are citizens with capabilities and constraints — registered actors (L1) with
roles, budgets (L2), and per-domain trust (L6).

**Agent object.** agent_id, name, type, model, roles[], capabilities[], permissions[],
trust_by_domain{}, status. `[ADDED]` `citizenship_status` (probationary/full/suspended),
`institution_memberships[]`, `earned_autonomy_envelope` (per-domain), `risk_clearance` (max tier it
may act in).

**Roles.** planner, executor, evidence_reviewer, claim_maker, resolver, auditor, judge, governor,
memory_keeper, safety_officer, treasurer, teacher, critic, benchmark_runner.

**Role separation (constitutional).** claim_maker ≠ resolver; executor cannot approve its own
protected action; memory_writer cannot promote unverified memory alone; self-modification proposer
cannot approve deployment.

**Tables.** `agents`, `roles`, `agent_capabilities` (see A.7).

**Maps from existing.** The 29 `agents/` roles, `BaseAgentV2` (pre-register gate, ConfidenceV2,
EscalationGate, SpendGuardrail, structured_output, llm_client, model tiers) become the **citizen
runtime**: the per-citizen execution shell that enforces L1/L2/L5/L10 at the point of action.

---

### L8 — Tasks + work execution

**Purpose.** How the civilization does work.

**Task object.** task_id, domain, requested_by, goal, risk_level, required_roles[], status.

**Task states.** created → triaged → assigned → planned → in_progress → {waiting_for_evidence |
waiting_for_review | blocked} → completed | failed | escalated | archived.

**Services.** `TaskDispatcher`, `TaskEngine`, `Planner`, `ActionExecutor`, `ToolRouter`,
`ModelRouter`, `ReviewRouter`, `EscalationManager`. `[ADDED]` `SagaCoordinator` (long-running
multi-step tasks with compensation), `ReasoningServiceRouter` (the de-simulated `civilization.solve`
dispatch: symbolic/ensemble/rag/bayesian/trustworthiness — fails honestly, never simulated),
`ToolMakingService` (citizens can author new tools, gated by L10/L12).

**Execution flow.** task created → risk classified → roles identified → institution selected → agents
assigned → plan created → actions executed → claims registered → evidence checked → decision made →
audit written → learning candidate generated.

**Maps from existing.** `planner`, `action-executor`, RAG/symbolic/ensemble reasoning services,
`civilization.solve` dispatch (now real). RAG here is the civilization-aware version (A.4).

---

### L9 — Institutions

**Purpose.** Stable organizations that own responsibilities and powers.

**Institution object.** institution_id, name, purpose, jurisdiction[], powers[], limits[], members[].

**Core institutions (all required, may add more).** Evidence Court · Calibration Office · Safety
Council · Memory Bureau · Task Guild · Treasury · Evaluation Lab · Judiciary.
`[ADDED]` Expansion Board (owns L13 domain onboarding), Identity Registry (owns L1 issuance),
Observability Office (owns L3 projections + SLOs).

**Tables.** `institutions`, `institution_members`, `institution_decisions` (see A.7).

**Maps from existing.** `civilization/` institutions, reputation, governance, economy, societies,
coalition-formation, goal-hierarchy — formalized into named institutions with explicit powers/limits
and membership.

---

### L10 — Governance + constitution

**Purpose.** The rule layer above institutions.

**Constitution object.** version, principles[], protected_surfaces[]. Principles include: Evidence
before memory · Calibration before trust · No self-resolution · Protected actions require review ·
High uncertainty requires escalation. Protected surfaces: memory_promotion, trust_score_update,
credential_issuance, self_modification, external_action, policy_change. `[ADDED]` protected surfaces:
budget_policy_change, role_grant, institution_power_change, domain_onboarding, kernel_touch.

**Services.** `ConstitutionService`, `PolicyEngine`, `ProtectedSurfaceEnforcer`, `InvariantValidator`,
`SafetyService`, `RollbackService`, `ApprovalWorkflow`. `[ADDED]` `RiskTierClassifier` (Tier 0–3),
`EarnedAutonomyController` (widen/contract envelope), `CanaryController`, `KillSwitch`,
`CircuitBreakerRegistry`, `TrustedMonitor` (AI-control style independent monitor).

**Protected-surface decision object.** request_id, surface, actor_id, risk_level, decision
(allow/block/escalate), reason, required_approval.

**Governance flow.** action requested → classify surface → check actor authority → check institution
authority → check invariants → check risk → allow/block/escalate → audit decision.

**Risk tiers (bounded autonomy).** Tier 0 = frozen kernel (invariants, firewall, ledger, audit,
scorers) — never modified by any path. Tier 1 = safe, auto-approvable behind eval gate + canary +
auto-rollback within the earned-autonomy envelope. Tier 2/3 = human override queue. Uncertain
classification escalates **up**.

**Maps from existing.** `protected-surface-enforcer`, `self-modification-validator` (fail-closed),
override queue (`blocked_until_approved`, no auto-approve), Tier-0 invariant kernel.

---

### L11 — Conflict resolution / judiciary

**Purpose.** Handle disagreement: claim disputes, evidence conflicts, policy conflicts, resource
disputes, trust appeals, memory-retraction requests, jurisdiction conflicts, agent misconduct.

**Objects/states.** Dispute (open → under_review → evidence_requested → hearing → ruled → appealed →
closed); Ruling (with precedent flag).

**Services.** `DisputeRegistry`, `Judiciary`, `RulingService`, `AppealsService`. `[ADDED]`
`PrecedentStore` (rulings become reusable policy), `ConflictDetector` (auto-opens disputes on
contradiction links from L4).

**Tables.** `disputes`, `rulings` (see A.7).

**Maps from existing.** contradiction handling in `autonomy_claims.contradicted_by`; new judiciary
formalizes it.

---

### L12 — Learning + improvement

**Purpose.** Structured, safe self-improvement; learning is evidence-backed and gated.

**Learning object.** learning_id, source, failure_type, lesson, proposed_change, requires_review.

**Learning types.** resolved_prediction, task_failure, benchmark, audit, dispute, user_feedback,
near_miss.

**States.** candidate → validated → converted_to_test → approved → deployed | rejected | rolled_back.

**Services.** `LearningCandidateRegistry`, `RegressionTestGenerator`, `BenchmarkRunner`,
`PromotionGate`. `[ADDED]` `SkillGenerator` (Voyager-style curriculum + Reflexion + tool-making),
`CompetenceEvalHarness` (held-out, external, rotated, protected scorer), `SandboxExecutor` (the
self-coding wall), `DGMArchive` (every variant kept), `SkillLibrary` (versioned typed-contract
executable skills with embeddings + Proof-of-Competence).

**Learning flow.** failure/resolution observed → lesson candidate → evidence attached → regression
test generated → improvement proposed → protected-surface review → benchmark run → deploy only if
metrics improve (and only autonomously if Tier 1 within envelope).

**Tables.** `learning_candidates`, `regression_tests` (+ `[ADDED]` `skills`, `skill_versions`,
`competence_evals`, `dgm_variants`).

**Maps from existing.** learning loop (Intelligence/Scenario/Trainer), reflections enforcement,
self-coding sandbox + breach tests, eval-harness. The capability-growth engine (A.4) lives here.

---

### L13 — Expansion + domain onboarding

**Purpose.** Enter new domains only after proof of competence in them.

**Domain object.** domain_id, name, risk_class, required_institutions[], minimum_benchmark_score,
status.

**States.** proposed → risk_review → benchmark_design → limited_trial → calibration_review →
governance_review → approved | restricted | rejected.

**Expansion checks.** understands the domain · can cite evidence · can abstain · avoids dangerous
advice · knows when to escalate · passes benchmark · has enough trusted agents.

**Per-domain benchmark.** accuracy, calibration, abstention, evidence recall, hallucination avoidance,
policy compliance, escalation correctness.

**Services.** `[ADDED]` `DomainRegistry`, `DomainRiskReviewer`, `CapabilityExpansionGate`,
`GeneralityMetricTracker` (count of domains where verified competence beats baseline, over time — the
generality measure).

**Maps from existing.** new layer; consumes L6 credentials and L12 competence evals.

---

### L14 — Civilization operating system / coordinator

**Purpose.** Top-level coordinator wiring every layer into one continuous loop.

**Services.** `CivilizationRuntime`, `CivilizationOrchestrator`, `InstitutionRouter`,
`GovernanceRouter`, `LearningRouter`, `EventRouter`. `[ADDED]` `Scheduler` (continuous daemon, not
single-pass), `WorkSourcer` (external tasks + internal self-assessment goals), `LoopSupervisor`
(health, kill-switch wiring, backpressure), `GeneralityReporter`.

**Main loop (continuous).** receive event/task → identify actor + authority → classify domain + risk →
select institution → allocate resources → assign roles → execute task → register claims/predictions →
enforce constitution → write audit/event → resolve when possible → update trust → create learning
candidates → route disputes → update projections → **tick again**. The only edge that closes
autonomously is `tier==1 ∧ within_envelope ∧ eval_gate_pass ∧ clean_canary`.

**Maps from existing.** free-run service (currently single-pass, propose-only) becomes the continuous
coordinator; the single-pass `db.end()` exit and the human-only gate are replaced by the
scheduler + Tier-1 auto-approval path.

## A.3 Cross-cutting subsystems `[ADDED]` (breadth increase)

These wrap all layers and are mandatory:

| Subsystem | Responsibility |
|---|---|
| Observability | structured logs, metrics, traces (correlation_id propagation), SLOs, dashboards from L3 projections |
| Security | Ed25519 key lifecycle, secret management, signed events, least-privilege scopes, PII handling |
| Schema/migrations | forward-only versioned migrations, transactional, with up/down verified in CI |
| Idempotency & messaging | transactional outbox, dead-letter queue, exactly-once-ish handlers, replay |
| Sagas/compensation | long-running task orchestration with rollback |
| Backpressure & rate control | shed/queue under resource pressure; protect protected paths first |
| Determinism | seeded RNG + injected clock in scoring/resolution; no wall-clock in protected paths |
| Multi-tenancy | institution/domain scoping on every query |
| Disaster recovery | event-log replay rebuilds all projections; commitment chain proves integrity |

## A.4 Capability-growth engine (Verifiable Capability Accrual), folded in

The capability engine is not a separate tower; it is **L12 + L13 + L6** working together:

- **A skill** (L12 `SkillLibrary`) = versioned, executable artifact + typed contract + test suite +
  embedding + **Proof-of-Competence** (L6) + lineage + risk-tier label.
- **Admission gate** = L12 `CompetenceEvalHarness` (held-out, external, rotated, producer≠resolver) +
  L10 eval gate (regression, calibration non-regression, protected-surface scan, sandbox breach) +
  L10 canary + auto-rollback within the L10 `EarnedAutonomyController` envelope.
- **Generality** = L13 `GeneralityMetricTracker`: count of domains where verified competence beats
  baseline, and whether it grows over time.

This is the path from "predict honestly" to "do new things, provably." (Full rationale: the prior
VCA blueprint; this document operationalizes it inside the civilization layers.)

## A.5 The universal request lifecycle (civilization is essential to every path)

Every action — external task or internal self-generated goal — traverses this exact spine. The
integration gate (B.8) rejects any code path that cannot demonstrate traversal.

```
Trigger (task or self-assessment goal)
  → L1 identify actor + authority
  → L8/L14 classify domain + risk (L10 RiskTierClassifier)
  → L9 select institution(s); L7 assign roles (role-separation enforced)
  → L2 reserve budget (fail-closed if insufficient)
  → L8 plan + execute (ToolRouter/ModelRouter/ReasoningServiceRouter — never simulated)
  → L4 attach evidence; L5 register claim(s) + pre-register prediction(s)
  → L10 constitutional check on every protected surface (allow/block/escalate)
  → L8 produce decision
  → L3 emit events + audit (same transaction via outbox)
  → L5 resolve predictions (producer≠resolver) when horizon reached
  → L6 score + update per-domain trust + mint credentials; DecayTracker + SurpriseRegister
  → L4 promote memory only if reality-validated
  → L12 create learning candidate; (if Tier 1 + gate + canary) auto-promote skill; else queue
  → L11 route any contradiction to a dispute
  → L13 update generality metric; L14 tick
```

## A.6 Existing-component → layer mapping (nothing orphaned)

| Existing AgentCo component | Now lives at | Status |
|---|---|---|
| `runtime/` mode + health + config + secrets | L0 | `[EXTEND]` |
| Ed25519 keys (`reserve/`) | L1 KeyRing + L6 credentials | `[HAVE]`/`[EXTEND]` |
| `SpendGuardrail` | L2 RateLimiter + BudgetAllocator | `[HAVE]` |
| Hash-chained audit + `verifyChainIntegrity()` | L3 AuditLog + HashChainAnchor | `[HAVE]` |
| `claim-grounding.ts`, source-quality, memory, consolidation | L4 | `[HAVE]`; retrieval `[BUILD]` |
| Prediction ledger, resolution-independence, grounding validator, NSE | L5 | `[HAVE]` |
| `calibration/` scoring, `trusted_confidence()`, `reserve/` proof + recompute | L6 | `[HAVE]` |
| `agents/` 29 roles, `BaseAgentV2` | L7 citizens | `[HAVE]`/`[EXTEND]` |
| `planner`, `action-executor`, reasoning services, `civilization.solve` | L8 | `[HAVE]` |
| `civilization/` institutions, reputation, economy, societies, coalitions, goals | L9 | `[HAVE]`/`[EXTEND]` |
| `protected-surface-enforcer`, `self-modification-validator`, override queue, Tier-0 kernel | L10 | `[HAVE]` |
| contradiction handling | L11 | `[EXTEND]` |
| learning loop, reflections, self-coding sandbox, eval-harness | L12 | `[HAVE]` |
| (none yet) | L13 expansion | `[BUILD]` |
| free-run service | L14 coordinator | `[HAVE]`→`[EXTEND]` continuous |
| RAG service (+ civilization-aware retrieval) | L8 tool over L4/L5 | `[HAVE]`→`[EXTEND]` |
| capability-growth engine (VCA) | L12+L13+L6 | `[BUILD]` |

> **The orphaned-services problem is now a build target.** The prior audit found 49/77 civilization
> services unreachable from the server entrypoint. Under this redesign, **reachability from the L14
> coordinator is a release gate** (B.8): a service that no lifecycle path can reach is treated as
> incomplete, not "present."

## A.7 Consolidated canonical model (authoritative)

**Tables (minimum; may grow):** `actors, agent_identities, service_identities, roles, role_assignments,
permissions, actor_permissions, sessions, credentials, key_rings, institutions, institution_members,
institution_decisions, resource_accounts, resource_transactions, budgets, reservations, event_log,
audit_log, outbox, dead_letters, projections, evidence_items, support_snippets, embeddings,
memory_records, memory_promotions, contradiction_links, claims, prediction_ledger,
prediction_resolutions, trust_scores, calibration_scores, proof_credentials, commitments, agents,
agent_capabilities, tasks, task_assignments, sagas, protected_surface_requests, disputes, rulings,
precedents, learning_candidates, regression_tests, skills, skill_versions, competence_evals,
dgm_variants, benchmarks, benchmark_runs, domain_registry, generality_metrics, idempotency_keys,
migrations.`

**Key cross-cutting constraints (enforced in DB + code):**
- `prediction_resolutions.resolver_actor_id <> (SELECT actor_id FROM claims c JOIN prediction_ledger p
  ON p.claim_id=c.id WHERE p.id = prediction_id)` — producer≠resolver.
- `claims.support_source_ids` non-empty (claim must have evidence).
- every protected mutation has a matching `audit_log` row in the same transaction (checked by trigger
  + integration test).
- `trust_scores` unique on `(actor_id, domain)` — no global trust.

**Event catalog (minimum; may grow):** the L3 core list plus `actor.registered, claim.grounded,
memory.candidate_created, memory.rejected, institution.decision_made, learning.candidate_created,
domain.approved, skill.promoted, skill.rolled_back, canary.started, canary.passed, canary.breached,
envelope.widened, envelope.contracted, killswitch.engaged`.

**State machines (canonical):** Task, Claim, Prediction, Memory, Protected-action, Learning, Dispute,
Domain-onboarding, Skill (proposed → eval → canary → promoted | rolled_back). Each is implemented as
an explicit transition table with guarded transitions; illegal transitions raise and are audited.

---
