# AgentCo Repository-Wide Re-Audit — 2026-07-07

Baseline: `AGENTCO_REPO_AUDIT.md` dated 2026-07-06. Branch audited: `audit/reaudit-2026-07`, based on `main` at `a0f207c`.

## 0. Delta Since 2026-07-06

| dimension | old score | new score | evidence for the change |
|---|---:|---:|---|
| Overall | 5.7 | 6.2 | Phase 1-6.5 merges present in `git log`; auth, V1 retirement, lockfile, and chain tests improved. Clean-clone default Python suite still fails. |
| Production | 4.2 | 4.8 | Staging compose now requires env vars (`docker-compose.staging.yml:11-13`, `:139-140`), but no hosted-ops proof and clean-clone suite fails. |
| Security | 4.8 | 6.1 | Route auth contract passes 157 routes; V1 high/critical fail-open closed (`agents/core/base_agent.py:117-122`). Raw error disclosure remains (`backend/src/server.ts:80-94`). |
| Architecture | 5.5 | 6.3 | Dead V1 department classes archived under `archive/agents_v1`; remaining LIVE V1 reachability documented ROUTINE (`docs/audit/V1_SEVERITY_REACHABILITY.md:3`). |
| Testing | 6.0 | 6.0 | Collection now passes with 552 tests; backend Jest passes. Default Python run fails `5 failed, 508 passed, 43 skipped, 1 error`, and Jest still uses `forceExit` (`backend/jest.config.ts:13-14`). |
| Documentation | 4.5 | 5.4 | Phase notes and archive status headers exist, but `make status` rewrites README status from `c26d4f6` to `ebe700f` in a clean clone. |
| Deployment | 3.8 | 4.6 | Python lockfile and CI install path exist (`requirements/README.md:3-19`, `.github/workflows/ci.yml:35-43`), but local/dev defaults and hosted deployment evidence remain weak. |

Original finding status:

| id | status | evidence |
|---|---|---|
| CRIT-001 | PARTIAL | BUILD_LEDGER documents V1 archive status, but clean-clone `make status` rewrites `README.md` status commit from `c26d4f6` to `ebe700f`. |
| CRIT-002 | PARTIAL | `python3.13 -m pytest --collect-only -q` passes with 552 collected; `python3.13 -m pytest -q` fails with 5 failures and 1 error and dirties generated reports. |
| CRIT-003 | CLOSED-VERIFIED | V1 `run()` writes required audit/override then raises `GovernanceUnavailableError` for high/critical (`agents/core/base_agent.py:117-122`). Proof tests passed: `agents/tests/test_base_agent.py` 7 passed. |
| CRIT-004 | CLOSED-VERIFIED | Route auth defaults protected unless route config is public (`backend/src/server.ts:52-77`); route contract passed 157/157. |
| HIGH-001 | CLOSED-VERIFIED | `scripts/smoke_frontend_auth.sh` passed frontend pages and authenticated backend dependencies. |
| HIGH-002 | PARTIAL | Smoke covers agents/audit/autonomy API dependencies, but authenticated invalid IDs still surface 500s in route-auth run, and smoke does not execute browser JS. |
| HIGH-003 | CLOSED-VERIFIED | CI now installs from `requirements/requirements.lock.txt` and verifies pytest collection in master gate (`.github/workflows/ci.yml:135-155`). |
| HIGH-004 | PARTIAL | Hardcoded `/Users/Zet/Agentco` remains in scripts/docs/tests; the originally named runtime path is improved, but repo portability is not closed. Evidence: `rg "/Users/Zet/Agentco"`. |
| HIGH-005 | PARTIAL | Durable audit writer exists (`runtime/base_agent/audit_writer.py:46-157`) and V2 requires ACK for high/critical (`runtime/base_agent/base_agent_v2.py:312-314`), but the live durable audit Python test failed before audit due confidence gating. |
| HIGH-006 | PARTIAL | Staging defaults replaced with `${VAR:?}` (`docker-compose.staging.yml:11-13`, `:139-140`), but dev compose/CI still use `agentco:password` local defaults. |
| HIGH-007 | PARTIAL | `scripts/verify_migrations_native.py` exists, but this run returned `{"core_schema_status":"missing","postgres_connectivity":"blocked","success":false}`. |
| HIGH-008 | PARTIAL | Disabled/archived systems are more honestly marked (`archive/agents_v1`, `docs/audit/02_agents.md`), but unsupported migrations and disabled route files remain. |
| MED-001 | CLOSED-VERIFIED | Lockfile exists and regeneration command is documented (`requirements/requirements.lock.txt`, `requirements/README.md:10-19`). |
| MED-002 | PARTIAL | CI secret scan exists (`.github/workflows/ci.yml:10-27`) but excludes markdown, docs, reports, and tests. |
| MED-003 | OPEN | Clean-clone verification dirtied README, eval acceptance files, and reports after required commands. |
| MED-004 | OPEN | Central error handler returns `error.message` (`backend/src/server.ts:80-94`); route-auth run logged raw Postgres UUID parse errors. |
| MED-005 | PARTIAL | Backend Jest reports `5 todo`; `backend/tests/specialist-integration.test.ts:239-243`. |
| MED-006 | PARTIAL | Evidence/provenance systems exist, but default tests still rely on generated local artifacts and optional external services. |
| LOW-001 | PARTIAL | More root make targets and lockfile docs exist, but `make status` is not clean/idempotent. |
| LOW-002 | PARTIAL | V1/V2 naming is better documented, but archived compatibility package names remain as stubs. |
| LOW-003 | OPEN | Frontend smoke checks pages/API availability only; no browser-rendered UX audit was performed. |

