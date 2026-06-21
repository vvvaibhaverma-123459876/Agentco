# Agentco

Agentco is a calibration-first trust substrate for AI agents. It records what agents claimed, when they claimed it, how independent reality resolved it, and whether their confidence was earned.

The long-term ambition is civilization-grade AI infrastructure. The current product wedge is narrower: verifiable calibration, resolution independence metadata, recomputable trust credentials, and institution-kernel experiments.

## Current Product

- Immutable pre-registration ledger for predictions.
- Resolution service with time gates, producer/resolver separation, source-independence checks, and evidence snapshot metadata.
- Trust updates based on resolved outcomes, not raw stated confidence.
- Python Reserve scoring and Proof-of-Calibration credentials that can be recomputed from ledger rows.
- Backend API for agents, credentials, audit, overrides, and governed entities.
- Institution-kernel services for Institution -> Department -> Agent workflows.

## What This Is Not

- Not a full autonomous company.
- Not a production-grade civilization layer.
- Not fully trustless or decentralized.
- Not complete RBAC/OAuth/service-identity infrastructure.
- Not durable production agent execution yet; task dispatch still needs DB-backed lifecycle and workers.

## Quick Start

```bash
python3 -m pytest tests/test_resolution_independence_engine.py
cd backend && npm test -- credential-canonical.test.ts
cd backend && npm run build
```

For broader local checks:

```bash
make smoke
make test
```

Some integration tests require local Postgres, Kafka, and project migrations.

## Security Model

Current backend auth includes minimal API-key protection plus role/scope checks for selected routes. Production secret guards reject known development defaults. Scoped service keys, resolver identity keys, issuer identity keys, rotation, and full admin audit remain future work.

## Credentials

The canonical credential implementation lives in Python Reserve:

- `reserve/scoring/scoring_function.py`
- `reserve/credentials/proof_of_calibration.py`
- `reserve/tools/recompute_credential.py`

The backend credential endpoint reads stored canonical credentials from `calibration_credentials`; it does not issue a separate TypeScript/HMAC credential as the primary credential.

## Resolution Independence

The resolution path now records claim and resolution source fingerprints, resolver identity, resolver type, content hashes when supplied, evidence hashes, and an independence verdict. Same canonical URL, same content hash, internal sources, missing production resolver identity, and producer/resolver conflicts are rejected.

See `docs/RESOLUTION_INDEPENDENCE.md`.

## Institution Kernel

The current governance layer is best described as an institution kernel. It contains institution, department, agent membership, review, memory, governance, dispute, economy, jurisdiction, and society/civilization experiments, but the repo should not be read as a complete production civilization system.

See `docs/CIVILIZATION_INSTITUTION_KERNEL.md`.

## Documentation

- `docs/production_hardening_plan.md`
- `docs/RESOLUTION_INDEPENDENCE.md`
- `docs/CREDENTIAL_CANONICALIZATION.md`
- `docs/DURABLE_TASK_DISPATCH.md`
- `docs/CIVILIZATION_INSTITUTION_KERNEL.md`
- `docs/REPO_BOUNDARIES.md`
- `ROADMAP.md`

## Repo Boundaries

Core runtime code lives under `calibration/`, `reserve/`, `backend/src/`, and institution-kernel service directories. Research artifacts under `evals/experiments/` and external datasets are optional evidence, not production runtime dependencies.
