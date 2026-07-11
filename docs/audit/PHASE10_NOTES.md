# Phase 10 Notes — Evaluation and Calibration

## Architecture

Phase 10 adds a deterministic evaluation runtime under `runtime/evaluation/`.
The standard record is `EvaluationRecord`; it captures agent identity, task id,
attempt id, output/claim, evidence refs, predicted confidence, evaluator
results, correctness score, evidence-quality score, calibration error, failure
category, timestamp, version, and audit acknowledgement.

Evaluation records are written through the governed audit protocol by
`EvaluationService._audit()`. The audit entry uses the evaluation id as the
stable `attempt_id`, so repeated evaluation is idempotent and does not append
duplicate audit entries.

The evaluator set is deterministic:

- factual correctness
- evidence support
- unsupported high-confidence claims
- tool-result consistency
- policy compliance
- task completion
- confidence calibration

Agents cannot self-certify unless the input is marked as a deterministic
verifier path. Non-deterministic self-certification raises `EvaluationError`.

## Benchmark Coverage

`runtime/evaluation/benchmark.py` defines `phase10.benchmark.v1`. It derives one
positive benchmark case per active Phase 9 agent from
`runtime/base_agent/agent_manifest.py`, covering all 11 active agents:

- 9 `BaseAgentV2` agents
- 2 TypeScript durable identities restricted to `record_observation`

The benchmark also includes negative cases for unsupported high-confidence
claims, tampered evidence, and evaluator disagreement.

## Calibration Metrics

`runtime/evaluation/metrics.py` generates:

- Brier score
- expected calibration error
- accuracy by confidence bucket
- abstention rate
- unsupported-claim rate
- evaluator disagreement rate

The generated machine report is
`docs/audit/EVALUATION_CALIBRATION_REPORT.json`.

## Release Gate

`make release-gate` now runs:

```text
make evaluation-calibration-report-check
```

The check fails if an active agent lacks benchmark coverage, benchmark results
are missing, metrics cannot be generated, evaluation records bypass the audit
writer, or unsupported high-confidence claims pass.

## Out of Scope

This phase does not implement persistent learning, automatic model promotion,
or self-modification.
