# Volume 10 — Reasoning Engine

## 1. Header

| Field | Value |
|---|---|
| Volume | 10 |
| Name | Reasoning Engine |
| Tier | article |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | ALL — this is a cross-cutting article; especially V1, V8, V11, V12, V13, V14, V16 |

## 2. Purpose

This is an **article**, not a subsystem. It imposes one obligation on every other layer:

> Every decision, at every layer, records *why* it was made — its assumptions, the
> alternatives it considered, its expected outcome, its uncertainty, and any dissent —
> in a durable, auditable form, so that a decision can later be understood, second-guessed,
> and learned from.

The Reasoning Engine is therefore not a place in the code; it is a discipline the whole
constitution must satisfy. Prescriptive tier: the *full* obligation is a design to build.
Where a fragment already exists (e.g. decision confidence, dissent in specific layers) it
is cited honestly in §9, but the article does not claim the reasoning record exists
system-wide — because it does not yet.

```text
Every governed decision (mission, vote, ruling, promotion, grant, transition, …)
   SHOULD carry a REASONING RECORD:
     • assumptions        what was taken as given
     • alternatives       what else was considered and why rejected
     • expected outcome   the prediction the decision commits to (→ V11)
     • uncertainty        calibrated confidence, not a bare boolean (→ V11)
     • dissent            recorded disagreement, never suppressed (→ V13 precedent)
     • rationale          the causal "because"
   linked to the decision_log row and the evidence (V9) it rests on.
```

## 3. Definitions

- **Reasoning record** — the structured "why" attached to a decision: assumptions,
  alternatives, expected outcome, uncertainty, dissent, rationale. (Prescriptive: the
  full structured record is to be built.)
- **Decision** — any recorded governed act (a mission transition, a vote, a ruling, a
  promotion, a capability grant, a kernel transition). Each layer defines its decisions;
  this article defines what their record must contain.
- **Uncertainty** — a calibrated confidence, ideally a pre-registered prediction (V11),
  not a free-text hedge.
- **Dissent** — recorded disagreement with a decision, preserved as first-class
  (already true in the judiciary, V13-INV-006).
- **Decision log** — the append-only, hash-chained record decisions attach to
  (`backend/src/db/migrations/004_decision_log.sql`; V1-INV-001).

## 4. Invariants

These are obligations. Where a fragment is enforced today it is marked enforced with its
citation; the system-wide obligation is planned.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V10-INV-001 | Every decision is recorded in the append-only, hash-chained decision log. | enforced | `backend/src/db/migrations/004_decision_log.sql`, `backend/src/db/migrations/014_decision_log_immutability_triggers.sql` |
| V10-INV-002 | Every recorded decision carries a calibrated confidence score in [0,1], not a bare yes/no. | enforced | `backend/src/db/migrations/004_decision_log.sql` |
| V10-INV-003 | Dissent from a decision is recordable and preserved where the layer supports it (judiciary today). | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/src/db/migrations/136_judiciary.sql` |
| V10-INV-004 | Every governed decision records the assumptions it relied on, as structured data. | planned | — |
| V10-INV-005 | Every governed decision records the alternatives considered and why they were rejected. | planned | — |
| V10-INV-006 | Every governed decision records an expected outcome that can be resolved and scored (linking the decision to Trust, V11). | planned | — |
| V10-INV-007 | Dissent is recordable at every decision-making layer, not only in the judiciary and coalitions. | planned | — |
| V10-INV-008 | A reasoning record is linked to the evidence (V9) and predictions (V11) it rests on, so the "why" is grounded, not narrated. | planned | — |
| V10-INV-009 | The reasoning record is queryable — a Reasoning Explorer (V28) can reconstruct why any decision was made. | planned | — |

## 5. Interfaces

As an article, the Reasoning Engine's "interface" is a contract other volumes implement:

- **Producers** — every service that records a decision (mission, governance, judiciary,
  safe-evolution, capability-expansion, kernel) is an obligated producer of reasoning
  records.
- **Substrate today** — `decision_log` (confidence, risk, input/output summary,
  human-approval), `runtime_governance_artifacts` (migration `127`:
  `runtime_evaluation_records`, `runtime_learning_artifacts`,
  `runtime_improvement_experiments`).
- **Consumers** — Trust (V11) scores expected outcomes; the Learning Engine (V14)
  mines failed decisions; the Operator Experience (V28) explores reasoning.

## 6. State

- **Today:** `decision_log` (migration `004`, chained by `012`, immutable by `014`);
  `runtime_governance_artifacts` (migration `127`); layer-specific dissent
  (`judiciary_dissents`, migration `136`).
- **To be built:** a structured reasoning-record schema (assumptions, alternatives,
  expected outcome, uncertainty, dissent, rationale) attachable to any decision, linked
  to evidence and predictions.

## 7. Failure modes and responses

- **Unexplained decisions** — today a decision may record only input/output summaries
  and confidence; assumptions and alternatives are not structurally required
  (V10-INV-004/005 planned). The failure this article guards against is a decision that
  cannot later be understood or second-guessed.
- **Bare-boolean confidence** — mitigated: `decision_log.confidence_score` is a
  calibrated [0,1] value (V10-INV-002), and V11 pushes toward pre-registered predictions.
- **Suppressed dissent** — enforced in the judiciary (V10-INV-003) but not universal
  (V10-INV-007 planned).
- **Ungrounded rationale** — a "why" narrated without linked evidence is not yet
  prevented (V10-INV-008 planned); the article requires reasoning to cite V9 evidence.

## 8. Verification obligations

Existing and green today: decision-log immutability and chaining
(`backend/tests/*` covering `decision_log`), judiciary dissent
(`backend/tests/judiciary-case.test.ts`).

Must exist to satisfy the article: a structured reasoning-record schema plus a
cross-layer contract test asserting that each governed decision type attaches
assumptions, alternatives, expected outcome, and uncertainty (V10-INV-004/005/006), and a
Reasoning Explorer query path (V10-INV-009).

## 9. Implementation mapping

- **Enforced fragments:** `decision_log` (migrations `004`/`012`/`014`) gives the
  append-only chained record with calibrated confidence; `judiciary_dissents`
  (migration `136`) gives first-class dissent in one layer;
  `runtime_governance_artifacts` (migration `127`) records evaluation/learning/experiment
  artifacts.
- **Not yet built:** the structured, system-wide reasoning record (assumptions,
  alternatives, expected outcome, uncertainty, dissent, rationale) linked to evidence
  (V9) and predictions (V11). No service today writes all six fields for every decision.
- **Adjacent:** `backend/src/services/autonomy-action-planner.service.ts` produces plans
  and could be an early producer of structured reasoning; today it records plans and
  claims but not the full reasoning record.

## 10. Open questions

1. **Where does the reasoning record live?** A single `reasoning_records` table linked by
   `decision_log.log_id`, or per-layer columns? A single linked table keeps the article's
   contract uniform and queryable (favoring V10-INV-009).
2. **How much is mandatory?** Requiring all six fields on every low-stakes decision could
   be onerous; a risk-tiered obligation (full record for high-risk decisions, minimal for
   low) may be the pragmatic reading — but the article's default is "record the why".
3. **Relationship to the Constraint Engine (V23).** Reasoning records *why* a decision was
   made; the Constraint Engine (the other article) records *what filtered the options*.
   The two articles are complementary and should share the decision-record substrate.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written as a cross-cutting article. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 16; articles are obligations on all volumes) | Establish the obligation that every decision records its assumptions, alternatives, uncertainty, and dissent — the discipline that makes the whole civilization auditable and learnable — while honestly marking the system-wide record as to-be-built. |
