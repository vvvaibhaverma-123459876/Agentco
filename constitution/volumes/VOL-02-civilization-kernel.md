# Volume 2 — Civilization Kernel

## 1. Header

| Field | Value |
|---|---|
| Volume | 2 |
| Name | Civilization Kernel |
| Tier | constitutional |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V3 (Runtime Operating System), V12 (Governance), V4 (Identity & Authority), V29 (Infrastructure) |

## 2. Purpose

The Kernel is the root of the running civilization: the singleton civilization identity,
its version lineage, jurisdictions, protected invariants, emergency state, objectives, and
charters — plus the bootstrap and migration machinery that brings a database to a runnable
state. Its constitutional properties are **singleton identity** (at most one active
civilization), **append-only kernel history** (transitions and versions cannot be
rewritten), and **gated transitions** (lifecycle changes flow only through the kernel
service). Mixed status; every present-tense claim cites its file.

```text
BOOTSTRAP  migrate.ts   filename-ordered SQL, each file in a transaction,
   │                    schema_migrations tracks applied files
   ▼
CIVILIZATION  civilizations   partial unique index: at most ONE active
   │   ensureCivilizationRoot / createCivilization / activateCivilization
   ├─ VERSIONS       civilization_versions        (append-only)
   ├─ JURISDICTIONS  civilization_jurisdictions
   ├─ PROTECTED INV  civilization_protected_invariants  (append-only)
   ├─ OBJECTIVES     civilization_objectives
   ├─ CHARTERS       civilization_charters  (one active per civilization)
   ▼
LIFECYCLE  transitionStatus → set_config('civilization.kernel_transition_authorized')
   │   guarded: status changes only through the kernel service
   ▼   append-only civilization_state_transitions (civilization_kernel_append_only)
EMERGENCY  enterEmergency (expires_at) → revokeEmergency / expireDueEmergencies
           one active emergency per (civilization, scope)
```

## 3. Definitions

- **Civilization** — the singleton root entity of a running instance
  (`civilizations`, migration `129`; `backend/src/services/civilization-kernel.service.ts`).
