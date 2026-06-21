# Production Hardening Plan

## What Exists

- Calibration ledger with immutable pre-registration fields and write-once resolution fields.
- Partial resolution independence checks for canonical source URLs and producer/resolver separation.
- Reserve scoring and Proof-of-Calibration credentials in Python, including deterministic scoring and Ed25519 authorship when issuer keys are configured.
- Backend API routes for agents, credentials, overrides, audit, and governed entities.
- Institution-oriented governance services and tests. The current working kernel is Institution -> Department -> Agent. Society and Civilization tables/services exist in parts of the repo, but they are not a complete production civilization layer.
- Minimal API-key auth and role/scope checks in the backend.
- Research and acceptance artifacts under `evals/`.

## What Changed In This Pass

- Added `calibration/resolution/independence_engine.py` with canonical URL, normalized domain, content hash, source fingerprint, resolver identity, resolver type, producer/resolver conflict, internal-source, evidence hash, and dispute-ready verdict metadata.
- Wired `ResolutionService.resolve()` to require resolver identity on the production path and attach independence verdict/evidence snapshot metadata to resolved records.
- Added `resolution_evidence_snapshots` migration for append-only evidence metadata.
- Added DB-backed persistence of resolution evidence snapshots when `PredictionLedger.persist_resolution()` is used.
- Canonicalized the backend credential boundary so it reads stored Python Reserve credentials from `calibration_credentials` instead of issuing a separate TypeScript/HMAC credential.
- Added tests for resolution independence adversarial cases and backend credential canonicalization.

## What Remains Future Work

- Durable task dispatch is still not completed in this pass; backend dispatch still needs a DB-backed task lifecycle and worker.
- Full service-key identity parsing and route-level scope enforcement should replace the role-header compatibility model.
- Credential issuance from the backend should be an explicit Python Reserve command/service boundary if automatic issuance is required.
- Resolution evidence snapshot persistence should be added to clean-clone migration verification and integration tests against Postgres.
- Institution controls need continued hardening around budget enforcement, review timeout sweep deployment, membership lifecycle, and department governance.
- Repo hygiene should continue separating core runtime from research artifacts.

## Explicit Non-Claims

- Agentco is not a full autonomous company.
- Agentco is not a production-grade civilization layer.
- Agentco does not yet provide complete RBAC, OAuth, service identity rotation, resolver key rotation, or admin audit coverage.
- Agentco does not yet have production-grade durable agent execution.
- Current strengthened calibration proves better resolution independence metadata and canonical credential boundaries, not full trustlessness.
