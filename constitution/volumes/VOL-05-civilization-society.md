# Volume 5 — Civilization Society

## 1. Header

| Field | Value |
|---|---|
| Volume | 5 |
| Name | Civilization Society |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V4 (Identity & Authority), V6 (Institutions), V13 (Judiciary), V7 (Civilization Economy), V12 (Governance) |

## 2. Purpose

Society is the population layer: the citizens who act, the societies they belong to, and
the lifecycle, sanctions, roles, and autonomy envelopes that bound what each citizen may
do. A **citizen** wraps an identity (V4 actor) with membership, standing, and a governed
autonomy envelope; sanctions restrict a citizen's standing; role eligibility gates which
roles a citizen may hold. This is where identity becomes *bounded participation*. Mixed
status: citizenship and society topology are built and cited; demographics and inter-
society migration are prescriptive. Every present-tense claim cites its file.

```text
IDENTITY (V4 actor)
   ▼  wrapped as
CITIZEN  citizens   citizen_type ∈ {agent,human,service}
   │   status: candidate→probationary→active→restricted→suspended→expelled→retired
   ├─ CITIZENSHIP RECORD    citizenship_records
   ├─ SANCTIONS             citizen_sanctions   (imposeSanction ← judiciary V13)
   ├─ ROLE ELIGIBILITY      citizen_role_eligibility  (grant/revoke; hasActiveRole)
   ├─ AUTONOMY ENVELOPE     citizen_autonomy_envelopes  (max_risk_level, budget mult.)
   │        assertProtectedExecutionAllowed ← gate on durable execution + spawn
   └─ SUCCESSION            citizen_successions
   ▼
SOCIETY  societies (V6 migration 131)   memberships · charters · jurisdictions
```

## 3. Definitions

- **Citizen** — a bounded participant wrapping an actor
  (`citizens`, migration `130`; `backend/src/services/citizenship.service.ts`).
- **Citizenship record** — the standing/history of a citizen (`citizenship_records`).
- **Sanction** — a restriction on a citizen's standing, liftable
  (`citizen_sanctions`; `imposeSanction`, `liftSanction`).
- **Role eligibility** — whether a citizen may hold a role, optionally scoped to an
  institution or domain (`citizen_role_eligibility`; `grantRoleEligibility`,
  `hasActiveRole`).
- **Autonomy envelope** — the governed bound on a citizen's risk and budget
  (`citizen_autonomy_envelopes`; `setAutonomyEnvelope`,
  `assertProtectedExecutionAllowed`, `budgetMultiplierFor`).
- **Succession** — the recorded handover of a citizen's role/standing
  (`citizen_successions`; `recordSuccession`).