## 1. Executive Summary

The remediation materially improved security posture and honesty around V1 agents, but the repository is not yet production-ready. The most important verified improvements are route auth, V1 high/critical fail-closed behavior, Python dependency locking, staging secret requirements, dead V1 archive movement, and cross-writer decision-log chain verification.

The most important negative result is the clean-clone credibility test: collection passes, backend and frontend typechecks pass, backend Jest passes, but the default Python suite fails and the verification run modifies generated artifacts. Production readiness remains capped below 5 because there is still no hosted-ops evidence.

## 2. Overall Repo Health Score

New score: 6.2/10. This is better than the 2026-07-06 score because several critical security and governance claims are now backed by tests. It is not higher because the default suite does not pass in a clean clone and operational proof is still local-only.

## 3. Production Readiness Score

New score: 4.8/10. Local runnability is improved, but hosted operations, incident response, deploy rollback, real secret management, and clean default verification remain insufficient.

## 4. Security Readiness Score

New score: 6.1/10. The route auth model now defaults protected and is contract-tested. V1 high/critical execution no longer fails open. Residual issues: raw error disclosure, broad secret-scan exclusions, local default credentials, and advisory legacy hash compatibility.

## 5. Architecture Readiness Score

New score: 6.3/10. The V1 retirement work removed a large amount of active-looking dead class inventory. Remaining architecture risk is concentrated in live V1 specialist adapters, V2 audit/approval semantics, disabled/unsupported systems, and mixed Python/TypeScript governance paths.

## 6. Testing Readiness Score

New score: 6.0/10. Collection, backend Jest, targeted route auth, chain, and smoke checks are much stronger. The score does not increase because `python3.13 -m pytest -q` fails in a clean clone and Jest still force-exits due open handles.

## 7. Documentation Readiness Score

New score: 5.4/10. Audit notes are much more precise, archive status is explicit, and lockfile regeneration is documented. However, generated README status is stale until `make status`, and old docs still contain hardcoded local paths, defaults, and aspirational TODOs.

## 8. Deployment Readiness Score

New score: 4.6/10. Staging compose fails loudly for missing secrets and CI uses the Python lockfile. Deployment remains below production-grade because the audit did not find hosted environment evidence, real secret rotation proof, or clean release-gate evidence in a fresh clone.

## 9. Repo Inventory

Inventory remains a mixed Python/TypeScript/Next/Postgres/Kafka runtime. New notable inventory since baseline: `archive/agents_v1`, `requirements/requirements.lock.txt`, `scripts/smoke_frontend_auth.sh`, route-auth contract tests, cross-writer audit chain tests, and Phase 6/6.5 audit docs.

