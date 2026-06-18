# Phase A — Independent Recomputation Acceptance Trace

**Date:** 2026-06-17  
**Claim proven:** Any third party can reproduce a stored credential's score from raw
public `prediction_ledger` rows using only the published deterministic algorithm.
No access to the signing key, no reuse of any in-memory object, is required.

---

## What was proven

Two independent code paths converge on identical numbers:

| Path | Input | Output |
|------|-------|--------|
| **Path 1 (normal issuance)** | In-memory `PredictionRecord` objects → `score_agent()` → `issue_credential()` | Stored credential with `overall_log_score` |
| **Path 2 (recomputation)** | Raw psycopg2 cursor rows from `prediction_ledger` → `recompute()` in `reserve/tools/recompute_credential.py` | Recomputed score dict |

Path 2 has **zero dependency** on `RESERVE_SIGNING_KEY`, any private state, or any Python
object from Path 1. It is what an independent third party would run.

---

## Raw ledger rows consumed (test run)

Agent: `recomputation-proof-agent`  
Eligible predictions: 5 (resolved=TRUE, post_hoc=FALSE, outcome=TRUE, p=0.75, domain=testing, horizon=short)

```
prediction_id | probability | resolved_outcome | domain  | horizon_class | consequence | hardness
--------------+-------------+------------------+---------+---------------+-------------+---------
<uuid-1>      | 0.75        | TRUE             | testing | short         | FALSE       | 0.3750
<uuid-2>      | 0.75        | TRUE             | testing | short         | FALSE       | 0.3750
<uuid-3>      | 0.75        | TRUE             | testing | short         | FALSE       | 0.3750
<uuid-4>      | 0.75        | TRUE             | testing | short         | FALSE       | 0.3750
<uuid-5>      | 0.75        | TRUE             | testing | short         | FALSE       | 0.3750
```

---

## Score comparison

```
Field                     Stored credential    Recomputed (Path 2)    Delta
------------------------  -------------------  ---------------------  ----------
overall_log_score         -0.28768207          -0.28768207            < 1e-8  ✓
overall_brier_score        0.06250000           0.06250000            < 1e-8  ✓
sample_count               5                    5                     exact   ✓
algorithm                  log_score+brier/...  log_score+brier/...   exact   ✓
cell (testing, short) log  -0.287682            -0.287682             < 1e-8  ✓
cell (testing, short) brr   0.062500             0.062500             < 1e-8  ✓
```

**MATCH: confirmed** — delta < 1e-8 on all numeric fields.

---

## Reference recomputer output (demo-agent, no secret)

```
$ python3 reserve/tools/recompute_credential.py demo-agent
{
  "agent_id": "demo-agent",
  "recomputed_at": "2026-06-17T23:58:59.696381+00:00",
  "source": "public prediction_ledger rows — no secret required",
  "score": {
    "algorithm": "log_score+brier/hardness_weighted/v1",
    "cells": [
      {
        "domain": "demo",
        "horizon_class": "short",
        "weighted_log_score": -0.2876820724517809,
        "weighted_brier_score": 0.0625,
        "sharpness": 0.1875,
        "sample_count": 5,
        "total_weight": 1.875
      }
    ],
    "overall_log_score": -0.2876820724517809,
    "overall_brier_score": 0.0625,
    "total_sample_count": 5
  }
}
```

No secret key was provided. No private state was accessed. Output is identical to
the credential embedded in the stored row.

---

## Test file

`reserve/tests/test_independent_recomputation.py::test_stored_credential_score_matches_independent_recomputation`

Pass confirmed on real Postgres (port 5433, agentco DB).

---

## What this does NOT prove yet

- The stored credential is cryptographically tied to its data in a way verifiable
  without the operator's secret. That is Phase B (asymmetric signing).
- The underlying resolved-prediction log is tamper-evident to a third party.
  That is Phase C (hash chain commitment).
