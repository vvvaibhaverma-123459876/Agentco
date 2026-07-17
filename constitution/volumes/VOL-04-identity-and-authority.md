# Volume 4 — Identity & Authority

## 1. Header

| Field | Value |
|---|---|
| Volume | 4 |
| Name | Identity & Authority |
| Tier | constitutional |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V5 (Civilization Society), V32 (Security & Threat Model), V13 (Judiciary), V27 (Operator Control Plane) |

## 2. Purpose

Identity & Authority answers "who is acting, and by what right?" Every act in AgentCo is
attributed to an **actor** with a typed identity, and every privileged act resolves
against an **authority chain** — roles, permissions, and time-bounded delegations — whose
decision is recorded. Cryptographic keys bind an identity to its signatures. This volume
is constitutional because attribution and authority are preconditions for governance
(V12), judiciary (V13), and every audit trail. Mixed status: the core is built and cited;
session/authentication surfaces are partial. Every present-tense claim cites its file.

```text
ACTOR  actors (typed: human/agent/service/…)   identity-authority.service.ts
   │   registerActor · unique active (actor_type, name)
   ├─ AGENT IDENTITY / SERVICE IDENTITY   agent_identities · service_identities
   ├─ KEY RING   registerKey (Ed25519 public_key) · revokeKey · verifySignature
   ▼
AUTHORITY
   ROLE → PERMISSION   roles · permissions · role_assignments · actor_permissions
   DELEGATION   authority_delegation_grants   (scope + expires_at)
   ▼
verifyAuthority(actor, permission, scope) → DECISION
   │   resolveAuthority walks roles + delegations
   ▼
AUTHORITY DECISION CHAIN  authority_decision_chains   (recorded, per decision)
```

## 3. Definitions

- **Actor** — the root identity of anything that acts; typed by `actor_type` CHECK
  (`actors`, migration `079`; `backend/src/services/identity-authority.service.ts`).
- **Agent / service identity** — subtypes carrying keys and status
  (`agent_identities`, `service_identities`, migration `079`).
- **Role / permission** — named authority and the capabilities it confers
  (`roles`, `permissions`, `role_assignments`, `actor_permissions`, migration `079`;
  `role_permissions`, migration `084`).
- **Delegation** — a scoped, optionally time-bounded grant of authority from one actor to
  another (`authority_delegation_grants`, migration `084`; `grantDelegation`).
- **Authority decision** — the resolved verdict of `verifyAuthority`, recorded as a chain
  (`authority_decision_chains`, migration `084`).
- **Key ring** — an actor's registered signing keys, revocable, used to verify signatures
  (`registerKey`, `revokeKey`, `verifySignature`).
