# Deep Audit: AgentCo Capabilities vs Actual Reality

**Date:** 2026-07-05  
**Branch:** `audit/capabilities-vs-reality`  
**Method:** Drill down from public claims to executable entrypoints. I read the current
status docs and build ledger, ran the release/doctor/mission gates, ran the backend build
and all backend Jest tests with local-network elevation, ran representative Python suites,
inspected the live Postgres schema, and executed direct adversarial probes against the
selfcoding sandbox. This is an audit-only report; no fixes were applied.

---

## Executive Verdict

AgentCo is not a fake repo, but it is also not the fully integrated "AI civilization"
implied by the strongest historical language. The current README is mostly honest about
the outer mission: long-horizon generality, repeated real-world autonomous improvement,
broad open-domain transfer, and hosted production operations remain unproven. The
strongest current reality is narrower:

- The TypeScript backend builds.
- Many DB-backed services are real and pass focused tests when local Postgres is reachable.
- Calibration/prediction-ledger hardening is substantially real, including real Postgres
  trigger tests.
- Runtime mode/feature-gate/doctor plumbing exists and labels fallbacks instead of hiding
  them.
- V2 agent escalation blocks in-process.
- Release-gate reachability is a partial route/slice check, not a full-system guarantee.

But the system currently has four hard breaks that prevent "complete integrated
capability" claims:

1. **Selfcoding sandbox is broken as a security boundary.** The release gate says
   `sandbox_breach: green`, but generated code can access the sealed resolver object via
   `score_prediction.__self__` and execute shell commands through
   `score_prediction.__globals__['os'].system(...)`.
2. **Backend all-test suite is not green.** With local DB/network permissions enabled,
   `npm run test:all -- --forceExit` produced **78 passed, 16 failed, 3 skipped** test
   suites (**394 passed, 46 failed, 8 skipped, 5 todo** tests). The failures cluster
   around schema drift in learning/self-improvement/proof paths.
3. **Migration verification is incomplete.** The live DB records migrations
   `061_add_goal_depth_column.sql` and `068_learner_schema_compatibility.sql` as applied,
   but columns required by active tests/services are missing:
   `learner_candidates.risk_level` and `autonomy_goals.depth`.
4. **Mission/production gates are blocked right now.** `make mission-progress` reports
   `mission_fully_proven=false` and marks the evidence-governed civilization claim
   `blocked`; `make production-posture` exits nonzero with `blocked_count=15`.

Bottom line: AgentCo is a serious local research/runtime system with several real
subsystems, not a production-certified autonomous civilization. The most honest capability
label is: **local-native, partially integrated, evidence-governed runtime with real
calibration and many real DB-backed slices, currently blocked by schema drift, broken
selfcoding confinement, stale verifier coverage, and non-portable test defaults.**

---

## 1. Top-Level Claims vs Reality

### Claim: "Evidence-governed, calibration-driven AI civilization"

**Reality: PARTIAL.** The core pattern exists in narrow slices: evidence registration,
claim grounding, prediction registration, authorized resolution, trust scoring, memory
promotion, event/audit records. Focused calibration and civilization tests pass. However,
the current full backend suite fails in learning/self-improvement/proof paths, and
`make mission-progress` now marks `evidence_governed_calibration_civilization` as
`blocked`.

### Claim: "Build ledger 68/71 verified"

**Reality: TRUE AS A LEDGER COUNT, BUT NOT ENOUGH.** `python3.13 scripts/build_ledger.py
status` reports `items: 68/71 verified (95.77%)`. The remaining items are the right ones:
long-horizon generality, durable real-world self-improvement, and hosted production
operations. However, the ledger/gate state is stale in places:

- `BUILD_LEDGER.yaml` says `no_stub: green`.
- A fresh `scripts/build_ledger.py report` reports `no_stub: red` with two scanner hits.
- Those hits appear to be false positives on the word "later", but the mismatch proves
  status-report drift.

### Claim: "Release gates passed"

**Reality: MIXED.** `make release-gates` exits 0 and reports:

- `credential_key_independence: green`
- `firewall: green`
- `reachability: green`
- `sandbox_breach: green`

But `sandbox_breach` is a false green. The gate only checks that
`python selfcoding/tests/test_wall_holds.py` exits 0. That script's adversarial cases are
too weak and miss actual Python object graph escapes.

### Claim: "Local backend runnable"

