# Volume 13 — Judiciary

## 1. Header

| Field | Value |
|---|---|
| Volume | 13 |
| Name | Judiciary |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V12 (Governance), V7 (Civilization Economy), V5 (Civilization Society), V6 (Institutions) |

## 2. Purpose

The Judiciary resolves disputes and enforces rulings with real consequences. It is what
makes governance (V12) more than advisory: a statute that is violated can be adjudicated,
and a ruling's enforcement order **mutates actual runtime state** — treasury penalties,
citizen sanctions, trust adjustments, capability revocations. Two independence rules keep
it fair: the judge cannot be a disputing party, and an appeal is heard by a panel distinct
from the trial judge. Descriptive tier: every normative sentence cites the enforcing file
or test.

```text
OPEN CASE  judiciary_cases       jurisdiction check → accept
   │  status machine: opened→jurisdiction→evidence→hearing→ruling
   ▼                              →enforcement→appeal→final→closed | dismissed
EVIDENCE   judiciary_evidence_submissions
   ▼
HEARING    judiciary_hearings    presiding judge asserted INDEPENDENT of parties
   ▼
RULING     judiciary_rulings     dissent recordable; duplicate final ruling blocked
   ▼
ENFORCEMENT judiciary_enforcement_orders  → MUTATES STATE:
   │   resource_penalty → treasuryService.imposePenalty (V7)
   │   citizen_sanction → citizenshipService.imposeSanction (V5)
   │   trust_adjustment · capability_revocation · policy_clarification · no_action
   ▼
APPEAL     judiciary_appeals     appellate panel ≠ trial judge
   ▼
FINAL → CLOSED   precedent recorded (judiciary_precedents)
```

## 3. Definitions

- **Case** — a dispute with a lifecycle status machine
  (`judiciary_cases`; `backend/src/services/judiciary-case.service.ts`).
- **Jurisdiction check** — acceptance of a case by an assigned institution
  (`checkJurisdiction`).
- **Ruling** — a decision on a case, with recordable dissent
  (`judiciary_rulings`, `judiciary_dissents`).
- **Enforcement order** — an executable consequence of a ruling that changes runtime
  state (`judiciary_enforcement_orders`; `issueEnforcement`).
- **Appeal** — a challenge heard by a panel independent of the trial judge
  (`judiciary_appeals`; `fileAppeal`, `ruleOnAppeal`).
- **Precedent** — a recorded principle retrievable for later cases
  (`judiciary_precedents`; `findPrecedents`).
