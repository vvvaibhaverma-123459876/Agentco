# Volume 26 — Multi-Agent Civilization

## 1. Header

| Field | Value |
|---|---|
| Volume | 26 |
| Name | Multi-Agent Civilization |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V6 (Institutions), V5 (Civilization Society), V13 (Judiciary), V12 (Governance), V4 (Identity & Authority) |

## 2. Purpose

Multi-Agent Civilization is how many agents cooperate, negotiate, and disagree without a
central controller: coalitions form, negotiate through rounds, reach consensus, record
dissent, make commitments, delegate, settle, and escalate. It also covers how specialist
agents are activated to do work. The load-bearing property is that **cooperation is
governed and auditable** — a coalition's negotiation, consensus, dissent, and settlement
are recorded state transitions, not emergent chatter. Mixed status: coalitions and
specialist activation are built and cited; adversarial structures (red/blue teams, war
games) and competition are prescriptive. Every present-tense claim cites its file.

```text
COALITION  institution_coalitions (mig 132)   coalition.service.ts
   propose → openNegotiation (rounds) → submitProposal → recordDissent
   → resolveConsensus → commit → constitute → activate → settle → terminate
   │                                            └→ escalate (to judiciary V13)
   ├─ members · threads · messages · commitments · delegations
   ▼
SPECIALIST ACTIVATION  team-activation.service.ts
   spawn specialist (role from specialist-roles registry) with HMAC (V32),
   budget enforcement, protected-execution gate (V5), graceful shutdown
   ▼
TARGET (to build): red teams · blue teams · war games · competition
```

## 3. Definitions

- **Coalition** — a governed multi-institution/agent grouping with a lifecycle
  (`institution_coalitions`, migration `132`;
  `backend/src/services/coalition.service.ts`).
- **Negotiation round** — a recorded round of proposals within a coalition
  (`coalition_negotiation_rounds`, `coalition_proposals`).
- **Consensus / dissent** — the recorded outcome of negotiation and recorded
  disagreement (`coalition_consensus_results`, `coalition_dissents`).
- **Commitment / delegation** — recorded obligations and delegated authority within a
  coalition (`coalition_commitments`, `coalition_delegations`).
- **Settlement / escalation** — coalition close-out and escalation to the judiciary
  (`coalition_settlements`, `coalition_escalations`; V13).
