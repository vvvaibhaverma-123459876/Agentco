# Phase 2 Regression Verdicts

## R1 — `test_resolution_write_once`

### TEST INTENT

Invariant: the prediction ledger is immutable after registration, and resolution
columns are write-once. The test asserts:

```python
with pytest.raises(Exception, match="already resolved"):
    cal["resolution"].resolve(pid, outcome=False, ground_truth_source="external_auditor", evidence="test2")
```

Cross-references:

- `BUILD_LEDGER.yaml`, item `L5.PredictionLedger`: resolution writes require the
  `resolution_service` DB role and write "write-once outcome" records.
- `backend/src/db/migrations/011_prediction_ledger.sql`: comments state that
  resolution columns are write-once, and the trigger raises
  `WRITE-ONCE VIOLATION` when `OLD.resolved` is true.
- `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`:
  preserves the write-once trigger while adding registration-boundary checks.
- `calibration/resolution/resolution_service.py`: `_validate_resolution()` raises
  `WRITE-ONCE VIOLATION` if `record.resolved` is already true.

### CURRENT BEHAVIOR

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q --tb=short \
  evals/regression/test_v2_regression.py::TestInvariant1_ImmutableLedger::test_resolution_write_once
```

Actual result:

```text
E   ValueError: resolution_date must be in the future for pre-registration
```

The test never reaches its write-once assertion. It fails during
`ledger.pre_register(reg)` because the fixture sets:

```python
resolution_date=datetime.now(timezone.utc) - timedelta(hours=1)
```

A manual probe using the intended historical-registration fixture path under a
pytest context shows that current app-layer write-once behavior still rejects a
second resolution:

```text
first resolved
ValueError WRITE-ONCE VIOLATION: prediction ... is already resolved
```

### GIT ARCHAEOLOGY

- Test introduced: `3753da9aee1e5679ed39dcb04d7a03bb24250985`
  (`feat(v2): Add Phase 5 — Governor Dashboard, regression suite, governance docs`).
  This commit added `test_resolution_write_once` with a backdated
  `resolution_date`.
- Registration invariant changed intentionally:
  `4968b7448df7f56c096d69421ea0e8496090e605`
  (`G: harden integrated calibration system`). This commit changed
  `PredictionLedger._validate_registration()` from logging a warning on
  backdated registrations to raising
  `ValueError("resolution_date must be in the future for pre-registration")`
  unless `historical_registration_reason` is provided. It also added
  `created_at` / `historical_registration_reason` fields and migration
  `120_prediction_ledger_registration_invariants.sql`, whose header says it
  closes the database insert-boundary calibration hole by requiring
  `resolution_date > created_at`.

### VERDICT

TEST-WRONG.

The write-once invariant remains documented and enforced in app code, and DB
trigger definitions still contain the `OLD.resolved` write-once rejection. The
regression is the test fixture: it relies on a backdated registration style that
was intentionally invalidated by commit `4968b74`. The legitimate replacement
for tests that need a past due prediction is the explicit
`historical_registration_reason` path added in that same commit.

### FIX

Update the test fixture to create a historical registration explicitly, using
`historical_registration_reason`. Do not weaken the write-once assertion.

## R2 — `test_internal_resolution_source_rejected`

### TEST INTENT

Invariant: resolution ground truth must originate outside the reasoning system.
The test asserts:

```python
with pytest.raises(ValueError):
    cal["resolution"].resolve(pid, True, ground_truth_source="self", evidence="test")
```

Cross-references:

- `calibration/ledger/prediction_ledger.py`: `ground_truth_source` is documented
  as "MUST be external to the reasoning system".
- `calibration/resolution/resolution_service.py`: `_validate_resolution()` raises
  `DISQUALIFIED SOURCE` for internal source tokens.
- `backend/src/db/migrations/011_prediction_ledger.sql`: table constraint
  `prediction_ledger_ground_truth_external` rejects internal registration
  sources.
- `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql`:
  explicitly says it prevents "disqualified internal source tokens" from being
  registered as ground truth.
- `BUILD_LEDGER.yaml`, item `L5.SourceIndependenceGate`: source independence
  rejects same-source, derivative, fixture, simulated, and contradictory
  evidence before promotion/resolution.

### CURRENT BEHAVIOR

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q --tb=short \
  evals/regression/test_v2_regression.py::TestInvariant10_GroundTruthExternal::test_internal_resolution_source_rejected
```

Actual result:

```text
E   ValueError: resolution_date must be in the future for pre-registration
```

The test never reaches the resolution-source assertion. It fails because its
registration fixture uses a past `resolution_date` without the historical
registration escape hatch.

