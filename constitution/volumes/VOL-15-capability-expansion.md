# Volume 15 — Capability Expansion

## 1. Header

| Field | Value |
|---|---|
| Volume | 15 |
| Name | Capability Expansion |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V11 (Trust & Calibration), V14 (Learning Engine), V25 (Capability Evolution Framework), V6 (Institutions), V12 (Governance) |

## 2. Purpose

Capability Expansion is the gate through which AgentCo may do something new — a new domain,
a new skill, a new power — and the reason a new discipline needs **no new architecture**
(the Domain Neutrality principle, V0-INV-009). It defines the ordered five-stage gate, the
requirement of a proof of competence minted by an actor independent of the proposer, and
the revocability of every grant. Domains and capabilities are *runtime entities*, not
compile-time assumptions. Descriptive tier: every normative sentence cites the enforcing
file or test.

```text
PROPOSE expansion (domain or capability)   expansion_proposals (mig 139)
   │  five ordered stages, each must pass to advance:
   ▼   risk_review → benchmark_design → limited_trial → calibration_review → governance_review
STAGE RECORDS  expansion_stage_records (append-only)   out-of-order stage ⇒ 409
   │  + PROOF OF COMPETENCE minted by an independent actor  (proof_of_competence, mig 106)
   │  + calibration/trust threshold met  (domain_registry, mig 102; V11)
   ▼
GRANT  capability_grants   → routing enabled immediately
   │        restrict ⇒ narrows;  revoke ⇒ blocks new work
   ▼
ASSERT AT USE  assertCapabilityGranted   (fail-closed at execution)
```

## 3. Definitions

- **Expansion proposal** — a request to add a domain or capability
  (`expansion_proposals`, migration `139`; `backend/src/services/capability-expansion.service.ts`).
- **Stage** — one of the five ordered gate stages
  (`risk_review`, `benchmark_design`, `limited_trial`, `calibration_review`,
  `governance_review`); `STAGE_ORDER` in `capability-expansion.service.ts`.
- **Stage record** — an append-only pass/fail record for a stage
  (`expansion_stage_records`, migration `139`).
- **Proof of competence** — a minted attestation that a skill version meets a benchmark,
  produced by an actor independent of the proposer
  (`proof_of_competence`, migration `106`; `backend/src/services/proof-of-competence.service.ts`).
- **Generality metric** — a bounded score tracking breadth of competence
  (`generality_metric_runs`, migration `103`;
  `backend/src/services/generality-metric-tracker.service.ts`).
- **Domain** — a runtime knowledge area with lifecycle status
  (`domain_registry`, migration `102`).
- **Capability grant** — a revocable authorization to exercise a capability
  (`capability_grants`, migration `139`).
