# AgentCo Repository-Wide Audit

Date: 2026-07-06  
Repository: `https://github.com/vvvaibhaverma-123459876/Agentco`  
Local path audited: `/Users/Zet/Agentco`  
Branch at audit start: `main` tracking `origin/main`  
Audit mode: read-only except for this report and `AGENTCO_AUDIT_EXECUTIVE_SUMMARY.md`

## 1. Executive Summary

AgentCo is a serious local research/runtime codebase, not an empty scaffold. The backend type-checks, the frontend type-checks, many Postgres-backed services exist, the calibration ledger has meaningful tests, and recent repairs moved several previously broken systems closer to reality.

It is not production-grade. The repository is best classified as a **local-native, partially integrated research/runtime system with production-posture aspirations**. It contains real subsystems, but the repo also contains stale reports, disabled routes/migrations, import-time test failures, hardcoded local paths, broad unauthenticated reads, in-memory audit paths, partially wired frontend flows, archived eval theater, and documentation that conflicts with the current build ledger.

Most important diagnosis: AgentCo has moved from "architecture sketch" toward "working local slices", but its integration story is still brittle. The strongest capabilities are narrow verified slices. The weakest areas are product coherence, deployment operability, CI truthfulness, long-horizon autonomy evidence, and capability honesty across older docs/reports.

## 2. Overall Repo Health Score

**5.7 / 10**

The repo has substantial implemented code and many tests, but it is large, uneven, noisy, and hard for a new developer to reason about. The tracked repo has 1,519 files; the local working tree has 46,745 files because dependency/build/cache artifacts are present. There are multiple generations of architecture, reports, evals, and disabled code.

## 3. Production Readiness Score

**4.2 / 10**

Local-native operation is credible. Hosted production is not. Production evidence is local smoke evidence, not operated SLO/DR/backup/incident evidence. Docker Compose uses dev credentials and dev Vault mode. The deploy workflow is manual and assumes pre-existing Kubernetes/Helm secret setup.

## 4. Security Readiness Score

**4.8 / 10**

There are real security controls: secret scanning, production secret guards, URL safety code, API write key enforcement, DB immutability triggers, and key-hygiene tests. But GET endpoints are broadly public, local/staging compose uses weak credentials, V1 agent governance fails open, some audit paths are in-memory or best-effort, and several scripts expose hardcoded local DSNs/paths.

## 5. Architecture Readiness Score

**5.5 / 10**

The architecture has coherent vertical slices: identity, event log, resource ledger, evidence registry, prediction ledger, trust, memory, civilization coordination. The problem is architecture layering drift: V1 and V2 agents coexist, disabled route sets imply absent capabilities, Python and TypeScript implementations duplicate semantics, and historical docs over-describe systems no longer canonical.

## 6. Testing Readiness Score

**6.0 / 10**

The backend suite is broad and previously ran green after local DB repair. Focused Python subsets pass. However repository-wide pytest collection currently fails, CI is likely broken in `master-gate`, live/infra tests skip often, and several important paths are tested by smoke fixtures rather than true product journeys.

## 7. Documentation Readiness Score

**4.5 / 10**

README has become more honest than older docs, but docs conflict with each other. `README.md` says `68/71`; `docs/CURRENT_IMPLEMENTATION_REALITY.md` says `67/67`; `BUILD_LEDGER.yaml` says `68/71`. Many historical docs still claim completion or production readiness.

## 8. Deployment Readiness Score

**3.8 / 10**

There are Dockerfiles, Compose files, Helm templates, and a deploy workflow. They are not enough for safe independent operation. Staging compose has weak defaults and stale service versions. Deploy requires manually provisioned secrets and does not include migrations, rollback, backup restore, or observable SLO gates.

## 9. Repo Inventory

### Inventory Counts

| Metric | Count / Status |
|---|---:|
| Raw filesystem files | 46,745 |
| Tracked files (`git ls-files`) | 1,519 |
| Top tracked directories by file count | `backend` 423, `docs` 197, `evals` 180, `agents` 141, `scripts` 111, `audit_artifacts` 99 |
| Active backend SQL migrations | 113 |
| Unsupported/disabled migrations | 18 |
| Backend test files | 100 |
| Python/TS tests under `tests` + `evals` | 60 |
| Empty files | Mostly package `__init__.py`, cache/vendor placeholders, and empty audit jsonl artifacts |
| Large first-party data/artifacts | `data/external/bike_sharing/hour.csv`, large eval/result JSON/CSV files |
| Local generated/vendor trees | `backend/node_modules`, `frontend/node_modules`, `frontend/.next`, `backend/dist`, `__pycache__`, `.pytest_cache` |

### Extension Counts, Tracked Files

| Extension | Count |
|---|---:|
| `.py` | 496 |
| `.md` | 337 |
| `.ts` | 272 |
| `.sql` | 121 |
| `.json` | 112 |
| `.jsonl` | 40 |
| `.csv` | 38 |
| `.disabled` | 21 |
| `.tsx` | 17 |
| `.txt` | 15 |
| `.yaml` | 13 |
| `.sh` | 13 |
| `.yml` | 6 |

### Inventory Treatment

I accounted for all directories. I audited first-party source/config/docs/scripts/tests directly. I treated `node_modules`, `.next`, `dist`, `__pycache__`, `.pytest_cache`, and generated reports as inventory/risk artifacts rather than line-by-line first-party code, because they are generated or vendored. Their presence in the local tree is still a repo hygiene and reproducibility risk.

## 10. Top-Level Directory Map