**Reality: BUILD YES, FULL TEST NO.** `npm run build` in `backend/` passes. With local
network/database elevation, all-Jest fails: **16 failed suites, 46 failed tests**. Most
failures are not random network errors after elevation; they are missing-column failures in
current runtime schema.

### Claim: "Production posture passes"

**Reality: FALSE RIGHT NOW.** `make production-posture` exits 2:

```text
{"report": "reports/system_run/latest/production_posture_verification.json", "can_continue": false, "blocked_count": 15}
```

That is consistent with the README's caveat that hosted production is not certified, but
inconsistent with any wording that implies current production posture is green at runtime.

---

## 2. What Actually Works

### 2.1 TypeScript Build

Command:

```bash
cd backend
npm run build
```

Result: **PASS**. `tsc` completed successfully.

### 2.2 Calibration Ledger and Real Postgres Trigger Layer

Previously verified in this workstream and rechecked in targeted runs:

- In-memory calibration ledger tests: **30 passed**.
- Real Postgres prediction-ledger immutability/persistence tests: **8 passed**.
- App-layer fixes for backdated registration, source matching, `earliest_knowable_at`,
  ECE top-bin inclusion, and trust arithmetic are real in the current codebase.

Verdict: **one of the strongest subsystems.** It is not perfect across every product path,
but the ledger invariants and trigger tests are substantially real.

### 2.3 V2 Escalation Gate

`runtime/escalation/escalation_gate.py` raises `HumanApprovalRequired` for high/critical
risk or trusted confidence below threshold. `BaseAgentV2.execute_action()` catches that,
writes an in-memory audit entry, and re-raises.

Direct test evidence: high/critical V2 actions block. Also, a low-risk action with stated
confidence 0.70 and no track record now blocks because trusted confidence is 0.49. That
behavior is conservative and arguably correct, but one runtime contract test still expects
the action to execute.

Verdict: **the in-process gate works; the test contract is stale.**

Important limitation: `BaseAgentV2._write_audit()` only appends to `self._audit_log`.
That is not a durable audit record unless the caller separately persists it.

### 2.4 Runtime Mode / Doctor / Fallback Honesty

`make doctor-offline` passes:

```text
AgentCo doctor selected offline_fixture can_continue=True
```

This is honest for an explicitly offline mode. Runtime mode code exposes fallback/simulated
providers rather than pretending they are production infrastructure.

Verdict: **works for mode labeling and local offline operation.**

### 2.5 Many Backend DB Slices Pass Under Real Local DB

In the elevated backend all-test run, 78 of 94 executed suites passed. Passing areas include
many of the important core slices:

- claim grounding / grounded resolver
- identity/event-log/audit-log
- idempotency store
- override queue
- calibration-driven planning
- civilization runtime reachability
- scheduler
- domain registry
- persistent agents
- evidence vector index
- protected surface enforcer
- kill switch
- contradiction learning

Verdict: **there is a real DB-backed backend here, not just mocks.**

---

## 3. Blockers and Hard Breaks

### BLOCKER 1: The selfcoding sandbox is not a sandbox

Files:

- `selfcoding/sandbox/run_generated.py`
- `selfcoding/tests/test_wall_holds.py`
- `scripts/verify_release_gates.py`

The sandbox claims generated code cannot access resolver internals or execute shell
commands. Actual implementation passes a bound method into `exec()`:

```python
"score_prediction": resolver.score_prediction
```

That bound method exposes:

- `score_prediction.__self__` -> the supposedly sealed resolver object
- `score_prediction.__globals__` -> module globals, including `os`

Executed exploit:

```python
score_prediction.__globals__['os'].system(
    'id > ' + str(scratch_dir) + '/codex_audit_id.txt'
)
```

Result:

```text
uid=502(Zet) gid=20(staff) groups=20(staff),12(everyone),61(localaccounts),100(_lpoperator),701(com.apple.sharepoint.group.1)
```

Executed resolver introspection:

```python
resolver_obj = score_prediction.__self__
result = {
  "breach": True,
  "resolver_class": str(resolver_obj.__class__),
  "resolver_state_keys": list(resolver_obj.__dict__.keys())
}
```

Result:

```text
breach=True
resolver_class=<class 'selfcoding.resolver.sealed_resolver.SealedResolver'>
resolver_state_keys=['_frozen_data_path', '_metadata', '_data_cache']
```

The wall script still prints "12/12 tests passed" because its tests are weak:

- write tests are blocked by `NameError: open is not defined`, not by OS confinement
- import tests are blocked by `__import__ not found`
- it never probes bound-method `__self__` or `__globals__`

