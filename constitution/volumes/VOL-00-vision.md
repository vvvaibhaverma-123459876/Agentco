# Volume 0 — Vision

## 1. Header

| Field | Value |
|---|---|
| Volume | 0 |
| Name | Vision |
| Tier | constitutional |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V17 (Self Inspection), V30 (Verification), V31 (Civilization Evolution) |

## 2. Purpose

### Why AgentCo exists

AgentCo exists to answer one question with running code: **can a system of AI agents be
organized so that its power grows while its honesty is structurally guaranteed?** Not an
AI application, not an orchestrator — an artificial civilization, where agents act as
bounded citizens, claims require evidence, predictions are pre-registered and
independently resolved, trust changes only from scored outcomes, and learning is
promoted through audited memory. That sentence is not aspiration: it paraphrases the
repository's own charter in `README.md`, and each clause has an implementation today
(see §9).

### Long-term objective

A **self-governing, evidence-driven, continuously evolving artificial civilization**
whose architecture, institutions, and capabilities can change over time while preserving
constitutional continuity, auditability, and human oversight. "Evolving" includes the
architecture itself (Volume 19) and, ultimately, the civilization's own constitution
(Volume 31) — always beneath a human root authority that cannot be voted away.

### Civilization philosophy

The system is layered like a real civilization. Each layer only exercises power the
layers above it grant, and each layer's claims are audited by machinery it does not own:

```text
Vision → Constitution → Civilization Kernel → Operating System
      → Identity & Authority → Society → Institutions → Economy
      → Knowledge → Reasoning → Governance → Judiciary
      → Learning → Capability Expansion → Autonomous Evolution
      → Self Inspection → Self Model → Architecture Evolution
      → Scientific Discovery → World Models → Imagination → Constraint Engine
      → Response Intelligence → Coder Civilization → Multi-Agent Coordination
      → Superuser Control Plane → Operator Plane → Infrastructure
      → Verification → Civilization Evolution
```

Each arrow is a dependency, not decoration: governance (V12) can only bind citizens that
identity (V4) can name; the judiciary (V13) can only sanction resources the economy (V7)
accounts for; learning (V14) can only promote what verification (V30) has scored.

### Evolution philosophy

Change is promoted, never assumed: failure → lesson → candidate → evaluation → canary →
promotion, with rollback as a first-class outcome. This pattern is already executable
today for skills (`backend/src/services/skill-canary.service.ts`, migration
`backend/src/db/migrations/108_skill_promotion_loop.sql`) and for civilization-level
improvements (`backend/src/services/safe-evolution.service.ts`, migration
`138_safe_evolution.sql`, where the evaluator must differ from the proposer and a canary
breach triggers rollback). The aspiration — not yet built — is to apply the same loop to
the architecture itself (V19) and to the constitution (V31): V0-INV-008.

### Success definition

Success is layered, and each layer is machine-checkable before the next is claimed:

1. **Constitutional success** — all ~34 volumes written and the drift checker green in
   CI on every push (`scripts/constitution/check_constitution.py`): V0-INV-001.
2. **Verification success** — completion claims derived from ledgers, never prose;
   canonical release gates green against the built code before any completion predicate
   is set true: V0-INV-003, V0-INV-007.
3. **Civilization success** — the layers above run continuously: missions complete with
   attested evidence, governance changes behaviour, the judiciary's enforcement mutates
   real state, learning promotes and rolls back, all under a live kill switch
   (V0-INV-004) — each already exercised by end-to-end scenarios A–H
   (`backend/tests/civilization-e2e-scenarios.test.ts`).
4. **Evolutionary success (aspirational)** — the system detects its own gaps, proposes
   its own next architecture, and migrates itself without losing constitutional
   continuity (V0-INV-008; Volumes 16–19, 31).

## 3. Definitions

Terms below are the repository's existing vocabulary and are binding for all volumes.

- **Evidence** — a stored, attributable observation; the atomic unit of belief
  (`autonomy_evidence` tables; evidence registry, migration `088_evidence_registry_events.sql`).