- **Specialist** — an activated worker agent with a role from the registry
  (`backend/src/services/team-activation.service.ts`,
  `backend/src/types/specialist-roles.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V26-INV-001 | A coalition advances only along its lifecycle, and every transition is recorded append-only. | enforced | `backend/src/services/coalition.service.ts`, `backend/src/db/migrations/132_institution_coalitions.sql`, `backend/tests/coalitions.test.ts` |
| V26-INV-002 | Negotiation proceeds in recorded rounds with recorded proposals, so a coalition's bargaining is auditable. | enforced | `backend/src/services/coalition.service.ts`, `backend/tests/coalitions.test.ts` |
| V26-INV-003 | Consensus is a recorded result and dissent is recordable and preserved, so agreement never erases disagreement. | enforced | `backend/src/services/coalition.service.ts`, `backend/src/db/migrations/132_institution_coalitions.sql` |
| V26-INV-004 | Coalition commitments and delegations are recorded obligations that bind the committing party. | enforced | `backend/src/services/coalition.service.ts`, `backend/tests/coalitions.test.ts` |
| V26-INV-005 | A coalition can settle and can escalate to the judiciary, so disputes have a governed exit. | enforced | `backend/src/services/coalition.service.ts`, `backend/src/services/judiciary-case.service.ts` |
| V26-INV-006 | Specialist activation authenticates via HMAC and enforces budget and the protected-execution gate, so spawned agents are bounded citizens. | enforced | `backend/src/services/team-activation.service.ts`, `backend/src/services/citizenship.service.ts`, `backend/tests/team-activation.test.ts` |
| V26-INV-007 | Specialist processes shut down gracefully, terminating their child processes on shutdown. | enforced | `backend/src/services/team-activation.service.ts` |
| V26-INV-008 | Specialist roles are a runtime registry, not a compile-time constant, so a new role is added without a code change. | planned | — |
| V26-INV-009 | Adversarial cooperation structures — red teams, blue teams, and war games — are first-class governed activities. | planned | — |

## 5. Interfaces

- **Coalitions** — `coalition.service.ts`: `proposeCoalition`, `openNegotiation`,
  `submitProposal`, `recordDissent`, `resolveConsensus`, `commit`, `constitute`,
  `activate`, `grantDelegation`, `settle`, `terminate`, `getCoalition`.
- **Specialists** — `team-activation.service.ts` (spawn, budget, HMAC, shutdown),
  `backend/src/types/specialist-roles.ts` (`getSpecialistRole`, `isValidSpecialistRole`).
- **Escalation** — `judiciary-case.service.ts` (V13).
- **Routes** — coalition HTTP routes (classified in the V32 matrix).

## 6. State

- **Coalitions (migration `132`):** `institution_coalitions`,
  `coalition_state_transitions` (append-only), `coalition_members`, `coalition_threads`,
  `coalition_messages`, `coalition_negotiation_rounds`, `coalition_proposals`,
  `coalition_commitments`, `coalition_delegations`, `coalition_consensus_results`,
  `coalition_dissents`, `coalition_settlements`, `coalition_escalations`.
- **Specialists:** `SPECIALIST_ROLES` constant (`backend/src/types/specialist-roles.ts`);
  specialist HTTP endpoint registration (migration `052`).

## 7. Failure modes and responses

- **Ungoverned collusion** — coalition negotiation, consensus, and commitments are
  recorded state transitions (V26-INV-001..004), so cooperation is auditable rather than
  opaque; escalation gives disputes a governed exit to the judiciary (V26-INV-005).
- **Erased disagreement** — dissent is first-class and preserved (V26-INV-003), the same
  principle as judiciary dissent (V13) and the reasoning article (V10).
- **Unbounded spawned agents** — specialist activation enforces HMAC, budget, and the
  protected-execution gate, so a spawned specialist is a bounded citizen, not a free
  agent (V26-INV-006, V5); processes shut down gracefully (V26-INV-007).
- **Hardcoded roles** — specialist roles are a compile-time constant
  (`SPECIALIST_ROLES`), not a runtime registry (V26-INV-008 planned;
  `GENERALIZATION_REPORT.md` M5) — the Domain Neutrality follow-through for agent roles.
- **No adversarial structures** — red teams, blue teams, and war games are not yet
  first-class governed activities (V26-INV-009 planned).

## 8. Verification obligations

Existing and green today: `backend/tests/coalitions.test.ts` (lifecycle, negotiation,
consensus, dissent, commitments, delegation, settlement, escalation),
`backend/tests/team-activation.test.ts` (HMAC, budget, spawn).

Must exist before the planned invariants flip: a runtime specialist-role registry with a
test proving a role is added without code change (V26-INV-008), and first-class red/blue
team + war-game activities with tests (V26-INV-009).

## 9. Implementation mapping

- `backend/src/services/coalition.service.ts` — coalition lifecycle, negotiation,
  consensus, dissent, commitments, delegation, settlement, escalation.
- `backend/src/db/migrations/132_institution_coalitions.sql` — schema, append-only
  transitions.
- `backend/src/services/team-activation.service.ts` — specialist activation (HMAC,
  budget, gate, shutdown).
- `backend/src/types/specialist-roles.ts` — the role catalogue (to become a registry,
  M5).
- `backend/src/services/judiciary-case.service.ts` — escalation target (V13).

## 10. Open questions

1. **Specialist roles are compile-time.** `SPECIALIST_ROLES` is a constant; making it a
   runtime registry (V26-INV-008, `GENERALIZATION_REPORT.md` M5) applies Domain
   Neutrality to agent roles — a new specialist should be addable without a code change,
   the same way a new domain is.
2. **Adversarial cooperation is unbuilt.** Red teams, blue teams, and war games (the
   Vision's adversarial structures) are not first-class (V26-INV-009); the substrate
   (coalitions + judiciary + the adversarial test corpus V30) could host them.
3. **Competition vs cooperation.** Coalitions model cooperation and negotiation;
   competition (agents contending for the same work/resource under governance) is not yet
   modeled and would need a governed contention mechanism (economy V7 + governance V12).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written; epistemic status set to mixed (coalitions are built) with INDEX updated. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 28) | Bind the coalition lifecycle (negotiation, consensus, dissent, commitments, settlement, escalation) and governed specialist activation into one citable multi-agent layer, and mark runtime roles and adversarial structures as the direction of travel. |
