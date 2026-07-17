# Volume 23 — Constraint Engine

## 1. Header

| Field | Value |
|---|---|
| Volume | 23 |
| Name | Constraint Engine |
| Tier | article |
| Epistemic status | prescriptive |
| Doc status | written |
| Related volumes | ALL — this is a cross-cutting article; especially V1, V7, V12, V15, V32, V3 |

## 2. Purpose

This is an **article**, the complement of the Reasoning Engine (V10). Where V10 requires
every decision to record *why* it was made, V23 requires every action to pass through
**reality filters** before it executes — and to fail closed when a filter cannot pass:

> Before any action executes, it is checked against the constraints that bind it —
> logical, physical, economic, ethical, computational, legal, resource, and time — and if
> a binding constraint cannot be satisfied, the action does not execute.

The Constraint Engine is not a single service; it is the discipline that every actuator in
the civilization checks its constraints and *fails closed*. Prescriptive tier: the unified
constraint contract is a design to build, but many concrete filters already exist and are
cited honestly in §9.

```text
ACTION requested
   ▼  CONSTRAINT FILTERS (fail closed if any binding one cannot pass):
   ├─ resource     budget reserved / balance ≥ 0        (V7; treasury, resource ledger)
   ├─ economic     resource policy: risk/trust limits   (V7-INV-008)
   ├─ legal        active runtime policy allows it       (V12; policy-enforcement)
   ├─ authority    capability granted / role permits     (V15, V4)
   ├─ computational SSRF / URL safety / token clamp       (V32, V33)
   ├─ time         ttl / expiry / deadline                (emergency powers, reservations)
   ├─ physical     kill switch not engaged                (V1, V3 run guard)
   ├─ logical      state-machine precondition met         (V8, V12, V13 transitions)
   └─ ethical      risk tier / human approval required    (V27 override queue)
   ▼  pass ⇒ execute ;  fail ⇒ deny (recorded), never partial
```

## 3. Definitions

- **Constraint** — a condition an action must satisfy to be permitted, in one of eight
  classes: logical, physical, economic, ethical, computational, legal, resource, time.
- **Reality filter** — a check that rejects an action violating a constraint before it
  executes.
- **Fail closed** — when a filter cannot positively confirm the constraint is satisfied,
  the action is denied, not allowed.
- **Binding vs advisory constraint** — a binding constraint blocks; an advisory one warns.
  (Prescriptive: the explicit binding/advisory classification is to be built.)
- **Constraint record** — the recorded verdict of the filters for an action (shares the
  decision-record substrate with V10).

## 4. Invariants

Obligations. Enforced fragments cite existing fail-closed guards; the unified contract is
planned.

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V23-INV-001 | A web fetch that cannot pass the SSRF/URL-safety filter is denied, not attempted (computational constraint, fail closed). | enforced | `backend/src/adapters/url-safety.ts`, `backend/tests/red-team-corpus.test.ts` |
| V23-INV-002 | An action lacking an active runtime-policy allowance is blocked at execution (legal constraint). | enforced | `backend/src/services/policy-enforcement.service.ts`, `backend/tests/governance.test.ts` |
| V23-INV-003 | A spend that would drive a balance negative or exceed a resource policy is rejected (resource and economic constraints). | enforced | `backend/src/db/migrations/081_resource_ledger.sql`, `backend/src/services/treasury.service.ts` |
| V23-INV-004 | An action requiring a capability without an active grant fails closed (authority constraint). | enforced | `backend/src/services/capability-expansion.service.ts`, `backend/tests/capability-expansion.test.ts` |
| V23-INV-005 | When the kill switch is engaged, run stages halt (physical/stop constraint). | enforced | `backend/src/services/run-guard.service.ts`, `backend/tests/main-loop-kill-switch.test.ts` |
| V23-INV-006 | A state transition whose precondition is unmet is rejected (logical constraint). | enforced | `backend/src/services/mission.service.ts`, `backend/src/services/governance.service.ts` |
| V23-INV-007 | Time-bounded authorities (emergency powers, reservations) expire and are unusable past expiry (time constraint). | enforced | `backend/src/db/migrations/135_governance.sql`, `backend/src/services/civilization-kernel.service.ts` |
| V23-INV-008 | Every actuator declares the constraint classes it checks, and a contract test asserts no actuator executes without checking its binding constraints. | planned | — |
| V23-INV-009 | Ethical constraints (risk-tier gating, required human approval) are uniformly applied across actuators, not per-service ad hoc. | planned | — |

