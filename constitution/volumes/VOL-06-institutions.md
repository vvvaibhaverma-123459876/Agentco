# Volume 6 — Institutions

## 1. Header

| Field | Value |
|---|---|
| Volume | 6 |
| Name | Institutions |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V5 (Civilization Society), V12 (Governance), V13 (Judiciary), V7 (Civilization Economy), V25 (Capability Evolution Framework) |

## 2. Purpose

Institutions are the civilization's organs: chartered bodies with mandates, powers, and
limits that carry out governed work. This volume defines what an institution *is* (charter
+ mandate + powers + limits), the rule that an institution can never hold authority the
civilization did not grant (jurisdiction subsetting, DB-enforced), and the direction of
travel: institutions must become **emergent** — created from a capability gap, justified
to persist, retired when no longer justified — rather than permanent by seed. Mixed
status: the charter/mandate/power/limit machinery is built and cited; the
emergent-lifecycle and periodic-justification mechanisms are to be built
(`GENERALIZATION_REPORT.md` §11).

```text
INSTITUTION (entity)   charter → mandate → powers → limits
   │   institution_charters (one active) · institution_mandates
   │   institution_powers · institution_limits   (grant-row guard: append-only status)
   ├─ JURISDICTION GRANT   institution_jurisdiction_grants
   │     composite FK → civilization_jurisdictions  ← cannot grant a key the
   │                                                   civilization never held
   ├─ SOCIETY MEMBERSHIP   institution_society_memberships (V5)
   ├─ CONTRACTS            inter_institution_contracts  (draft→active→…)
   ▼
SEED TODAY: 10 mandatory institutions (function-fundamental), each 5 departments
   ▼
TARGET (to build): capability gap → research proposal → temporary program →
   specialists → evaluation → permanent institution OR archived program;
   creation · branching · merging · splitting · succession · retirement · federation
```

## 3. Definitions

- **Institution** — a chartered entity (`institutions`, entity_type `institution`;
  `backend/src/services/institution-governance.service.ts`).
- **Charter** — the institution's identity/mission document, one active per institution
  (`institution_charters`, migration `131`).
- **Mandate / power / limit** — what an institution must do, may do, and may not do
  (`institution_mandates`, `institution_powers`, `institution_limits`).
- **Jurisdiction grant** — a scope granted to an institution, constrained to be a subset
  of the civilization's jurisdiction (`institution_jurisdiction_grants`, composite FK).
- **Inter-institution contract** — an agreement between institutions with a lifecycle
  (`inter_institution_contracts`; `proposeContract`, `transitionContract`).
- **Mandatory institution** — one of ten function-fundamental seeded institutions
  (`MANDATORY_INSTITUTIONS`); each is a constitutional function (evidence, calibration,
  safety, memory, economy, evaluation, justice, expansion, identity, observability), not
  a knowledge-domain profession (Domain Neutrality, V0-INV-009).
- **Emergent institution** — one created from a justified capability gap and retired when
  no longer justified (to be built).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V6-INV-001 | An institution has at most one active charter, and charter/mandate/power/limit grant rows are append-only in their immutable columns. | enforced | `backend/src/db/migrations/131_societies_and_institution_charters.sql`, `backend/tests/societies-institutions.test.ts` |
| V6-INV-002 | An institution's jurisdiction grant must be a subset of the civilization's jurisdiction — a composite foreign key makes granting an un-held key impossible. | enforced | `backend/src/db/migrations/131_societies_and_institution_charters.sql`, `backend/tests/societies-institutions.test.ts` |
| V6-INV-003 | Institutions declare mandates, powers, and limits, and a limit constrains what the institution may do. | enforced | `backend/src/services/institution-governance.service.ts`, `backend/tests/societies-institutions.test.ts` |
| V6-INV-004 | Inter-institution contracts advance only along their lifecycle (draft → active → …). | enforced | `backend/src/services/institution-governance.service.ts`, `backend/src/db/migrations/131_societies_and_institution_charters.sql` |
| V6-INV-005 | The ten mandatory institutions are function-fundamental, not domain-specific, satisfying Domain Neutrality. | enforced | `backend/src/services/institution-governance.service.ts`, `scripts/constitution/check_constitution.py` |
| V6-INV-006 | Mandatory-institution seeding is idempotent — re-running does not duplicate institutions. | enforced | `backend/src/services/institution-governance.service.ts`, `backend/tests/societies-institutions.test.ts` |
| V6-INV-007 | An institution emerges from a justified capability gap through a temporary program before becoming permanent (creation → evaluation → permanent or archived). | planned | — |
| V6-INV-008 | Every permanent institution is periodically re-justified, and one that is no longer justified is retired (no permanence without ongoing justification). | planned | — |
| V6-INV-009 | Institutions can branch, merge, split, undergo succession, and federate under governance. | planned | — |

