# Phase 11 Notes — Controlled Learning and Rollback

## Architecture

Phase 11 adds `runtime/controlled_learning/`, a controlled learning pipeline for
immutable learning artifacts. It does not implement autonomous self-modification.

The pipeline is:

```text
observation -> candidate learning artifact -> offline evaluation
-> approval -> canary -> promotion -> monitoring -> retain or rollback
```

Learning artifacts include source observations, Phase 10 evaluation record ids,
proposed change, evidence refs, benchmark impact, proposer identity, approval
status, artifact version, and promotion/rollback history.

## Controls

- Agents cannot directly modify production prompts, policies, tools, models, or
  memory rules.
- Promotion requires Phase 10 evaluation record ids.
- Self-approval is rejected.
- Benchmark regressions reject artifacts before production exposure.
- Canary, promotion, and rollback events are written through the governed audit
  writer using stable event attempt ids.
- Previous active versions remain recoverable through artifact lineage.
- `FileLearningArtifactStore` proves artifact persistence across process runs.

## Rollback Triggers

Automatic rollback covers:

- benchmark regression
- calibration degradation
- unsupported-claim increase
- policy or authorization failure
- audit-chain failure

## Release Gate

`make release-gate` now runs:

```text
make controlled-learning-report-check
```

The check fails on unauthorized production mutation, missing evaluation
evidence, benchmark regression not being blocked, unrecoverable active versions,
missing rollback coverage, or unaudited promotions.

## Out of Scope

This phase intentionally does not implement autonomous self-modification,
automatic model promotion, or claims of general continual learning.