- **Claim** — a statement grounded in evidence rows
  (`backend/src/services/claim-grounding.service.ts`).
- **Prediction** — a pre-registered, falsifiable expectation, independently resolved
  (`backend/src/services/falsifiable-prediction.service.ts`,
  `backend/src/services/independent-resolver.service.ts`).
- **Trust** — a score changed only by resolved outcomes, never by assertion
  (`backend/src/services/persistent-trust-scorer.service.ts`).
- **Memory** — knowledge promoted through an audited pipeline
  (`backend/src/services/memory-promotion-pipeline.service.ts`).
- **Citizen** — a bounded agent identity with lifecycle, sanctions, and budget envelopes
  (`backend/src/services/citizenship.service.ts`, migration `130_citizenship.sql`).
- **Institution** — a chartered body with mandates, powers, and limits
  (`backend/src/services/institution-governance.service.ts`, migration
  `131_societies_and_institution_charters.sql`).
- **Mission** — governed work decomposed from objectives and goals, completed only
  through evidence-gated evaluation (`backend/src/services/mission.service.ts`,
  migration `133_missions.sql`).
- **Treasury / ledger** — double-entry resource accounting with reservation and
  settlement (`backend/src/services/treasury.service.ts`, migration
  `134_civilization_economy.sql`).
- **Ledger (build)** — the machine-readable source of truth for implementation status
  (`BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml`).
- **Outbox** — the transactional event-publication mechanism
  (`backend/src/workers/outbox-worker.ts`).
- **Invariant** — one testable sentence, registered in `constitution/invariants.yaml`
  per `constitution/CONVENTIONS.md`.

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V0-INV-001 | Every constitution volume conforms to TEMPLATE.md's sections and its header agrees with INDEX.md, checked automatically on every push and pull request. | enforced | `scripts/constitution/check_constitution.py`, `.github/workflows/constitution.yml` |
| V0-INV-002 | An invariant may carry status "enforced" only if it cites at least one enforcement path that exists in the repository. | enforced | `scripts/constitution/check_constitution.py` |
| V0-INV-003 | Civilization completion status is machine-derived from CIVILIZATION_BUILD_LEDGER.yaml and the generated report states the termination predicate explicitly instead of asserting completion in prose. | enforced | `scripts/generate_civilization_completion.py`, `.github/workflows/civilization-completion.yml`, `docs/civilization/OUTSTANDING_GATES.md` |
| V0-INV-004 | Human authority is root — a governed kill switch and an emergency-power path exist and are exercised by tests. | enforced | `backend/src/services/kill-switch.service.ts`, `backend/src/services/governance.service.ts`, `backend/tests/civilization-e2e-scenarios.test.ts` |
| V0-INV-005 | Civilization state changes append to tamper-evident logs, and kernel history plus decision-log tables reject in-place mutation at the database layer. | enforced | `backend/src/db/migrations/129_civilization_kernel.sql`, `backend/src/db/migrations/014_decision_log_immutability_triggers.sql` |
| V0-INV-006 | Every human-readable status surface is generated from a ledger rather than hand-edited, so no two status documents can disagree. | planned | — |
| V0-INV-007 | A completion predicate may be set true only after the repository's canonical release gates have run green against the built code. | planned | — |
| V0-INV-008 | AgentCo evolves its own architecture, institutions, and capabilities over time while preserving constitutional continuity, auditability, and human oversight. | aspirational | — |

## 5. Interfaces

The Vision layer's "interface" is the constitution machinery itself plus the status
surfaces every other layer reports through:

- `scripts/constitution/check_constitution.py` — validates volumes, registry, and
  enforcement paths; run by CI (`.github/workflows/constitution.yml`) on every push/PR.
- `scripts/generate_status.py` — regenerates the README status block from
  `BUILD_LEDGER.yaml` (the block in `README.md` is marked "do not edit").