## 10. Top-Level Directory Map

Key active directories: `agents`, `backend`, `runtime`, `calibration`, `learning`, `synthesis`, `frontend`, `scripts`, `requirements`, `docs`, `tests`, `evals`. Key archived directory: `archive/agents_v1`.

## 11. System Capability Map

Verified capabilities: backend build, frontend typecheck, route-auth protection, decision-log cross-writer verification, V1 high/critical block behavior, frontend auth smoke. Partially verified: V2 durable audit, migration state, autonomy UI behavior. Not verified: hosted deployment, live Kafka full path, browser JS execution, production observability.

## 12. What The Repo Claims vs What Exists

Claims are more honest than baseline for V1 agents and approval gating. The repo still overstates end-to-end cleanliness when default pytest fails and generated verification artifacts dirty the tree. Frontend smoke proves API reachability with headers, not user-visible browser correctness.

## 13. Critical Findings

CRIT-001 is partial: capability honesty improved, but generated status remains stale. CRIT-002 is partial: collection is fixed but the default suite still fails. CRIT-003 is closed: V1 high/critical no longer executes. CRIT-004 is closed for the tested route matrix.

New critical finding: none. The clean-clone Python failure is severe but not new enough to classify above the original CI/testability critical item.

## 14. High Severity Findings

1. Clean-clone default Python suite fails: `5 failed, 508 passed, 43 skipped, 1 error`.
2. V2 audit fail-closed path still has an unavoidable lost-ack ambiguity: if Postgres commits but the client loses the acknowledgement, callers see `AuditUnavailableError`; retry semantics are not idempotent.
3. Migration verification could not be independently demonstrated without a live core schema.
4. Staging secrets improved, but non-staging defaults remain broad.
5. Backend route auth is strong at the hook level, but authenticated invalid input can still hit raw 500s.

## 15. Medium Severity Findings

1. Jest requires `forceExit` (`backend/jest.config.ts:13-14`).
2. Secret scan excludes large text surfaces (`.github/workflows/ci.yml:24`).
3. Generated eval/report artifacts are modified by verification.
4. Belief read-only enforcement blocks normal assignment but is bypassable via deliberate Python object mutation.
5. Legacy decision-log hash compatibility accepts multiple serialization candidates per row instead of binding an explicit version tag in the row.

## 16. Low Severity Findings

1. Documentation still contains hardcoded local paths.
2. Old aspirational docs remain noisy.
3. Frontend UX remains under-audited.

## 17. Placeholder / Mock / Fake-System Findings

Backend Jest still reports 5 todo tests in `backend/tests/specialist-integration.test.ts:239-243`. Some docs still claim no TODO-only gaps while historical plans contain many TODO markers.

## 18. Incomplete / Underbuilt Systems

Remaining incomplete systems include browser-verified frontend behavior, hosted deployment, migration live verification in this environment, V2 specialist migration, and production-grade audit acknowledgement/idempotency.

## 19. Logic Inconsistencies

The clean-clone Python failures include confidence-gate side effects causing tests intended to exercise durable audit to block before audit. That is a test design/runtime contract mismatch. Route auth also tests authenticated bad IDs returning 500, which is protected but not a healthy API contract.

## 20. Dead Code and Unused Code

Dead V1 department classes were moved to `archive/agents_v1`. A sweep for archived V1 imports found only archive-status docs/package stubs and V2 imports, not live imports of archived classes.

## 21. Security Risks

Main remaining security risks are raw error disclosure, broad secret scan exclusions, local default credentials in dev/CI paths, advisory legacy chain hash versions, and no hosted evidence for real secret posture.

## 22. Architecture Risks

The architecture is cleaner but still split across TS route services, Python V1 specialists, Python V2 agents, and calibration/firewall modules. The live V1 specialist path is ROUTINE rather than urgent because it bypasses severity/governance, but this also means V1 specialists are not V2-durable yet.

## 23. Backend/API Findings

Route auth: verified by `npm test -- route-auth-contract.test.ts --runInBand`, 157 passed. Public route is explicitly configured for `/health`; unclassified routes default protected. Raw error disclosure remains in `backend/src/server.ts:80-94`.

