# AgentCo V2 — Adversarial Invariant Audit

**Date:** 2026-06-16
**Scope:** Calibration Engine, V2 runtime, learning loop, synthesis, backend DB layer
**Method:** Invariant-first, adversarial. For each guarantee: "can I construct an execution path that violates it?"

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 2 |
| LOW | 3 |

- **Master gate (seeded-false-belief test): PASS** (verified `evals/regression/test_v2_regression.py::TestSeededFalseBeliefRegression`)
- **No epistemic-invariant violation found.** All 10 invariants hold against every path attempted. The firewall could not be made to promote on simulation evidence; stated confidence could not be made to drive a decision; the ledger's resolution is write-once; the human gate has no timeout-proceed path.
- The HIGH findings are **crash / silent-failure bugs that fail closed** (they break functionality, they do not weaken a safety guarantee) plus one **DB-layer enforcement gap** against the build-prompt spec.

---

## Invariant results (all PASS — adversarially verified)

| # | Invariant | Status | Enforcement (file:line) |
|---|---|---|---|
| 1 | Only reality promotes | PASS | `firewall.py:99-180` — `promote_to_reality_validated()` is the sole path |
| 2 | Immutable prediction ledger | PASS* | App: `resolution_service.py:112` write-once. *DB layer missing — see HIGH-4 |
| 3 | Pre-registration enforced; post-hoc excluded | PASS | `ledger.py:94-101` flag; `scoring_module.py:52` excludes; `trust_controller.py:112` skips |
| 4 | Firewall hard gate; sim_support_count excluded | PASS | `firewall.py:167` — 4 gates, sim count never read |
| 5 | Decisions on trusted_confidence not stated | PASS | `base_agent_v2.py:183` always `get_trusted()`; gate gets trusted value |
| 6 | Human gates block; no auto-approve on timeout | PASS | `escalation_gate.py:122` raises; no timeout path exists |
| 7 | Outputs carry confidence + prompt_version + HMAC | PASS | `base_agent_v2.py:236-253` envelope; `event-bus.service.ts` verifies |
| 8 | 100% immutable audit log | PASS | `004_decision_log.sql:21-22` REVOKE; `audit-log.service.ts` hash chain |
| 9 | Config-Agent cannot self-modify | PASS | `config_agent_v2.py:54-62` hardcoded `target == AGENT_ID` block |
| 10 | Ground truth external only | PASS | `ledger.py:149`, `resolution_service.py:120`, `firewall.py:150` all reject internal |

---

## HIGH findings

### HIGH-1 · `n_resolved` / `sample_count` field mismatch — crashes the decision hot path
- **File:** `calibration/trust/trust_controller.py:190` (and `learning/intelligence_agent/intelligence_agent.py:106`)
- **Path:** `BaseAgentV2.execute_action()` → `ConfidenceV2.get_trusted()` → `TrustController.get_sample_count()` → `return score.n_resolved`. The `TrustScore` dataclass field is named `sample_count` (line 44), not `n_resolved`.
- **Reproduction:** Any agent that already has ≥1 resolved prediction (so a `TrustScore` exists) calls `execute_action()` → `AttributeError: 'TrustScore' object has no attribute 'n_resolved'`. New agents return 0 before reaching the bad line, which is why the existing regression suite (which only uses fresh agents) passes.
- **Canonical name:** the DB column (`009_trust_scores.sql:15`), the dashboard type (`calibration.ts:40`), `meta/failure_modes.md`, and both Python consumers all use `n_resolved`. The dataclass is the outlier.
- **Fix:** rename `TrustScore.sample_count` → `n_resolved`; update the 6 internal references in `trust_controller.py`. Fails closed (crash), so not an invariant violation, but disables every with-history agent.

### HIGH-2 · `escalation.route()` does not exist — malformed-output escalation path is dead
- **File:** `runtime/base_agent/structured_output.py:64`
- **Path:** `BaseAgentV2.act()` passes `escalation=self._gate` (an `EscalationGate`). On `MAX_RETRIES` schema failures, `get_validated_output()` calls `escalation.route(...)`. `EscalationGate` has no `route()` method → `AttributeError`.
- **Reproduction:** call `agent.act()` where the model returns 3 consecutive invalid JSON responses → crash instead of clean escalation.
- **Impact:** `LOCAL_MODEL_SETUP.md §4` guarantee — "a malformed structured output never reaches the bus; escalate rather than emit garbage" — is broken. (Introduced by the local-model layer.)
- **Fix:** add `EscalationGate.route(reason, detail, risk_level)` that records a pending human approval and returns a structured escalation result.

### HIGH-3 · Downgrade propagation is dead code — mechanical downgrade never fires
- **File:** `calibration/trust/trust_controller.py:136-138`
- **Path:** `ingest_resolution()` calls `_recompute_multiplier(score)` (line 133, mutates `trusted_multiplier`), THEN captures `was = score.trusted_multiplier` (line 136) and tests `if was - score.trusted_multiplier > 0.05`. Since `was` is read after the mutation, the difference is always 0 → the `_propagate_downgrade()` callback is never invoked.
- **Reproduction:** register a downgrade callback; resolve several high-confidence predictions FALSE; observe the callback never fires even though the multiplier dropped.
- **Impact:** The "mechanical downgrade propagation" feature (docstring, lines 11-14) is dead. The **pull** path still works (next `trusted_confidence()` reads the lowered score), so decisions remain safe — but consumers relying on the **push** notification go un-notified. Silent failure.
- **Fix:** capture `was` before `_recompute_multiplier()`.