- **Independence** — the constraint that a judge is neither complainant nor respondent
  (`assertIndependent`, `judiciary-case.service.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V13-INV-001 | A judge or presiding actor cannot be the complainant or the respondent in the case they rule on. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/tests/judiciary-case.test.ts` |
| V13-INV-002 | An enforcement order mutates real runtime state — a resource penalty debits the treasury and a citizen sanction restricts the citizen — not merely a recorded verdict. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/src/services/treasury.service.ts`, `backend/src/services/citizenship.service.ts`, `backend/tests/judiciary-case.test.ts` |
| V13-INV-003 | An appeal is ruled on by an actor distinct from the trial judge. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/tests/judiciary-case.test.ts` |
| V13-INV-004 | A case advances only along its status machine, and transitions are recorded append-only. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/src/db/migrations/136_judiciary.sql` |
| V13-INV-005 | A duplicate final ruling on the same case is blocked. | enforced | `backend/src/db/migrations/136_judiciary.sql`, `backend/tests/judiciary-case.test.ts` |
| V13-INV-006 | Dissent from a ruling is recordable and preserved, not suppressed. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/src/db/migrations/136_judiciary.sql` |
| V13-INV-007 | Rulings can record precedent principles retrievable for later cases. | enforced | `backend/src/services/judiciary-case.service.ts`, `backend/src/db/migrations/136_judiciary.sql` |
| V13-INV-008 | An enforcement order that partially fails (e.g. penalty applied but sanction rejected) rolls back atomically, leaving no half-applied ruling. | planned | — |
| V13-INV-009 | Precedent is consulted as a first-class input to rulings, not merely retrievable after the fact. | planned | — |

## 5. Interfaces

- **Case lifecycle** — `judiciary-case.service.ts`: `openCase`, `checkJurisdiction`,
  `openEvidenceCollection`, `submitEvidence`, `holdHearing`, `issueRuling`,
  `issueEnforcement`, `recordDissent`, `fileAppeal`, `ruleOnAppeal`, `finalizeCase`,
  `findPrecedents`, `getCase`.
- **Enforcement targets** — `treasuryService.imposePenalty` (V7),
  `citizenshipService.imposeSanction` (V5), trust and capability adjustments.
- **Prior judiciary substrate** — `judiciary.service.ts`, `judiciary-review.service.ts`
  (migration `109`).
- **Routes** — judiciary-case HTTP routes (classified in the V32 matrix).

## 6. State

- **Judiciary (migration `136`):** `judiciary_cases`, `judiciary_case_transitions`
  (append-only), `judiciary_evidence_submissions`, `judiciary_hearings`,
  `judiciary_rulings`, `judiciary_enforcement_orders`, `judiciary_appeals`,
  `judiciary_dissents`, `judiciary_precedents`.
- **Prior judiciary tables:** migration `109`.
- **Enforcement side-effects:** treasury ledger (V7, migration `134`), citizen sanctions
  (V5, migration `130`).

## 7. Failure modes and responses

- **Self-judging** — `assertIndependent` throws `409` when the judge is the complainant
  or respondent (including respondent-as-citizen resolution), and appeals require a
  distinct ruler (`judiciary-case.service.ts`, V13-INV-001, V13-INV-003) — the same
  no-self-judging principle as Trust (V11) and Learning (V14).
- **Toothless rulings** — enforcement orders call into the treasury and citizenship
  services (`issueEnforcement`, V13-INV-002), so a ruling changes real state; scenario D
  proves this end to end (`backend/tests/judiciary-case.test.ts`).
- **Double jeopardy / conflicting finals** — a duplicate final ruling is blocked at the
  schema (V13-INV-005).
- **Suppressed dissent** — dissent is a first-class recordable object (V13-INV-006).
- **Half-applied enforcement** — a multi-effect order that partially fails is not yet
  proven atomic (V13-INV-008 planned; open question 1) — the cross-service transaction
  boundary is the risk.
- **Precedent ignored** — precedent is retrievable but not yet a required ruling input
  (V13-INV-009 planned; open question 2).

## 8. Verification obligations

Existing and green today: `backend/tests/judiciary-case.test.ts` (scenario D —
independence, enforcement mutates treasury/citizenship state, appeal by distinct panel,
duplicate-final block).

Must exist before the planned invariants flip: an atomic-rollback test for a
partially-failing multi-effect enforcement order (V13-INV-008), and a test proving
precedent is consulted as a ruling input (V13-INV-009).

## 9. Implementation mapping

- `backend/src/services/judiciary-case.service.ts` — full case lifecycle, independence
  checks, enforcement dispatch, appeals, precedent.
- `backend/src/db/migrations/136_judiciary.sql` — schema, status CHECK, append-only
  transitions, duplicate-final constraint.
- `backend/src/services/treasury.service.ts` (`imposePenalty`),
  `backend/src/services/citizenship.service.ts` (`imposeSanction`) — enforcement
  side-effects.
- `backend/src/services/judiciary.service.ts`,
  `backend/src/services/judiciary-review.service.ts`, migration `109` — prior substrate.

## 10. Open questions

1. **Cross-service enforcement atomicity.** `issueEnforcement` can apply a treasury
   penalty and a citizen sanction; if the second fails after the first commits, the
   ruling is half-applied (V13-INV-008 planned). Needs a single transaction spanning
   both services or a compensating-action protocol.
2. **Precedent is advisory, not binding.** `findPrecedents` retrieves principles but
   nothing requires a ruling to consider them (V13-INV-009 planned); binding precedent
   would need a consultation record on each ruling.
3. **Two judiciary generations.** `judiciary.service.ts` (migration `109`) and
   `judiciary-case.service.ts` (migration `136`) coexist; which is canonical for new
   cases should be frozen (a Volume 2 canonical-runtime concern).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 9) | Bind the case→ruling→enforcement→appeal machinery, its independence rules, and its real state-mutating enforcement into one citable justice system — the layer that gives governance teeth. |
