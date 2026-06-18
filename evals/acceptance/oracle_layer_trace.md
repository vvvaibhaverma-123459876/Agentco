# Acceptance Trace — Recursive Resolution Layer (Phase 3)

**Status:** PASS
**Run against:** REAL Postgres (`oracle_resolutions`, `oracle_standing_history`) — no mocks.
**Date captured:** 2026-06-18

## Self-Correction Invariant

An oracle whose resolution is contradicted by a stronger downstream source
(higher credential weight, or mechanical external ground truth) loses standing
proportional to the authority gap. Oracle activity cannot improve standing —
only correct uncontradicted resolutions preserve it.

## Recursive Property

Resolutions are themselves falsifiable. Round 0 = first resolution.
Round N+1 contradicts round N. Chain terminates at mechanical/external
ground truth (source_type='mechanical'), which cannot be contradicted.
This is the bedrock.

## What is proven

| Test | Invariant |
|---|---|
| Oracle resolution | Authority recorded; standing history appended |
| Oracle contradiction | Higher-authority oracle contradicts lower; loser is docked |
| Mechanical contradiction | External ground truth overrides oracle; mechanical is bedrock |
| Threshold enforcement | Below-threshold agent cannot act as oracle |

## Captured trace (real run)

```
>>> test_1_oracle_resolution: START
>>> test_1: resolution_id=f054f53f authority=0.2005 standing_resolutions=1
>>> test_1_oracle_resolution: PASS
>>> test_2_oracle_contradiction: START
>>> test_2: oracle_a resolved TRUE with authority=0.1703
>>> test_2: oracle_b contradicted with FALSE, authority=0.2408 round=1
>>> test_2: oracle_a standing docked by 0.1204 contradiction_count=1
>>> test_2_oracle_contradiction: PASS
>>> test_3_mechanical_contradiction: START
>>> test_3: oracle resolved TRUE authority=0.2005
>>> test_3: mechanical contradicted FALSE authority=1.0000 round=1
>>> test_3: standing docked contradiction_count=1
>>> test_3: cannot contradict mechanical ground truth — correctly rejected
>>> test_3_mechanical_contradiction: PASS
>>> test_4_unqualified: START
>>> test_4: unqualified agent correctly rejected
>>> test_4_unqualified: PASS
ASSERTIONS PASSED: Recursive Resolution Layer proven on real Postgres
```

## How to reproduce

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest reserve/tests/test_oracle_layer.py -v -s
```
