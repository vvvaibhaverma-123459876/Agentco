# Production Readiness

## Product-Ready Oriented Capabilities

- Resolution independence has deterministic checks and Postgres-backed append-only evidence snapshots.
- Canonical Proof-of-Calibration issuance runs through Python Reserve.
- Backend credential routes no longer issue independent TypeScript/HMAC credentials as primary artifacts.
- Task dispatch is durable at the API and database lifecycle level.
- Scoped service-key identity foundations protect credential, task, governance, and override mutation paths.
- Institution kernel has partial lifecycle hardening for memberships, review timeouts, and reputation floors.
- Epistemic foundation models claims, evidence, validation rings, validation policies, and promotion decisions.
- Dispute/ruling/precedent foundations exist in-memory.
- Jurisdiction authority-check foundation exists.
- Clean-clone migration order was verified on a scratch Postgres database.

## Not Product-Ready

- Durable worker execution is still an explicit placeholder and does not invoke the real Python runtime.
- Credential authorship verification is not fully performed by the backend.
- OAuth, key rotation, and persistent admin security audit are not implemented.
- Institution creation budget, emergency shutdown enforcement, and department governance are incomplete.
- Epistemic DB services, APIs, appeals, and full ruling integration are incomplete.
- Authority DB services, APIs, and governance integration are incomplete.
- Society and civilization layers are not production-grade.
- Frontend was not verified in this pass.
- The full repository test suite was not run in this pass.

## Local Verification

```bash
python3 -m pytest tests/test_resolution_independence_engine.py tests/integration/test_resolution_evidence_snapshots.py reserve/tests/test_canonical_credential_issuer_service.py tests/civilization/test_institution_kernel_lifecycle_services.py tests/test_epistemic_engine_foundation.py tests/test_epistemic_disputes_and_precedent.py tests/test_jurisdiction_authority.py
python3 -m pytest reserve/tests/test_proof_of_calibration.py reserve/tests/test_independent_recomputation.py reserve/tests/test_tamper_evidence.py calibration/tests/test_ledger_immutability.py
cd backend && npm test -- service-identity.test.ts security.test.ts rbac.test.ts credential-canonical.test.ts credential-routes.test.ts task-dispatch.test.ts
cd backend && npm run build
python3 -m json.tool evals/acceptance/latest_core_acceptance.json >/dev/null
DATABASE_URL=<scratch-postgres-dsn> RESOLUTION_SERVICE_PASSWORD=resolution-service-dev-password python3 backend/src/db/run_migrations.py
```

## Allowed Claims

- Verifiable calibration improved.
- Resolution independence has append-only evidence snapshots.
- Canonical credentials issue through Python Reserve.
- Task dispatch is durable at lifecycle level.
- Scoped service identity foundations exist.
- Institution kernel is partially hardened.
- Epistemic engine foundation exists.
- Dispute/precedent foundation exists.
- Jurisdiction authority-check foundation exists.

## Forbidden Claims

- Production-grade calibration.
- Production-grade civilization.
- Full autonomous company.
- Full trustless credential infrastructure.
- Real autonomous task execution through the durable worker.
- Complete OAuth/RBAC/key-rotation security.
- Complete epistemic court/dispute system.
- Complete authority/jurisdiction governance system.

## Current Risk Level

Medium-high for production deployment. Core calibration trust hardening has improved, but worker execution, full security lifecycle, dispute/authority systems, and operational verification still need completion before production-grade claims.
