# Agentco Architecture

Status: **PARTIAL**.

Agentco is organized by dependency order:

1. Foundation: Substrate Runtime.
2. Foundation: Evidence Kernel and Source Independence.
3. Foundation: Durable Execution Fabric.
4. Foundation: Provenance and Attestation.
5. Foundation: Uncertainty Stack.
6. Core: Memory Kernel.
7. Core: Learning Kernel.
8. Core: Universal Ingestion.
9. Organizational: Agent and Skill Kernel.
10. Organizational: Governance, Constitutions, and Policy.
11. Organizational: Institutions and Societies.
12. Advanced: Simulation and World Lab.
13. Advanced: Self-Modification Kernel.
14. Advanced: Model Foundry.
15. Surface: Operator and Governance Console.

## Current Module Mapping

| Module | Layer | Status |
|---|---|---|
| `backend/src/services/audit-log.service.ts` | Substrate Runtime | **PARTIAL** |
| `backend/src/services/event-bus.service.ts` | Substrate Runtime | **PARTIAL** |
| `backend/src/db/migrations` | Substrate Runtime | **PARTIAL** |
| `calibration/*` | Evidence Kernel / Uncertainty Stack | **PARTIAL** |
| `reserve/*` | Evidence Kernel / Provenance seed | **PARTIAL** |
| `runtime/confidence`, `calibration/trust` | Uncertainty Stack | **PARTIAL** |
| `backend/src/services/memory-store.service.ts`, `runtime/memory`, `learning/memory_agent` | Memory Kernel | **PARTIAL** |
| `learning/*` | Learning Kernel | **PARTIAL** |
| `agents/*` | Agent and Skill Kernel | **PARTIAL** |
| `runtime/escalation`, `civilization/services/governance_service.py` | Governance and Policy | **PARTIAL** |
| `civilization/*` | Institutions and Societies | **PARTIAL** |
| `synthesis/*` | Learning/advanced research support | **PARTIAL** |
| `frontend/src/app/*` | Operator Console | **PARTIAL** |

## Canonical Schema Target

Phase 1 must add migrations for: `principals`, `constitutions`, `policies`, `workflow_intents`, `claims`, `evidence_artifacts`, `sources`, `resolutions`, `calibration_cells`, `action_attestations`, `override_cases`, `memory_events`, and `eval_runs`.
