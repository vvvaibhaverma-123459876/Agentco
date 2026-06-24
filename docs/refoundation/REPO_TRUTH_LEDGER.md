# Repo Truth Ledger

| Claim | Status | Proof | Notes |
|---|---|---|---|
| Agentco's present-day product promise is evidence-governed control plane, not autonomous company | **REAL** | `README.md`, `AGENTCO_TRUE_NORTH.md` | Older docs remain legacy references until rewritten. |
| Python calibration/runtime/learning/synthesis/regression no-infra slice passes locally | **FIXTURE** | `make smoke-python` excluding DB-backed ledger tests | Does not prove external validation. |
| Frontend import break for `@/lib/api` is fixed | **PARTIAL** | `frontend/src/lib/api.ts` | TS build not verified due missing dependencies. |
| Frontend write calls can attach API key | **PARTIAL** | `frontend/src/lib/api.ts` | Uses `NEXT_PUBLIC_AGENTCO_API_KEY` for non-GET requests. |
| Backend can require write API key | **PARTIAL** | `backend/src/server.ts` | Enforced only when `AGENTCO_API_KEY` is set. |
| Backend and frontend typecheck/build pass | **REAL** | `./node_modules/.bin/tsc --noEmit`; `npm run build` in both packages | Requires dependencies installed by `npm ci`. |
| Backend migration numeric prefixes are unique | **REAL** | `scripts/gate0_check.py` | Lifecycle hardening is migration `017`. |
| Canonical refoundation schema exists with rollback contract | **REAL** | `backend/src/db/migrations/018_refoundation_canonical_schema.sql`, `backend/src/db/rollbacks/018_refoundation_canonical_schema.down.sql`, `evals/regression/test_canonical_schema_gate1.py` | Migration applied successfully to local Postgres. |
| Gate 2 source independence rejects circular verification | **REAL** | `calibration/evidence/evidence_kernel.py`, `evals/regression/test_evidence_kernel_gate2.py` | Same-source and declared derivative resolvers are mechanically rejected. |
| Simulation and fixture evidence cannot promote claims | **REAL** | `evals/regression/test_evidence_kernel_gate2.py` | Promotion gate blocks `FIXTURE`, `simulated`, and unresolved evidence. |
| Durable execution no longer uses in-memory task queue | **REAL** | `backend/src/services/durable-execution.service.ts`, `backend/src/db/migrations/019_durable_execution.sql`, `evals/regression/test_gate3_durable_execution.py` | API dispatch persists workflow state and unsupported tasks fail closed. |
| Action attestations verify externally and tamper tests fail | **REAL** | `provenance/attestation.py`, `evals/regression/test_gate4_provenance_attestation.py` | Ed25519 verification uses public-key material and transparency inclusion. |
| Uncertainty gates can abstain and expose metrics | **REAL** | `calibration/uncertainty/uncertainty_stack.py`, `evals/regression/test_gate5_uncertainty_stack.py` | Computes Brier/log/ECE/coverage and abstention decisions. |
| Memory Kernel enforces provenance and immutable/mutable split | **REAL** | `memory_kernel/memory_kernel.py`, `evals/regression/test_gate6_memory_kernel.py` | Experiential memories require provenance; operational memory is separate and mutable. |
| Universal ingestion routes text, web, and code to untrusted claims | **REAL** | `ingestion/*`, `evals/regression/test_gate7_ingestion.py` | Claims enter Evidence Kernel as untrusted and carry source provenance. |
| Autonomous learning loop emits governed adaptation proposals | **REAL** | `learning/cycle.py`, `evals/regression/test_gate8_learning_loop.py` | Observe/extract/evaluate/experiment/learn/adapt/govern path writes memory and does not auto-apply. |
| Agent routing is trust weighted and can propose spawn/demotion | **REAL** | `agents/registry.py`, `evals/regression/test_gate9_agent_kernel.py` | Best trusted agent is selected; unmet capability emits governance proposal; poor performance demotes. |
| Policy engine mechanically blocks high-risk and protected-surface changes | **REAL** | `governance/policy.py`, `evals/regression/test_gate10_governance_policy.py` | Protected Evidence Kernel surface is denied. |
| Institutions and societies persist proposal lifecycle | **REAL** | `institutions/society.py`, `evals/regression/test_gate11_institutions.py` | Agents belong to institutions; structural change routes through approval/rejection. |
| Simulation remains quarantined until external validation | **REAL** | `simulation/world_lab.py`, `evals/regression/test_gate12_simulation.py` | Simulated evidence cannot promote; external evidence can. |
| Self-modification blocks protected surfaces and failed tests | **REAL** | `self_modification/kernel.py`, `evals/regression/test_gate13_self_modification.py` | Safe changes require rollback and governance. |
| Model Foundry preserves lineage and calibration weight | **REAL** | `foundry/traces.py`, `evals/regression/test_gate14_model_foundry.py` | Trace-to-training-example conversion includes claim/evidence/action lineage and trust weight. |
| Validation suite produces evidence-quality-labelled release reports | **REAL** | `validation/suite.py`, `scripts/run_real_world_validation.py`, `evals/regression/test_gate15_validation.py`, `validation/reports/validation_report.json` | Deterministic external-harness adapters and fixture tier are separated; live third-party benchmark runners remain future hardening. |
| Operator console exposes validation and governance surfaces | **REAL** | `frontend/src/app/validation/page.tsx`, `frontend/src/app/governance/page.tsx`, `backend/src/routes/governance.routes.ts`, `evals/regression/test_gate16_operator_console.py` | Includes validation labels and why-allowed API shape for action attestations. |
| CI enforces full master gate | **REAL** | `.github/workflows/ci.yml`, `Makefile`, `evals/regression/test_gate17_ci_master.py` | CI runs `make master-gate`; local run passed. |
