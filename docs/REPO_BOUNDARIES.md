# Repo Boundaries

## Core Product Code

- `calibration/`: ledger, resolution, trust, scoring, and calibration mechanics.
- `reserve/`: deterministic scoring, Proof-of-Calibration credentials, recomputation, staking/oracle extensions.
- `backend/src/`: API routes, services, security, DB migrations.
- `civilization/services/` and `civilization/contracts/`: institution-kernel services and contracts.
- `tests/`, `reserve/tests/`, and `backend/tests/`: executable verification.

## Acceptance Traces

- `evals/acceptance/` contains demo traces and acceptance reports. These are evidence artifacts, not production runtime dependencies.

## Experiments

- `evals/experiments/` contains research experiments, frozen models, reports, and CSV/JSON outputs.
- These files are optional research evidence and are not required to run the core product.

## Frozen Datasets

- `data/external/` and experiment data directories may contain frozen or external datasets.
- They should not be imported by production runtime code unless explicitly documented.

## Generated Reports

- Markdown, CSV, JSON, and log reports under `evals/` are historical evidence unless a test explicitly consumes them.

## Production Install Boundary

Required:

- Python calibration/reserve code.
- Backend source and migrations.
- Tests relevant to calibration, reserve, backend, and institution kernel.

Optional:

- Research experiments.
- Historical reports.
- Large frozen datasets used only for evaluation.

## Future Work

- Move large research artifacts into `evals/research_archive/` or a separate repository if they continue to grow.
- Keep root README focused on verifiable calibration and current limitations.
