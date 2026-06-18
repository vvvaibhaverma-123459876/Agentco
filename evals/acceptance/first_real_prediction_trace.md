# First Real Prediction Trace

**Generated:** 2026-06-18T14:02:08.793950+00:00

---

## 1. Prediction Registration

| Field | Value |
|---|---|
| `prediction_id` | `e8a8c2c6-dd57-4ab8-b097-6e7d02941e1a` |
| `agent` | `ceo-agent` |
| `domain` | `system_reliability` |
| `claim_type` | `guardrail_behaviour` |
| `horizon_class` | `short` |
| `stated_confidence` | `0.85` |
| `registered_at` | `2026-06-18T14:02:05.683568+00:00` |
| `resolution_date` | `2026-06-18T14:02:08.682747+00:00` |
| `post_hoc` | `False` |
| `ground_truth_source` | `pytest_spend_cap_test_runner` |

**Claim:**
> The AgentCo spend guardrail will correctly halt new LLM calls when the token cap is exceeded in a real autonomous run.

**Resolution criterion:**
> A real test sets cap to 10 tokens, records 50 tokens of usage, then calls check_before_call() — must raise SpendCapExceeded (REFUSED). Throttle or delay does NOT count.

---

## 2. Real Test Execution

```
SpendGuardrail(max_tokens=10, agent_id="ceo-agent-test-run")

  Call 1: check_before_call()      → ALLOWED (tokens_used=0 < cap=10)
           record_usage(50)         → tokens_used = 50

  Call 2: check_before_call()      → REFUSED — SpendCapExceeded raised
```

**Refusal message:**
```
agent 'ceo-agent-test-run' has used 50 tokens (cap=10). Halting further LLM calls.
```

| Assertion | Result |
|---|---|
| Cap exceeded after first call | `True` (50 ≥ 10) |
| Second call raised SpendCapExceeded | `True` |
| Guardrail mode | REFUSED (not throttled, not delayed) |

**Outcome: TRUE**

---

## 3. Scoring

| Metric | Value | Formula |
|---|---|---|
| Stated probability | `0.85` | |
| Actual outcome | `TRUE` | |
| Log score | `-0.1625` | log(0.85) = -0.1625 |
| Brier score | `0.0225` | `(0.85 − 1)²` |
| Was surprise | `False` | |
| Resolved at | `2026-06-18T14:02:08.784815+00:00` | |
| Resolved by | `resolution_service_v1` | |

---

## 4. Trust Controller Update (ceo-agent / system_reliability)

| | Value |
|---|---|
| `trusted_confidence` before | `0.6800` |
| `trusted_confidence` after | `0.7140` |
| Δ | `+0.0340` |

Note: With n=1 resolved prediction (< MIN_SAMPLES_FOR_TRUST=5),
the trust controller applies a conservative 80% + 4%×n penalty on stated confidence.
As the track record grows, this penalty shrinks and the reliability curve takes over.

---

## 5. Audit Log

| Field | Value |
|---|---|
| `audit_log entry id` | `fcc25855-ec64-44e1-b394-9100678ccaa6` |
| `auditor` | `claude-code-orchestrator` |
| `passed` | `True` |

---

## What This Demonstrates

The AgentCo calibration loop completed its **first real end-to-end cycle**:

1. **Pre-registered** — prediction logged in the immutable ledger (PostgreSQL) before the test ran
2. **Reality ran** — real `SpendGuardrail` code with `max_tokens=10`; real `SpendCapExceeded` raised on second call
3. **Reality ruled** — outcome `TRUE` recorded by `ResolutionService` (not by the predicting agent)
4. **Score applied** — log score `-0.1625`, brier score `0.0225` computed from stated p=0.85
5. **Trust updated** — `ceo-agent`'s trusted_confidence in `system_reliability` is now `0.7140`
6. **Audit recorded** — entry `fcc25855-ec64-44e1-b394-9100678ccaa6` in the spot-audit log

The system predicted before knowing, let reality rule, and updated trust based on evidence.