- **Society** — a population grouping with charter and jurisdiction
  (`societies`, migration `131`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V5-INV-001 | A citizen is a typed participant with a lifecycle status, and status changes only along the defined lifecycle. | enforced | `backend/src/db/migrations/130_citizenship.sql`, `backend/src/services/citizenship.service.ts`, `backend/tests/citizenship.test.ts` |
| V5-INV-002 | A citizen's autonomy envelope gates protected execution: an action above the citizen's permitted risk level is refused. | enforced | `backend/src/services/citizenship.service.ts`, `backend/tests/citizenship.test.ts` |
| V5-INV-003 | The protected-execution gate is wired into durable execution and specialist spawn, so envelope limits bind real work. | enforced | `backend/src/services/durable-execution.service.ts`, `backend/src/services/team-activation.service.ts`, `backend/src/services/citizenship.service.ts` |
| V5-INV-004 | Sanctions restrict a citizen's standing and are liftable, and their imposition is a recorded act (invoked by the judiciary). | enforced | `backend/src/services/citizenship.service.ts`, `backend/src/services/judiciary-case.service.ts`, `backend/tests/citizenship.test.ts` |
| V5-INV-005 | Role eligibility gates which roles a citizen may hold, optionally scoped to an institution or domain. | enforced | `backend/src/services/citizenship.service.ts`, `backend/tests/citizenship.test.ts` |
| V5-INV-006 | A citizen's budget multiplier is derived from standing/trust, not chosen freely, so participation scales with earned trust. | enforced | `backend/src/services/citizenship.service.ts`, `backend/tests/citizenship.test.ts` |
| V5-INV-007 | A society has an active charter and a jurisdiction that is a subset of the civilization's. | enforced | `backend/src/db/migrations/131_societies_and_institution_charters.sql`, `backend/tests/societies-institutions.test.ts` |
| V5-INV-008 | Population demographics (counts by status/type/society) are derivable as governed metrics. | planned | — |
| V5-INV-009 | A citizen may migrate between societies under a governed process, with membership history preserved. | planned | — |

## 5. Interfaces

- **Citizenship** — `citizenship.service.ts`: `registerCitizen`, `transitionCitizen`,
  `imposeSanction`, `liftSanction`, `suspendCitizen`, `grantRoleEligibility`,
  `revokeRoleEligibility`, `hasActiveRole`, `setAutonomyEnvelope`,
  `assertProtectedExecutionAllowed`, `budgetMultiplierFor`, `recordSuccession`.
- **Gate consumers** — `durable-execution.service.ts` (enqueue/run),
  `team-activation.service.ts` (specialist spawn) call
  `assertProtectedExecutionAllowed`.
- **Society** — society topology in `institution-governance.service.ts` and migration
  `131` (memberships, charters, jurisdictions).
- **Routes** — citizenship and society HTTP routes (classified in the V32 matrix).

## 6. State

- **Citizenship (migration `130`):** `citizens`, `citizenship_records`,
  `citizen_sanctions`, `citizen_role_eligibility`, `citizen_autonomy_envelopes`,
  `citizen_successions`.
- **Society (migration `131`):** `societies`, `society_state_transitions`,
  `society_charters`, `society_jurisdictions`, `society_memberships`,
  `institution_society_memberships`.
- **Identity substrate:** `actors` (V4, migration `079`).

## 7. Failure modes and responses

- **Unbounded agent action** — the autonomy envelope caps a citizen's risk level, and
  `assertProtectedExecutionAllowed` refuses over-risk actions at the durable-execution and
  spawn gates (V5-INV-002, V5-INV-003) — the concrete link from "citizen" to bounded
  execution.
- **Standing without consequence** — sanctions restrict standing and are the judiciary's
  citizen-side enforcement (V5-INV-004); scenario D exercises this.
- **Trust-free privilege** — the budget multiplier derives from standing/trust
  (V5-INV-006), so participation cannot be inflated by assertion.
- **Authority inflation via society** — a society's jurisdiction is a subset of the
  civilization's (V5-INV-007), the same referential guard as institutions (V6-INV-002).
- **No demographics / no migration** — population analytics and inter-society migration
  are not yet built (V5-INV-008/009 planned; open questions 1–2).

## 8. Verification obligations

Existing and green today: `backend/tests/citizenship.test.ts` (lifecycle, envelope gate,
sanctions, role eligibility, budget multiplier),
`backend/tests/societies-institutions.test.ts` (society charter + jurisdiction subset).

Must exist before the planned invariants flip: a demographics metric with a test
(V5-INV-008), and an inter-society migration process preserving membership history
(V5-INV-009).

## 9. Implementation mapping

- `backend/src/services/citizenship.service.ts` — the full citizen lifecycle, envelope
  gate, sanctions, role eligibility, budget multiplier, succession.
- `backend/src/db/migrations/130_citizenship.sql` — citizenship schema and lifecycle
  CHECKs.
- `backend/src/db/migrations/131_societies_and_institution_charters.sql` — society
  topology (the V5 half of migration 131; institutions are the V6 half).
- Gate consumers: `durable-execution.service.ts`, `team-activation.service.ts`.
- Judiciary seam: `judiciary-case.service.ts` (`imposeSanction`).

## 10. Open questions

1. **Actor vs citizen boundary (from V4).** Authority checks (V4) read actors; execution
   gates (V5) read citizens. Which layer a given check should consult — and whether every
   actor must become a citizen to act — should be stated explicitly. Proposed: actors are
   the identity primitive; citizenship is the *participation* wrapper that execution gates
   require.
2. **No demographics.** Population counts by status/type/society are not exposed as
   governed metrics (V5-INV-008 planned) — needed by the operator plane (V28) and
   self-inspection (V17).
3. **No inter-society migration.** Citizens belong to societies but cannot migrate
   between them under a governed process with preserved history (V5-INV-009 planned).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written; epistemic status set to mixed (citizenship is built, not merely prescriptive) with INDEX updated to match. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 19) | Bind the citizen lifecycle, autonomy-envelope execution gate, sanctions, role eligibility, and society topology into one citable society layer — where identity (V4) becomes bounded participation. |
