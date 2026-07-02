# Current Runtime — Canonical Architecture

This document states, without ambiguity, which parts of the repository are the
real runtime and how to verify them reproducibly. If any other document
conflicts with this one or with `BUILD_LEDGER.yaml`, this one and the ledger win.

## Canonical runtime: TypeScript + Postgres (`backend/`)

The real, tested runtime is the Fastify/Postgres backend under `backend/`:

- Postgres schema and migrations: `backend/src/db/migrations/` (run with
  `npm run db:migrate`).
- Services: `backend/src/services/` — evidence registry, claim grounding,
  prediction ledger + resolution firewall, calibration/trust scoring, memory
  promotion/retrieval, the autonomy planner/orchestrator, judiciary,
  domain registry, institutions, and (added in this work) the closed
  self-improvement loop, calibration-aware routing, longitudinal learning
  harness, civilization live flow, goal formation, and supervised free-run.
- API: `backend/src/server.ts` (write-path API key + governance RBAC).

Verify everything clean-room (no LLM/web keys required):

```bash
make verify-clean-room
```

## Closed loops now implemented (previously open)

| Loop | Entry | Persistence | Reaches planner? | Test |
|---|---|---|---|---|
| Promoted skill → planner use | `skill-retrieval.service.ts` | `skill_usage_events` | yes | `skill-consumption-e2e.test.ts` |
| Candidate → eval → canary → promote/rollback | `candidate-evaluation`, `skill-canary`, `skill-deployment` | `candidate_evaluations`, `skill_canary_runs` | yes | `self-improvement-closed-loop-e2e.test.ts` |
| Longitudinal improvement across runs | `longitudinal-learning-harness.service.ts` | `longitudinal_learning_cycles` | yes | `longitudinal-learning-harness.test.ts` |
| Calibration → planner routing/authority | `calibration-aware-routing.service.ts` | `trust_scores`, `event_log` | yes | `calibration-driven-planning.test.ts` |
| Institution acts on live events | `civilization-live-flow.service.ts` | `institution_work_requests`, `event_log` | yes | `civilization-live-flow-e2e.test.ts` |
| Self-generated goals + bounded free-run | `goal-formation`, `supervised-free-run` | `autonomy_goals`, `goal_evidence`, `event_log` | yes | `goal-formation-supervised-free-run.test.ts` |

## Python modules: tooling / research / deprecated

The Python trees (`agents/`, `autonomy/`, `calibration/`, `learning/`,
`synthesis/`, `reserve/`, `runtime/`, …) are **not** the canonical product
runtime. They fall into three buckets:

- **Tooling used by Make/tests** — e.g. `runtime/orchestration/doctor.py`,
  `scripts/build_ledger.py`, the Reserve/calibration Python suites invoked by
  `make smoke-python`. These are real and maintained as tooling.
- **Research / parallel implementations** — Python versions of concepts that
  the backend implements canonically (agent abstractions, calibration scoring).
  Kept for research; not the deployed path. Do not extend these to add product
  behavior; add it in `backend/` instead.
- **Deprecated** — anything under `docs/history/` and `archive/`.

Live-LLM Python tests are opt-in (`RUN_REAL_LLM_TESTS=1`); they skip cleanly
without credentials (see `conftest.py`).

## Where truth lives

- `BUILD_LEDGER.yaml` (`python3.13 scripts/build_ledger.py status`)
- `docs/CURRENT_IMPLEMENTATION_REALITY.md`
- `docs/DB_TABLE_USAGE.md`
- `reports/system_run/latest/score_validation.json` (from
  `npm run agentco:score-validation`)
- `docs/history/` — historical only; never current truth.
