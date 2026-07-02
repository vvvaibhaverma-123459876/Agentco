# Acceptance Trace — Proof-of-Calibration Credential

**Status:** PASS
**Run against:** REAL Postgres (`prediction_ledger`, `calibration_credentials`) — no mocks.
**Date captured:** 2026-07-02

## What is proven

| Test | Invariant |
|---|---|
| Deterministic scoring | Same ledger data → identical scores every time |
| Differential credentials | Different track records → different, independently verifiable credentials |
| Non-transferability | Tampered agent_id → HMAC verification fails |
| Fresh identity | Zero resolved predictions → neutral-low standing (no cells) |
| DB persistence | Credentials durably stored in `calibration_credentials` (append-only) |

## Captured trace (real run)

```
>>> test_1_deterministic_scoring: START
>>> test_1: registered+resolved 3 predictions for determinism-probe-agent
>>> test_1: score_a == score_b: overall_log=-0.328504 brier=0.078400 n=3
>>> test_1_deterministic_scoring: PASS
>>> test_2_two_agents: START
>>> test_2: agent_a log_score=-0.356675 brier=0.090000 n=3
>>> test_2: agent_b log_score=-2.302585 brier=0.810000 n=3
>>> test_2: cred_a.credential_id=0560b686 hmac=abc68b3c5006e52f... verified=True
>>> test_2: cred_b.credential_id=e2defde6 hmac=f137a9397439d72b... verified=True
>>> test_2: persisted cred_a → DB row confirmed agent_id=calibrated-agent-alpha
>>> test_2: persisted cred_b → DB row confirmed agent_id=overconfident-agent-beta
>>> test_2: tampered credential (wrong agent_id) correctly rejected by HMAC
>>> test_2_two_agents: PASS
>>> test_3_fresh_agent: START
>>> test_3: fresh agent credential: sample_count=0 cells=0 verified=True
>>> test_3_fresh_agent: PASS
ASSERTIONS PASSED: Proof-of-Calibration credential proven on real Postgres
```

## Scoring algorithm (published)

    hardness(p)   = 2 * p * (1 - p)              # ∈ [0, 0.5]
    weight(p, c)  = hardness(p) * (2 if c else 1) # consequence doubles credit
    log_score(p, o) = log(p) if o else log(1-p)   # clipped ε
    brier_score(p, o) = (p - o)²

    cell_log_score = Σ(weight × log_score) / Σweight

    Credential HMAC = HMAC-SHA256(canonical_json, RESERVE_SIGNING_KEY)

## How to reproduce

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  python3 -m pytest reserve/tests/test_proof_of_calibration.py -v -s
```
