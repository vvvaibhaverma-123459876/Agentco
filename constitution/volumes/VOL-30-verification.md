# Volume 30 — Verification

## 1. Header

| Field | Value |
|---|---|
| Volume | 30 |
| Name | Verification |
| Tier | statute |
| Epistemic status | descriptive |
| Doc status | written |
| Related volumes | V17 (Self Inspection), V32 (Security), V14 (Learning Engine), V29 (Infrastructure), V1 (Constitutional Core) |

## 2. Purpose

Verification is the layer that decides whether a claim of "done" is true. It defines the
test regime, the release gate, and the CI workflows that must pass before code is trusted —
and the constitutional rule that **a completion claim is machine-derived from executable
evidence, never asserted.** This is the volume that gives the whole constitution its teeth:
every other volume's "enforced" invariant is a promise that a test exists, and this volume
is where those tests are marshalled. Descriptive tier: every normative sentence cites the
enforcing file or workflow.

```text
UNIT / INTEGRATION / E2E   backend/tests/*.test.ts (116 files, jest --runInBand)
   │   route-auth contract · adversarial · restart/replay · fault injection
   ▼
RELEASE GATE  make release-gate  — 12 steps, fail-closed:
   [0] clean tree · [0a] gate-integrity · [0b] advertised targets
   [1] status-check · [1a-1e] conformance/calibration/learning/score validation
   [2-3] install + migrations · route-auth contract · decision-log chain · suites
   ▼
CI WORKFLOWS  .github/workflows/  ci · constitution · civilization-completion
   clean-room-audit · runtime-integration-audit · staging-deployment-audit ·
   hosted-staging-audit · longitudinal-evidence · deploy
   ▼
COMPLETION EVIDENCE  machine-generated, predicate-bound (never prose "done")
```

## 3. Definitions

- **Test regime** — the jest suites run in-band (`backend/tests/`, `backend/jest.config.ts`).
- **Release gate** — the authoritative 12-step gate (`make release-gate`).
- **Gate integrity** — the check that gates are not faked (`verify_gate_integrity.py`, V17).
- **Route-auth contract** — the test that every route is classified (V32,
  `route-auth-contract.test.ts`).
- **Completion predicate** — the machine-derived boolean for a build's completeness
  (`termination_predicate_met` in the ledgers; `generate_civilization_completion.py`).
- **Adversarial / fault-injection tests** — suites that attack the system
  (`red-team-corpus.test.ts`, `civilization-adversarial.test.ts`, restart/replay).
- **Evals** — benchmark and acceptance evaluations (`evals/`).

## 4. Invariants

| ID | Statement | Status | Enforcement |
|---|---|---|---|
| V30-INV-001 | The authoritative release gate is a fail-closed multi-step sequence, not a single command; any step failing fails the gate. | enforced | `Makefile` (`release-gate`) |
| V30-INV-002 | The release gate refuses fake-success and bypass patterns before running tests (gate integrity runs first). | enforced | `Makefile`, `scripts/verify_gate_integrity.py` |
| V30-INV-003 | Every route is classified and a contract test fails the build on an unclassified route. | enforced | `backend/tests/route-auth-contract.test.ts`, `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` |
| V30-INV-004 | The decision-log hash chain is verified as part of the gate, detecting tampering. | enforced | `Makefile`, `backend/src/db/migrations/012_decision_log_chain.sql` |
| V30-INV-005 | Adversarial and restart/replay behaviour is tested, not only happy paths. | enforced | `backend/tests/civilization-adversarial.test.ts`, `backend/tests/red-team-corpus.test.ts` |
| V30-INV-006 | Completion is machine-derived from ledger evidence and states its predicate explicitly, never asserted in prose. | enforced | `scripts/generate_civilization_completion.py`, `.github/workflows/civilization-completion.yml` |
| V30-INV-007 | CI runs the constitution, civilization-completion, and integration audit workflows on push. | enforced | `.github/workflows/constitution.yml`, `.github/workflows/civilization-completion.yml`, `.github/workflows/runtime-integration-audit.yml` |
| V30-INV-008 | The release gate runs green against the built civilization code before any completion predicate is set true. | planned | — |
| V30-INV-009 | Test coverage of enforced invariants is measured, so a constitutional "enforced" claim without a covering test is detected. | planned | — |

## 5. Interfaces

- **Test runner** — `backend/jest.config.ts`; npm scripts `test`, `test:unit`,
  `test:integration`, `test:e2e` (all `--runInBand`).
