# Validation Plan

Status: **PARTIAL**.

Validation uses evidence-quality labels:

- **EXTERNAL-VALIDATED**: external benchmark or independent ground truth.
- **REAL**: real system behavior against real dependencies or externally sourced evidence.
- **FIXTURE**: deterministic repo-authored fixtures.
- **simulated**: simulation/world-lab outputs, quarantined by default.
- **unresolved**: claims not yet resolved.

## Release-Gate Target

Phase 15 will add a single validation command under `validation/` and `scripts/run_real_world_validation.py` that runs:

- digital-workflow benchmark tasks inspired by WebArena and TheAgentCompany,
- unsafe-action leakage tasks inspired by Agent-SafetyBench,
- Agentco's claim-resolution benchmark using independent evidence,
- internal fixture tiers for deterministic regression only.

Until Phase 15 passes, fixture tests are useful engineering checks but are not top-line proof of calibrated real-world competence.
