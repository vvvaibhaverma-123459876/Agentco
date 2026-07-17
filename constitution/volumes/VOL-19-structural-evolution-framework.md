# Volume 19 — Structural Evolution Framework

## 1. Header

| Field | Value |
|---|---|
| Volume | 19 |
| Name | Structural Evolution Framework |
| Tier | statute |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | V14 (Learning Engine), V18 (Civilization Self Model), V1 (Constitutional Core), V2 (Civilization Kernel), V17 (Self Inspection) |

## 2. Purpose

The Structural Evolution Framework is how AgentCo changes its own *structure* over time —
safely, under governance, preserving constitutional continuity. The Domain Neutrality
correction renamed this from "Architecture Evolution" because **architecture is one
structure among many** (`GENERALIZATION_REPORT.md` §9): the framework must evolve runtime,
services, institutions, governance, economy, communication, deployment, memory
organization, schedulers, and organizational topology alike. The reusable mechanism already
exists at the capability level — failure → candidate → independent evaluation → canary →
promotion → rollback (V14) — and this framework generalizes it to structural change, gated
by protected-surface validation (V1). Prescriptive tier: structural self-modification
beyond skills does not yet exist; §9 cites the validation substrate honestly.

```text
STRUCTURAL CHANGE (any of: runtime · services · institutions · governance · economy ·
   communication · deployment · memory org · schedulers · topology)
   ▼  proposed as a CANDIDATE (reuse V14 candidate lifecycle)
   ▼  VALIDATE against protected surfaces (self-modification-validator, mig 097)
   │     a change touching a protected surface (V1) is rejected / requires a vote
   ▼  INDEPENDENT EVALUATION (evaluator ≠ proposer, V14)
   ▼  CANARY (skill-canary pattern reused for structure)
   ▼  PROMOTE with a VERSION GRAPH entry  OR  ROLLBACK
   ── architecture is ONE structure among many, not the only evolvable thing
```

## 3. Definitions

- **Structure** — any of the evolvable structural classes above (architecture is one).
- **Structural candidate** — a proposed structural change, following the V14 candidate
  lifecycle.
- **Self-modification validation** — checking a candidate against protected surfaces
  before it can change structure
  (`backend/src/services/self-modification-validator.service.ts`, migration `097`).
- **Protected-surface validation** — rejecting a candidate that touches an immutable or
  vote-required surface (`backend/src/services/protected-surface-validator.service.ts`; V1).
- **Version graph** — the recorded lineage of structural versions (to be built; seeds:
  `schema_migrations`, kernel versions V2).
- **Migration engine** — the mechanism that applies a validated structural change
  (partial: the migration runner, V2).

## 4. Invariants

Prescriptive: structural evolution is planned; enforced entries are the validation
substrate that already guards self-modification.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V19-INV-001 | A self-modification candidate is validated before it can take effect, producing a recorded validation result. | enforced | `backend/src/services/self-modification-validator.service.ts`, `backend/src/db/migrations/097_self_modification_validation_compatibility.sql` |
| V19-INV-002 | A candidate that touches a protected surface is rejected or requires a constitution-level vote (structural changes cannot silently alter protected state). | enforced | `backend/src/services/protected-surface-validator.service.ts`, `backend/src/services/calibration-constitution.service.ts` |
| V19-INV-003 | Structural change reuses the learning engine's candidate → independent-evaluation → canary → promotion/rollback pattern rather than inventing an unsafe path. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/src/services/skill-canary.service.ts` |
| V19-INV-004 | Every structural change is recorded with lineage, so the system's structure has a version history. | enforced | `backend/src/db/migrations/117_artifact_lineage_identity.sql`, `backend/src/db/migrate.ts` |
| V19-INV-005 | Services can be replaced, merged, and split under the framework without violating constitutional continuity. | planned | — |
| V19-INV-006 | Institutions, governance, economy, communication, deployment, memory organization, schedulers, and topology are evolvable structures under the same framework. | planned | — |
| V19-INV-007 | A structural version graph records the lineage of every structural version and supports rollback to a prior structure. | planned | — |
| V19-INV-008 | A migration engine applies validated structural changes transactionally, with rollback on failure. | planned | — |
| V19-INV-009 | Structural evolution preserves constitutional continuity — a change cannot remove a protected invariant or human root authority (V1). | planned | — |