`scripts/verify_release_gates.py` maps sandbox green only from the script exit code.
Therefore `sandbox_breach: green` is a false signal.

Severity: **BLOCKER.** Do not use selfcoding as a gate for real self-modification until
generated code runs behind an OS/process boundary with no Python object graph escape.

### BLOCKER 2: Learning/self-improvement schema drift breaks active backend tests

Command:

```bash
cd backend
npm run test:all -- --forceExit
```

Run with local network/database elevation to avoid sandbox EPERM artifacts.

Result:

```text
Test Suites: 16 failed, 3 skipped, 78 passed, 94 of 97 total
Tests:       46 failed, 8 skipped, 5 todo, 394 passed, 453 total
```

Dominant failure:

```text
error: column "risk_level" of relation "learner_candidates" does not exist
```

Impacted claims/tests include:

- `learning-candidate-registry`
- `regression-test-generator`
- `proof-of-competence`
- `skill-library`
- `capability-expansion-gate`
- `self-improvement-closed-loop-e2e`
- `civilization-live-flow-e2e`
- `longitudinal-learning-harness`
- `bounded-goal-formation-e2e`
- `goal-formation-supervised-free-run`

The service writes the missing column in `backend/src/services/learner.service.ts`:

```sql
INSERT INTO learner_candidates (... risk_level, simulation_trained, status, trace_id)
```

Migration `068_learner_schema_compatibility.sql` is supposed to add it:

```sql
ADD COLUMN IF NOT EXISTS risk_level risk_level NOT NULL DEFAULT 'low'
```

But live DB inspection shows:

- `034_learner_infrastructure.sql` recorded
- `068_learner_schema_compatibility.sql` recorded
- `learner_candidates.risk_level` missing
- neighboring columns from the same migration, such as `simulation_trained`,
  `trace_id`, and `artifact_json`, present

Severity: **BLOCKER for learning/self-improvement/proof capability.**

### BLOCKER 3: Goal-depth schema drift breaks specialist integration

Active tests insert `autonomy_goals.depth`, e.g. specialist integration and specialist
spawning tests. Migration `061_add_goal_depth_column.sql` is supposed to add it:

```sql
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS depth INTEGER DEFAULT 0;
```

Live DB inspection shows:

- `061_add_goal_depth_column.sql` recorded
- `autonomy_goals.depth` missing
- `goal_depth`, `goal_path`, and `rollup_status` present

The migration verifier requires `goal_depth` but not `depth`, so it passes while active
tests fail.

Severity: **MUST-FIX / BLOCKER for specialist activation paths.**

### BLOCKER 4: Mission and production gates are currently blocked

Commands:

```bash
make mission-progress
make production-posture
```

Results:

```text
mission_fully_proven=false
evidence_governed_calibration_civilization=blocked
durable_autonomous_improvement_from_repeated_real_world_operation=unproven
progressively_more_general_intelligence_over_long_horizons=unproven
```

```text
production-posture: can_continue=false, blocked_count=15
```

This is honest and useful behavior from the gates, but it means the system cannot currently
claim production readiness or fully proven civilization behavior.

---

## 4. Important Must-Fix Gaps

### 4.1 Migration verifier does not cover the columns that current code needs

`scripts/verify_migrations_native.py` checks a small set of runtime-critical columns:

```python
"autonomy_goals": {"id", "institution_id", "goal_depth", "goal_path", "rollup_status"}
```

It does not check:

- `autonomy_goals.depth`
- `learner_candidates.risk_level`
- other learner/self-improvement columns used by active services

That is why `make verify-migrations-native` passes even though all-Jest fails on missing
runtime columns.

### 4.2 Migration tracker can be out of sync with actual schema

`schema_migrations` says migrations are applied. The actual schema lacks columns from those
migrations. This is worse than an unapplied migration: the runner will skip the migration,
and verifiers do not currently detect the drift.

Probable remediation:

- Add repair migration(s), not manual DB edits.
- Expand `verify_migrations_native.py` to include every column used by current production
  services and tests.
- Add a drift detector that compares migration expectations against `information_schema`,
  especially for compatibility migrations.

### 4.3 Python test defaults are not clean-clone portable

Agent integration tests default to:

```python
postgresql://agentco:password@localhost:5433/agentco?host=/tmp
```

Reserve tests default similarly when `AGENTCO_TEST_DATABASE_URL` is absent, then fall back
to current-user socket behavior and fail with database `"Zet"` missing.

