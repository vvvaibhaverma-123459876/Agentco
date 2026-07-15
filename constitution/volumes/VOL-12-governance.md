# Volume 12 — Governance

## 1. Header

| Field | Value |
|---|---|
| Volume | 12 |
| Name | Governance |
| Tier | constitutional |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V13 (Judiciary), V8 (Missions), V7 (Civilization Economy), V11 (Trust & Calibration) |

## 2. Purpose

Governance is how AgentCo changes its own rules legitimately. A proposal is sponsored,
impact-assessed, deliberated, voted, and — if approved — **activated into an enforceable
runtime policy that the rest of the system checks at execution time.** Governance is not
advisory: an active policy changes behaviour (proven by scenario C), can be rolled back,
and can grant time-bounded emergency powers that may engage the kill switch (V1). This is
the H3 statute layer of the constitutional hierarchy (V1). Mixed status; every
present-tense claim cites its file.

```text
PROPOSAL  governance_proposals   createProposal
   │  status machine: proposed→sponsored→assessed→deliberating→voting→approved/rejected→active
   ├─ SPONSOR      proposal_sponsors
   ├─ IMPACT       impact_assessments
   ├─ DELIBERATE   deliberations
   ▼
VOTE  governance_votes → closeVoting → tally → approved | rejected
   │  (approve required to activate)
   ▼
ACTIVATE  activateProposal → runtime_policies (active)   supersedes prior
   │                          policy_activations
   ▼
ENFORCE  policy-enforcement.service.ts assertAllowed  ← checked at execution
   │      (e.g. mission creation, V8)
   ├─ ROLLBACK  rollbackPolicy
   └─ EMERGENCY  grantEmergencyPower (ttl_seconds) → optional kill switch (V1)
                 expireEmergencyPowers  (time-bounded)
```

## 3. Definitions

- **Proposal** — a governance item with a lifecycle status machine
  (`governance_proposals`; `backend/src/services/governance.service.ts`).
- **Sponsor / impact assessment / deliberation** — the stages before a vote
  (`proposal_sponsors`, `impact_assessments`, `deliberations`, migration `135`).
- **Vote / tally** — recorded votes and their close-out outcome
  (`governance_votes`, `governance_decisions`; `castVote`, `closeVoting`).
- **Runtime policy** — the enforceable artifact an approved proposal activates
  (`runtime_policies`, `policy_activations`, migration `135`).
- **Enforcement** — the execution-time check of active policy
  (`backend/src/services/policy-enforcement.service.ts` `assertAllowed`).