- `scripts/generate_civilization_completion.py` — regenerates
  `reports/civilization_completion/latest/` from `CIVILIZATION_BUILD_LEDGER.yaml`,
  stating the termination predicate.
- `make release-gate` (Makefile) — the repository's canonical multi-step release gate.
- Operator surfaces: the Next.js console (`frontend/`), including the civilization
  operator page (`frontend/src/app/civilization/page.tsx`).

## 6. State

- `constitution/` — this constitution: `CONVENTIONS.md`, `TEMPLATE.md`, `INDEX.md`
  (the build plan and writing order), `invariants.yaml`, `volumes/`.
- `BUILD_LEDGER.yaml` — L-series ledger (base system), 71 items; its
  `termination_predicate_met` is `false` today.
- `CIVILIZATION_BUILD_LEDGER.yaml` — C-series ledger (civilization layer), 64 items
  verified; `termination_predicate_met` is `false` today pending canonical gates
  (`docs/civilization/OUTSTANDING_GATES.md`).
- `docs/civilization/PLAN_AND_PROGRESS.md`, `docs/civilization/CANONICAL_RUNTIME_MAP.md`
  — the civilization build's plan/progress and the frozen canonical-runtime decisions.
- `reports/civilization_completion/latest/` — machine-generated completion evidence.
- `AGENTCO_REPO_AUDIT.md`, `docs/CURRENT_IMPLEMENTATION_REALITY.md` (marked HISTORICAL)
  — prior audit and superseded status documents, retained as drift history.

## 7. Failure modes and responses

