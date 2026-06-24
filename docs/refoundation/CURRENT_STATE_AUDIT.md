# Current State Audit

Audit date: 2026-06-21.

## Summary

Agentco contains valuable calibration, trust, reserve, memory, audit, override, and early civilization code. Gates 0-17 are complete for the implemented repo scope; remaining work is hardening, live third-party benchmark connectors, dependency/security triage, and infrastructure cleanup.

## Status-Labeled Findings

| Area | Status | Evidence | Gap |
|---|---|---|---|
| README product promise | **REAL** after Phase 0 edit | `README.md`, `scripts/gate0_check.py` | Older docs retain historical/legacy framing but are no longer live product surfaces. |
| Python calibration/runtime/learning/regression slice | **FIXTURE** | `python3 -m pytest calibration runtime learning synthesis evals/regression -q` passed 115 tests | Does not prove external validation or source independence. |
| Evidence Kernel | **REAL** | `calibration/evidence/evidence_kernel.py`, `evals/regression/test_evidence_kernel_gate2.py` | Python kernel implements claim/evidence/source/resolution APIs, graph, demotion, source reliability, source independence, and promotion gates. DB/API persistence remains later hardening. |
| Memory | **REAL** | `memory_kernel/*`, `backend/src/services/memory-store.service.ts`, `runtime/memory`, `learning/memory_agent`, `tests/e2e/test_memory_lifecycle.py` | Canonical kernel enforces provenance and immutable/mutable split; DB-backed service remains parallel. |
| Backend audit/event/override services | **PARTIAL** | `backend/src/services/*`, `backend/tests/integration/*` | Integration tests need local infra; API write-auth was only added as optional middleware in this pass. |
| Frontend | **REAL** | `frontend/src/app/*`, `frontend/src/lib/api.ts`, `frontend/src/app/validation`, `frontend/src/app/governance` | Dependency install, typecheck, build, validation console, and governance console pass. |
| Durable execution | **REAL** | `backend/src/services/durable-execution.service.ts`, `backend/src/db/migrations/019_durable_execution.sql` | Persistent workflow task state replaces in-memory queue for API dispatch. |
| External attestation | **REAL** | `provenance/attestation.py`, `backend/src/services/provenance.service.ts`, `action_attestations` | Ed25519 attestation and local transparency log verifier are implemented. |
| Uncertainty stack | **REAL** | `calibration/uncertainty/*`, `runtime/confidence`, `calibration/trust`, `calibration/scoring` | Metrics, conformal wrapper, semantic uncertainty, and abstention are implemented. |
| Institutions and societies | **REAL** | `institutions/*`, `civilization/*`, `evals/regression/test_gate11_institutions.py` | Minimal persisted society/institution/proposal lifecycle exists. |
| Model Foundry | **REAL** | `foundry/*`, `evals/regression/test_gate14_model_foundry.py` | Trace-to-training-example lineage and trust weighting implemented. |
| Validation suite | **REAL** | `validation/*`, `scripts/run_real_world_validation.py`, `evals/regression/test_gate15_validation.py` | Deterministic external-harness adapters and fixture tier are separated; live third-party connectors remain future hardening. |
| CI | **REAL** | `.github/workflows/ci.yml`, `Makefile`, `evals/regression/test_gate17_ci_master.py` | CI runs `make master-gate`. |

## Known Breakage / Risks

- **REAL after dependency install**: backend/frontend TypeScript checks and production builds pass.
- **REAL after escalation/local Postgres**: Postgres ledger tests passed with `AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco`.
- **REAL** migration path through Gate 1: backend TypeScript runner applied migrations 001-018 to local Postgres; Python check-only path points to the same migration directory; duplicate `015` numbering is resolved.
- **REAL** dispatch path: API dispatch now enqueues `workflow_tasks` and runs measured supported tasks via durable execution service. Unsupported task types fail closed.
- **BROKEN dependency hygiene**: `npm ci` reports 25 backend vulnerabilities and 8 frontend vulnerabilities; not remediated in Phase 0 pass.