## 24. Frontend/Dashboard Findings

`scripts/smoke_frontend_auth.sh` passed. It proves pages load and backend API dependencies require/provide auth headers. It does not execute browser JavaScript or verify rendered dashboard correctness.

## 25. Agent/AI/Autonomy Findings

V1 high/critical block behavior is verified. Phase 6.5 shows 18/18 LIVE V1 agents cannot emit high/critical through the live loop (`docs/audit/V1_SEVERITY_REACHABILITY.md:3`). Remaining work is routine V2 migration for audit durability.

## 26. Governance/Memory/Provenance Findings

Decision-log chain interleave test passed. Belief firewall remains a Python-level convention plus transition API; deliberate mutation can bypass the property setter. Production code search did not find normal use of those bypass patterns.

## 27. Data/Schema Findings

Chain verification now recomputes row hashes and accepts historical seams. Migration verification against live Postgres was blocked in this audit environment. Default DSN logic still permits local dev fallback (`backend/src/db/dsn.ts:26-34`).

## 28. Testing and Eval Gaps

Required verification results:

| command | result |
|---|---|
| clean clone | passed |
| clean clone `pytest --collect-only -q` | `552 tests collected in 5.17s` |
| clean clone `pytest -q` | failed: `5 failed, 508 passed, 43 skipped, 1 error` |
| clean clone backend `npm ci` | passed, 0 vulnerabilities |
| clean clone backend `npm run build` | passed |
| clean clone backend Jest | passed: `96 passed, 3 skipped`, `600 passed`, `5 todo`; force-exited |
| clean clone frontend `npm ci` | passed, 0 vulnerabilities |
| clean clone frontend `npx tsc --noEmit` | passed |
| clean clone `make status` | exited 0 but rewrote README status |
| `scripts/smoke_frontend_auth.sh` | passed |
| chain interleave test | passed: 3/3 |
| route-auth contract suite | passed: 157/157 |
| Phase 6.5 proof test | passed: 1/1 |

## 29. CI/CD and Deployment Findings

CI uses the Python lockfile and verifies pytest collection. It still uses local Postgres service credentials (`password`) appropriate for CI but not proof of production secrets. The master gate does not prove the same as full default pytest.

## 30. Dependency and Supply Chain Findings

Python dependencies are now pinned by `requirements/requirements.lock.txt`. Backend and frontend `npm ci` reported 0 vulnerabilities in this run. Secret scanning is still a custom grep with major exclusions.

## 31. Documentation Gaps

The repo has much better remediation docs, but old docs remain aspirational and local-path-heavy. README status generation is not current in the checked-in tree.

## 32. File-by-File Findings

- `agents/core/base_agent.py:117-122`: V1 high/critical disabled; verified.
- `backend/src/server.ts:52-77`: global auth hook; verified.
- `backend/src/server.ts:80-94`: raw error response remains.
- `backend/src/services/audit-log.service.ts:164-192`: multi-version hash candidate acceptance.
- `runtime/base_agent/audit_writer.py:109-151`: Python canonical writer.
- `runtime/base_agent/base_agent_v2.py:312-314`, `:375-398`: high/critical audit ACK requirement.
- `calibration/firewall/firewall.py:61-74`: read-only property setter plus internal `object.__setattr__`.
- `docker-compose.staging.yml:11-13`, `:139-140`: required env vars.
- `.github/workflows/ci.yml:135-155`: lockfile/master gate path.

## 33. Recommended Fix Plan

1. Make the clean-clone default Python suite pass without side effects.
2. Remove raw error disclosure and convert invalid UUID/path IDs to 400.
3. Make decision-log serialization version explicit and tamper-evident for new rows.
4. Resolve Jest open handles and remove `forceExit`.
5. Migrate the 18 LIVE V1 specialists to V2 in the Phase 6.5 batch order.

## 34. 30-Day Remediation Roadmap

Focus on test credibility: default pytest green, no generated diffs, no raw 500s, no `forceExit`. Add browser-level dashboard smoke after API smoke.

## 35. 60-Day Remediation Roadmap

