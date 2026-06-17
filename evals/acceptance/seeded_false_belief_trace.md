# Acceptance Trace — Seeded False Belief Cannot Reach `reality_validated`

**Status:** PASS
**Run against:** REAL Postgres (`prediction_ledger`, port 5433) — DB-backed calibration engine, no mocks.
**Date captured:** 2026-06-17

This is the §7 acceptance test the system must always satisfy: a deliberately
seeded **false** belief, even after heavy simulation support and high-confidence
predictions, must **never** be promoted to `reality_validated`. Reality is the
only thing that promotes a belief — and reality (external resolution) here says
the belief is false.

## What is exercised

| Layer | Real dependency |
|---|---|
| Prediction Ledger | REAL Postgres `prediction_ledger` (rows verified by direct SELECT) |
| Resolution Service | resolves predictions against external ground-truth source |
| Surprise Register | fires on the gap between stated confidence and false outcome |
| Reality/Simulation Firewall | promotion gate — the component under test |

## Scenario

1. Inject a false belief: *"Our market share is growing by 30% MoM."*
2. Add **20 simulation supports** (the belief reaches `simulation_supported`).
3. Pre-register **3 high-confidence (p=0.88) predictions** asserting the belief,
   into the **real** `prediction_ledger`.
4. Resolve all 3 **FALSE** against `external_market_research` (real ground truth).
5. Observe the **Surprise Register** fire.
6. Call the **promotion gate** — it must return `False`, and the belief must
   stay out of `reality_validated`.

## Captured trace (real run)

```
>>> 1_inject_false_belief: belief_id=7308fd6a... status=provisional
>>> 2_simulation_supported: status=simulation_supported after 20 sim supports
>>> 3_predictions_registered: real pids=['252f968a', '90e1a887', 'e0e2d459']
>>> 3b_verify_in_real_postgres: 3/3 rows confirmed durable in prediction_ledger
>>> 4_resolved_false: all 3 resolved outcome=False
>>> 5_surprise_fired: 3 surprise events for the seeded predictions
>>> 6_promotion_gate: promote_to_reality_validated -> False
>>> 7_final_status: belief status=simulation_supported
ASSERTIONS PASSED: false belief BLOCKED from reality_validated
```

## Invariant proven

- **A belief is never promoted to `reality_validated` on the strength of
  simulation support + confident predictions alone.** When external reality
  resolves the predictions FALSE, the promotion gate returns `False` and the
  belief remains at `simulation_supported` — it does **not** advance.
- The predictions were durably written to and read back from **real Postgres**
  (`3b_verify_in_real_postgres: 3/3 rows confirmed`), so the ledger leg is proven
  against the real store, not an in-memory stand-in.

## How to reproduce

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest \
  "evals/regression/test_v2_regression.py::TestSeededFalseBeliefRegression::test_seeded_false_belief_cannot_reach_reality_validated" -v
```

The DB-backed full trace above is reproduced by running the same scenario with
`create_calibration_engine(db=<psycopg2 conn>)` so every prediction is persisted
to and verified in the real `prediction_ledger` table.
