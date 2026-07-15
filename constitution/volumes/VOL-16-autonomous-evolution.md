# Volume 16 — Autonomous Evolution

## 1. Header

| Field | Value |
|---|---|
| Volume | 16 |
| Name | Autonomous Evolution |
| Tier | statute |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | V8 (Missions), V14 (Learning Engine), V3 (Runtime Operating System), V17 (Self Inspection), V19 (Structural Evolution Framework) |

## 2. Purpose

Autonomous Evolution is what AgentCo does when no one is asking it to do anything: it forms
its own goals, plans and executes them, improves itself, researches open questions, and
schedules its own work — all within governed bounds and under the kill switch. The Domain
Neutrality correction mandated that this be **six separated loops, not one monolith**
(`GENERALIZATION_REPORT.md` §8): Autonomous Goal Generation, Autonomous Planning,
Autonomous Execution, Autonomous Improvement, Autonomous Research, and Autonomous
Scheduling, each with a distinct responsibility. Prescriptive tier: today there is one
fused supervised tick; the six-loop decomposition is the design to build. §9 cites the
fused substrate honestly.

```text
TODAY (one fused loop): supervised-runtime tick / supervised-free-run
   RunGuard (kill switch + budgets) → scheduler tick → goal formation
   (propose bounded goals from DB state) → approve (governed) → execute → outcomes
   stops on: time_limit | goal_limit | kill_switch | idle
   ▼
TARGET (six separated loops, each a distinct responsibility):
   ├─ Autonomous Goal Generation   propose bounded internal goals
   ├─ Autonomous Planning          decompose goals into missions (V8)
   ├─ Autonomous Execution         run missions under constraints (V23)
   ├─ Autonomous Improvement       failure → candidate → promotion (V14)
   ├─ Autonomous Research          open question → discovery (V20)
   └─ Autonomous Scheduling        leader-elected tick allocation (V3)
   all bounded by RunGuard (V3), budgets (V7), and the kill switch (V1)
```

## 3. Definitions

- **Goal formation** — proposing bounded internal goals from database state
  (`backend/src/services/goal-formation.service.ts` `proposeGoals`,
  `approveProposedGoals`).
- **Free run** — a bounded autonomous run that forms, approves, and executes goals until a
  stop condition (`backend/src/services/supervised-free-run.service.ts`).
- **Supervised tick** — the fused cycle driving scheduler + goal formation + judiciary on
  real state (`backend/src/services/supervised-runtime.service.ts`).
- **The six loops** — Goal Generation, Planning, Execution, Improvement, Research,
  Scheduling; each a separate responsibility (to be built).
- **Bound** — the RunGuard/budget/kill-switch envelope every autonomous action runs in
  (V1, V3, V7).

## 4. Invariants

Prescriptive: the six-loop decomposition is planned; enforced entries are the real bounded
autonomy that exists today.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V16-INV-001 | Autonomous goal formation proposes only bounded goals, and goals are approved through a governed step before execution. | enforced | `backend/src/services/goal-formation.service.ts`, `backend/tests/bounded-goal-formation-e2e.test.ts` |
| V16-INV-002 | An autonomous run halts on the kill switch, budget exhaustion, a goal limit, or idle — it cannot run unbounded. | enforced | `backend/src/services/supervised-free-run.service.ts`, `backend/tests/goal-formation-supervised-free-run.test.ts` |
| V16-INV-003 | The supervised tick consults the run guard (kill switch + budgets) before doing work in each cycle. | enforced | `backend/src/services/supervised-runtime.service.ts`, `backend/src/services/run-guard.service.ts` |
| V16-INV-004 | Autonomous improvement runs the same independent-evaluation and canary gates as attended learning. | enforced | `backend/src/services/safe-evolution.service.ts`, `backend/tests/autonomous-promotion.test.ts` |
| V16-INV-005 | Autonomous Goal Generation is a distinct loop with its own responsibility and record. | planned | — |
| V16-INV-006 | Autonomous Planning, Execution, and Improvement are distinct loops, not fused into one tick. | planned | — |
| V16-INV-007 | Autonomous Research is a distinct loop that turns open questions into discovery work (V20). | planned | — |
| V16-INV-008 | Autonomous Scheduling is a distinct loop allocating work across the leader-elected tick (V3). | planned | — |
| V16-INV-009 | Each autonomous loop can be independently enabled, disabled, and rate-limited under governance. | planned | — |

