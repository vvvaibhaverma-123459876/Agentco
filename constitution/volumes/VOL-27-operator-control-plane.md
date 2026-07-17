# Volume 27 — Operator Control Plane

## 1. Header

| Field | Value |
|---|---|
| Volume | 27 |
| Name | Operator Control Plane |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V1 (Constitutional Core), V4 (Identity & Authority), V12 (Governance), V28 (Operator Experience), V32 (Security) |

## 2. Purpose

The Operator Control Plane is how a human exercises root authority (H0 from V1) over the
running civilization: observing it, inspecting it, approving protected actions, and — in
extremis — stopping it. The Domain Neutrality correction renamed this from "Superuser
Control Plane" because **superuser is one operator role, not the interface itself**
(`GENERALIZATION_REPORT.md` §10): the plane is an Operator Interface with modes (Observe,
Inspect, Chat, Preview, Execute, Govern, Emergency), and different operators hold different
modes. Its load-bearing built properties: protected high/critical actions require human
approval through a queued gate with an SLA, and the kill switch is a governed,
single-active, reason-required stop. Mixed status; every present-tense claim cites its
file.

```text
OPERATOR (a role, not "the superuser")
   ▼  Operator Interface — modes:
   Observe   ── read governed status (V28 console, no fabricated data)
   Inspect   ── self-inspection reports (V17)
   Chat      ── interaction (V24)
   Preview   ── dry-run before Execute (to build)
   Execute   ── protected actions via the OVERRIDE QUEUE:
   │              override-queue.service.ts  enqueue(high|critical) → human resolve
   │              SLA per action; overdue surfaced (getOverdueSla)
   Govern    ── governance proposals / emergency powers (V12)
   Emergency ── KILL SWITCH: governance_kill_switches (one active per scope),
                engaged via a governance emergency power, REASON REQUIRED
```

## 3. Definitions

- **Operator** — a human acting on the civilization through the control plane; **one role
  among possible operator roles**, not a synonym for the interface.
- **Operator Interface** — the moded surface (Observe/Inspect/Chat/Preview/Execute/
  Govern/Emergency) through which operators act.
- **Override queue** — the human-approval gate for protected actions
  (`backend/src/services/override-queue.service.ts`, migration `013`).
- **SLA** — the per-action approval deadline; overdue requests are surfaced
  (`getOverdueSla`).
- **Kill switch** — the governed stop, one active per scope
  (`governance_kill_switches`, migration `098`;
  `backend/src/services/kill-switch.service.ts`).
- **Break-glass / root authority** — the emergency human override path (kill switch +
  emergency power), the concrete form of H0 (V1).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V27-INV-001 | Protected high- or critical-risk actions are enqueued for human approval before they execute; unresolved requests do not proceed. | enforced | `backend/src/services/override-queue.service.ts`, `backend/src/db/migrations/013_override_queue.sql` |
| V27-INV-002 | Each override request carries an approval SLA, and overdue requests are surfaced rather than silently expiring. | enforced | `backend/src/services/override-queue.service.ts` |
| V27-INV-003 | The kill switch is governed: at most one is active per scope, and engaging it is an audited act. | enforced | `backend/src/db/migrations/098_governance_kill_switch.sql`, `backend/src/services/kill-switch.service.ts`, `backend/tests/kill-switch.test.ts` |
| V27-INV-004 | Engaging the kill switch from the operator console requires a human-entered reason. | enforced | `frontend/src/app/civilization/page.tsx` |
| V27-INV-005 | The operator console shows only governed backend data — no fabricated or placeholder values. | enforced | `frontend/src/app/civilization/page.tsx`, `backend/tests/civilization-operator.test.ts` |
| V27-INV-006 | Operator actions resolve authority through the identity/authority layer, so an operator acts under a recorded authority decision. | enforced | `backend/src/services/identity-authority.service.ts`, `backend/src/routes/override.routes.ts` |
| V27-INV-007 | An engaged kill switch actually halts governed run loops (the Emergency mode has effect, not just record). | enforced | `backend/src/services/run-guard.service.ts`, `backend/tests/main-loop-kill-switch.test.ts` |
| V27-INV-008 | The Operator Interface exposes its modes (Observe, Inspect, Chat, Preview, Execute, Govern, Emergency) as first-class, role-gated capabilities — superuser being one role among several. | planned | — |
| V27-INV-009 | A Preview mode lets an operator dry-run a protected action and see its projected effect before executing. | planned | — |