A manual probe with `historical_registration_reason` under a pytest context
reaches the intended behavior:

```text
registered
ValueError DISQUALIFIED SOURCE: 'self' is internal. Ground truth must originate outside the reasoning system.
```

### GIT ARCHAEOLOGY

- Test introduced: `3753da9aee1e5679ed39dcb04d7a03bb24250985`
  (`feat(v2): Add Phase 5 — Governor Dashboard, regression suite, governance docs`).
  This commit added `test_internal_resolution_source_rejected` with
  `resolution_date=datetime.now(timezone.utc) - timedelta(hours=1)`.
- Source validation existed from `0e14f1e71c049809a2ee06e1993a77a8ecb794c9`
  (`feat(v2): Add Layer 0 — Calibration Engine`), which introduced
  `_validate_resolution()` with internal source rejection.
- Source-token validation and the registration-boundary change were intentionally
  hardened in `4968b7448df7f56c096d69421ea0e8496090e605`
  (`G: harden integrated calibration system`). That commit changed substring
  source checks to token checks, added sandbox/internal source handling, and
  added `historical_registration_reason` plus the strict
  `resolution_date must be in the future for pre-registration` check.

### VERDICT

TEST-WRONG.

The external-ground-truth invariant remains intended and enforced in
`ResolutionService._validate_resolution()`. The failing test is still built for
the pre-`4968b74` world where backdated registration was allowed. The code
change was intentional and documented by migration
`120_prediction_ledger_registration_invariants.sql`; the test should use the
historical-registration fixture path to reach the invariant it means to assert.

### FIX

Update the R2 fixture to include `historical_registration_reason`. Do not weaken
the assertion that internal resolution sources are rejected.

## R3 — `test_seeded_false_belief_cannot_reach_reality_validated`

### TEST INTENT

Invariant: a simulation-seeded false belief must never attain
`reality_validated`. The test asserts:

```python
result = firewall.promote_to_reality_validated(false_belief.belief_id, records)
assert result is False
assert firewall._beliefs[false_belief.belief_id].validation_status != "reality_validated"
```

Cross-references:

- `calibration/firewall/firewall.py`: "ONLY REALITY PROMOTES"; simulation support
  is explicitly ignored by `promote_to_reality_validated()`.
- `backend/src/db/migrations/010_beliefs.sql`: raw updates to
  `reality_validated` are blocked unless executed as `resolution_service`; the
  migration says simulation volume never crosses to `reality_validated`.
- `evals/acceptance/seeded_false_belief_trace.md`: names this as the §7
  acceptance test and records a passing real-Postgres trace.
- `evals/audit/audit_report_2026-06-16.md`: lists "Only reality promotes" and
  "Firewall hard gate; sim_support_count excluded" as passed invariants.

### CURRENT BEHAVIOR

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q --tb=short \
  evals/regression/test_v2_regression.py::TestSeededFalseBeliefRegression::test_seeded_false_belief_cannot_reach_reality_validated
