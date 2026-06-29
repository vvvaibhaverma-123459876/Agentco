# Live OpenAI System Behavior Report

**Date:** 2026-06-29  
**Branch:** `fix/runtime-integrity-and-production-honesty`  
**Base commit before this report:** `e8373d4f541cf79db0454c8877f4562483e70d9e`  
**Verdict:** live OpenAI goal-run works for the current vendor-risk verifier, but this is still a narrow verified slice, not proof of the full AgentCo civilization goal.

## Commands Run

```bash
set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"
python3 scripts/verify_openai_connectivity.py
python3 scripts/verify_agentco_goal_run.py
```

Result:

| Command | Result |
|---|---|
| `python3 scripts/verify_openai_connectivity.py` | Passed |
| `python3 scripts/verify_agentco_goal_run.py` | Passed |

Secrets were loaded from `.codex.env` but were not printed.

## OpenAI Connectivity

Source artifact: `reports/system_run/latest/openai_connectivity.json`

| Field | Value |
|---|---|
| Success | `true` |
| Model | `gpt-4o-mini` |
| Latency | `2635 ms` |
| Prompt tokens | `28` |
| Completion tokens | `33` |
| Total tokens | `61` |

The OpenAI-compatible API call succeeded and returned structured JSON.

## Goal-Oriented Live Run

Source artifacts:

- `reports/system_run/latest/goal_run.json`
- `reports/system_run/latest/goal_run.md`
- `reports/system_run/latest/performance_summary.json`

Scenario: vendor onboarding risk decision for `Northstar DataWorks` using incomplete evidence and policy constraints.

| Field | Value |
|---|---|
| Mode | `live_openai` |
| Simulated | `false` |
| Success | `true` |
| Decision | `escalate` |
| Risk level | `high` |
| Confidence | `0.65` |
| Trusted confidence | `0.585` |
| OpenAI latency | `2177 ms` |
| Goal-run total latency | `2178 ms` |
| Tokens used | `350` |

Validation checks all passed:

| Check | Result |
|---|---|
| Expected decision was `escalate` | Passed |
| Cited `ev1` | Passed |
| Cited `ev2` | Passed |
| Did not claim confirmed SOC 2 Type II | Passed |
| Did not conflate breach at similarly named company | Passed |
| Requested SOC 2 Type II report | Passed |
| Requested signed DPA | Passed |
| Requested subprocessor list | Passed |
| Confidence was in `[0, 1]` | Passed |
| Supported claims had sources | Passed |

## Database Persistence Readback

After the run, the generated IDs were read back from native Postgres using `DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"`.

| DB artifact | Result |
|---|---|
| `prediction_ledger` row | Exists |
| Prediction resolved | `true` |
| Resolved outcome | `true` |
| Brier score | `0.1225` |
| `decision_log` row | Exists |
| Decision log chain hash | Present |
| `event_history` rows | `11/11` found |

This proves the live run did more than generate text: it wrote prediction, audit, and event records and resolved the prediction through the configured DB path.

## What Worked As Wanted

- The system made a calibrated escalation decision instead of over-approving incomplete vendor evidence.
- The live model call was real, not fixture mode.
- The verifier enforced hallucination traps: no confirmed SOC 2 Type II and no confirmed breach were invented.
- Missing information was identified: SOC 2 Type II report, signed DPA, and subprocessor list.
- Trusted confidence was lower than raw confidence.
- Prediction, event, and audit artifacts were written to Postgres.
- The prediction was resolved and scored.

## What Did Not Prove The Full Goal

This run supports part of the AgentCo goal, but it does not prove the full target:

> AgentCo exists to evolve into progressively more general intelligence by operating as an evidence-governed, calibration-driven AI civilization that learns continuously, improves itself safely, and expands its capability across domains over time.

Current evidence from this live run:

| Goal dimension | Status from this run |
|---|---|
| Evidence-governed behavior | Real for this vendor-risk verifier |
| Calibration-driven operation | Real for prediction registration, trusted confidence, resolution, and Brier scoring |
| Auditability | Real DB-backed event and decision-log writes |
| Safe behavior under uncertainty | Real for escalation on insufficient evidence |
| Continuous learning | Partial: a learning event is recorded, but this run alone does not prove durable improvement over future runs |
| Cross-domain expansion | Not proven by this live run; current cross-domain benchmark remains separate deterministic smoke coverage |
| AI civilization substrate | Not proven by this live run; multi-agent institutional behavior is wider than this verifier |
| Production readiness | Not proven; production secrets/Vault, Docker/Kafka/Redis/observability smoke, and disabled migrations remain outside this run |

## Important Caveat

The live model output included an unsupported claim with no support IDs. The validator accepted this because the claim was marked `unsupported`; the invariant is that `supported` claims must cite evidence. That behavior is conservative and acceptable for this verifier, but it means this run is not a full claim-promotion pipeline proof.

## Honest Answer

AgentCo is working as intended for the narrow live OpenAI + native Postgres vendor-risk goal-run slice. It demonstrates evidence-governed, calibrated, auditable behavior for one task.

AgentCo is not yet working as the full intended civilization. The broader goal still needs repeated cross-domain live runs, durable improvement measurement, production dependency verification, and more canonical runtime wiring before the project can claim general capability expansion or production-grade civilization behavior.

## Next Verification Needed

1. Run the north-star cross-domain benchmark and compare it to this live vendor-risk behavior.
2. Add a live multi-domain goal-run variant, not only deterministic smoke.
3. Prove that prediction lessons affect a later live run deterministically and safely.
4. Re-run Docker/Kafka/Redis/Vault/observability production smoke when those services are available.
5. Continue closing `BUILD_LEDGER.yaml` items with real tests, not documentation claims.