| Path | Apparent Purpose | Audit Status |
|---|---|---|
| `.github/workflows` | CI and deploy workflows | Real, but CI has likely broken master gate and weak secret scan exclusions |
| `agentco_security` | Python env/secret guard | Small real utility |
| `agents` | V1/V2 department agents, prompts, tool registry | Mixed: real tool gate, V1 governance weak, V2 stronger |
| `archive` | Old eval regression theater | Historical, not current evidence |
| `audit_artifacts` | Prior audit outputs and validation artifacts | Evidence archive; many stale claims |
| `autonomy` | Older Python autonomy components | Partial; some hardcoded paths and abstract/scaffolded pieces |
| `backend` | Main Fastify/Postgres/Kafka TypeScript backend | Strongest runtime surface, broad tests |
| `calibration` | Prediction ledger, trust, scoring, firewall | Strong core, but duplicated semantics with backend/agents |
| `civilization` | Python governance/institution services | Partial/legacy relative to backend civilization services |
| `dashboard/src` | Separate calibration dashboard stub | Very small, disconnected from main frontend |
| `data/external/bike_sharing` | External dataset | Real dataset, provenance/versioning limited |
| `docs` | Architecture, status, production, history | Extensive but conflicting and stale |
| `evals` | Eval harnesses, experiments, benchmark reports | Mixed real and experimental/theater |
| `foundry` | Minimal package marker | Mostly empty/scaffold |
| `frontend` | Next.js UI | Builds/types, but several flows are partial or mismatched |
| `governance` | Small Python policy module | Thin, overshadowed by backend governance |
| `infrastructure` | Helm, Prometheus, Grafana, Kafka, Vault, OTel | Present, not production-complete |
| `ingestion` | Data ingestion/adapters | Partial |
| `institutions` | Minimal package marker | Scaffold |
| `learning` | Python learning agents | Partial; simulation-heavy |
| `memory_kernel` | Small memory kernel | Thin/legacy |
| `meta` | decision/failure notes | Documentation |
| `prompts` | Resume/system prompts | Operational prompt artifacts |
| `provenance` | Attestation helper | Real but not fully integrated |
| `reports/system_run/latest` | Generated verification outputs | Useful but mutable/stale risk |
| `reserve` | Proof-of-calibration credential/reserve | Meaningful tests; operator-run trust model |
| `results` | Generated experiment outputs | Evidence archive, not code |
| `runtime` | Python V2 agent runtime | Real safety gates, but audit is in-memory |
| `scripts` | Verification, demos, smoke, staging scripts | Useful but noisy, non-portable, some import-time tests |
| `self_modification` | Kernel stub | Mostly proposal/scaffold |
| `selfcoding` | Selfcoding sandbox/planner/resolver | Recently hardened; old reports stale |
| `simulation` | World lab | Simulation only |
| `synthesis` | Principle/synthesis agents | Small test-covered research layer |
| `tests` | Python integration/e2e/system tests | Broad but collection currently fails |
| `validation` | Validation reports/helpers | Mostly artifact/report |

## 11. System Capability Map

| Capability | Implemented | Wired | Tested | Verdict |
|---|---:|---:|---:|---|
| Backend Fastify API | Yes | Yes | Yes | Local-real |
| Postgres migrations | Yes | Yes | Partial | Real but drift-prone |
| Event log / audit log | Yes | Yes | Yes | Real, with some in-memory bypasses |
| Prediction ledger | Yes | Yes | Yes | Strong |
| Calibration scoring | Yes | Partially duplicated | Yes | Strong core, semantic divergence remains |
| Trust/memory promotion | Yes | Partial | Yes | Real in slices |
| V2 escalation gate | Yes | Yes in V2 | Yes | Real in-process |
| V1 agent governance | Yes | Yes for V1 agents | Weak | Fails open |
| Frontend dashboard | Yes | Partial | Type-check only | Underbuilt |
| Autonomy loop | Yes in backend slices | Partial | Many focused tests | Not proven as product loop |
| Self-improvement | Partial | Partial | Focused only | Not proven durable |
| Hosted production ops | No | No | No | Not production-ready |
| External real-world evidence intake | Partial | Partial | Limited | Requires live services |
| Governance/civilization | Partial | Partial | Focused tests | Architecture ahead of product |

## 12. What The Repo Claims vs What Exists

| Claim | Evidence | Reality |
|---|---|---|
| "Evidence-governed, calibration-driven AI civilization" | README lines 3-5 | Partially true for narrow local slices; not proven as a civilization/product |
| "68/71 verified" | README line 11; BUILD_LEDGER lines 1177-1183 | True in ledger, but conflicts with `CURRENT_IMPLEMENTATION_REALITY` line 5 |
| "All current build-ledger items verified" | `docs/CURRENT_IMPLEMENTATION_REALITY.md` lines 5 and 11 | Stale/contradictory |
| "Release gates passed" | README lines 13, 28-31 | Some gates pass; gates do not prove full capability |
| "Production posture passes" | README line 17 | Local posture only; hosted production is unproven |
| "Every decision is audited" | `agents/core/base_agent.py` docs and code | False for V1: audit exceptions swallowed |
| "High/critical actions pause" | `agents/core/base_agent.py` lines 108-112 | False for V1: request queued then output returned |
| "Frontend autonomy dashboard works" | frontend routes and API client | Partial; health endpoint is wrong and several routes are not backed |

## 13. Critical Findings

### Finding ID: CRIT-001
Severity: Critical  
Category: Capability honesty / documentation drift  
File(s): `README.md`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, `BUILD_LEDGER.yaml`  
Line(s): `README.md:11`, `docs/CURRENT_IMPLEMENTATION_REALITY.md:5`, `BUILD_LEDGER.yaml:1177-1183`  
Evidence: README says `68/71 verified`; current reality doc says `67/67 verified`; build ledger says `total_items: 71`, `verified: 68`, `termination_predicate_met: false`.  
Problem: The repo has multiple active "source of truth" documents that disagree on completeness.  
Impact: Maintainers and users cannot trust readiness claims without rerunning audits. This is a production blocker for governance-heavy software.  
Recommended Fix: Make `BUILD_LEDGER.yaml` the only status source; generate README/current-reality status blocks from it; mark historical docs with a frontmatter status.  
Confidence: High

