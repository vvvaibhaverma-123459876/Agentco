> **Historical/superseded status notice:** This document is retained for audit history. Do not treat production-ready, complete, deployment-ready, or old ledger-count language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

# Migration Status Report

Generated during branch `fix/runtime-integrity-and-production-honesty`.

## Enabled Migrations

`backend/src/db/migrations/*.sql` contains the active migration set. The new migration in this pass is:

| Migration | Status | Purpose |
| --- | --- | --- |
| `075_agent_tasks_canonical_view.sql` | enabled | Exposes the existing deployable `workflow_tasks` dispatch table as `agent_tasks` for durable executor tooling. |

## Unsupported Migration Archive

Files ending in `.sql.disabled` have been moved out of the active migration directory to `backend/src/db/unsupported_migrations/`. They are not part of the active schema and must not be treated as implemented runtime capability.

| Migration | Classification |
| --- | --- |
| `020_evaluation_manifests.sql.disabled` | unsupported/future until enabled and tested |
| `025_autonomy_goals.sql.disabled` | unsupported/future until enabled and tested |
| `025_goal_management.sql.disabled` | unsupported/future until enabled and tested |
| `026_autonomy_plans.sql.disabled` | unsupported/future until enabled and tested |
| `026_phases_5_8_integrated.sql.disabled` | unsupported/future until enabled and tested |
| `027_phases_9_13_integrated.sql.disabled` | unsupported/future until enabled and tested |
| `027_reward_system.sql.disabled` | unsupported/future until enabled and tested |
| `028_civilization_learning_structure.sql.disabled` | unsupported/future until enabled and tested |
| `028_eval_harness.sql.disabled` | unsupported/future until enabled and tested |
| `029_learner_infrastructure.sql.disabled` | unsupported/future until enabled and tested |
| `029_rollback_infrastructure.sql.disabled` | unsupported/future until enabled and tested |
| `030_self_modification.sql.disabled` | unsupported/future until enabled and tested |
| `031_artifact_registry.sql.disabled` | unsupported/future until enabled and tested |
| `033_rbac.sql.disabled` | unsupported/future until enabled and tested |
| `034_policy_control.sql.disabled` | unsupported/future until enabled and tested |
| `035_canary_deployment.sql.disabled` | unsupported/future until enabled and tested |
| `035_simulator_infrastructure.sql.disabled` | unsupported/future until enabled and tested |

## Required Schema Checks

The current deployable task dispatch path uses `workflow_tasks`. The compatibility view `agent_tasks` is now the canonical external name for the durable executor. The older prompt-referenced `durable_tasks` table is not present and is not a supported path.

Required production verification remains:

```bash
cd backend
DATABASE_URL=<real-postgres-dsn> npm run db:migrate
DATABASE_URL=<real-postgres-dsn> npm run test:integration
```

## Honesty Notes

This report does not claim all disabled migrations are production ready. Disabled migrations remain explicitly unsupported until they are enabled, migrated, wired to routes/services, and covered by integration tests.