- **Version** — an append-only civilization version row (`civilization_versions`).
- **Jurisdiction** — a scope the civilization governs (`civilization_jurisdictions`).
- **Protected invariant (kernel)** — a registered rule row no process may violate
  (`civilization_protected_invariants`; the runtime half of V1's H1).
- **Charter** — the kernel-level identity/mission document, one active per civilization
  (`civilization_charters`; `proposeCharter`, `activateCharter`).
- **Emergency state** — a time-bounded exceptional condition, one active per scope
  (`civilization_emergency_states`).
- **Transition gate** — the `set_config('civilization.kernel_transition_authorized', …)`
  SET LOCAL that only the kernel service sets, without which the guard rejects a change.
- **Bootstrap** — filename-ordered, per-file-transactional migration application with
  `schema_migrations` tracking (`backend/src/db/migrate.ts`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V2-INV-001 | At most one civilization is active at a time, enforced by a partial unique index. | enforced | `backend/src/db/migrations/129_civilization_kernel.sql`, `backend/tests/civilization-kernel.test.ts` |
| V2-INV-002 | Kernel history — versions, state transitions, and protected invariants — is append-only at the database layer. | enforced | `backend/src/db/migrations/129_civilization_kernel.sql`, `backend/tests/civilization-kernel.test.ts` |
| V2-INV-003 | Civilization lifecycle status changes only through the kernel service's authorized transition gate; a direct update without the gate is rejected. | enforced | `backend/src/services/civilization-kernel.service.ts`, `backend/src/db/migrations/129_civilization_kernel.sql`, `backend/tests/civilization-kernel.test.ts` |
| V2-INV-004 | At most one charter is active per civilization, and at most one emergency state is active per civilization and scope. | enforced | `backend/src/db/migrations/129_civilization_kernel.sql` |
| V2-INV-005 | Emergency states are time-bounded and expire, and expiry moves the civilization out of emergency. | enforced | `backend/src/services/civilization-kernel.service.ts`, `backend/src/db/migrations/129_civilization_kernel.sql` |
| V2-INV-006 | Migrations apply in filename order, each within a transaction, and each applied file is recorded so migration is idempotent. | enforced | `backend/src/db/migrate.ts` |
| V2-INV-007 | The kernel seeds and counts protected invariants, giving the runtime a live count of the rules it must honor. | enforced | `backend/src/services/civilization-kernel.service.ts`, `backend/tests/civilization-kernel.test.ts` |
| V2-INV-008 | Migration numbering is unique and gap-checked so two files cannot silently share an ordinal. | planned | — |
| V2-INV-009 | The kernel protected-invariant registry is reconciled with the document-level invariant registry (constitution/invariants.yaml). | planned | — |

## 5. Interfaces

- **Kernel APIs** — `civilization-kernel.service.ts`: `createCivilization`,
  `ensureCivilizationRoot`, `getActiveCivilization`, `getRoot`, `activateCivilization`,
  `transitionStatus`, `enterEmergency`, `revokeEmergency`, `expireDueEmergencies`,
  `proposeCharter`, `activateCharter`, `getActiveCharter`.
- **Routes** — `civilization-kernel.routes.ts` (classified in the V32 matrix).
- **Bootstrap** — `backend/src/db/migrate.ts` (`npm run db:migrate`); server startup
  `backend/src/server.ts` (`app.listen`, auth-posture and secret guards from V32).
- **Canonical logs** — `event_log`, `decision_log`, and the transactional outbox (V3)
  are the kernel's audit substrate.

## 6. State

- **Kernel (migration `129_civilization_kernel.sql`):** `civilizations` (singleton),
  `civilization_versions`, `civilization_charters`, `civilization_jurisdictions`,
  `civilization_protected_invariants`, `civilization_emergency_states`,
  `civilization_state_transitions` (append-only), `civilization_objectives`.
- **Migration tracking:** `schema_migrations` (`backend/src/db/migrate.ts`).
- **Append-only guard:** `civilization_kernel_append_only()` trigger function.

## 7. Failure modes and responses

- **Two active civilizations** — the partial unique index
  `WHERE status = 'active'` makes it impossible (V2-INV-001).
- **Rewriting kernel history** — the `civilization_kernel_append_only()` trigger rejects
  UPDATE on versions, transitions, and protected invariants (V2-INV-002).
- **Bypassing lifecycle** — a status change without
  `civilization.kernel_transition_authorized` set (only the service sets it) is rejected
  by the guard (V2-INV-003).
- **Permanent emergency** — emergency states expire and expiry recovers the civilization
  (V2-INV-005), matching V1's time-bounded-power principle.
- **Partial migration** — each migration file applies in its own transaction and is
  recorded on commit, so a failure rolls back that file and re-running skips applied ones
  (V2-INV-006).
- **Duplicate migration ordinal** — two files can currently share a number (there are
  both `129_civilization_kernel.sql` and `129_longitudinal_mission_evidence.sql`); the
  runner tolerates it by filename, but numbering discipline is not enforced
  (V2-INV-008 planned; open question 1).

## 8. Verification obligations

Existing and green today: `backend/tests/civilization-kernel.test.ts` (singleton,
append-only history, gated transitions, protected-invariant seed/count, emergency
lifecycle).

Must exist before the planned invariants flip: a migration-numbering uniqueness/gap check
in CI (V2-INV-008), and a reconciliation between the kernel protected-invariant registry
and `constitution/invariants.yaml` (V2-INV-009).

## 9. Implementation mapping

- `backend/src/services/civilization-kernel.service.ts` — civilization identity,
  lifecycle transitions (gated), emergency states, charters, protected-invariant seed.
- `backend/src/db/migrations/129_civilization_kernel.sql` — schema, partial unique
  singleton indexes, `civilization_kernel_append_only()` trigger, transition guard.
- `backend/src/db/migrate.ts` — filename-ordered, per-file-transactional migration
  runner with `schema_migrations`.
- `backend/src/server.ts` — startup, route registration, V32 startup guards.
- `backend/src/routes/civilization-kernel.routes.ts` — kernel HTTP surface.

## 10. Open questions

1. **Duplicate migration ordinal 129.** `129_civilization_kernel.sql` and
   `129_longitudinal_mission_evidence.sql` share a number (the latter arrived via the
   operator's PR #25). The filename-ordered runner tolerates it, but nothing prevents a
   future collision or an ordering ambiguity (V2-INV-008 planned). Renumbering *applied*
   migrations is unsafe, so the fix is a forward numbering-discipline check.
2. **Two protected-invariant registries.** The kernel's
   `civilization_protected_invariants` and the document `constitution/invariants.yaml`
   are not reconciled (V2-INV-009 planned; the same family as V1 open question 3 and V9
   open question 1).
3. **Canonical-runtime freeze belongs here.** Many volumes deferred "which of two
   generations is canonical" to a Volume 2 concern (V7 ledgers, V8 goals, V13 judiciary,
   V14 learning, V33 model resolution). The frozen decisions live in
   `docs/civilization/CANONICAL_RUNTIME_MAP.md` (D1–D10); binding those into invariants
   is this volume's outstanding integrative work.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 15) | Bind the singleton civilization identity, append-only kernel history, gated lifecycle, emergency states, charters, and the migration bootstrap into one citable kernel — the root the runtime OS (V3) keeps alive. |