### Finding ID: CRIT-002
Severity: Critical  
Category: Testability / CI truthfulness  
File(s): `scripts/test_autonomy_governance_integration.py`, `scripts/test_governance_integration.py`, `scripts/test_governance_rbac.py`, `scripts/test_civilization_integration.py`, `archive/evals_regression_theater/test_civilization_integration.py`  
Line(s): collection-time behavior; command evidence below  
Evidence: `PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest --collect-only -q -p no:cacheprovider` collected 741 tests but failed with 4 collection errors: three scripts connect to Postgres at import time; one import-file mismatch shares the same module name as archive test.  
Problem: Repository-wide pytest cannot even collect. Test files under `scripts/` behave like executable scripts, not tests.  
Impact: A new developer cannot run the repo-wide test suite. CI coverage is selective by necessity, and broken tests can hide indefinitely.  
Recommended Fix: Move script probes out of pytest discovery or guard DB connections under test functions/fixtures; rename duplicate test modules; add root `pytest.ini` with explicit testpaths.  
Confidence: High

### Finding ID: CRIT-003
Severity: Critical  
Category: AI governance enforcement  
File(s): `agents/core/base_agent.py`  
Line(s): `91-112`, `179-195`, `197-214`  
Evidence: `run()` validates presence of confidence, calls `_write_audit`, calls `_request_human_approval`, then returns output. Both audit and override helpers catch exceptions and only log.  
Problem: V1 high/critical actions do not hard-block and audit/approval failure is fail-open. Prior focused audit executed this path and confirmed CRITICAL output was returned after audit/override failures.  
Impact: 29 V1 agents can claim governance while bypassing it in runtime. This is unsafe if V1 agents remain callable.  
Recommended Fix: Deprecate V1 agents or make V1 `run()` raise/block on high/critical until durable approval is recorded; fail closed if audit write fails for protected actions.  
Confidence: High

### Finding ID: CRIT-004
Severity: Critical  
Category: Production authorization model  
File(s): `backend/src/server.ts`, route files under `backend/src/routes`  
Line(s): `server.ts:52-75`  
Evidence: Global auth hook lets all `GET`, `HEAD`, and `OPTIONS` requests through even when `AGENTCO_API_KEY` is configured. Many governance, identity, audit, resource, build-status, system, and dashboard endpoints are GET.  
Problem: The backend uses write-auth, not read-auth. In production-like settings this exposes potentially sensitive operational state unless isolated by network controls.  
Impact: Leaks agent identities, audit entries, governance state, system readiness, migrations, resource state, and operational metadata.  
Recommended Fix: Classify routes by sensitivity. Require auth for all non-public reads. Keep only `/health` and minimal readiness public. Add tests for unauthenticated GET denial.  
Confidence: High

## 14. High Severity Findings

### Finding ID: HIGH-001
Severity: High  
Category: Frontend/backend integration  
File(s): `frontend/src/lib/api/autonomy.ts`, `backend/src/server.ts`  
Line(s): `frontend/src/lib/api/autonomy.ts:221-224`, `backend/src/server.ts:112-116`  
Evidence: Frontend health check calls `/api/health`; backend registers `/health`, not `/api/health`.  
Problem: The autonomy dashboard can report the API unavailable even when backend health is up.  
Impact: User-visible autonomy UI is unreliable and may hide real backend state.  
Recommended Fix: Point frontend health to `/health` or add backend `/api/health`; cover it with a frontend smoke test.  
Confidence: High

### Finding ID: HIGH-002
Severity: High  
Category: Frontend capability mismatch  
File(s): `frontend/src/lib/api/autonomy.ts`, `backend/src/routes/autonomy-dashboard.routes.ts`, disabled route files  
Line(s): `frontend/src/lib/api/autonomy.ts:117-157`; disabled routes include `backend/src/routes/phases-9-13.routes.ts.disabled`  
Evidence: Frontend calls `/api/autonomy/candidates/:id` and `/api/autonomy/evals/scorecards/:id`; current active routes expose dashboard/read paths, while richer eval/candidate mutation routes are disabled.  
Problem: UI types imply a complete autonomy/eval product that is only partly backed by active APIs.  
Impact: Dashboard can become a read-only artifact browser, not an end-to-end autonomy control plane.  
Recommended Fix: Generate frontend API client from active route contract; remove UI affordances for disabled capabilities or enable/test routes.  
Confidence: Medium

### Finding ID: HIGH-003
Severity: High  
Category: CI/CD  
File(s): `.github/workflows/ci.yml`  
Line(s): `133-135`  
Evidence: CI master-gate installs `requirements-dev.txt` and `requirements-runtime.txt` from repo root, but root inventory only shows `agents/requirements.txt` and docs history requirement files.  
Problem: The master gate likely fails from a clean checkout before running the advertised gate.  
Impact: CI does not reliably enforce current repo health.  
Recommended Fix: Move requirement files to root or update workflow to existing paths; add a CI self-test job that validates all referenced files exist.  
Confidence: High

### Finding ID: HIGH-004
Severity: High  
Category: Non-portability / unsafe local file access  
File(s): `autonomy/perception_adapter.py`  
Line(s): `102-124`  
Evidence: `LocalFileAdapter` hardcodes `/Users/Zet/Agentco` as project root and allows reading any file under that path or temp directory.  
Problem: The adapter is both non-portable and broad. It treats a developer's entire repo path as a safe read surface.  
Impact: Agent/tool code can read local repo secrets or generated artifacts if exposed through `file://` paths.  
Recommended Fix: Resolve project root dynamically and restrict reads to configured data/artifact roots; block dotfiles and secret files; add path traversal/symlink tests.  
Confidence: High