```

Actual result:

```text
E   ValueError: resolution_date must be in the future for pre-registration
```

The test fails while registering the first backdated prediction. It does not
reach the firewall promotion path.

A manual probe using `historical_registration_reason` under a pytest context
traced the full intended path:

```text
after sim simulation_supported
surprises True
outcomes [False, False, False] posthoc [False, False, False]
promoted False
final simulation_supported
```

Gate trace:

1. `add_simulation_support()` advances the belief only to
   `simulation_supported`.
2. Three high-confidence predictions are registered through the explicit
   historical fixture path, with `post_hoc=False`.
3. `ResolutionService.resolve()` resolves all three `False` against
   `external_market_research`; the surprise register fires.
4. `RealitySimulationFirewall.promote_to_reality_validated()` reaches Gate 2
   and rejects because all three `resolved_outcome` values are false.
5. Final belief status remains `simulation_supported`.

### GIT ARCHAEOLOGY

- Firewall introduced: `0e14f1e71c049809a2ee06e1993a77a8ecb794c9`
  (`feat(v2): Add Layer 0 — Calibration Engine`). The commit message says the
  seeded-false-belief acceptance test passed, and that the firewall has a
  four-gate promotion path with `sim_support_count` intentionally ignored.
- Test introduced: `3753da9aee1e5679ed39dcb04d7a03bb24250985`
  (`feat(v2): Add Phase 5 — Governor Dashboard, regression suite, governance docs`).
  This commit added the R3 regression test using
  `past = datetime.now(timezone.utc) - timedelta(hours=1)` for its prediction
  registrations.
- Registration invariant changed intentionally:
  `4968b7448df7f56c096d69421ea0e8496090e605`
  (`G: harden integrated calibration system`). This commit added
  `historical_registration_reason` and migration
  `120_prediction_ledger_registration_invariants.sql`, closing the database
  insert-boundary hole by requiring `resolution_date > created_at`.

### VERDICT

TEST-WRONG.

The firewall invariant is still intended and the code blocks the seeded false
belief once the test reaches the promotion gate. The failure is in the test
fixture: it uses the old backdated-registration pattern invalidated by
`4968b74`. The legitimate fixture path is the explicit historical-registration
field added by the same commit.

Because the verdict is TEST-WRONG, the R3-specific requirement to add a second
adversarial route test is not triggered; that requirement applies when the
promotion gate itself is CODE-WRONG.

### FIX

Update the three seeded-false-belief prediction fixtures to include
`historical_registration_reason`. Do not weaken the assertion that promotion
returns `False` and the belief remains out of `reality_validated`.

## R4-R6 — `test_audit_findings.py` trust regression tests

### TEST INTENT

R4 invariant: trust sample accounting must use the actual resolved prediction
count for an agent/domain track record. The test asserts:

```python
count = cal["trust"].get_sample_count("agent-x", "sales", "general", "short")
assert count == 3
```

R5 invariant: an agent with calibration history must not crash when executing a
low-risk action and must weight decisions through trusted confidence. The test
asserts:

```python
result = agent.execute_action(action)
assert result["trusted_confidence"] <= result["stated_confidence"]
```

R6 invariant: a real trust downgrade must notify registered downstream
consumers. The test asserts:

```python
assert notified, "downgrade callback never fired (propagation was dead code)"
assert notified[0][0] == "agent-drop"
assert notified[0][1] < 1.0
```

Cross-references:

- `evals/audit/audit_report_2026-06-16.md`: HIGH-1 documents the
  `sample_count`/`n_resolved` crash; HIGH-3 documents the dead downgrade
  propagation callback.
- `calibration/trust/trust_controller.py`: the module docstring says decisions
  must call `trusted_confidence()` and that downgrade propagation must notify
  all downstream consumers.
- `runtime/base_agent/base_agent_v2.py`: `execute_action()` is the decision path
  that consumes `trusted_confidence()`.
- `BUILD_LEDGER.yaml`: L6 describes sample-size conservative trust scoring and
  resolved prediction outcomes feeding trust state.

### CURRENT BEHAVIOR

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q --tb=short \
  evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_get_sample_count_with_track_record \
  evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_execute_action_does_not_crash_for_agent_with_history \
  evals/regression/test_audit_findings.py::TestHigh3DowngradePropagation::test_downgrade_propagates_to_consumers
```

Actual result:

```text
E   ValueError: resolution_date must be in the future for pre-registration
```

All three fail in the shared `_resolve_n()` fixture before reaching trust
sample-count, action execution, or downgrade propagation assertions.

A manual probe using the same helper shape, but adding
`historical_registration_reason` under a pytest context, reached the intended
trust paths:

```text
count 3
execute keys 0.7 0.7 None
notified [('agent-drop', 0.3)]
```

### GIT ARCHAEOLOGY

- Trust fixes and regression tests introduced:
  `12a0fa446aa439bfd8dc2b92a6a57967bd3da8b3`
  (`audit: fix HIGH/MEDIUM/LOW findings from adversarial invariant audit`).
  The commit message explicitly states:
  - HIGH-1 renamed `TrustScore.sample_count` to `n_resolved` and fixed
    `get_sample_count()` plus the decision hot path.
  - HIGH-3 moved `was = score.trusted_multiplier` before
    `_recompute_multiplier(score)` so real drops propagate.
  - `evals/regression/test_audit_findings.py` was added to encode those audit
    findings as regression tests.
- Registration invariant changed intentionally:
  `4968b7448df7f56c096d69421ea0e8496090e605`
  (`G: harden integrated calibration system`). This commit added
  `historical_registration_reason` and made backdated registration invalid
  unless the explicit historical-fixture path is used.

### VERDICT

TEST-WRONG.

The intended HIGH-1 and HIGH-3 trust fixes are still present in current code:
`TrustScore` has `n_resolved`, `get_sample_count()` returns it, `ingest_resolution()`
captures the old multiplier before recompute, and `_propagate_downgrade()` is
called when the multiplier drops. The three tests fail only because their shared
fixture still uses the old backdated-registration pattern invalidated by
`4968b74`.

### FIX

Update the shared `_resolve_n()` fixture to include
`historical_registration_reason`. Do not alter the sample-count, execute-action,
or downgrade-propagation assertions.
