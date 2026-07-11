# Phase 12 Notes - Bounded Self-Improvement

Phase 12 adds bounded self-improvement experiments that can propose and evaluate changes but cannot mutate production behavior.

## Architecture

- `runtime.self_improvement.schema.ImprovementExperiment` is the versioned experiment record. It includes hypothesis, target capability, proposed change, evidence and benchmark references, allowed scope, resource budget, risk level, evaluator, outcome, and promotion recommendation.
- `runtime.self_improvement.experiments.BoundedExperimentRunner` executes only sandbox-scoped experiments and writes each outcome through the governed audit writer using the experiment id as the idempotent attempt id.
- `runtime.self_improvement.report.build_experiment_report()` generates the machine-derived report consumed by `make self-improvement-report-check` and `make release-gate`.

## Enforced Boundaries

- Production surfaces are read-only: scopes beginning with `production:` and explicit production mutation requests are blocked.
- Every experiment must have positive time, spend, tool, and scope budgets.
- Requested tools must be declared in the allowed tool set.
- Agents cannot approve their own proposed changes.
- Phase 10 evidence and benchmark references are mandatory.
- Phase 11 remains the only promotion path: accepted experiments emit `propose_phase11_artifact`, not an approval.
- Model weight modification and unrestricted code rewriting are forbidden experiment change types.
- Duplicate experiment requests are idempotent and return the existing audited record.
- Failed or blocked experiments leave production state unchanged.

## Supported Experiment Types

- Prompt variants
- Policy proposals
- Tool-selection strategies
- Memory-rule proposals
- Model-routing strategies

## Release Gate

`make release-gate` now includes `make self-improvement-report-check`, which fails on stale reports, missing budgets, unbounded scopes, production mutation paths, unaudited experiments, self-approved recommendations, missing rollback compatibility, or missing negative safety violations.