## 5. Interfaces

- **Validation** — `self-modification-validator.service.ts` (`validateCandidate`,
  `getValidation`), `protected-surface-validator.service.ts` (`validateProtectedSurfaces`).
- **Reused promotion** — `safe-evolution.service.ts`, `skill-canary.service.ts` (V14).
- **Constitution seam** — `calibration-constitution.service.ts` (`validateChange`, V1).
- **Migration substrate** — `backend/src/db/migrate.ts`, `schema_migrations` (V2).
- **Target** — a structural-change API spanning the ten structure classes, a version
  graph, and a migration engine (to be built).

## 6. State

- **Validation:** self-modification validation records (migration `097`),
  protected-surface violation logs.
- **Lineage seeds:** `schema_migrations` (V2), artifact lineage (migration `117`), kernel
  versions (V2).
- **To be built:** a structural version graph and per-structure change records.

## 7. Failure modes and responses

- **Unsafe self-modification** — candidates are validated before taking effect
  (V19-INV-001) and rejected if they touch protected surfaces (V19-INV-002), so a
  structural change cannot silently alter protected state.
- **Reinventing an unsafe change path** — structural change reuses the proven V14 pattern
  (independent evaluation + canary + rollback), not a bespoke one (V19-INV-003).
- **Losing structural history** — changes carry lineage (V19-INV-004); a full structural
  version graph with rollback is planned (V19-INV-007).
- **Only architecture evolves** — the core prescriptive gap: the framework should evolve
  ten structure classes, but structural evolution beyond skills/capabilities is not yet
  built (V19-INV-005/006 planned; `GENERALIZATION_REPORT.md` §9).
- **Continuity break** — nothing yet formally guarantees a structural change cannot remove
  a protected invariant or human root authority (V19-INV-009 planned) — the constitutional
  safety property that must hold before autonomous structural change is trusted.

## 8. Verification obligations

Existing and green today: self-modification and protected-surface validation
(`backend/tests/*` covering the validators), the reused safe-evolution/canary suites
(V14).

Must exist to satisfy the volume: structural change operations (replace/merge/split) with
tests (V19-INV-005/006), a version graph with rollback (V19-INV-007), a transactional
migration engine (V19-INV-008), and a continuity-preservation proof (V19-INV-009).

## 9. Implementation mapping

- `backend/src/services/self-modification-validator.service.ts` — candidate validation.
- `backend/src/services/protected-surface-validator.service.ts` — protected-surface
  gating (V1).
- `backend/src/services/safe-evolution.service.ts`,
  `backend/src/services/skill-canary.service.ts` — the reused promotion pattern (V14).
- `backend/src/db/migrate.ts`, `schema_migrations` — migration substrate (V2).
- **Not yet built:** the structural-change framework spanning the ten structure classes,
  the version graph, and the migration engine.

## 10. Open questions

1. **Generalize beyond skills.** The validation + promotion substrate is real, but it
   governs skill/capability change; extending it to services, institutions, governance,
   economy, deployment, schedulers, and topology (V19-INV-005/006) is the framework's whole
   direction (`GENERALIZATION_REPORT.md` §9).
2. **Continuity is the safety property.** Before autonomous structural change is trusted,
   V19-INV-009 must hold: no structural change can remove a protected invariant or human
   root authority. This binds V19 to V1 and is the precondition for real self-evolution.
3. **Version graph needs the Self Model.** A structural version graph (V19-INV-007) is
   part of the Self Model's evolution graph (V18-INV-006); the two should share one
   representation rather than duplicate.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (renamed from Architecture Evolution per GENERALIZATION_REPORT §9). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 31) | Generalize architecture evolution to structural evolution of ten structure classes, bind the self-modification/protected-surface validation substrate and the reused V14 promotion pattern, and name continuity preservation (V19-INV-009) as the precondition for trusted self-evolution. |