This means "real Postgres tests" are real only when the environment is primed. They are not
self-describing or clean-clone portable by default.

### 4.4 V2 audit is not durable by itself

`BaseAgentV2._write_audit()` appends to an in-memory list:

```python
self._audit_log.append(entry)
```

The V2 code is safer than v1 on gating, but "audit log captures" should not be read as
durable audit persistence unless an outer service persists the entry.

### 4.5 Runtime contract tests are stale against current conservative gating

`runtime/tests/test_base_agent_v2.py` expects a low-risk, stated-confidence 0.70 action to
execute so it can inspect envelope fields. The trust layer discounts no-track-record
confidence to 0.49, below the approval threshold, so the action now correctly blocks.

This is not necessarily a product defect. It is a stale test/contract mismatch.

### 4.6 The no-stub scanner is noisy and stale

Fresh build-ledger report marks `no_stub: red` because it scans the marker `later` in normal
comments/docstrings. The committed ledger still says green. This is not a product blocker,
but the gate is not suitable as a high-confidence release signal in its current form.

---

## 5. Capability Matrix

| Capability | Actual status | Evidence |
|---|---:|---|
| Backend TypeScript compile | WORKS | `npm run build` passed |
| Local offline doctor | WORKS | `make doctor-offline` passed |
| Release firewall gate | WORKS | `make release-gates`, firewall subtest passed |
| Credential key-independence gate | WORKS | `make release-gates`, credential subtest passed |
| Release reachability gate | PARTIAL | route registration + focused L14 route tests, not full internal behavior |
| Release sandbox-breach gate | BROKEN | gate green, direct shell/resolver exploit succeeds |
| Calibration ledger app-layer tests | WORKS | 30/30 targeted suite previously passed |
| Prediction ledger PG triggers | WORKS | 8/8 PG suite previously passed |
| V2 escalation blocking | WORKS | `HumanApprovalRequired` raised for high risk and low trusted confidence |
| V2 durable audit | PARTIAL/ABSENT | in-memory `_audit_log`; no DB write in `BaseAgentV2` itself |
| v1 agent governance | BROKEN | prior audit: audit/approval side effects fail open |
| Backend all-Jest | BROKEN | 78/94 suites pass, 16 fail under real local DB |
| Learning candidate registry | BROKEN | missing `learner_candidates.risk_level` |
| Skill/proof/capability expansion loop | BROKEN | same schema drift blocks tests |
| Specialist activation integration | BROKEN | missing `autonomy_goals.depth` |
| Migration native verifier | PARTIAL | passes while required active columns are missing |
| Mission progress | BLOCKED/PARTIAL | `mission_fully_proven=false`, key claim blocked |
| Production posture | BLOCKED | `can_continue=false`, 15 blockers |
| Hosted production | UNPROVEN | no hosted SLO/backup/DR/incident evidence |
| Long-horizon generality | UNPROVEN | explicitly unproven by mission gate |
| Durable real-world self-improvement | UNPROVEN/BROKEN | unproven and self-improvement tests blocked by schema drift |

---

## 6. Drilling Order Findings

### Layer 0: Runnability and Mode Honesty

Works for build and offline doctor. Production posture blocks, as it should. The docs
should keep saying local research/runtime, not production.

### Layer 1: Schema and Migration Foundation

This is currently the most damaging integration gap. The migration tracker says the schema
is up to date, but active columns are absent. Because verifiers do not check those columns,
release/migration gates produce false confidence.

### Layer 2: Evidence, Claims, Predictions, Calibration

This is comparatively strong. The calibration/prediction path has real tests, real
Postgres triggers, and recent hardening. Remaining risk is less about the ledger and more
about upstream agents feeding it meaningful stated confidence and downstream learning
paths being schema-compatible.

### Layer 3: Agents and Runtime Governance

There are two realities:

- v1 agents: broad coverage but governance fails open and confidence is largely hardcoded.
- v2 agents/runtime: narrower coverage but escalation blocks and trusted-confidence gating
  is real.

The system should be described as "V2-governed where V2 is wired", not globally governed.

### Layer 4: Learning / Self-Improvement / Skill Promotion

Currently broken as an integrated path due schema drift. The tests that would prove this
path are the ones failing. The selfcoding sandbox, separately, is not safe.

### Layer 5: Civilization / Institutions / Coordinator

Many focused DB-backed slices pass, including runtime reachability and scheduler tests. The
full "civilization" claim is blocked by the mission gate and by learning/self-improvement
failures.

### Layer 6: Production / Operations