- **Assertion at use** — the fail-closed check that a grant exists before a capability
  runs (`assertCapabilityGranted`, `capability-expansion.service.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V15-INV-001 | An expansion proposal advances only by completing the five gate stages in order; an out-of-order stage is rejected. | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/tests/capability-expansion.test.ts` |
| V15-INV-002 | A capability is granted only after all five stages pass and a proof of competence exists. | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/src/services/capability-expansion-gate.service.ts`, `backend/tests/capability-expansion.test.ts` |
| V15-INV-003 | A proof of competence is minted against a specific skill version and is not producible by the proposing actor alone. | enforced | `backend/src/services/proof-of-competence.service.ts`, `backend/src/db/migrations/106_proof_of_competence.sql`, `backend/tests/proof-of-competence.test.ts` |
| V15-INV-004 | Capability grants are revocable and restrictable, and revocation blocks new work immediately. | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/tests/capability-expansion.test.ts` |
| V15-INV-005 | Exercising a capability asserts an active grant at execution time and fails closed when none exists. | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/tests/capability-expansion.test.ts` |
| V15-INV-006 | The capability-expansion gate only routes work to a domain that is active in the domain registry and a skill that meets its calibration threshold. | enforced | `backend/src/services/capability-expansion-gate.service.ts`, `backend/tests/capability-expansion-gate.test.ts` |
| V15-INV-007 | Stage records and expansion decisions are append-only. | enforced | `backend/src/db/migrations/139_capability_expansion.sql`, `backend/src/db/migrations/107_capability_expansion_gate.sql` |
| V15-INV-008 | A domain can be retired (not only suspended), releasing its grants, so no permanent domain persists without justification. | planned | — |
| V15-INV-009 | The research and knowledge-acquisition stages of the universal capability lifecycle have first-class records, not only the five admission stages. | planned | — |

## 5. Interfaces

- **Expansion lifecycle** — `capability-expansion.service.ts`: `propose`, `recordStage`
  (ordered), `grantCapability`, `restrictCapability`, `revokeCapability`,
  `assertCapabilityGranted`.
- **Gate evaluation** — `capability-expansion-gate.service.ts` `evaluate` /
  `evaluateWithClient` (active-domain + current-skill + proof checks).
- **Competence** — `proof-of-competence.service.ts` `mintProof` (independent),
  `generality-metric-tracker.service.ts`.
- **Domain registry** — domain lifecycle (`domain_registry`, migration `102`) — see
  Volume 6/GENERALIZATION_REPORT M1 for the missing `retired` state.
- **Routes** — capability-expansion HTTP routes (classified in the V32 matrix).

## 6. State

- **Expansion (migration `139`):** `expansion_proposals`, `expansion_stage_records`
  (append-only, 5-stage CHECK), `expansion_proposal_transitions`, `capabilities`,
  `capability_grants`.
- **Gate (migration `107`):** `capability_expansion_decisions` (append-only).
- **Competence (migration `106`):** `proof_of_competence`.
- **Generality (migration `103`):** `generality_metric_runs`.
- **Domains (migration `102`):** `domain_registry` (`proposed`/`active`/`suspended`/`rejected`).

## 7. Failure modes and responses

- **Skipping the gate** — `recordStage` throws `409` unless the prior stage's status is
  present, forcing the five stages in order (`capability-expansion.service.ts`,
  V15-INV-001).
- **Granting without proof** — the gate requires all five stages plus a proof of
  competence before a grant (V15-INV-002); the proof is minted by an independent actor
  (V15-INV-003), the same no-self-judging rule as V11/V13/V14.
- **Runaway capability** — grants are revocable/restrictable and asserted at use, so a
  capability can be switched off and the next execution fails closed
  (V15-INV-004, V15-INV-005).
- **Routing to an unready domain** — the gate refuses domains not `active` and skills
  below their calibration threshold (`capability-expansion-gate.service.ts`,
  V15-INV-006), tying expansion to Trust (V11).
- **Permanent domains** — domains can be suspended but not yet *retired*
  (V15-INV-008 planned; `GENERALIZATION_REPORT.md` M1), so a no-longer-justified domain
  lingers.
- **Incomplete lifecycle records** — the five admission stages are recorded, but the
  research and knowledge-acquisition phases of the universal lifecycle (V25) are not
  first-class (V15-INV-009 planned; `GENERALIZATION_REPORT.md` M4).

## 8. Verification obligations

Existing and green today: `backend/tests/capability-expansion.test.ts` (ordered stages,
grant-after-gate, revoke-blocks-work, assert-at-use),
`backend/tests/capability-expansion-gate.test.ts` (active-domain + threshold routing),
`backend/tests/proof-of-competence.test.ts`, `backend/tests/generality-metric-tracker.test.ts`,
`backend/tests/domain-registry.test.ts`.

Must exist before the planned invariants flip: a domain-retirement test that releases
grants (V15-INV-008), and first-class research/knowledge-acquisition stage records with a
test (V15-INV-009).

## 9. Implementation mapping

- `backend/src/services/capability-expansion.service.ts` — proposal, ordered stages,
  grant/restrict/revoke, assertion at use.
- `backend/src/services/capability-expansion-gate.service.ts` — routing gate
  (active-domain, current-skill, proof).
- `backend/src/services/proof-of-competence.service.ts` — independent competence proofs.
- `backend/src/services/generality-metric-tracker.service.ts` — breadth metric.
- Migrations: `102` (domain registry), `103` (generality), `106` (proof of competence),
  `107` (gate decisions), `139` (expansion).

## 10. Open questions

1. **No domain retirement.** `domain_registry` supports `proposed`/`active`/`suspended`/
   `rejected` but not `retired`; a no-longer-justified domain cannot be cleanly retired
   with its grants released (V15-INV-008 planned; `GENERALIZATION_REPORT.md` M1). This is
   the Domain Neutrality follow-through: domains must be as removable as they are
   addable.
2. **Universal lifecycle is partial.** V25 (Capability Evolution Framework) defines a
   lifecycle including research and knowledge acquisition; only the five admission stages
   have records here (V15-INV-009 planned; `GENERALIZATION_REPORT.md` M4).
3. **Two competence lineages.** Skill-library proofs (V14, migration `105`) and
   `proof_of_competence` (migration `106`) both attest capability; the boundary between
   "learned skill" and "granted capability" deserves an explicit statement (a Volume 25
   concern).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 8) | Bind the five-stage expansion gate, independent competence proof, and revocable grants into one citable capability boundary — the mechanism that lets a new discipline enter without new architecture (V0-INV-009). |
