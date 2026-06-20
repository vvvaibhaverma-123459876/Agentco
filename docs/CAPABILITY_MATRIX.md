# Capability Matrix

| Capability | Status | Evidence | Notes |
|---|---|---|---|
| Prediction ledger | Shipped | `calibration/ledger/`, tests in `calibration/tests/` and `evals/regression/` | Current baseline Python run reached these tests successfully. |
| Calibration scoring | Shipped | `calibration/scoring/`, `reserve/scoring/`, regression tests | Calibration is the executable foundation. |
| Trust scoring | Shipped | `calibration/trust/`, `tests/test_trust_monotonicity.py` | Trust must be derived from resolved calibration evidence. |
| Proof-of-Calibration credentials | Shipped | `reserve/credentials/`, `reserve/tests/test_proof_of_calibration.py` | Credentials are recomputable and covered by reserve tests. |
| Audit trails / hash-chain primitives | Partially Implemented | `backend/src/services/audit-log.service.ts`, `reserve/chain/` | Backend integration tests require Postgres at baseline. |
| Resolution source independence | Partially Implemented | `calibration/resolution/source_independence.py` | Phase 1 will harden adversarial invariants. |
| Institution Kernel | Partially Implemented | `civilization/`, `tests/civilization/` | Institution -> Department -> Agent exists; hardening remains. |
| Governed API boundaries | Partially Implemented | `backend/src/routes/` | Current API is not yet a full governed institution/civilization API. |
| RBAC / scoped service identity | Experimental | `backend/security.ts`, `backend/tests/security.test.ts` | Minimal controls exist; production RBAC is future Phase 4 work. |
| Frontend dashboard | Experimental | `frontend/src/app/` | Current pages are operational dashboards, not a civilization OS. |
| Society layer | Future | Not present as production model/services/tests | Phase 5 target. |
| Jurisdiction engine | Future | Not present as production model/services/tests | Phase 6 target. |
| Dispute judiciary | Future | Not present as production model/services/tests | Phase 7 target. |
| Institutional economy | Future | Not present as production model/services/tests | Phase 8 target. |
| Civilization constitution and law registry | Future | Not present as production model/services/tests | Phase 9 target. |
| Civilizational memory and precedent system | Future | Not present as production model/services/tests | Phase 10 target. |
| "Fully autonomous company" positioning | Historical / Deprecated | Historical README/docs language | Not a shipped production claim. |
| "29 AI employees" positioning | Historical / Deprecated | Historical README/docs language | Agent files/prompts exist, but this is not a shipped autonomous company claim. |
| "Civilization OS already shipped" positioning | Historical / Deprecated | Historical README/docs language | Future vision only until full gated tests pass. |