### Finding ID: HIGH-005
Severity: High  
Category: Durable audit gap  
File(s): `runtime/base_agent/base_agent_v2.py`  
Line(s): `286-342`  
Evidence: V2 writes audit entries to `self._audit_log.append(entry)` only.  
Problem: V2 audit is in-memory unless a higher layer separately persists action envelopes.  
Impact: A process restart loses BaseAgentV2 action audit records, contradicting strong audit claims for direct V2 usage.  
Recommended Fix: Inject a durable audit writer into BaseAgentV2 and fail closed for protected actions when it is unavailable.  
Confidence: High

### Finding ID: HIGH-006
Severity: High  
Category: Infrastructure security  
File(s): `docker-compose.yml`, `docker-compose.staging.yml`  
Line(s): `docker-compose.yml:38-44`, `157-174`; `docker-compose.staging.yml:7-15`, `135-181`  
Evidence: Local compose uses `POSTGRES_PASSWORD: password` and dev Vault root token; staging compose uses `staging_password_change_me` and Grafana `admin/admin`.  
Problem: The repo includes staging-like infrastructure with unsafe defaults. Some docs call it staging, not just local dev.  
Impact: Easy accidental exposure if used outside isolated local development.  
Recommended Fix: Make staging compose require env-file secrets; fail if defaults remain; separate local-dev compose from staging/prod examples.  
Confidence: High

### Finding ID: HIGH-007
Severity: High  
Category: Migration architecture  
File(s): `backend/src/db/migrations`, `backend/src/db/unsupported_migrations`, `backend/src/db/migrate.ts`  
Line(s): duplicate prefixes detected: `051`, `058`, `059`; `migrate.ts:36-58`  
Evidence: Active migrations include duplicate numeric prefixes: `051_fix_fk_constraints.sql` and `051_team_activations.sql`, `058_*`, `059_*`. Migration runner sorts by filename and records by filename.  
Problem: Ordering is lexicographic, not single monotonic versioning. Duplicate version numbers make human reasoning and rollback sequencing fragile.  
Impact: Schema drift risk grows as migrations accumulate.  
Recommended Fix: Enforce unique numeric prefixes or explicit timestamp IDs; add a migration dependency manifest; retire compatibility patches once baselines are rebuilt.  
Confidence: High

### Finding ID: HIGH-008
Severity: High  
Category: Disabled systems / architecture theater  
File(s): `backend/src/routes/*.disabled`, `backend/src/db/unsupported_migrations/*.disabled`  
Line(s): route inventory and unsupported migration inventory  
Evidence: 18 unsupported migrations and multiple disabled route files exist for evals, goals, phases 6-13.  
Problem: The repo advertises broad autonomy/eval/self-modification surfaces, but meaningful pieces are intentionally disabled.  
Impact: New maintainers cannot tell which capabilities are real without reading disabled files and gate reports.  
Recommended Fix: Move disabled systems to `archive/` with status metadata, or convert to active routes with tests.  
Confidence: High

## 15. Medium Severity Findings

### Finding ID: MED-001
Severity: Medium  
Category: Dependency reproducibility  
File(s): `agents/requirements.txt`, `backend/package.json`, `frontend/package.json`  
Line(s): package manifests  
Evidence: Python requirements are all lower-bounded (`>=`) with no lockfile. Node packages use caret ranges but have lockfiles.  
Problem: Python installs are not reproducible.  
Impact: CI and local behavior may drift as Python packages release updates.  
Recommended Fix: Add a root Python lock strategy (`uv.lock`, `requirements.lock`, or Poetry/PDM lock).  
Confidence: High

### Finding ID: MED-002
Severity: Medium  
Category: Secret scanning coverage  
File(s): `.github/workflows/ci.yml`  
Line(s): `16-27`  
Evidence: Secret scan excludes all markdown, docs, reports, tests, and node_modules.  
Problem: Docs/reports can still leak real secrets, especially in generated run outputs.  
Impact: The scan can miss secrets in exactly the files most likely to include copied terminal output.  
Recommended Fix: Use gitleaks/trufflehog with allowlisted test fixtures, not broad directory exclusions.  
Confidence: Medium

### Finding ID: MED-003
Severity: Medium  
Category: Generated artifacts in working tree  
File(s): local filesystem, `.gitignore`  
Line(s): inventory evidence  
Evidence: Raw filesystem includes `backend/node_modules`, `frontend/node_modules`, `frontend/.next`, `backend/dist`, caches, pyc files.  
Problem: Local audit and grep are noisy; accidental commits become more likely.  
Impact: Slower audits, false positives, and reproducibility confusion.  
Recommended Fix: Clean local generated trees before audits; ensure ignore rules cover all generated files; do not treat `.next` reports as repo evidence.  
Confidence: High

### Finding ID: MED-004
Severity: Medium  
Category: Error handling / sensitive logging  
File(s): `backend/src/server.ts`  
Line(s): `77-92`  
Evidence: Central error handler logs full error object and returns `error.message`.  
Problem: Production errors may leak implementation details or sensitive upstream messages.  
Impact: Information disclosure and inconsistent API error contract.  
Recommended Fix: Return sanitized public messages; log structured internal error IDs; suppress stack/details unless debug mode.  
Confidence: Medium

