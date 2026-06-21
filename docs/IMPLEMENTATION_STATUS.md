# Implementation Status

## Current Implemented State

- Agentco is currently a calibration-first trust substrate with an immutable prediction ledger, resolution service, trust controller, Python Reserve scoring, and canonical Proof-of-Calibration credential storage.
- Resolution independence has a dedicated engine that evaluates canonical URLs, domains, content hashes, source fingerprints, resolver identity, resolver type, internal-source markers, producer/resolver conflict, and deterministic evidence hashes.
- `ResolutionService.resolve()` attaches independence verdicts and evidence snapshot payloads to resolved records.
- `resolution_evidence_snapshots` migration exists and is append-only.
- `PredictionLedger.persist_resolution()` now requires evidence snapshot metadata and persists the snapshot plus ledger update in one transaction.
- Backend credential reads are canonicalized around stored Python Reserve credentials; the backend no longer creates a primary TypeScript/HMAC credential.
- `scripts/issue_canonical_credential.py` issues and persists canonical Reserve credentials from Postgres ledger rows.
- Backend credential issue/verify routes exist and are scoped by the current role-header security model.
- Backend task dispatch now writes durable `agent_tasks` rows and reads task state from DB.
- A worker exists, but its execution mode is explicitly `durable_placeholder` until real Python runtime execution is wired.
- Backend security has scoped service-key identity foundations with wildcard scope checks and production fail-closed behavior. OAuth, key rotation, and persistent admin audit are not complete.
- Epistemic claim/evidence/validation/promotion/dispute foundations exist.
- Jurisdiction authority-check foundation exists.
- Civilization code is best described as an institution kernel with additional society/civilization experiments, not a production civilization layer.

## Current Verified Tests

- `python3 -m pytest tests/test_resolution_independence_engine.py` passed with 10 tests.
- `python3 -m pytest tests/test_resolution_independence_engine.py tests/integration/test_resolution_evidence_snapshots.py reserve/tests/test_canonical_credential_issuer_service.py` passed with 18 tests.
- `python3 -m pytest reserve/tests/test_proof_of_calibration.py reserve/tests/test_independent_recomputation.py reserve/tests/test_tamper_evidence.py calibration/tests/test_ledger_immutability.py` passed with 35 tests after adding the snapshot migration to legacy Postgres fixtures.
- `cd backend && npm test -- credential-canonical.test.ts` passed with 2 tests.
- `cd backend && npm test -- credential-canonical.test.ts credential-routes.test.ts` passed with 8 tests.
- `cd backend && npm test -- credential-canonical.test.ts credential-routes.test.ts task-dispatch.test.ts` passed with 13 tests.
- `cd backend && npm test -- service-identity.test.ts security.test.ts rbac.test.ts credential-canonical.test.ts credential-routes.test.ts task-dispatch.test.ts` passed with 31 tests.
- `python3 -m pytest tests/civilization/test_institution_kernel_lifecycle_services.py` passed with 3 tests.
- `python3 -m pytest tests/test_epistemic_engine_foundation.py` passed with 9 tests.
- `python3 -m pytest tests/test_epistemic_disputes_and_precedent.py tests/test_jurisdiction_authority.py` passed with 7 tests.
- `cd backend && npm run build` passed.
- `python3 -m py_compile calibration/resolution/independence_engine.py calibration/resolution/source_independence.py calibration/resolution/resolution_service.py calibration/ledger/prediction_ledger.py` passed.
- `DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco_migration_check RESOLUTION_SERVICE_PASSWORD=resolution-service-dev-password python3 backend/src/db/run_migrations.py` passed on a scratch database with all 35 migrations.

## Current Remaining Gaps

- Backend credential authorship verification checks signature presence but does not yet verify Ed25519 signatures with the public key.
- Durable task dispatch is implemented at API/service/migration level, but live worker integration with the real Python runtime is not complete.
- OAuth, key rotation, and persistent security audit remain future work.
- Institution-kernel controls and membership lifecycle remain partial.
- Epistemic claim/evidence/validation/promotion/dispute foundation exists; DB-backed services, APIs, appeals, and full ruling integration remain future work.
- Jurisdiction authority-check foundation exists; DB services, APIs, and governance integration remain future work.
- Society and civilization layers are not production-grade.
- Older historical docs may contain aspirational claims; README and current status docs are authoritative.
- Full repository test suite has not been run in this continuation.

## Product Claims Allowed

- Agentco improves verifiable calibration for AI agents.
- Agentco records pre-registered predictions and resolved outcomes.
- Agentco has stronger resolution independence checks than same-URL rejection alone.
- Agentco can expose stored canonical Proof-of-Calibration credentials from the Python Reserve path.
- Agentco can issue canonical Proof-of-Calibration credentials through a Python Reserve service boundary.
- Agentco can persist dispatched tasks durably and expose DB-backed task status.
- Agentco has scoped service-key identity foundations for sensitive backend routes.
- Agentco has partial institution-kernel membership lifecycle, timeout escalation, and reputation floor enforcement.
- Agentco has a minimal executable epistemic claim/evidence/validation/promotion/dispute foundation.
- Agentco has a minimal executable jurisdiction authority-check foundation.
- Agentco has an institution kernel with limitations.

## Product Claims Forbidden

- Do not claim production-grade calibration yet.
- Do not claim full trustlessness or decentralization.
- Do not claim durable production agent execution.
- Do not claim complete OAuth/RBAC/key-rotation security.
- Do not claim a full autonomous company.
- Do not claim a production-grade civilization layer.
- Do not claim Society or Civilization are complete unless the entities, services, and tests prove it.

## Next Phase Plan

1. Complete Phase B with Postgres-backed evidence snapshot tests and acceptance JSON updates.
2. Complete Phase C with a Python Reserve credential issuer boundary and backend issue/verify routes.
3. Implement Phase D durable task dispatch.
4. Implement Phase E scoped service identity.
5. Harden the institution kernel before adding broader society/civilization claims.

## Verification Commands

```bash
python3 -m pytest tests/test_resolution_independence_engine.py
AGENTCO_TEST_DATABASE_URL=<postgres-dsn> python3 -m pytest tests/integration/test_resolution_evidence_snapshots.py reserve/tests/test_canonical_credential_issuer_service.py
AGENTCO_TEST_DATABASE_URL=<postgres-dsn> python3 -m pytest reserve/tests/test_proof_of_calibration.py reserve/tests/test_independent_recomputation.py reserve/tests/test_tamper_evidence.py calibration/tests/test_ledger_immutability.py
cd backend && npm test -- credential-canonical.test.ts credential-routes.test.ts
cd backend && npm test -- task-dispatch.test.ts
cd backend && npm test -- service-identity.test.ts security.test.ts rbac.test.ts
python3 -m pytest tests/civilization/test_institution_kernel_lifecycle_services.py
python3 -m pytest tests/test_epistemic_engine_foundation.py
python3 -m pytest tests/test_epistemic_disputes_and_precedent.py tests/test_jurisdiction_authority.py
cd backend && npm run build
python3 -m py_compile calibration/resolution/independence_engine.py calibration/resolution/source_independence.py calibration/resolution/resolution_service.py calibration/ledger/prediction_ledger.py
DATABASE_URL=<scratch-postgres-dsn> RESOLUTION_SERVICE_PASSWORD=resolution-service-dev-password python3 backend/src/db/run_migrations.py
```
