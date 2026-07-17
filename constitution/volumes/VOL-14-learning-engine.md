# Volume 14 — Learning Engine

## 1. Header

| Field | Value |
|---|---|
| Volume | 14 |
| Name | Learning Engine |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V9 (Knowledge System), V11 (Trust & Calibration), V15 (Capability Expansion), V19 (Structural Evolution Framework), V16 (Autonomous Evolution) |

## 2. Purpose

The Learning Engine is how AgentCo improves without trusting itself to grade its own
improvements. It defines the promotion pipeline — failure → lesson → candidate →
independent evaluation → canary → promotion, with rollback as a first-class outcome — and
the two rules that make it safe: **the evaluator can never be the proposer, and a canary
breach forces rollback.** Descriptive tier: every normative sentence cites the enforcing
file or test.

```text
FAILURE  civ_failure_analyses
   │  distil a lesson, register a candidate (proposer actor recorded)
   ▼
CANDIDATE  civ_learning_candidates   status machine:
   │   proposed→sandboxed→evaluated→approved→canary→promoted
   │                     └→ rejected            └→ rolled_back → retained/monitored
   │  EVALUATE — evaluator_actor_id  ≠  proposer_actor_id   (409 if equal)
   ▼        requires passing regression cases (civ_regression_cases)
CANARY  civ_canary_runs   breach ⇒ forced rollback
   ▼
PROMOTED  (Tier-2/3 not auto-promotable; human approval gate)
   │   lineage recorded  (civ_improvement_lineage)
   ▼
MONITORED → retained | ROLLED_BACK
```

## 3. Definitions

- **Failure analysis** — a recorded diagnosis of a failure that seeds a lesson
  (`civ_failure_analyses`, migration `138`).
- **Learning candidate** — a proposed improvement with a proposer, tier, and status
  machine (`civ_learning_candidates`; `backend/src/services/safe-evolution.service.ts`).
- **Independent evaluation** — evaluation by an actor distinct from the proposer
  (enforced at `safe-evolution.service.ts` line ~201).
- **Regression case** — a stored test a candidate must pass before promotion
  (`civ_regression_cases`, migration `138`; generator migration `104`).
- **Canary** — a bounded trial whose breach forces rollback
  (`civ_canary_runs`; `backend/src/services/skill-canary.service.ts`).
- **Tier** — the risk classification (1/2/3); Tier-2/3 candidates are not
  auto-promotable and require human approval (`safe-evolution.service.ts`).
- **Skill** — a promoted, versioned capability artifact
  (`skill_library_entries`, `skill_library_versions`, migration `105`).
