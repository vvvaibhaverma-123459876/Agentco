# Acceptance Trace — Staking + Weighted Decision (Phase 2)

**Status:** PASS
**Run against:** REAL Postgres (`belief_questions`, `belief_stakes`, `calibration_credentials`) — no mocks.
**Date captured:** 2026-06-20

## Collusion-Resistance Property: Reality-Contact Weight Bound (RCWB)

**Statement:** The total voting weight a coalition of k agents can contribute is bounded by
Σᵢ max(0, cell_log_score_i(domain, horizon)), where each term is derived from
independently verified, externally-resolved predictions. Creating Sybil identities
adds weight ≈ 0 per identity (no resolved predictions → cell score = 0 → weight = 0).

**Structural proof:** see `reserve/staking/staking.py` module docstring.

## What is proven

| Test | Invariant |
|---|---|
| Weighted majority | Higher-credential agent wins even if headcount minority |
| Sybil resistance | 10 zero-weight agents cannot override 1 credentialed agent |
| Write-once stakes | Duplicate stake rejected by DB unique constraint |
| RCWB audit values | `weight_concentration` + `sybil_filtered_count` in every decision |

## Captured trace (real run)

```
>>> test_1_weighted_decision: START
>>> test_1: question registered: fa7585f3
>>> test_1: weight_for_true=0.0000 weight_for_false=0.2005 outcome=False
>>> test_1_weighted_decision: PASS
>>> test_2_sybil_resistance: START
>>> test_2: question registered: bf78b7dc, real_weight=0.1703
>>> test_2: stake_count=11 effective=1 sybil_filtered=10 outcome=False
>>> test_2: RCWB proven — 10 Sybil votes (weight=0) overridden by 1 credentialed vote
>>> test_2_sybil_resistance: PASS
>>> test_3_write_once: START
>>> test_3: duplicate stake correctly rejected by DB unique constraint
>>> test_3_write_once: PASS
>>> test_4_rcwb_audit: START
>>> test_4: weight_concentration=0.8315 max_single_weight=0.2408 total_weight=0.2896
>>> test_4: RCWB audit fields present and correct
>>> test_4_rcwb_audit: PASS
ASSERTIONS PASSED: Staking + Weighted Decision proven on real Postgres
```

## How to reproduce

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest reserve/tests/test_staking_and_decisions.py -v -s
```