### Finding ID: MED-005
Severity: Medium  
Category: Test skips / todos  
File(s): `backend/tests/specialist-integration.test.ts`, multiple e2e files  
Line(s): skip scan evidence  
Evidence: Specialist integration has 5 `test.todo`; live LLM/web/DB suites skip based on env.  
Problem: Critical product paths are tracked as future tests.  
Impact: CI can be green without proving specialist depth limits, timeout handling, and multi-specialist aggregation.  
Recommended Fix: Promote `todo` tests to real fail-closed tests with deterministic local fixtures.  
Confidence: High

### Finding ID: MED-006
Severity: Medium  
Category: Data provenance  
File(s): `data/external/bike_sharing/hour.csv`, `evals/experiments/*`, `results/*`  
Line(s): inventory evidence  
Evidence: Large datasets/results exist as checked-in or local artifacts, with mixed provenance documentation.  
Problem: Results are not uniformly reproducible from manifest + code + dataset hash.  
Impact: Evaluation evidence can become stale or non-reproducible.  
Recommended Fix: Add dataset manifest with source URL, license, hash, transformation commands, and result regeneration commands.  
Confidence: Medium

## 16. Low Severity Findings

### Finding ID: LOW-001
Severity: Low  
Category: Developer experience  
File(s): root, `agents`, `backend`, `frontend`  
Line(s): inventory evidence  
Evidence: Python code lives at root plus `agents/pyproject.toml`; Node has separate backend/frontend package roots.  
Problem: There is no single root toolchain definition.  
Impact: New contributors must infer how to install and test each layer.  
Recommended Fix: Add root `pyproject.toml` or documented `uv` environment; add `make bootstrap-clean-room`.  
Confidence: High

### Finding ID: LOW-002
Severity: Low  
Category: Naming consistency  
File(s): `backend/src/db/migrations`, `calibration/ledger/schema.sql`, backend code  
Line(s): broad schema evidence  
Evidence: Historical drift includes `producing_prompt_ver` vs `producing_prompt_version`, `goal_depth` vs `depth`, legacy compatibility migrations.  
Problem: Compatibility layers obscure canonical names.  
Impact: Maintenance cost and query mistakes.  
Recommended Fix: Publish canonical schema docs generated from migrations and remove stale schema artifacts.  
Confidence: Medium

### Finding ID: LOW-003
Severity: Low  
Category: UI polish  
File(s): `frontend/src/app/autonomy/page.tsx`  
Line(s): page content  
Evidence: UI contains in-app implementation checklist text and command instructions.  
Problem: Product UI reads like developer status docs, not an operator console.  
Impact: Weak product usability.  
Recommended Fix: Move implementation text to docs; show real operational state, actions, errors, and next required operator decision.  
Confidence: Medium

## 17. Placeholder / Mock / Fake-System Findings

| Class | Evidence | Classification |
|---|---|---|
| `MockWebAdapter` | README admits test-only; backend support files | Harmless if isolated to tests |
| `deterministic_test_only` provider | bounded learning service and CLI | Legitimate offline fixture, dangerous if allowed in production |
| Disabled routes/migrations | `.disabled` files | Active incomplete implementation |
| `archive/evals_regression_theater` | Archive name and tests | Historical/theater, not production evidence |
| Frontend autonomy dashboard claims | hardcoded implementation checklist | UI overclaim / product theater |
| V1 `BaseAgent` governance language | docs vs fail-open code | Dangerous placeholder/facade |
| Self-modification kernel | build ledger says no closed loop | Scaffolded |
| Simulation scripts | PawDent/bike-sharing results | Useful experiments, not real-world autonomy proof |

## 18. Incomplete / Underbuilt Systems

- Hosted production operations: no real SLO, incident, backup, DR, rollback evidence.
- Self-improvement: no durable repeated real-world improvement cycle evidence.
- Frontend operator workflows: dashboards exist but do not fully control/observe backend workflows.
- V1 agent deprecation: duplicate hierarchies still present.
- Evals: many are experiments or archived theater; not all are acceptance gates.
- Source discovery: deterministic and live paths exist, but broad live-source reliability is not proven.
- Deployment: Kubernetes Helm exists, but production readiness depends on manually provisioned secrets and cluster state.

## 19. Logic Inconsistencies

- Status documents disagree on build-ledger counts.
- Backend health is `/health`; autonomy client checks `/api/health`.
- V1 says high/critical actions are blocked; code queues approval and returns output.
- V2 says audit log captures actions; BaseAgentV2 stores audit in memory.
- README says clean clone can run `make verify-clean-room`; Makefile excerpt contains many gates but no visible `verify-clean-room` target in the audited portion.
- CI Python version is 3.12 while README prerequisites say Python 3.13.
- Backend and Python layers duplicate calibration/trust concepts with different historical semantics.

## 20. Dead Code and Unused Code

- `backend/src/routes/*.disabled` are dead from runtime routing.
- `backend/src/db/unsupported_migrations/*.disabled` are not runtime migrations.
- `archive/evals_regression_theater` is explicitly historical.
- `dashboard/src` is a separate small calibration dashboard, apparently not integrated with main Next app.
- V1/V2 duplicate agent roles create ambiguous live ownership.
- Generated local trees (`.next`, `dist`, `node_modules`, pycache) are not first-party source.

## 21. Security Risks

- Broad unauthenticated GET access to operational endpoints.
- Dev/staging compose credentials and dev Vault mode.
- V1 governance fail-open.
- In-memory V2 audit.
- Hardcoded local file access root.
- Secret scan excludes docs/reports broadly.
- Error handler returns raw error messages.
- Frontend can expose `NEXT_PUBLIC_AGENTCO_API_KEY` by design if set; it must only be treated as a low-privilege browser token.
- Scripts include many local DSN defaults with `agentco:password`.

## 22. Architecture Risks

- Too many parallel systems: Python agents, backend services, runtime V2, calibration, civilization, reserve, selfcoding.
- Disabled systems remain in-place next to active systems.
- Compatibility migrations are accumulating rather than converging to a clean baseline.
- Product API contract is hand-written and drifts from backend routes.
- Reports are mutable evidence files and can become stale while docs point to them as truth.

