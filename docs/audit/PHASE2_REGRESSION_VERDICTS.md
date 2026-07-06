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