Not certified and not currently green. This is correctly reflected by `production-posture`
and mission-progress, but some older docs still contain stronger historical language.

---

## 7. Test and Command Log

Commands run and material results:

```text
git status --short --branch
  clean branch at start: main...origin/main; audit branch created

python3.13 scripts/build_ledger.py status
  items: 68/71 verified (95.77%)
  no_stub: red
  no_simulation/reachability/firewall/sandbox/credential/e2e: green

python3.13 scripts/build_ledger.py remaining
  L15.LongHorizonGenerality not_started
  L15.DurableRealWorldSelfImprovement in_progress
  L15.HostedProductionOperations not_started

python3.13 scripts/build_ledger.py report
  no_stub red with two scanner hits on "later"

python3.13 selfcoding/tests/test_wall_holds.py
  prints 12/12 PASS, WALL HOLDS

Direct selfcoding exploit
  success=True; resolver __self__ exposed
  success=True; os.system wrote id output

make release-gates
  success=true; sandbox_breach green (false green)

make doctor-offline
  selected offline_fixture can_continue=True

python3.13 -m pytest runtime/tests runtime/orchestration/tests calibration/tests/test_ledger_immutability.py tests/test_verify_release_gates.py tests/test_build_ledger.py -q
  99 passed, 1 failed
  failure: BaseAgentV2 low-risk 0.70 action now gates due trusted confidence 0.49

cd backend && npm run build
  PASS

cd backend && npm run test:all -- --forceExit
  sandboxed: many EPERM false failures
  elevated local network/DB: 78 suites passed, 16 failed, 3 skipped; 394 tests passed, 46 failed, 8 skipped, 5 todo

Live Postgres schema inspection
  schema_migrations records 034, 061, 068
  learner_candidates.risk_level missing
  autonomy_goals.depth missing
  risk_level type exists

make verify-migrations-native
  success=true despite missing active columns

python3.13 -m pytest tests/test_verify_migrations_native.py -q
  2 passed

make mission-progress
  mission_fully_proven=false
  evidence_governed_calibration_civilization=blocked
  production hosted certification=blocked

make production-posture
  exit 2; can_continue=false; blocked_count=15
```

---

## 8. Recommended Repair Order

1. **Disable or relabel the selfcoding sandbox gate immediately.** It should be red until
   generated code is run in a separate process/container/VM with a restricted uid, bounded
   filesystem, no resolver object references, and tests that prove `__self__`,
   `__globals__`, subclass walks, pandas file IO, and shell execution fail.
2. **Repair DB schema drift with migrations, not manual edits.** Add compatibility
   migrations for `learner_candidates.risk_level` and `autonomy_goals.depth` or migrate code
   to canonical columns consistently. Then run all backend tests from a clean DB.
3. **Expand migration verification to active service contracts.** Required columns must
   include learner/self-improvement/skill/proof/specialist columns used by current code.
4. **Make the backend all-test suite a release gate.** The current release gate is too
   narrow; it missed 16 failing suites.
5. **Fix Python test defaults.** Require `AGENTCO_TEST_DATABASE_URL` for real-DB tests or
   skip with a clear message; do not default to port 5433 socket paths that fail mysteriously.
6. **Make V2 audit durable or rename it.** In-memory audit is useful debugging context, not
   an audit guarantee.
7. **Retire or isolate v1 agents from governed paths.** Until v1 governance is fixed, only
   V2-governed roles should feed safety-critical runtime claims.
8. **Update status docs after fixes.** `docs/CURRENT_IMPLEMENTATION_REALITY.md` is stale
   (`67/67`, green no-stub, green production smoke language) relative to current ledger and
   gate results.

---

## Final Assessment

AgentCo has moved past scaffolding in several important areas. The calibration ledger,
prediction resolution firewall, event/audit services, identity/resource/event slices, and
many TypeScript backend services are real enough to pass focused DB-backed tests. The system
also has an unusually strong habit of documenting what remains unproven, especially at the
mission level.

The integration reality is not yet at the level the architecture claims. The current
breakpoints are not cosmetic: a false-green sandbox gate, a failing all-backend suite, a
migration tracker that says applied while active columns are absent, and blocked mission and
production posture gates. Those are exactly the places a real autonomous system cannot be
loose.

The next honest milestone is not "more features." It is **make the current claimed system
coherent under one clean DB and one release gate**: all active migrations applied, all
active backend tests green, selfcoding either genuinely confined or excluded, and docs
updated to distinguish verified local slices from unproven civilization behavior.