Complete V2 specialist migration and add idempotent audit ACK semantics. Require explicit DB DSNs outside local dev and make migration verification a first-class release gate.

## 36. 90-Day Remediation Roadmap

Produce hosted staging evidence: deploy logs, secret provenance, monitoring, backup/restore drill, incident rollback proof, and browser E2E against the deployed environment.

## 37. Questions for the Maintainer

1. Is the default Python suite intended to require Kafka, or should those tests be opt-in live-service tests?
2. Should `make status` update committed README status in CI, or should it be a check-only gate?
3. Are legacy decision-log serialization candidates a temporary compatibility layer with a removal date?

## 38. Appendix: Commands Run

Key commands run:

```text
git fetch origin
git log --oneline --decorate --max-count=50
git clone /Users/Zet/Agentco /private/tmp/agentco-reaudit-clean-2026-07
python3.13 -m pytest --collect-only -q
python3.13 -m pytest -q
npm ci
npm run build
npm test -- --runInBand
npm ci
npx tsc --noEmit
make status
scripts/smoke_frontend_auth.sh
npm test -- audit-chain-cross-writer.test.ts --runInBand
npm test -- route-auth-contract.test.ts --runInBand
python3.13 -m pytest agents/tests/test_phase65_v1_severity_reachability.py -q
python3.13 -m pytest agents/tests/test_base_agent.py -q
python3.13 scripts/verify_migrations_native.py
```

## 39. Appendix: Search Terms Used

Searches included: `route-auth`, `decision_log`, `interleave`, `GovernanceUnavailableError`, `Belief`, `archive/agents_v1`, `/Users/Zet/Agentco`, `password`, `TODO`, `test.skip`, and V1 archived package import patterns.

## 40. Appendix: Files Audited

Audited representative files: `AGENTCO_REPO_AUDIT.md`, `README.md`, `BUILD_LEDGER.yaml`, `.github/workflows/ci.yml`, `docker-compose.staging.yml`, `requirements/README.md`, `requirements/requirements.lock.txt`, `backend/src/server.ts`, `backend/src/services/audit-log.service.ts`, `runtime/base_agent/audit_writer.py`, `runtime/base_agent/base_agent_v2.py`, `agents/core/base_agent.py`, `calibration/firewall/firewall.py`, `docs/audit/V1_SEVERITY_REACHABILITY.md`, `archive/agents_v1/README.md`, and targeted test files.

## 41. Remediation-Introduced Risk

Versioned decision-log verification: `verifyChainIntegrity()` recomputes historical entry hashes and accepts multiple candidate serializers (`backend/src/services/audit-log.service.ts:164-192`, `:325-348`). This verified both seams (`25e1919`, `821da70`) in tests. Risk: the version is not stored as a tamper-evident row field; acceptance is inferred by matching any legacy candidate. A buggy writer can continue producing a legacy-valid hash and still pass verification. This is backward-compatible, not a strongly version-bound protocol.

Route auth layer: the hook is global and registered before routes (`backend/src/server.ts:52-77`), and unclassified routes default protected. The contract suite includes `/ws/events` and unclassified route coverage. Residual risk: case/trailing-slash/HEAD behavior is not called out in the report output, and authenticated invalid parameters can reach raw 500s.

AuditWriter fail-closed path: V2 high/critical writes audit before returning (`runtime/base_agent/base_agent_v2.py:312-314`) and raises on missing ACK (`:375-398`). If the DB commit succeeds and the connection drops before the ACK reaches Python, the caller sees failure despite a committed audit row. There is no idempotency key tying retry to the original attempted action, so double-audit or lost-ack ambiguity remains.

Belief read-only property: direct assignment raises `AttributeError` (`calibration/firewall/firewall.py:65-69`). A local probe showed `__dict__`, `object.__setattr__`, copy-then-mutate, and pickle-then-mutate can set `_validation_status` to `reality_validated`. This is deliberate-only bypass in ordinary Python, not true enforcement. Production code search did not find normal use of those bypasses.

Archive sweep: no live imports of archived V1 department classes were found outside archive-status docs/package stubs and V2 tests. The sweep command was `rg` for archived package names excluding `archive/**`.