- **Scope** — the domain a permission or delegation applies to, normalized (`*` = all)
  (`normalizeScope`, `identity-authority.service.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V4-INV-001 | Every actor has a typed identity, and there is at most one active actor per (type, name). | enforced | `backend/src/db/migrations/079_identity_authority.sql`, `backend/src/services/identity-authority.service.ts`, `backend/tests/identity-authority.test.ts` |
| V4-INV-002 | A privileged act resolves against roles, permissions, and delegations, and the resulting authority decision is recorded as a chain. | enforced | `backend/src/services/identity-authority.service.ts`, `backend/src/db/migrations/084_authority_chain.sql`, `backend/tests/identity-authority.test.ts` |
| V4-INV-003 | A delegation is scoped and may be time-bounded; authority resolution respects the delegation's scope. | enforced | `backend/src/services/identity-authority.service.ts`, `backend/tests/identity-authority.test.ts` |
| V4-INV-004 | Identity keys are registerable and revocable, and signature verification rejects signatures from a revoked or unregistered key. | enforced | `backend/src/services/identity-authority.service.ts`, `backend/tests/identity-authority.test.ts` |
| V4-INV-005 | Identity history is not deletable — the Identity Registry institution cannot delete identity history. | enforced | `backend/src/services/institution-governance.service.ts` (`Identity Registry` limits), `backend/src/db/migrations/079_identity_authority.sql` |
| V4-INV-006 | Authority verification is transactional: the decision and its recorded event commit together or not at all. | enforced | `backend/src/services/identity-authority.service.ts` |
| V4-INV-007 | Calibration credentials are independently recomputable from public prediction-ledger rows without any signing secret. | enforced | `backend/src/services/credential.service.ts`, `reserve/credentials/proof_of_calibration.py` |
| V4-INV-008 | A delegation cannot exceed the granting actor's own authority (no privilege escalation through delegation). | planned | — |
| V4-INV-009 | Sessions and interactive authentication for human operators are first-class, time-bounded, and revocable. | planned | — |

## 5. Interfaces

- **Identity** — `identity-authority.service.ts`: `registerActor`, `registerKey`,
  `revokeKey`, `verifySignature`.
- **Authority** — `assignRole`, `grantPermission`, `grantDelegation`, `verifyAuthority`
  (transactional, records a decision chain).
- **Credentials** — `credential.service.ts` (HMAC-signed calibration credential with a
  public recompute path), `reserve/credentials/proof_of_calibration.py`.
- **Consumers** — every service that attributes an act reads an `actor_id`; the API auth
  hook (V32) resolves the caller; the judiciary (V13) resolves respondent citizens to
  actors.
- **Routes** — agents/override routes (classified in the V32 matrix).

## 6. State

- **Identity (migration `079`):** `actors` (typed, unique-active index),
  `agent_identities`, `service_identities`, `roles`, `permissions`, `role_assignments`,
  `actor_permissions`.
- **Authority (migration `084`):** `role_permissions`, `authority_delegation_grants`
  (scope + expiry), `authority_decision_chains`; compatibility migration `085`.
- **Lineage:** `artifact_lineage_identity` (migration `117`).
- **Reserve:** `reserve/credentials/` (Python proof-of-calibration material).

## 7. Failure modes and responses

- **Ambiguous identity** — the unique-active `(actor_type, name)` index prevents two
  active actors colliding (migration `079`, V4-INV-001).
- **Unauthorized act** — `verifyAuthority` resolves the chain and records the decision;
  a missing role/permission/delegation yields a deny (V4-INV-002).
- **Forged signature** — `verifySignature` rejects signatures from revoked or
  unregistered keys (V4-INV-004).
- **Identity erasure** — the Identity Registry institution's declared limit
  `cannot_delete_identity_history` (V4-INV-005) plus append-only history keep the record.
- **Privilege escalation via delegation** — delegation is scoped, but nothing yet proves
  a delegation cannot exceed the granter's own authority (V4-INV-008 planned; open
  question 1) — the most important gap in this volume.
- **Human session management** — interactive human auth/sessions are not yet first-class
  (V4-INV-009 planned; open question 2); today API access is an API-key posture (V32).

## 8. Verification obligations

Existing and green today: `backend/tests/identity-authority.test.ts` (actor
registration, role/permission/delegation resolution, decision chain, key
register/revoke/verify).

Must exist before the planned invariants flip: a delegation-escalation test proving a
delegate cannot gain authority the granter lacks (V4-INV-008), and session lifecycle
tests for human operators (V4-INV-009).

## 9. Implementation mapping

- `backend/src/services/identity-authority.service.ts` — actors, keys, roles,
  permissions, delegations, `verifyAuthority` (transactional, chain-recorded).
- `backend/src/services/credential.service.ts` — HMAC calibration credential with a
  secretless public recompute path; `reserve/credentials/proof_of_calibration.py`.
- Migrations: `079` (identity/authority core), `084` (authority chain + delegation),
  `085` (decision-actor compatibility), `117` (artifact lineage identity), `130`
  (citizenship — the V5 subtype of identity).
- `backend/src/services/institution-governance.service.ts` — the Identity Registry
  institution and its `cannot_delete_identity_history` limit.

## 10. Open questions

1. **Delegation escalation is unproven.** Delegations are scoped and time-bounded, but no
   invariant yet guarantees a delegation cannot exceed the granter's own authority
   (V4-INV-008 planned). This is the classic confused-deputy risk and the highest-value
   gap to close in this volume.
2. **Human sessions are not first-class.** Operator authority (V27) currently rides on
   the API-key posture (V32); interactive, revocable, time-bounded human sessions are not
   modeled (V4-INV-009 planned).
3. **Citizenship is a second identity layer.** `citizens` (V5, migration `130`) wraps
   actors with lifecycle and sanctions; the exact boundary between "actor" (this volume)
   and "citizen" (V5) — which one authority checks read — should be stated explicitly in
   V5.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 10) | Bind actors, keys, roles, permissions, delegations, and the recorded authority-decision chain into one citable identity/authority layer, since attribution and authority are preconditions for governance, judiciary, and every audit trail. |