## 23. Backend/API Findings

Backend strengths:
- `npx tsc --noEmit` passed.
- Fastify server wires many real route modules.
- Postgres migrations and DB-backed tests are extensive.
- Production secret guard exists.
- Rate limiter is applied globally.

Backend gaps:
- Public reads are too broad.
- Request validation is inconsistent; many routes use `any` body/query types.
- Error responses expose raw messages.
- Disabled route files signal incomplete product surfaces.
- Migration ordering is fragile with duplicate prefixes.
- Health checks are shallow for Kafka and do not verify producer connectivity.

Endpoint risk summary:
- Public GET endpoints can expose audit/governance/system state.
- POST routes rely on global API key, not actor-scoped authorization.
- Resource and identity routes need explicit permission checks per operation, not just API-key possession.

## 24. Frontend/Dashboard Findings

Frontend strengths:
- `npx tsc --noEmit` passed.
- API client has retry logic for common failures.
- Basic dashboards exist for agents, audit, events, governance, validation, override, autonomy.

Frontend gaps:
- Autonomy health check is wrong.
- UI is mostly dashboard/read-only, not a complete operator product.
- No observed frontend test suite beyond smoke script.
- Some API client types imply backend capabilities that are disabled or partial.
- Some UI text is implementation-status prose rather than user workflow.
- Browser-exposed API key pattern must not be treated as strong auth.

## 25. Agent/AI/Autonomy Findings

Capability classification:

| Capability | Classification |
|---|---|
| V2 escalation gate | Fully implemented in-process; durable audit partial |
| V1 department agents | Dangerous if used as governed agents; governance fail-open |
| Tool permission registry | Implemented and tested |
| Prompt files | Real role prompts, but prompts are not enforcement |
| Memory retrieval/injection | Implemented in slices; best-effort fallback |
| Autonomy coordinator | Partially implemented and tested in backend slices |
| Self-improvement | Scaffolded/partial; no durable real-world proof |
| Selfcoding sandbox | Recently hardened; old reports are stale |
| Evaluation harness | Mixed real tests and benchmark theater |

## 26. Governance/Memory/Provenance Findings

- Backend governance services are materially implemented, but public GET and API-key-only writes are coarse.
- V1 governance is facade-level.
- V2 memory and audit paths are best-effort in places.
- Provenance/attestation helpers exist, but not every path emits durable provenance.
- Reserve trust model is explicitly operator-run, not decentralized, which is honest and should remain clear.

## 27. Data/Schema Findings

- 113 active SQL migrations plus 18 unsupported migrations is a large schema surface.
- Recent compatibility migrations repair drift, but the pattern indicates schema churn.
- Duplicate migration prefixes exist.
- Some data artifacts are checked in without uniform regeneration manifests.
- `reports/system_run/latest` is treated as evidence, but reports are mutable and environment-specific.

## 28. Testing and Eval Gaps

### Test Gap Matrix

| Area | Current Coverage | Gap |
|---|---|---|
| Backend type check | Passes | Does not prove runtime product flows |
| Frontend type check | Passes | No route-contract/e2e UI tests observed |
| Python repo-wide collection | Fails | Import-time DB connections and duplicate module names |
| Backend Jest suite | Previously passed after DB repair | CI truth still needs confirmation |
| Calibration | Strong focused tests | Duplicated semantics elsewhere |
| V1 agents | Helper tests, prior audit | No hard-block governance tests |
| V2 agents | Better runtime tests | Audit durability not enforced |
| Live LLM/web | Skipped unless env present | Not continuous CI evidence |
| Specialist spawning | Several todos | Depth/timeout/multi-specialist missing |
| Deployment | Smoke/local only | No hosted ops test |

## 29. CI/CD and Deployment Findings

- CI has secret scan, agents, backend, master gate, frontend jobs.
- CI likely fails at master-gate dependency install due missing root requirement files.
- CI does not run root-wide pytest collection.
- Deploy is manual or tag-triggered, builds/pushes images and Helm upgrades.
- Deploy does not visibly run migrations, canary checks, backups, or rollback validation.
- Helm values rely on existing Kubernetes secrets.

## 30. Dependency and Supply Chain Findings

- Backend and frontend have lockfiles and local `npm ls --depth=0` succeeds.
- Python has no root lockfile and uses `>=` ranges.
- Node versions are inconsistent: CI uses Node 20; local reports show Node 24 in generated doctor output.
- Secret scanning is custom and narrower than mature tools.
- Docker images are versioned for core services, but staging uses older Postgres/Kafka/Grafana than local compose.

## 31. Documentation Gaps

- No single generated current-state document.
- Historical docs are too numerous and can be mistaken for current truth.
- Setup docs do not fully reconcile Python 3.13 local vs Python 3.12 CI.
- Deployment docs do not prove a safe independent production runbook.
- Disabled systems need explicit current/non-current status.
- Reports should include generation commit, dirty flag, environment, and expiry.

## 32. File-by-File Findings

This section summarizes every meaningful tracked file group. Full tracked inventory was accounted for with `git ls-files`; generated/vendor local files were accounted for by inventory and excluded from first-party line audit.

