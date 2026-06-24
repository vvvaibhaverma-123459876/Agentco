# Civilization Layer Audit — Phase A Inventory

**Date:** 2026-06-25
**Method:** Static import-graph reachability from runtime entrypoints + stub/test classification.
**Scope:** 77 TypeScript services in `backend/src/services/` (Python trees noted separately).

---

## HEADLINE: Integration is the real gap, not "unbuilt"

The civilization layer is largely **written** but barely **wired**. Reachability from
the actual runtime entrypoints:

| Entrypoint | Services reached |
|---|---|
| `server.ts` (HTTP API — the deployable app) | **5 / 77** |
| `autonomy-orchestrator.service.ts` (autonomy loop, run only from a one-off test script) | 23 / 77 |
| **Union (integrated into *some* runtime)** | **28 / 77** |
| **Truly orphaned (wired into nothing)** | **49 / 77** |

The user directive is "everything integrated, no stubs." **The 49-orphan number is that gap.**
Most of the named "civilization" (institutions, coalitions, governance, trust, goal hierarchy,
calibration governance) is built as disconnected islands and connected to no running process.

### Critical specifics
- `autonomy-civilization-bridge.service` — the intended connector between the autonomy loop and
  the civilization — is **itself orphaned**. The bridge is not wired in.
- `protected-surface-enforcer.service` — the "Brick 3 VERIFIED" constitutional enforcer — is
  **orphaned**. It has a passing unit test but is integrated into **no runtime path**. Verified
  in isolation ≠ enforcing anything in the running system.
- `provenance.service` — a declared **protected surface** — is orphaned.
- The only deployable entrypoint (`server.ts`) reaches just: `audit-log`, `credential`,
  `memory-store`, `override-queue`, `task-dispatch`. None of the autonomy/civilization layer.

---

## Classification (detector + manual)

**REAL + has real integration test (7):** `audit-log`, `credential`, `event-bus`,
`memory-store`, `override-queue`, `protected-surface-enforcer`, `task-dispatch`.

**Throwing-stub services: 0** — after this session's restoration of `task-dispatch` and
`credential` (see commit `fface77`), the detector finds no `throw 'not implemented'` service
bodies. (Was 2 before restoration; those were stubs I introduced and then corrected.)

**Integrated into autonomy runtime (reachable from orchestrator, 23):** includes
`action-executor`, `autonomy-action-planner`, `loop-detector`, `reflection`, `source-discovery`,
`team-activation`, `trajectory-store`, `reputation-learning`, `adaptive-strategy`, `learner`,
`self-modification-validator`, `worker-coordinator`, `trust-policy`, `trust-reputation`,
`structured-logger`, `observability`, `crash-recovery`, `task-engine`, `autonomy-metrics`,
`autonomy-model-selection`, `rag`, `symbolic`, `ensemble` (full list in `audit_results.json`).

**Truly orphaned (49)** — built, wired into nothing. Highest-value cluster for the
"integrate the civilization" directive:
- **Civilization core:** `civilization`, `institutions`, `institution-work-assignment`,
  `coalition-formation`, `goal-hierarchy`, `goal-manager`, `autonomy-civilization-bridge`
- **Governance/constitution:** `governance-rbac`, `governance-reputation-integration`,
  `calibration-constitution`, `calibration-change-governance`, `protected-surface-enforcer`,
  `protected-surface-validator`, `invariant-validator`, `safety`, `rollback`, `provenance`
- **Trust:** `trust-scoring`, `trust-impact-assessment`, `trust-policy-canary`,
  `trustworthiness`, `reputation-scale`
- **Calibration/learning:** `phase0b-calibration`, `dynamic-calibration`,
  `calibration-drift-monitor`, `confidence`, `bayesian`, `claim-accuracy-tracker`,
  `autonomy-forecasting`, `bounded-learning-run`, `learning`, `reward-calculator`,
  `multi-agent-ensemble`, `knowledge-persistence`, `kb-expansion`
- **Infra/other:** `integration`, `orchestrator`, `perception`, `deadlock-detector`,
  `durable-execution`, `rate-limiter`, `input-validator`, `metrics`, `simulator`,
  `load-test-harness`

---

## Detector blind spots (stated honestly)

1. **Private-method circular tests are invisible to the scan.** `claim-grounding.test.ts` tests a
   *copy* of `validateClaimGrounding` pasted into the test file; it never imports the real
   (private) method in `action-executor.service.ts`. The scan keys on *exported* functions, so it
   did not flag this. **Known issue, must fix in Phase B:** the grounding test proves only that a
   copy matches itself.
2. **Singleton-export services** (`export const xService = new X()`) show "0 exported functions"
   — not hollow, just a different export shape. Not counted as stubs.
3. **Reachability ≠ correctness.** A service reachable from the orchestrator may still be a
   shallow/partial implementation. Reachability is necessary-not-sufficient for "integrated and real."
4. **Runtime-string / DI wiring** (services resolved by name at runtime rather than static import)
   is not captured. None observed so far, but the graph is import-static only.

---

## Known quality issues beyond reachability

- **`claim-grounding.test.ts` is circular** (blind-spot #1). Must be rewritten to import the real
  method with a mocked `db`, and must add the missing **snippet-substring grounding check**
  (accepted claims must carry `supportSnippets` that are verbatim substrings of the cited source).
- **`credential-canonical.test.ts`: 1 failing test** — a *pre-existing* (origin commit `4e62e1b`)
  security-model contradiction: should `valid` require inline Ed25519 verification, or only
  ledger-recompute correctness with the signature delegated for external verification? Needs a
  decision, not a silent flip.
- **`task-dispatch.test.ts` needs a live Postgres** (real queue, real SQL). Currently red without a
  DB; the implementation is real.

---

## Proposed Phase B hardening order (integration spine first)

Each step: de-stub/complete → real test (no copied logic) → wire into a runtime → commit green.

1. **Fix the grounding foundation** (closes the Step-1 hole the whole project rests on):
   real (non-circular) grounding test + snippet-substring check, exercised through the real
   executor path.
2. **The bridge:** make `autonomy-civilization-bridge` real and wire `civilization.service` into
   the orchestrator runtime — one civilization capability flowing end-to-end from the autonomy loop.
3. **Constitution actually enforces:** wire `protected-surface-enforcer` + `invariant-validator`
   + `safety` into the self-modification path so they gate at runtime (not just in a unit test).
4. **Institutions + goals:** `institutions`, `goal-hierarchy`, `coalition-formation`,
   `institution-work-assignment` integrated behind the bridge.
5. **Trust + reputation** cluster wired to decisions.
6. **Calibration governance** cluster wired to the model-decision/forecast path.
7. **HTTP surface:** expose the integrated civilization through `server.ts` so the deployable app
   reaches it (closes the 5/77 gap).

Artifacts: `audit_results.json`, `reach.py`, `audit.py` (in session scratchpad).
