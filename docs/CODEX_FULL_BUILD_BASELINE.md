# Codex Full Build Baseline

Date: 2026-06-20
Branch: `codex/full-civilization-gated-build`
Starting commit: `3ea9521c19fcf193cc6ea645927029271ffa73d4`

## Repository Structure Summary

- `calibration/`: prediction ledger, resolution service, source independence helpers, scoring, trust, firewall, surprise, decay, self-audit.
- `reserve/`: proof-of-calibration credentials, oracle, staking, weighted decisions, commitment chain, migrations, recomputation tools.
- `civilization/`: bounded Institution Kernel with domain entities, institution/review/reputation/governance/memory services, contracts, controls, and reputation weights.
- `backend/`: Fastify/TypeScript API, services, routes, migrations, Jest tests.
- `frontend/`: Next.js dashboard, typed API helper, app pages.
- `agents/`, `runtime/`, `learning/`, `synthesis/`: Python agent runtime, memory, learning loop, synthesis, and tests.
- `tests/`, `evals/`, `reserve/tests/`, `calibration/tests/`: Python regression, integration, civilization, calibration, and reserve tests.

## Current Makefile Targets

- `dev`
- `migrate`
- `test`
- `smoke`
- `demo`
- `business-demo`
- `business-sim`
- `clean`

`make doctor`, `make dev-minimal`, `make dev-full`, and `make demo` profiles beyond the existing target are not present at baseline.

## Backend Scripts

From `backend/package.json`:

- `npm run dev`: `ts-node-dev --respawn src/server.ts`
- `npm run build`: `tsc`
- `npm start`: `node dist/server.js`
- `npm test`: `jest --passWithNoTests`
- `npm run db:migrate`: `python3 src/db/run_migrations.py`
- `npm run lint`: `eslint src --ext .ts`

## Frontend Scripts

From `frontend/package.json`:

- `npm run dev`: `next dev`
- `npm run build`: `next build`
- `npm start`: `next start`
- `npm run lint`: `next lint`
- `npm test`: `jest`

## Python Test Commands

- `python3 -m pytest calibration runtime reserve tests evals learning synthesis`
- Targeted examples already present:
  - `python3 -m pytest calibration`
  - `python3 -m pytest reserve`
  - `python3 -m pytest tests/civilization`
  - `python3 -m pytest tests/e2e`
  - `python3 -m pytest evals/regression`

## Existing Migrations

Backend migrations:

- `001_agent_state.sql`
- `002_agent_memory.sql`
- `003_shared_knowledge.sql`
- `004_decision_log.sql`
- `005_event_history.sql`
- `006_prompt_registry.sql`
- `007_performance_metrics.sql`
- `008_customer_data.sql`
- `009_trust_scores.sql`
- `010_beliefs.sql`
- `011_prediction_ledger.sql`
- `012_decision_log_chain.sql`
- `013_override_queue.sql`
- `014_decision_log_immutability_triggers.sql`
- `015_agent_memories.sql`
- `015_agent_memories_lifecycle.sql`
- `016_resolution_service_role.sql`

Reserve migrations:

- `001_reserve_extension.sql`
- `002_staking.sql`
- `003_oracle_layer.sql`
- `004_ed25519_signature.sql`
- `005_prediction_chain.sql`
- `006_civilization.sql`

## Existing Calibration / Reserve Files

- `calibration/ledger/prediction_ledger.py`
- `calibration/ledger/schema.sql`
- `calibration/resolution/resolution_service.py`
- `calibration/resolution/source_independence.py`
- `calibration/scoring/scoring_module.py`
- `calibration/trust/trust_controller.py`
- `calibration/firewall/firewall.py`
- `reserve/credentials/proof_of_calibration.py`
- `reserve/tools/recompute_credential.py`
- `reserve/chain/commitment_chain.py`
- `reserve/oracle/oracle_layer.py`
- `reserve/staking/staking.py`
- `reserve/decisions/weighted_decision.py`

## Existing Civilization Files

- `civilization/domain/entities.py`
- `civilization/services/institution_service.py`
- `civilization/services/review_service.py`
- `civilization/services/reputation_service.py`
- `civilization/services/governance_service.py`
- `civilization/services/memory_service.py`
- `civilization/contracts/engineering.yaml`
- `civilization/contracts/security.yaml`
- `civilization/controls.yaml`
- `civilization/reputation_weights.yaml`

## Current Docs That Are Accurate

- `docs/launch_readiness_audit.md`: useful as an audit-style status document, though some results require rerun.
- `docs/runnability_audit.md`: useful local runnability notes.
- `docs/civilization_migration_map.md`: useful as migration/planning context.
- `docs/memory_audit.md`: useful memory-system context.
- `README.md`: the opening calibration-first positioning is broadly accurate before Phase 0 edits.

## Current Docs That Are Stale Or Over-Claimed

- `README.md`: includes historical "fully autonomous company", "29 agents", and checkmark-heavy production/proven language that is not supported by the current baseline run.
- `AGENTCO_COMPLETE_GUIDE.md`, `COMPLETION_SUMMARY.md`, `SYSTEM_CIVILIZATION.md`, `SELF_EXTENSION_IMPLEMENTATION_SUMMARY.md`, `HARDENING_REPORT.md`: may contain historical or aspirational claims and should not be treated as shipped status until reconciled.
- Historical test count claims in README do not match the current baseline command results.

## Current Test Status

- `make doctor`: not present.
- `make test`: failed after running Python tests. Result before failure: 224 passed, 1 failed.
  - Failure: `tests/e2e/test_memory_lifecycle.py::test_learning_loop_consolidates_semantics`
  - Root cause: UUID values from memory rows are placed inside JSON content and passed to `psycopg2.extras.Json`, causing `TypeError: Object of type UUID is not JSON serializable`.
- `backend npm test`: failed.
  - Postgres-dependent integration tests cannot connect to `/tmp/.s.PGSQL.5433`.
  - Kafka-dependent event bus tests cannot connect to `localhost:9092`.
  - `backend/tests/security.test.ts` passed within that run.
- `backend npm run build`: passed.
- `frontend npm test`: failed because `jest` is not installed/resolvable in the frontend workspace.
- `frontend npm run build`: passed with an existing React hook dependency warning in `frontend/src/app/audit/page.tsx`.

## Current Blockers

- Full `make test` is blocked by the Python UUID serialization failure.
- Backend integration tests require local Postgres and Kafka services not available in this baseline shell.
- Frontend test script requires Jest, but frontend dependencies do not currently provide a runnable `jest` binary.
- `make doctor` and the requested later clean-run targets are absent.

## Assumptions

- No paid external LLM APIs will be used for tests.
- Deterministic mocks/offline behavior are acceptable where external services are unavailable.
- Existing historical docs should be preserved as context but clearly marked when they are not current shipped claims.
- The current Institution Kernel is bounded and should not be described as a complete Society or Civilization layer.