- **Documentation drift** (docs claim what code doesn't do). This happened here: four
  status surfaces with disagreeing numbers (see §10). Response: the checker fails CI on
  header/INDEX disagreement and dead enforcement paths (V0-INV-001, V0-INV-002).
- **Fake success** (gates that pass without testing anything). This happened here:
  `autonomy-memory-quality-test` and `autonomy-observability-test` were echo-only until
  fixed on 2026-07-14 (Makefile; see `docs/civilization/PLAN_AND_PROGRESS.md`).
  Response: `make gate-integrity` rejects fake-success patterns; volumes must cite
  executable enforcement.
- **Self-graded completion** (predicates set true without running canonical gates).
  This happened here on 2026-07-14 and was walked back the same day
  (`docs/civilization/OUTSTANDING_GATES.md`). Response: V0-INV-003 today; V0-INV-007
  once predicate-setting is mechanically bound to gate results.
- **Vocabulary drift** (synonyms multiplying until nothing is checkable). Response:
  §3 definitions are binding; `constitution/CONVENTIONS.md` forbids invented synonyms.

## 8. Verification obligations

- `scripts/constitution/check_constitution.py` must run green in CI on every push/PR
  (`.github/workflows/constitution.yml`) — exists today.
- The civilization completion workflow must keep regenerating evidence from the ledger
  (`.github/workflows/civilization-completion.yml`) — exists today.
- The README status block must remain generated, never hand-edited
  (`scripts/generate_status.py`) — exists today; continuous regeneration is not yet
  automated (§10).
- Before V0-INV-007 can move to `enforced`: a gate that mechanically refuses
  `termination_predicate_met: true` unless the canonical release gates ran green
  against HEAD — to be built (Volumes 17/30).

## 9. Implementation mapping

What exists in this repository today for each clause of the vision sentence:

- "agents act as bounded citizens" — `backend/src/services/citizenship.service.ts`,
  migration `130_citizenship.sql`; execution gating via the protected-execution check
  wired into durable execution and specialist spawn.
- "claims require evidence" — `backend/src/services/claim-grounding.service.ts`,
  evidence registry migration `088_evidence_registry_events.sql`.
- "predictions are pre-registered and independently resolved" —
  `backend/src/services/falsifiable-prediction.service.ts`,
  `backend/src/services/independent-resolver.service.ts`, migration
  `120_prediction_ledger_registration_invariants.sql`.
- "trust changes only from scored outcomes" —
  `backend/src/services/persistent-trust-scorer.service.ts`.
- "learning is promoted through audited memory" —
  `backend/src/services/memory-promotion-pipeline.service.ts`,
  `backend/src/services/skill-canary.service.ts`, migrations `105_skill_library.sql`,
  `108_skill_promotion_loop.sql`.
- Civilization layers C0–C15 (kernel → citizenry → societies/institutions → coalitions
  → missions → economy → governance → judiciary → epistemics → safe evolution →
  capability expansion → civilization OS → operator plane → reliability/deployment →
  completion proof): migrations `129_civilization_kernel.sql` through
  `140_civilization_os.sql`, services `backend/src/services/civilization-*.service.ts`
  et al., scheduler worker `backend/src/workers/civilization-scheduler-worker.ts`,
  operator console `frontend/src/app/civilization/page.tsx`. Status: implemented and
  regression-verified; canonical release gates outstanding
  (`docs/civilization/OUTSTANDING_GATES.md`).

### Non-goals

- **Not a hosted production operation.** `README.md` states this; certification
  requires live SLOs, DR, backups, and incident evidence that do not exist here.
- **Not an AGI claim.** Capability grows only through the proof-of-competence and
  expansion gates (`backend/src/services/capability-expansion-gate.service.ts`).
- **Not autonomous beyond human authority.** No design in any volume may remove the
  kill switch or human root authority (V0-INV-004; Volume 1 will make this precise).
- **Not model training.** AgentCo orchestrates and governs models; it does not train them.

### Design assumptions

- PostgreSQL is the single source of durable truth; all state changes are transactional
  and audited (`backend/src/db/migrate.ts`; V0-INV-005).
- The TypeScript Fastify backend (`backend/src/server.ts`) is the canonical runtime;
  Python layers are quarantined or advisory per
  `docs/civilization/CANONICAL_RUNTIME_MAP.md`.
- Tests are the constitution's teeth: an invariant without an executable enforcement
  path is an aspiration, not a rule (V0-INV-002).
- Everything meaningful is expressible as ledger items, evidence, and invariants; if a
  volume cannot state testable invariants, it is a charter, not a statute.

## 10. Open questions

1. **Multiple status sources still coexist.** `README.md`'s generated block (68/71,
   stamped 2026-07-06), `BUILD_LEDGER.yaml`, `CIVILIZATION_BUILD_LEDGER.yaml`, and
   `docs/civilization/PLAN_AND_PROGRESS.md` all carry status; the README block is stale
   relative to the civilization layer. V0-INV-006 (planned) exists to end this. Which
   ledger becomes the single root, and does the README block learn about the C-series?
2. **Duplicate migration number.** `backend/src/db/migrations/` contains both
   `129_civilization_kernel.sql` and `129_longitudinal_mission_evidence.sql`
   (filename-ordered runner tolerates it; numbering discipline does not). Renumbering
   applied migrations is unsafe; the rule for future numbering belongs in Volume 2.
3. **Canonical release gates have not run against the built civilization code** —
   `make release-gate`, post-build `make audit-runtime-integration`, full-tree
   anti-stub sweep (`docs/civilization/OUTSTANDING_GATES.md`). Until then the
   completion predicate stays `false`.
4. **Pre-existing CI failures on `main`.** The `Clean-Room Audit` and `CI` workflows
   were already failing at merge commit `651794a` (before C12–C15 landed):
   `make audit-clean-room` exits 2 in CI. Cause not yet diagnosed; belongs to
   Volume 30's scope.
5. **Python/TypeScript duplication.** The quarantined Python civilization stack and the
   dual outbox split are frozen decisions in `docs/civilization/CANONICAL_RUNTIME_MAP.md`
   (D1, D2); whether quarantine becomes deletion is a Volume 19 (Architecture
   Evolution) decision.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (constitution bootstrap). | Claude (build agent), directed by the operator's Architecture Constitution prompt kit | Establish the vision layer and the drift-checker discipline before any other volume. |