- **Rollback** — reverting an active policy (`rollbackPolicy`).
- **Emergency power** — a time-bounded extraordinary authority that may engage the kill
  switch (`governance_emergency_powers`; `grantEmergencyPower`, `expireEmergencyPowers`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V12-INV-001 | A proposal becomes an active runtime policy only after it is approved by a recorded vote. | enforced | `backend/src/services/governance.service.ts`, `backend/tests/governance.test.ts` |
| V12-INV-002 | An active runtime policy changes runtime behaviour — enforcement is checked at execution time, not merely recorded. | enforced | `backend/src/services/policy-enforcement.service.ts`, `backend/src/services/governance.service.ts`, `backend/tests/governance.test.ts` |
| V12-INV-003 | A proposal advances only along its status machine, and every transition is recorded. | enforced | `backend/src/services/governance.service.ts`, `backend/src/db/migrations/135_governance.sql` |
| V12-INV-004 | Activating a new policy supersedes the prior policy for the same matched action rather than silently coexisting. | enforced | `backend/src/services/governance.service.ts`, `backend/src/db/migrations/135_governance.sql` |
| V12-INV-005 | An active policy can be rolled back, and rollback is a recorded governed act. | enforced | `backend/src/services/governance.service.ts`, `backend/tests/governance.test.ts` |
| V12-INV-006 | Emergency powers are time-bounded (ttl), their grant is recorded, and expiry is enforced. | enforced | `backend/src/services/governance.service.ts`, `backend/src/db/migrations/135_governance.sql` |
| V12-INV-007 | An emergency power may engage the kill switch, and doing so is an audited event. | enforced | `backend/src/services/governance.service.ts`, `backend/src/services/kill-switch.service.ts`, `backend/tests/civilization-e2e-scenarios.test.ts` |
| V12-INV-008 | A proposal that would violate a protected invariant fails activation, fail-closed (constitutionality check at activation time). | planned | — |
| V12-INV-009 | Voting eligibility and quorum are enforced so a decision cannot be made by an unauthorized or sub-quorum vote. | planned | — |

## 5. Interfaces

- **Proposal lifecycle** — `governance.service.ts`: `createProposal`, `sponsor`,
  `recordImpactAssessment`, `openDeliberation`, `recordDeliberation`, `openVoting`,
  `castVote`, `closeVoting`, `activateProposal`, `rollbackPolicy`.
- **Emergency** — `grantEmergencyPower` (ttl, optional kill switch),
  `expireEmergencyPowers`.
- **Enforcement** — `policy-enforcement.service.ts` `evaluate` / `assertAllowed`,
  consumed by mission creation (V8) and other governed actions.
- **Constitution machinery** — `calibration-constitution.service.ts` `validateChange`
  (V1) is the seam where V12-INV-008 would attach.
- **Routes** — governance-proposals HTTP routes (classified in the V32 matrix).

## 6. State

- **Governance (migration `135`):** `governance_proposals`, `proposal_sponsors`,
  `impact_assessments`, `deliberations`, `governance_votes`, `governance_decisions`,
  `runtime_policies`, `policy_activations`, `governance_emergency_powers`.
- **Enforcement seam:** `runtime_policies` active index by `match_action_type`.
- **Kill switch:** `kill-switch.service.ts` state (V1).
- **Prior governance substrate:** governance RBAC / reputation integration services and
  their migrations.

## 7. Failure modes and responses

- **Rule change without mandate** — activation requires an approved vote
  (V12-INV-001); a proposal cannot become policy by assertion.
- **Advisory-only policy** — enforcement is checked at execution
  (`policy-enforcement.assertAllowed`), so an active policy actually blocks a
  non-compliant action (V12-INV-002); scenario C proves governance changes behaviour.
- **Shadow policies** — activating supersedes the prior policy for the same action
  (V12-INV-004), preventing conflicting active rules.
- **Permanent emergency** — emergency powers carry a ttl and expiry (V12-INV-006), and
  their kill-switch engagement is audited (V12-INV-007).
- **Unconstitutional statute** — a proposal contradicting a protected invariant is not
  yet rejected at activation (V12-INV-008 planned; open question 1) — this is the same
  gap named in V1-INV-007 and the highest-value one here.
- **Illegitimate vote** — quorum/eligibility enforcement is not yet an invariant
  (V12-INV-009 planned; open question 2).

## 8. Verification obligations

Existing and green today: `backend/tests/governance.test.ts` (scenario C — approve →
activate → enforcement blocks a non-compliant action → rollback),
`backend/tests/governance-coalition-integration.test.ts`,
`backend/tests/civilization-e2e-scenarios.test.ts` (scenario H — emergency + kill switch).

Must exist before the planned invariants flip: an activation-time constitutionality
check with a fail-closed test (V12-INV-008), and quorum/eligibility enforcement tests
(V12-INV-009).

## 9. Implementation mapping

- `backend/src/services/governance.service.ts` — proposal lifecycle, voting, activation
  into `runtime_policies`, rollback, emergency powers.
- `backend/src/services/policy-enforcement.service.ts` — execution-time enforcement.
- `backend/src/services/kill-switch.service.ts` — kill-switch engagement (V1).
- `backend/src/services/calibration-constitution.service.ts` — the `validateChange` seam
  for V12-INV-008 (V1).
- Migration: `135_governance.sql`.

## 10. Open questions

1. **No constitutionality gate at activation.** A governance majority can currently
   activate a policy that contradicts a protected invariant; it binds until judicially
   struck (V13). Closing this (V12-INV-008 / V1-INV-007) means calling `validateChange`
   against protected surfaces at `activateProposal` and failing closed — the single
   most important governance gap.
2. **Quorum and eligibility.** `castVote`/`closeVoting` tally votes, but eligibility and
   quorum thresholds are not yet enforced invariants (V12-INV-009); a decision could be
   reached by an unauthorized or sub-quorum vote.
3. **Meta-governance boundary.** How the *rules about voting* themselves change (the H2→H1
   boundary from V1) is not yet specified; V31 (Civilization Evolution) owns the
   long-horizon version, but the near-term amendment path for governance rules needs a
   home.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 12) | Bind the proposal→vote→activation→enforcement→rollback machinery and time-bounded emergency powers into one citable governance layer — the H3 statute layer that judiciary (V13) adjudicates and economy (V7) and missions (V8) obey. |