- **Lineage** — the recorded ancestry of an improvement
  (`civ_improvement_lineage`, migration `138`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V14-INV-001 | A learning candidate cannot be evaluated by its proposer; independent evaluation is required and rejected otherwise. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/tests/safe-evolution.test.ts` |
| V14-INV-002 | A candidate advances only along the defined status machine; transitions are recorded append-only. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/src/db/migrations/138_safe_evolution.sql` |
| V14-INV-003 | A canary breach forces rollback rather than allowing promotion to stand. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/src/services/skill-canary.service.ts`, `backend/tests/safe-evolution.test.ts` |
| V14-INV-004 | Higher-tier (Tier-2/3) candidates are not auto-promotable and require human approval. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/tests/safe-evolution.test.ts` |
| V14-INV-005 | Promotion requires passing regression cases, not merely a successful trial. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/src/db/migrations/138_safe_evolution.sql` |
| V14-INV-006 | Promoted skills are versioned, and rollback restores a prior version rather than deleting history. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/src/db/migrations/105_skill_library.sql` |
| V14-INV-007 | Every promotion records improvement lineage linking the promoted artifact to its originating failure and candidate. | enforced | `backend/src/db/migrations/138_safe_evolution.sql`, `backend/tests/civilization-learning-e2e.test.ts` |
| V14-INV-008 | Learning executed autonomously (unattended) stays within the same evaluation and canary gates as attended learning. | enforced | `backend/tests/autonomous-promotion.test.ts`, `backend/tests/bounded-learning-production-guard.test.ts` |
| V14-INV-009 | A promoted improvement whose post-promotion monitoring degrades is automatically demoted or rolled back without human intervention. | planned | — |

## 5. Interfaces

- **Safe evolution** — `safe-evolution.service.ts`: `createCandidate`, `evaluate`
  (independence-checked), `promote` (tier/human-approval gated), `rollback`, plus the
  status machine.
- **Canary** — `skill-canary.service.ts` `runCanary(...)` executes the bounded trial and
  reports breach.
- **Skill library** — versioned skill entries and versions (migration `105`),
  promotion-loop runs (migration `108`).
- **Regression generation** — candidate regression tests (migration `104`).
- **Memory bridge** — promoted lessons feed memory via the V9 promotion pipeline
  (`memory-promotion-pipeline.service.ts`).

## 6. State

- **Safe evolution (migration `138`):** `civ_learning_candidates`,
  `civ_candidate_transitions` (append-only), `civ_failure_analyses`,
  `civ_regression_cases`, `civ_evaluations`, `civ_canary_runs`,
  `civ_improvement_lineage`.
- **Skills:** `skill_library_entries`, `skill_library_versions` (migration `105`),
  `skill_promotion_loop_runs` (migration `108`).
- **Regression tests:** migration `104`.
- **Prior learning substrate:** migrations `026`, `057` (reputation learning), `058`
  (bounded learning).

## 7. Failure modes and responses

- **Grading your own work** — `evaluate` throws `409` when
  `proposer_actor_id === evaluator_actor_id` (`safe-evolution.service.ts`), the same
  no-self-judging principle as Trust (V11) and Judiciary (V13).
- **Promotion on a lucky trial** — promotion requires passing regression cases, and
  Tier-2/3 requires human approval (V14-INV-004, V14-INV-005); a single good canary is
  not sufficient.
- **Silent bad promotion** — a canary breach forces rollback (V14-INV-003); rollback
  restores a prior version rather than deleting, preserving audit (V14-INV-006).
- **Autonomous drift** — unattended learning runs the same gates
  (`autonomous-promotion.test.ts`, `bounded-learning-production-guard.test.ts`), so
  autonomy cannot loosen the evaluation contract.
- **Post-promotion decay** — automatic demotion on degraded monitoring is not yet an
  enforced invariant (V14-INV-009 planned; open question 1); today monitoring exists but
  the automatic-response obligation is not proven.

## 8. Verification obligations

Existing and green today: `backend/tests/safe-evolution.test.ts` (independence, status
machine, canary→rollback, tier gating, regression requirement),
`backend/tests/autonomous-promotion.test.ts`,
`backend/tests/bounded-learning-production-guard.test.ts`,
`backend/tests/learning-candidate-registry.test.ts`,
`backend/tests/civilization-learning-e2e.test.ts`,
`backend/tests/contradiction-learning-e2e.test.ts`.

Must exist before the planned invariant flips: a monitoring-degradation → automatic
demotion/rollback test (V14-INV-009).

## 9. Implementation mapping

- `backend/src/services/safe-evolution.service.ts` — candidate lifecycle, independent
  evaluation, tier gating, promotion, rollback, lineage.
- `backend/src/services/skill-canary.service.ts` — bounded canary trials.
- Migrations: `104` (regression tests), `105` (skill library), `108` (promotion loop),
  `138` (safe evolution), plus `026`/`057`/`058` (prior learning substrate).
- `backend/src/services/memory-promotion-pipeline.service.ts` — the bridge that turns a
  resolved learning outcome into promoted memory (Volume 9).

## 10. Open questions

1. **Automatic demotion on decay is not yet enforced.** Monitoring records exist, but no
   invariant proves a degrading promoted improvement is automatically rolled back
   (V14-INV-009 planned). This is the closed-loop half of "rollback as a first-class
   outcome."
2. **Skill vs candidate lineage split.** `skill_library_*` (migration `105`) and
   `civ_learning_candidates`/`civ_improvement_lineage` (migration `138`) are two
   generations of the learning substrate; which is canonical for new promotions should
   be frozen (a Volume 2 canonical-runtime concern).
3. **Regression coverage is not measured.** Promotion requires regression cases to pass,
   but nothing measures whether the regression set actually *covers* the change; a
   coverage floor would strengthen V14-INV-005.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 7) | Bind the failure→candidate→independent-evaluation→canary→promotion/rollback pipeline into one citable learning engine, since it is the reusable pattern V19 (Structural Evolution) and V16 (Autonomous Evolution) generalize. |