- **Gate** — `make release-gate` (12 steps), `make gate-integrity`,
  `make status-check`, `make civilization-suite`, `make civilization-completion`.
- **CI** — nine workflows in `.github/workflows/` (ci, constitution,
  civilization-completion, clean-room-audit, runtime-integration-audit,
  staging-deployment-audit, hosted-staging-audit, longitudinal-evidence, deploy).
- **Evals** — `evals/` (acceptance, agent_benchmarks, north_star_cross_domain, …).
- **Completion** — `scripts/generate_civilization_completion.py`.

## 6. State

- **Tests:** `backend/tests/*.test.ts` (116 files), `evals/`.
- **Gate definition:** `Makefile` (`release-gate` and its 12 steps).
- **CI:** `.github/workflows/`.
- **Evidence:** `reports/system_run/latest/`, `reports/civilization_completion/latest/`.
- **Contracts:** `docs/audit/ROUTE_SENSITIVITY_MATRIX.md`.

## 7. Failure modes and responses

- **"Done" without proof** — completion is machine-derived and predicate-explicit
  (V30-INV-006); the 2026-07-14 walk-back (setting the civilization predicate back to
  false because canonical gates had not run) is this invariant working
  (`docs/civilization/OUTSTANDING_GATES.md`).
- **Faked gates** — gate integrity runs before tests and fails closed on echo-only or
  force-exit patterns (V30-INV-002); it flagged this build's own targets.
- **Unclassified attack surface** — the route-auth contract fails the build on any
  unclassified route (V30-INV-003).
- **Happy-path-only testing** — adversarial, restart/replay, and fault suites exist
  (V30-INV-005).
- **Predicate set before gates run** — the highest-value gap: nothing mechanically
  prevents `termination_predicate_met: true` before `make release-gate` runs green
  against the built code (V30-INV-008 planned = V1-INV-007). The pre-existing `main` CI
  failures (V0 open question 4) are release-gate steps not yet green.
- **Uncovered "enforced" invariants** — no measurement yet ties each constitutional
  enforced invariant to a covering test (V30-INV-009 planned).

## 8. Verification obligations

Existing and green today: the 116 jest suites, the constitution checker, the
civilization-completion workflow, the runtime-integration audit. (Note: some
release-gate steps and the clean-room/CI workflows are currently red on `main` for
pre-existing reasons — score-validation report staleness and clean-room audit — tracked
in V0 open question 4; this volume is where that debt is owned.)

Must exist before the planned invariants flip: a gate binding predicate-setting to a
green release-gate run (V30-INV-008), and an invariant-coverage measurement
(V30-INV-009).

## 9. Implementation mapping

- `Makefile` — `release-gate` (12 steps), `gate-integrity`, suite targets.
- `backend/jest.config.ts`, `backend/tests/` — the test regime.
- `.github/workflows/` — CI enforcement.
- `scripts/verify_gate_integrity.py`, `scripts/generate_civilization_completion.py`,
  `scripts/generate_status.py` — the anti-fake-success and completion machinery (V17).
- `docs/audit/ROUTE_SENSITIVITY_MATRIX.md`, `backend/tests/route-auth-contract.test.ts`
  — the route contract.

## 10. Open questions

1. **Predicate-setting is not gate-bound.** A completion predicate can be set true
   without `make release-gate` running green against the built code (V30-INV-008 =
   V1-INV-007). This is the constitutional loop's most important verification gap; the
   2026-07-14 walk-back showed why it matters.
2. **`main` carries pre-existing gate debt.** Clean-room audit and CI are red on `main`
   for score-validation/report-staleness reasons predating the constitution work; owning
   and clearing this debt is this volume's live task (V0 open question 4).
3. **No invariant-coverage metric.** The constitution now has 197 invariants, 143 marked
   enforced; nothing yet proves each enforced invariant has a covering test (V30-INV-009).
   A coverage report keyed by invariant id would close the loop between the constitution
   and the test suite.

## 11. Change log

| Date | Change | Author / authorizing human | Rationale |
|---|---|---|---|
| 2026-07-15 | Volume written. | Claude (build agent), per the operator's Architecture Constitution prompt kit (order position 23) | Bind the test regime, the 12-step release gate, the CI workflows, and machine-derived completion into one citable verification layer — the teeth behind every other volume's "enforced" claim — and name the predicate-not-gate-bound gap that the 2026-07-14 walk-back exposed. |