## 5. Interfaces

As an article, the contract is implemented by every actuator:

- **Existing filters** — `url-safety.ts` (computational), `policy-enforcement.service.ts`
  (legal), `treasury.service.ts` + `resource-ledger.service.ts` (resource/economic),
  `capability-expansion.service.ts` (authority), `run-guard.service.ts` (stop),
  service state machines (logical), emergency/reservation expiry (time),
  `override-queue.service.ts` + risk-tier classifier (ethical).
- **Obligated actuators** — mission execution, governance activation, judiciary
  enforcement, capability use, model calls, web fetches.
- **Shared substrate** — constraint verdicts record alongside decisions (V10).

## 6. State

- **Today:** the constraint state lives in the systems that own each filter — resource
  ledger (V7), runtime policies (V12), capability grants (V15), kill-switch state (V1),
  emergency/reservation expiries. There is no single constraint registry.
- **To be built:** a declared per-actuator constraint manifest and a uniform
  binding/advisory classification (V23-INV-008/009).

## 7. Failure modes and responses

- **Executing past a constraint** — each existing filter denies rather than warns
  (V23-INV-001..007); the failure this article guards is an actuator that runs without
  consulting its constraints.
- **Fail open** — the design rule is fail closed: an unverifiable constraint denies (as in
  `url-safety.ts` and the production budget guard in V33). The gap is that this is a
  per-service convention, not a system-wide contract test (V23-INV-008 planned).
- **Inconsistent ethics** — risk-tier gating and human-approval requirements are applied
  where each service chose to, not uniformly (V23-INV-009 planned) — the highest-value
  gap, since ethical constraints are the ones most costly to miss.
- **Unrecorded denials** — a denied action should be recorded (shares V10's substrate);
  uniform denial-recording is part of the unified contract to build.

## 8. Verification obligations

Existing and green today: the per-filter tests cited in §4 (`red-team-corpus`,
`governance`, `capability-expansion`, `main-loop-kill-switch`, treasury).

Must exist to satisfy the article: a per-actuator constraint manifest and a cross-cutting
contract test asserting every actuator checks its binding constraints and fails closed
(V23-INV-008), plus uniform ethical-constraint application (V23-INV-009).

## 9. Implementation mapping

- **Enforced fragments (real fail-closed filters):** `backend/src/adapters/url-safety.ts`,
  `backend/src/services/policy-enforcement.service.ts`,
  `backend/src/services/treasury.service.ts`,
  `backend/src/services/resource-ledger.service.ts`,
  `backend/src/services/capability-expansion.service.ts`,
  `backend/src/services/run-guard.service.ts`, service state machines
  (`mission.service.ts`, `governance.service.ts`, `judiciary-case.service.ts`),
  emergency/reservation expiry (`civilization-kernel.service.ts`, migration `135`).
- **Not yet built:** the unified constraint contract — a per-actuator manifest of checked
  constraint classes, a binding/advisory classification, and a contract test that no
  actuator executes without checking its binding constraints.
- **Risk/ethics substrate:** `backend/src/services/risk-tier-classifier.service.ts`,
  `backend/src/services/override-queue.service.ts` (human approval).

## 10. Open questions

1. **Unify or federate?** A single Constraint Engine service that every actuator calls,
   versus the current federation of per-domain filters. Federation is what exists and is
   robust; a unifying *contract* (manifest + contract test) may be better than a unifying
   *service*, keeping filters where the domain knowledge lives while making coverage
   provable (favoring V23-INV-008).
2. **Ethical constraints are the weakest link.** Resource, legal, and computational
   filters are strong; ethical constraints (when is human approval required?) are the
   least uniform (V23-INV-009). This deserves priority.
3. **Shared substrate with V10.** Constraint verdicts and reasoning records should share
   the decision-record store so a decision's *why* (V10) and *what-filtered-it* (V23) are
   one auditable object.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written as a cross-cutting article. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 17; articles are obligations on all volumes) | Establish the obligation that every action passes its reality filters and fails closed — generalizing the many concrete fail-closed guards that already exist into one coverage-provable contract, while honestly marking that unified contract as to-be-built. |