### HIGH-4 · Prediction ledger immutability is not enforced at the DB layer
- **File:** missing `backend/src/db/migrations/0XX_prediction_ledger.sql`
- **Path:** `ledger.py:122` comment says "In production: INSERT … DB enforces immutability," but no `prediction_ledger` table/trigger exists. Immutability and write-once live only in Python (`resolution_service.py:112`). Build-prompt §2.1: "FAIL if immutability is enforced only in application code."
- **Impact:** In the current in-memory dev architecture there is no DB to bypass, so no runtime exploit today — but the spec's DB-layer guarantee is absent. `beliefs` (010) and `trust_scores` (009) have triggers; the ledger does not.
- **Fix:** add `011_prediction_ledger.sql` mirroring the build-prompt schema: REVOKE UPDATE/DELETE; trigger blocking mutation of pre-registration columns; write-once resolution columns; time-gate; `resolution_service` role restriction.

---

## MEDIUM findings

### MEDIUM-1 · Hardcoded `MODEL = "claude-..."` strings remain in ~50 agent files
- **Files:** all `agents/**/*.py` and `learning/**/*.py` agent classes (e.g. `intelligence_agent.py:45`, `trainer_agent.py:30`, `ceo_agent_v2.py:24`), plus the V1 default `agents/core/base_agent.py:43`.
- **Impact:** `LOCAL_MODEL_SETUP.md §8` DoD: "no Claude strings remain in code." For V2 agents the attribute is vestigial (runtime model comes from `model_for(agent_id)` in `BaseAgentV2.__init__`), but `agents/core/base_agent.py:43` is the **live** default for V1 agents and would call a cloud model. Misleading and DoD-violating.
- **Fix:** point V1 `base_agent.py` default at the tier map; treat remaining V2 `MODEL` attrs as documentation or remove. (Reported; full sweep is mechanical — recommend a follow-up PR to avoid touching 50 files + 5 tests in the same change as the safety fixes.)

### MEDIUM-2 · `resolved_by_service` written to a non-existent dataclass field
- **File:** `calibration/resolution/resolution_service.py:81`
- **Impact:** `PredictionRecord` has no `resolved_by_service` field; Python silently creates a dynamic attribute. Works in-memory but will not map to a DB column / serialize predictably.
- **Fix:** add `resolved_by_service: Optional[str] = None` to `PredictionRecord`.

---

## LOW findings

### LOW-1 · Comment claims a check that does not exist
- `resolution_service.py:126-127` says "Predicting agent cannot resolve their own prediction (enforced at service layer)" but `resolve()` takes no resolver identity and performs no such check. It is enforced architecturally (agents lack access to `ResolutionService`). Comment overstates code.

### LOW-2 · Python `Belief` vs SQL `beliefs` schema mismatch
- `firewall.py:30-39` `Belief` uses `statement` / `origin`; `010_beliefs.sql:8-10` uses `claim` / `domain` / `claim_type`. Latent (Python is in-memory) but will break any future ORM mapping.

### LOW-3 · Belief status enum mismatch
- Python `VALID_STATUSES` (`firewall.py:59`) includes `"retired"`; SQL CHECK (`010_beliefs.sql:12`) allows `"quarantined"` not `"retired"`. Writing `retired` to the DB would violate the CHECK.

---

## Silent-failure class results

| Class | Result | Note |
|---|---|---|
| Echo-chamber leak | PASS | Trainer tags backtests `simulation`; Memory writes only `provisional`; firewall ignores sim count |
| Confidence inflation | PASS | All decisions route through `trusted_confidence()`; no raw stated value reaches a decision |
| Version-attribution drift | PASS | `producing_prompt_version` captured at pre-register and in envelope |
| Surprise suppression | PASS (detection) / see HIGH-3 (propagation) | `SurpriseRegister.check` fires on both tails; trust score updates; only the push-callback is dead |
| Decay bypass | PASS | `last_reality_contact` updated on every `ingest_resolution` |
| Goodhart on calibration | PARTIAL | Documented residual risk in `meta/failure_modes.md`; no engineered cherry-pick detector |
| Gate-default-allow | PASS | No exception/timeout path proceeds without an approval token |
| Event idempotency gap | PASS (in scope reviewed) | Handlers stateless; offset-tracked at bus |

---

## Correct-behavior items (do NOT "fix")

- Trust Controller downgrading an agent after failed predictions — **working as designed.**
- Firewall blocking a simulation-only promotion — **correct; do not add a sim promotion path.**
- Escalation gate blocking and waiting on a human — **correct; do not add timeout-proceed.**
- Stated confidence read down to trusted value for new agents — **correct.**
- Malformed model output escalating instead of proceeding — **correct intent** (the *mechanism* is broken, HIGH-2; fix the mechanism, do not bypass it).

---

## Regression tests added (Pass 2)

| Finding | Test | Prevents |
|---|---|---|
| HIGH-1 | `test_audit_findings.py::test_get_sample_count_with_track_record` | get_sample_count crash on agents with history |
| HIGH-2 | `test_audit_findings.py::test_malformed_output_escalates_cleanly` | act() crashing instead of escalating |
| HIGH-3 | `test_audit_findings.py::test_downgrade_propagates_to_consumers` | dead downgrade-propagation regressing |
| HIGH-4 | `011_prediction_ledger.sql` | ledger mutability at DB layer |