## 5. Interfaces

- **Institution governance** — `institution-governance.service.ts`: `proposeCharter`,
  `activateCharter`, `getActiveCharter`, `addMandate`, `grantPower`, `setLimit`,
  `listGovernance`, `proposeContract`, `transitionContract`,
  `ensureMandatoryInstitutions`, `institutionActorId`.
- **Prior institution substrate** — `institutions.service.ts` (5-department creation),
  `institution-work-assignment.service.ts`, `institution-claim-vetting.service.ts`,
  `institutional-synthesis.service.ts`, `institutional-knowledge-bridge.service.ts`.
- **Consumers** — the judiciary assigns cases to institutions (V13), the economy funds
  institution-scoped accounts (V7), domains are custodied by institutions (V15).
- **Routes** — society/institution HTTP routes (classified in the V32 matrix).

## 6. State

- **Societies & institutions (migration `131`):** `societies`,
  `society_state_transitions`, `society_charters`, `society_jurisdictions`,
  `society_memberships`, `institution_society_memberships`,
  `institution_jurisdiction_grants`, `institution_charters`, `institution_mandates`,
  `institution_powers`, `institution_limits`, `inter_institution_contracts`.
- **Institution entities:** `institutions` (prior migrations, L9 substrate).
- **Grant-row guard:** `civilization_grant_row_guard()` (append-only status columns).

## 7. Failure modes and responses

- **Authority inflation** — an institution cannot be granted a jurisdiction the
  civilization never held; the composite FK to `civilization_jurisdictions` makes it a
  referential impossibility (V6-INV-002) rather than a runtime check.
- **Silent charter rewrite** — charters/mandates/powers/limits are append-only in their
  immutable columns via the grant-row guard (V6-INV-001).
- **Domain capture** — the mandatory institutions are function-fundamental, and the
  Domain Neutrality checker (V0-INV-009) fails CI if a domain-named institution volume
  ever appears (V6-INV-005).
- **Permanent bureaucracy** — the highest-value gap: institutions are permanent by seed
  with no periodic-justification review and no retirement lifecycle
  (V6-INV-007/008/009 planned; `GENERALIZATION_REPORT.md` §11, M2/M3). Today an
  institution, once seeded, persists unconditionally.

## 8. Verification obligations

Existing and green today: `backend/tests/societies-institutions.test.ts` (charter/
mandate/power/limit flows, jurisdiction subsetting, idempotent seeding),
`backend/tests/institution-claim-vetting.test.ts`,
`backend/tests/institutional-synthesis.test.ts`.

Must exist before the planned invariants flip: an emergent-institution lifecycle with a
temporary-program-to-permanent test (V6-INV-007), a periodic-justification + retirement
mechanism and test (V6-INV-008), and branch/merge/split/succession/federation operations
(V6-INV-009).

## 9. Implementation mapping

- `backend/src/services/institution-governance.service.ts` — charters, mandates, powers,
  limits, jurisdiction grants, contracts, mandatory seeding.
- `backend/src/db/migrations/131_societies_and_institution_charters.sql` — schema,
  composite-FK jurisdiction subsetting, grant-row guard, contract lifecycle.
- `backend/src/services/institutions.service.ts` — prior five-department creation
  (the fixed-template that V6-INV-009 generalizes; `GENERALIZATION_REPORT.md` M3).
- `backend/src/services/institution-work-assignment.service.ts`,
  `institution-claim-vetting.service.ts`, `institutional-synthesis.service.ts` —
  institutional work and knowledge.

## 10. Open questions

1. **Institutions are permanent by seed.** The ten mandatory institutions pass Domain
   Neutrality (they are functions, not professions) but there is no periodic
   re-justification or retirement (V6-INV-007/008 planned). "No permanent institution
   without ongoing justification" (`GENERALIZATION_REPORT.md` §11) is the core unbuilt
   mechanism — the direction the whole generalization pass pointed institutions toward.
2. **Fixed department template.** `institutions.service.ts` creates a fixed five-
   department structure (Production/Verification/Audit/Adversarial/Improvement); emergent
   department structure per charter is M3 (V6-INV-009).
3. **Two institution generations.** `institutions.service.ts` (L9) and
   `institution-governance.service.ts` (migration `131`) both create/manage institutions;
   which is canonical for new institutions should be frozen (a Volume 2 concern).

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 18) | Bind the charter/mandate/power/limit machinery and DB-enforced jurisdiction subsetting into one citable institutions layer, and record the emergent-institution lifecycle the Domain Neutrality correction mandates as the direction of travel. |