| File / Group | Purpose | Status | Issues | Severity | Used? |
|---|---|---|---|---|---|
| `README.md` | Current public status/setup | Partial | Conflicts with current reality doc; claims local posture | Critical | Yes |
| `BUILD_LEDGER.yaml` | Status ledger | Important | Termination false; 68/71 only; docs drift | Critical | Yes |
| `SYSTEM.md`, `SYSTEM_CIVILIZATION.md`, `AGENTS.md` | Architecture/invariants | Partial | Mix of target and actual; some V1 claims false | High | Docs |
| `.github/workflows/ci.yml` | CI | Partial | Missing root req files; broad exclusions | High | Yes |
| `.github/workflows/deploy.yml` | Deploy | Partial | Manual assumptions; no migration/rollback gate | High | Yes |
| `.env*.example` | Env docs | Useful | Dev defaults; must stay examples only | Medium | Yes |
| `docker-compose.yml` | Local infra | Dev-only | Weak defaults, dev Vault | High | Yes |
| `docker-compose.staging.yml` | Staging infra | Risky | Weak staging credentials; stale images | High | Maybe |
| `Makefile` | Command surface | Useful | Huge target set, likely stale targets | Medium | Yes |
| `backend/package.json`, lockfile | Backend deps/scripts | Real | Build/test scripts work locally; lock present | Low | Yes |
| `frontend/package.json`, lockfile | Frontend deps/scripts | Real | Type-check works; UI tests thin | Medium | Yes |
| `agents/requirements.txt`, `agents/pyproject.toml` | Python deps | Partial | No lock; pyproject only agents | Medium | Yes |
| `backend/src/server.ts` | API entrypoint | Real | Public GETs; raw error messages | Critical/Medium | Yes |
| `backend/src/security.ts` | Auth/secret guard | Real | API-key model coarse | Medium | Yes |
| `backend/src/routes/*.ts` | API route modules | Real/partial | Inconsistent validation/auth sensitivity | High | Yes |
| `backend/src/routes/*.disabled` | Disabled APIs | Incomplete | Architecture theater if documented as real | High | No |
| `backend/src/services/*.ts` | Main service layer | Real/partial | Many `any`, console logging, drift repairs | Medium | Yes |
| `backend/src/db/migrations/*.sql` | Active schema | Real | Duplicate prefixes, many compat migrations | High | Yes |
| `backend/src/db/unsupported_migrations/*.disabled` | Unsupported schema | Not active | Must not be counted as capability | High | No |
| `backend/tests/*.test.ts` | Backend tests | Broad | Some skipped/live/todo; CI needs proof | Medium | Yes |
| `frontend/src/app/*` | Main UI pages | Partial | Dashboard product underbuilt | Medium | Yes |
| `frontend/src/lib/api*.ts` | Frontend API client | Partial | `/api/health` mismatch; manual contract drift | High | Yes |
| `dashboard/src/*` | Separate dashboard | Scaffold | Disconnected from main app | Medium | Unknown |
| `agents/core/*` | V1 agent framework | Mixed | Governance fail-open; tool gate real | Critical | Yes |
| `agents/*/*_agent.py` | Department agents | Mixed | Many V1 hardcoded confidences; V2 subset stronger | High | Yes |
| `agents/prompts/**/*.md` | Agent prompts | Prompt-only | Not enforcement | Medium | Yes |
| `runtime/base_agent/*` | V2 runtime | Real | In-memory audit; best-effort memory | High | Yes |
| `runtime/escalation/*` | Human approval gate | Real | Needs durable integration everywhere | Medium | Yes |
| `runtime/orchestration/*` | Doctor/best-effort modes | Real | Mode evidence not product evidence | Medium | Yes |
| `calibration/**` | Ledger/trust/scoring | Strong | Semantics duplicated across repo | Medium | Yes |
| `reserve/**` | Proof-of-calibration | Real | Operator-run, not decentralized | Medium | Yes |
| `selfcoding/**` | Selfcoding sandbox/planner | Mixed | Sandbox improved; historical reports stale | High | Partial |
| `autonomy/**` | Python autonomy layer | Partial | Hardcoded path, older abstractions | High | Partial |
| `learning/**` | Learning agents | Partial | Simulation/backtest-heavy | Medium | Partial |
| `synthesis/**` | Synthesis research layer | Small real | Provisional outputs | Low | Partial |
| `civilization/**` | Python civilization services | Partial | Shadowed by backend civilization implementation | Medium | Partial |
| `governance/**`, `memory_kernel/**`, `provenance/**` | Thin Python helpers | Partial | Small/legacy, limited wiring | Medium | Partial |
| `ingestion/**`, `institutions/**`, `foundry/**`, `simulation/**` | Misc layers | Scaffold/partial | Sparse or simulation-only | Medium | Partial |
| `scripts/**` | Runbooks, verifiers, demos | Mixed | Non-portable paths, import-time tests, local DSNs | High | Some |
| `tests/**` | Python tests | Mixed | Root collection fails | Critical | Yes |
| `evals/**` | Eval harness/experiments | Mixed | Real plus theater/archive | Medium | Some |
| `docs/**` | Docs/status/history | Mixed | Stale and conflicting | Critical | Yes |
| `audit_artifacts/**`, `reports/**`, `results/**`, `outputs/**` | Evidence artifacts | Generated/historical | Mutable, environment-specific | Medium | No runtime |
| `data/external/**` | Dataset | Real data | Need provenance manifest/hash | Medium | Yes |
| `archive/**` | Old tests/docs | Historical | Do not count as current capability | Medium | No |
| `node_modules`, `.next`, `dist`, `__pycache__`, `.pytest_cache` | Local generated/vendor | Generated | Audit noise; not first-party | Low | Local only |

## 33. Recommended Fix Plan

1. Make status truth generated from `BUILD_LEDGER.yaml`.
2. Fix root pytest collection and add it to CI.
3. Lock down backend read authorization.
4. Retire or hard-block V1 agents.
5. Persist BaseAgentV2 audit entries durably.
6. Fix frontend/backend API contract drift.
7. Clean CI master gate dependency paths.
8. Split local dev compose from staging/prod.
9. Move disabled systems to archive or activate with tests.
10. Add a reproducible Python dependency lock.