## 5. Interfaces

- **Override** — `override-queue.service.ts` (`enqueue`, `resolve`, `listPending`,
  `getOverdueSla`); `backend/src/routes/override.routes.ts`; frontend override page
  (`frontend/src/app/override/`).
- **Kill switch** — `kill-switch.service.ts`; engaged via governance emergency power
  (`governance.service.ts`, V12); honored by `run-guard.service.ts` (V3).
- **Operator console** — `frontend/src/app/civilization/page.tsx` (Observe/Emergency
  today), backed by `civilization-operator.service.ts`.
- **Authority** — operator acts resolve through `identity-authority.service.ts` (V4).

## 6. State

- **Override queue:** `override_requests` (migration `013`).
- **Kill switch:** `governance_kill_switches` (migration `098`, one active per scope).
- **Emergency powers:** `governance_emergency_powers` (migration `135`, V12).
- **Frontend:** `frontend/src/app/civilization/`, `frontend/src/app/override/`.

## 7. Failure modes and responses

- **Unattended risky action** — high/critical actions block on human approval via the
  override queue (V27-INV-001), with an SLA so nothing silently stalls (V27-INV-002).
- **Ungoverned stop** — the kill switch is single-active-per-scope, audited, and
  reason-required from the console (V27-INV-003, V27-INV-004), and it actually halts run
  loops (V27-INV-007) — Emergency mode has effect.
- **Fabricated dashboards** — the console renders only governed backend data
  (V27-INV-005), a rule enforced by the operator service test.
- **Superuser-as-architecture** — the renamed plane treats superuser as one role; but the
  full moded, role-gated Operator Interface is not yet first-class (V27-INV-008 planned;
  open question 1).
- **Blind execution** — there is no Preview/dry-run mode yet (V27-INV-009 planned), so an
  operator executes without a projected-effect preview.

## 8. Verification obligations

Existing and green today: `backend/tests/kill-switch.test.ts`,
`backend/tests/main-loop-kill-switch.test.ts`,
`backend/tests/civilization-operator.test.ts` (governed data), override-queue behaviour.

Must exist before the planned invariants flip: a role-gated mode model with tests
(V27-INV-008), and a Preview/dry-run path with a projected-effect test (V27-INV-009).

## 9. Implementation mapping

- `backend/src/services/override-queue.service.ts` — human-approval gate + SLA.
- `backend/src/services/kill-switch.service.ts` — governed stop.
- `backend/src/services/run-guard.service.ts` — kill-switch enforcement (V3).
- `backend/src/services/civilization-operator.service.ts`,
  `frontend/src/app/civilization/page.tsx` — operator console (governed data,
  reason-required emergency).
- `backend/src/routes/override.routes.ts`, `frontend/src/app/override/` — override
  surface.
- Migrations: `013` (override queue), `098` (kill switch), `135` (emergency powers).

## 10. Open questions

1. **Modes are not yet first-class.** The console today does Observe and Emergency; the
   full Operator Interface (Observe/Inspect/Chat/Preview/Execute/Govern/Emergency) as
   role-gated capabilities — with superuser as one role among operators — is the unbuilt
   generalization (V27-INV-008; `GENERALIZATION_REPORT.md` §10).
2. **No Preview mode.** Operators cannot dry-run a protected action to see its projected
   effect before executing (V27-INV-009) — a high-value safety affordance.
3. **Operator identity.** Operator actions resolve authority (V4), but human sessions are
   not first-class (V4-INV-009); the operator plane is where that gap is most felt, since
   root authority should be exercised under a strong, revocable session.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written (renamed from Superuser Control Plane per GENERALIZATION_REPORT §10). | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 25) | Bind the override-approval gate, governed kill switch, and governed operator console into one citable control plane, and reframe superuser as one operator role within a moded Operator Interface rather than the interface itself. |
