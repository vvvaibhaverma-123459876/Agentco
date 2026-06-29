# AgentCo — Civilization-Centric Architecture Redesign + Codex End-to-End Production Build Plan

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

# PART B — CODEX END-TO-END PRODUCTION BUILD PLAN

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