## 34. 30-Day Remediation Roadmap

- Week 1: status-doc generator; pytest collection fix; CI master-gate fix.
- Week 2: backend route sensitivity matrix and auth tests for every route.
- Week 3: V1 agent deprecation or fail-closed governance patch.
- Week 4: frontend route-contract tests and autonomy dashboard health/API fixes.

## 35. 60-Day Remediation Roadmap

- Durable V2 audit writer.
- Schema baseline cleanup and unique migration version policy.
- Python dependency lock and clean-room bootstrap.
- Replace staging compose defaults with required secret injection.
- Convert top skipped/todo specialist tests into real tests.

## 36. 90-Day Remediation Roadmap

- Hosted staging environment with SLOs, backups, restore drills, incident simulation, and rollback tests.
- Longitudinal real-world improvement registry with at least three independent cycles.
- Open-domain transfer eval with held-out independent adjudication.
- Product-grade operator UI with authenticated workflows and audit trail.

## 37. Questions for the Maintainer

1. Is V1 `agents.core.BaseAgent` still a supported runtime path, or should it be archived?
2. Should public GET endpoints be considered safe behind a private network, or must the API be internet-safe?
3. Which document should be authoritative: README, current reality doc, build ledger, or reports?
4. Are `reports/system_run/latest` intended to be committed evidence or local generated outputs?
5. Is there a real hosted staging/prod cluster, or only local production-posture smoke?
6. Should disabled routes/migrations be preserved as design history or removed from runtime directories?

## 38. Appendix: Commands Run

Commands were run non-destructively, avoiding build commands that rewrite artifacts where possible.

```bash
pwd
git status --short --branch
find . -type f | sort | wc -l
find . -maxdepth 2 -type d | sort
find . -type f -empty | sort
find . -type f -size +1M | sort
git ls-files | wc -l
git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -nr
git ls-files | awk '...' | sort -nr | head -80
find . -maxdepth 3 -type f \( manifests/config patterns \) | sort
find .github/workflows -type f -maxdepth 2 | sort
find . -maxdepth 3 -type f \( -iname '*readme*' -o -iname '*.md' \) | sort
sed -n '1,220p' README.md
sed -n '1,220p' SYSTEM.md
sed -n '1,220p' AGENTS.md
sed -n '1,220p' Makefile
sed -n '1,220p' backend/package.json
sed -n '1,220p' frontend/package.json
sed -n '1,260p' .github/workflows/ci.yml
sed -n '1,260p' .github/workflows/deploy.yml
sed -n '1,260p' docker-compose.yml
sed -n '1,220p' docker-compose.staging.yml
sed -n '1,220p' backend/Dockerfile
sed -n '1,220p' frontend/Dockerfile
rg placeholder/security/search patterns across first-party files
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest --collect-only -q -p no:cacheprovider
cd backend && npx tsc --noEmit
cd frontend && npx tsc --noEmit
cd backend && npm ls --depth=0
cd frontend && npm ls --depth=0
```

Key command results:
- Backend type-check: passed.
- Frontend type-check: passed.
- Python repo-wide collection: failed with 4 collection errors after collecting 741 tests.
- Backend dependencies listed successfully.
- Frontend dependencies listed successfully.
- Git status was clean before report creation.

## 39. Appendix: Search Terms Used

```text
TODO FIXME HACK XXX WIP TEMP temporary placeholder stub mock dummy fake sample
example only not implemented NotImplementedError pass return None return null
raise NotImplementedError throw new Error console.log print debug hardcoded
localhost 127.0.0.1 admin password secret api_key token private_key
ts-ignore eslint-disable type: ignore noqa pragma: no cover deprecated legacy
disabled skip xfail manual simulated toy prototype MVP later future coming soon
OPENAI_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN SECRET_KEY DATABASE_URL JWT
BEGIN RSA BEGIN OPENSSH sk- ghp_ xoxb_ xoxp_ Bearer
eval exec subprocess os.system shell=True child_process spawn execSync
readFileSync writeFileSync open requests.get fetch yaml.load pickle md5 sha1
verify=False cors
```

## 40. Appendix: Files Audited

Audited by inventory:
- All 46,745 local filesystem files were accounted for by `find`.
- All 1,519 tracked files were accounted for by `git ls-files`.
- First-party source/docs/config/tests/scripts were directly inspected by directory, targeted reads, and ripgrep context.
- Generated/vendor/local-only files were summarized by class: `node_modules`, `.next`, `dist`, `__pycache__`, `.pytest_cache`, generated reports, generated results.

Representative first-party files read directly include:
- `README.md`, `SYSTEM.md`, `AGENTS.md`, `BUILD_LEDGER.yaml`, `Makefile`
- `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`
- `docker-compose.yml`, `docker-compose.staging.yml`, backend/frontend Dockerfiles
- `backend/package.json`, `frontend/package.json`, `agents/requirements.txt`, `agents/pyproject.toml`
- `backend/src/server.ts`, `backend/src/security.ts`, active route inventories, migration runner, migration verifier
- `frontend/src/lib/api.ts`, `frontend/src/lib/api/autonomy.ts`, `frontend/src/app/autonomy/page.tsx`
- `agents/core/base_agent.py`, `agents/core/confidence_scorer.py`
- `runtime/base_agent/base_agent_v2.py`, runtime orchestration files
- `autonomy/perception_adapter.py`
- `docs/CURRENT_IMPLEMENTATION_REALITY.md`, `docs/audit/02_agents.md`, `docs/audit/03_capabilities_vs_reality.md`
- CI, infra, reports, evals, scripts, and disabled migration/route inventories

This report should be treated as a current-state audit, not a permanent truth source. The repository changes quickly; rerun the command appendix after remediation.
