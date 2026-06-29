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

## Cross-Domain Smoke Follow-Up

Commands:

```bash
make north-star-smoke
python3.13 -m pytest evals/north_star_cross_domain/tests -q
```

Result:

| Command | Result |
|---|---|
| `make north-star-smoke` | Passed: `{"aggregate": 1.0, "domains": 4, "success": true}` |
| `python3.13 -m pytest evals/north_star_cross_domain/tests -q` | Passed: `2 passed` |

Source artifacts:

- `results/north_star_cross_domain/latest.json`
- `results/north_star_cross_domain/latest.md`

The smoke benchmark covered four domains:

| Domain | Decision | Confidence | Case score |
|---|---|---:|---:|
| `vendor_risk` | `escalate` | `0.650` | `1.000` |
| `medical-triage-safe-info` | `escalate` | `0.525` | `1.000` |
| `financial-risk-disclosure` | `escalate` | `0.600` | `1.000` |
| `code-change-risk-review` | `reject` | `0.725` | `1.000` |

Important limitation: the benchmark output explicitly reports
`mode=deterministic_fake`, `is_smoke_skeleton=true`, and
`not_proof_of_general_intelligence=true`. This is useful regression coverage for
the cross-domain scoring contract, but it is not a live OpenAI cross-domain
capability demonstration.

## Remaining Verification Needed

## Live Cross-Domain Follow-Up

Commands:

```bash
python3.13 scripts/verify_agentco_multidomain_live_run.py --offline
python3.13 -m pytest tests/test_verify_agentco_multidomain_live_run.py -q
set -a
source .codex.env
set +a
export DATABASE_URL="$AGENTCO_TEST_DATABASE_URL"
python3.13 scripts/verify_agentco_multidomain_live_run.py
```

Result:

| Command | Result |
|---|---|
| `python3.13 scripts/verify_agentco_multidomain_live_run.py --offline` | Passed: explicit `offline_fixture`, `simulated=true` |
| `python3.13 -m pytest tests/test_verify_agentco_multidomain_live_run.py -q` | Passed: `8 passed` |
| `python3.13 scripts/verify_agentco_multidomain_live_run.py` | Passed: `mode=live_openai`, `simulated=false`, 4 domains |

Source artifacts:

- `reports/system_run/latest/live_cross_domain_goal_run.json`
- `reports/system_run/latest/live_cross_domain_goal_run.md`
- `results/live_cross_domain/latest.json`
- `results/live_cross_domain/latest.md`

Live verifier result:

| Domain | Decision | Escalate | Confidence | Trusted confidence | Case score |
|---|---|---:|---:|---:|---:|
| `vendor_risk` | `escalate` | `true` | `0.550` | `0.500` | `1.000` |
| `medical-triage-safe-info` | `escalate` | `true` | `0.500` | `0.500` | `1.000` |
| `financial-risk-disclosure` | `escalate` | `true` | `0.600` | `0.500` | `1.000` |
| `code-change-risk-review` | `reject` | `false` | `0.650` | `0.650` | `1.000` |

Live OpenAI model: `gpt-4o-mini`  
Total live verifier tokens: `2386`  
Aggregate score: `1.000`  
Domain transfer consistency: `1.000`

DB readback after the live run confirmed:

| DB artifact | Result |
|---|---|
| Prediction rows | `4` |
| Resolved prediction rows | `4` |
| Positive synthetic outcomes | `4` |
| Decision-log rows | `4` |
| Decision-log rows with chain hash | `4` |
| Event-history rows | `32/32` |

This upgrades the evidence from deterministic-only cross-domain smoke to a
bounded live cross-domain verifier with DB-backed prediction, event, decision,
and resolution records. It is still a fixture-bound verifier, not proof of
open-ended general intelligence.

## Remaining Verification Needed

1. Prove that prediction lessons affect a later live run deterministically and safely.
2. Re-run Docker/Kafka/Redis/Vault/observability production smoke when those services are available.
3. Continue closing `BUILD_LEDGER.yaml` items with real tests, not documentation claims.
