# Volume 7 — Civilization Economy

## 1. Header

| Field | Value |
|---|---|
| Volume | 7 |
| Name | Civilization Economy |
| Tier | statute |
| Epistemic status | mixed |
| Doc status | written |
| Related volumes | V8 (Missions), V13 (Judiciary), V12 (Governance), V6 (Institutions), V11 (Trust & Calibration) |

## 2. Purpose

The Economy makes scarcity real. Compute, tokens, and budget are finite, so every unit is
accounted for in a double-entry ledger, reserved before use and settled after, and
periodically reconciled against its own transaction history. Budgets are proposed and
approved through governance; penalties debit real balances (the judiciary's teeth, V13).
The constitutional rule is that **resources cannot be created from nothing** — a balance
never goes negative, and the ledger must reconcile. Mixed status: two ledger generations
coexist (open question 1); every present-tense claim cites its file.

```text
ACCOUNT  treasury_accounts (per scope) / civilization_resource_accounts
   │   balance NUMERIC CHECK (>= 0)    resources cannot be created from nothing
   ▼
FUND → RESERVE (two-phase) → SETTLE     resource_reservations (mig 082)
   │   transaction_type ∈ {credit(+), debit(−), adjustment(+)}, amount CHECK (> 0)
   ▼
BUDGET  budget_proposals → decideBudget (governed) → budget_allocations
   │
PENALTY  penalties   ← judiciary imposePenalty (V13)   debits a real balance
   │
COST  cost_attribution_records → costRollup (mission/institution/domain)
   ▼
RECONCILE  reconciliation_runs   recompute balance from signed history;
                                 imbalance ⇒ not balanced (fail-visible)
```

## 3. Definitions

- **Treasury account** — a per-scope balance for a resource type
  (`treasury_accounts`, migration `134`; `backend/src/services/treasury.service.ts`),
  scopes: civilization/society/institution/coalition/mission/citizen.
- **Resource account (base)** — the older civilization resource account with a
  `balance >= 0` CHECK (`civilization_resource_accounts`, migration `081`;
  `backend/src/services/resource-ledger.service.ts`).
- **Transaction** — a credit, debit, or adjustment with a positive amount and a
  non-negative `balance_after` (`civilization_resource_transactions`, migration `081`).
- **Reservation** — a two-phase hold placed before spend and released or settled after
  (`resource_reservations`, migration `082`).
- **Budget** — a proposed, governance-decided allocation
  (`budget_proposals`, `budget_allocations`, migration `134`).
- **Penalty** — a debit imposed as a judiciary consequence
  (`penalties`, migration `134`; `imposePenalty`).
- **Cost attribution** — recorded spend rolled up by dimension
  (`cost_attribution_records`, `costRollup`).
- **Reconciliation** — recomputing balances from signed transaction history and
  reporting any imbalance (`reconcile`, `reconciliation_runs`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V7-INV-001 | A resource balance can never go negative — resources cannot be created from nothing. | enforced | `backend/src/db/migrations/081_resource_ledger.sql`, `backend/src/db/migrations/134_civilization_economy.sql` |
| V7-INV-002 | Every resource transaction has a positive amount and records the balance after it, giving a replayable ledger. | enforced | `backend/src/db/migrations/081_resource_ledger.sql`, `backend/tests/treasury.test.ts` |
| V7-INV-003 | Reconciliation recomputes each account's balance from its signed transaction history (credit +, debit −, adjustment +) and reports any imbalance. | enforced | `backend/src/services/treasury.service.ts`, `backend/tests/treasury.test.ts` |
| V7-INV-004 | Spend is reserved before use and settled or released after; a two-phase reservation stands between request and debit. | enforced | `backend/src/db/migrations/082_resource_reservations.sql`, `backend/src/services/treasury.service.ts` |
| V7-INV-005 | Budgets are proposed and decided through a governed proposal path before allocation. | enforced | `backend/src/services/treasury.service.ts`, `backend/tests/treasury.test.ts` |
| V7-INV-006 | A judiciary penalty debits a real account balance, not a symbolic marker. | enforced | `backend/src/services/treasury.service.ts`, `backend/src/services/judiciary-case.service.ts`, `backend/tests/judiciary-case.test.ts` |
| V7-INV-007 | Cost is attributed per scope and rolled up per mission, institution, or domain. | enforced | `backend/src/services/treasury.service.ts`, `backend/tests/treasury.test.ts` |
| V7-INV-008 | A resource-policy limit (max risk level, min trust factor) gates spend requests before they draw down a balance. | enforced | `backend/src/db/migrations/134_civilization_economy.sql`, `backend/src/services/treasury.service.ts` |
| V7-INV-009 | The two ledger generations are reconciled or unified so a single authoritative balance exists per scope and resource. | planned | — |

## 5. Interfaces

- **Accounts & ledger** — `treasury.service.ts`: `openAccount`, `getAccount`, `balance`,
  `fund`, `recordCost`, `costRollup`, `reconcile`.
- **Budgets** — `proposeBudget`, `decideBudget` (governed), `allocateBudget`,
  `evaluateRequest`, `setPolicy`.
- **Penalties** — `imposePenalty` (called by the judiciary, V13).
- **Base ledger** — `resource-ledger.service.ts` (migrations `081`/`082`).
- **Routes** — treasury HTTP routes (classified in the V32 matrix).

## 6. State

- **Treasury (migration `134`):** `treasury_accounts`, `resource_policies`,
  `budget_proposals`, `budget_allocations`, `penalties`, `cost_attribution_records`,
  `reconciliation_runs`.
- **Base ledger (migrations `081`/`082`):** `civilization_resource_accounts`
  (`balance >= 0`), `civilization_resource_transactions` (positive amount,
  non-negative balance_after), `resource_reservations`.
- **Consumers:** missions settle here (V8, `mission_settlements`); the judiciary debits
  here (V13); token budgets are read from the LLM provider (V33).

## 7. Failure modes and responses

- **Creating resources from nothing** — the `balance >= 0` CHECK and positive-amount
  constraints reject it at the database (V7-INV-001, V7-INV-002).
- **Silent drift** — `reconcile` recomputes from signed history and flags imbalance
  rather than trusting the stored balance (V7-INV-003); a prior bug where per-scope
  accounts collapsed and where the debit sign was wrong was fixed by keying accounts per
  scope-owner and recomputing with `CASE transaction_type WHEN 'debit' THEN -amount`
  (see `docs/civilization/PLAN_AND_PROGRESS.md` and `treasury.service.ts`).
- **Ungoverned spend** — budgets require a governed decision before allocation
  (V7-INV-005), and resource policies gate requests by risk/trust (V7-INV-008).
- **Toothless penalties** — `imposePenalty` debits a real balance (V7-INV-006),
  exercised by scenario D.
- **Two ledgers disagreeing** — the base ledger (migrations `081`/`082`) and the treasury
  (migration `134`) are two generations; nothing yet guarantees a single authoritative
  balance (V7-INV-009 planned; open question 1) — the most important gap here.

## 8. Verification obligations

Existing and green today: `backend/tests/treasury.test.ts` (accounts, funding,
two-phase reservation, governed budget, cost rollup, signed reconciliation),
`backend/tests/judiciary-case.test.ts` (penalty debits a real balance).

Must exist before the planned invariant flips: a cross-ledger reconciliation test
proving the base ledger and treasury agree on the authoritative balance (V7-INV-009).

## 9. Implementation mapping

- `backend/src/services/treasury.service.ts` — accounts, funding, reservations, budgets,
  penalties, cost attribution, reconciliation.
- `backend/src/services/resource-ledger.service.ts` — base resource ledger.
- Migrations: `081` (resource ledger), `082` (reservations), `134` (civilization
  economy).
- Enforcement seams: `judiciary-case.service.ts` (penalties), `mission.service.ts`
  (settlements, V8).

## 10. Open questions

1. **Two ledger generations.** `civilization_resource_accounts` (migration `081`) and
   `treasury_accounts` (migration `134`) both hold balances; which is authoritative for a
   given scope/resource is not frozen (V7-INV-009 planned). This is the economy's version
   of the recurring "two generations" drift and the highest-value gap.
2. **Reservation settlement completeness.** The V8 (Missions) invariant V8-INV-008
   (release on abandonment) lives at the mission↔economy seam; the economy side needs a
   matching guarantee that no reservation is orphaned.
3. **Token budget integration.** LLM token budgets are read in the provider (V33) but the
   binding between provider token accounting and the treasury ledger is not yet a stated
   invariant.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 11) | Bind the double-entry ledger, two-phase reservations, governed budgets, penalties, and signed reconciliation into one citable economy — the scarcity layer missions spend and the judiciary debits. |