## 5. Interfaces

- **Goal formation** — `goal-formation.service.ts` (`proposeGoals`,
  `listOpenFormationGoals`, `approveProposedGoals`).
- **Free run** — `supervised-free-run.service.ts` (`run`).
- **Supervised tick** — `supervised-runtime.service.ts` (`tick`, `runFor`).
- **Bounds** — `run-guard.service.ts` (V3), budgets (V7), kill switch (V1).
- **Improvement** — `safe-evolution.service.ts` (V14).
- **Target** — six loop interfaces, each independently governable (to be built).

## 6. State

- **Today:** goal-formation proposals, free-run outcomes, supervised-tick state; all
  bounded by run-guard/budget state.
- **To be built:** per-loop state and control (enable/disable/rate-limit) for the six
  loops, and per-loop records so each loop's activity is separately auditable.

## 7. Failure modes and responses

- **Runaway autonomy** — every autonomous run is bounded by the run guard, budgets, a goal
  limit, and idle detection (V16-INV-002, V16-INV-003); it cannot loop unbounded, and the
  kill switch halts it within one tick.
- **Ungoverned goals** — goal formation proposes bounded goals that require a governed
  approval before execution (V16-INV-001).
- **Autonomy loosening gates** — autonomous improvement runs the same evaluation/canary
  gates as attended learning (V16-INV-004, V14), so unattended operation cannot weaken the
  contract.
- **Monolithic loop** — the core prescriptive gap: today the loops are fused in one tick,
  so they cannot be independently reasoned about, governed, or rate-limited
  (V16-INV-005..009 planned; `GENERALIZATION_REPORT.md` §8) — the decomposition is the
  volume's whole direction.

## 8. Verification obligations

Existing and green today: `backend/tests/bounded-goal-formation-e2e.test.ts`,
`backend/tests/goal-formation-supervised-free-run.test.ts`,
`backend/tests/autonomous-promotion.test.ts`,
`backend/tests/full-autonomy-integration.test.ts`.

Must exist to satisfy the volume: six separated loops with per-loop records and tests
(V16-INV-005..008), and per-loop enable/disable/rate-limit governance controls
(V16-INV-009).

## 9. Implementation mapping

- `backend/src/services/goal-formation.service.ts` — bounded goal generation (the seed of
  the Goal Generation loop).
- `backend/src/services/supervised-free-run.service.ts`,
  `backend/src/services/supervised-runtime.service.ts` — the fused run loop today (to be
  decomposed into the six loops).
- `backend/src/services/run-guard.service.ts` — the bound (V3).
- `backend/src/services/safe-evolution.service.ts` — autonomous improvement (V14).
- **Not yet built:** the six separated loops as distinct services/records with
  independent governance.

## 10. Open questions

1. **Decompose the monolith.** The fused supervised tick works and is bounded, but the six
   loops (Goal Generation / Planning / Execution / Improvement / Research / Scheduling)
   are not separate (V16-INV-005..008). Separation lets each be independently governed,
   rate-limited, and audited — the mandate of `GENERALIZATION_REPORT.md` §8.
2. **Research loop needs V20.** Autonomous Research (turning open questions into discovery)
   depends on the Knowledge Discovery Framework (V20), which is a charter; the loop can be
   scaffolded but not fully built until V20 has substance.
3. **Per-loop governance.** Each loop should be enable/disable/rate-limitable under
   governance (V16-INV-009), so an operator can, say, pause autonomous improvement while
   leaving autonomous scheduling running — impossible with one fused tick.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 30) | Bind the bounded goal-formation and free-run substrate into one citable autonomy layer and specify the six-loop decomposition the Domain Neutrality correction mandated, so autonomous evolution becomes independently governable rather than a monolith. |
