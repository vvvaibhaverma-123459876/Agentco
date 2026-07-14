# Score Validation (signal-gated)

Generated 2026-07-14T19:34:42.542Z at commit `365a2eb9b700de20118f27686bb734d43ff81aa4`.
Input hash: `0413af4522ec42eaadf67cb44a23a9131136451e03e216694147fbf020ff653f`.

This report separates structural acceptance from verified behaviour. The structural score is based on repository signals. This command does NOT execute the test suites and therefore does not emit an overall production-readiness score; run `make release-gate` and clean-room/staging commands for behavioural proof.

**Acceptance checks:** 30/30 pass.
**Structural score:** 82.5/100 (132/160).
**Verified behaviour score:** not emitted by this structural validator.
**Tracked structural snapshot input hash is current:** true
**Claims 80+ :** true

## Acceptance checks

| ID | Check | Pass | Evidence |
|---|---|---|---|
| A1_clean_room_target | make verify-clean-room target exists | ✅ | Makefile:verify-clean-room |
| A2_py_live_gating | Python live-LLM tests are opt-in (conftest gating) | ✅ | conftest.py live_llm marker |
| A3_ledger_scan_expanded | build ledger scans autonomy/civilization/frontend | ✅ | scripts/build_ledger.py RUNTIME_DIRS |
| A4_docs_archived | legacy status docs archived under docs/history | ✅ | docs/history/README.md |
| B1_skill_retrieval | SkillRetrievalService exists and planner consumes it | ✅ | skill-retrieval.service.ts + planner import |
| B2_skill_usage_events | skill_usage_events migration + skill-consumption E2E present | ✅ | migration 110 + skill-consumption-e2e.test.ts |
| C1_eval_canary_deploy | candidate evaluation, canary, deployment services exist | ✅ | candidate-evaluation/skill-canary/skill-deployment services |
| C2_closed_loop_e2e | self-improvement closed-loop E2E present | ✅ | self-improvement-closed-loop-e2e.test.ts |
| D1_longitudinal_harness | longitudinal learning harness + 3-cycle test present | ✅ | longitudinal-learning-harness service + test |
| D2_longitudinal_cli | longitudinal learning CLI generates a DB-derived report | ✅ | run-longitudinal-learning.ts |
| E1_calibration_routing | calibration-aware routing service + planner integration | ✅ | calibration-aware-routing.service.ts + planner import |
| E2_calibration_test | calibration-driven planning test present | ✅ | calibration-driven-planning.test.ts |
| F1_civilization_live_flow | civilization live flow service + E2E present | ✅ | civilization-live-flow service + e2e |
| F2_civilization_learning_backbone | civilization produces learning: knowledge bridge + E2E (clean-room & live) | ✅ | institutional-knowledge-bridge + migration 113 + backbone e2e + live test |
| G1_goal_formation_free_run | goal formation + supervised free-run services + test | ✅ | goal-formation + supervised-free-run + test |
| G2_free_run_cli | supervised free-run CLI present | ✅ | supervised-free-run.ts |
| H1_ssrf_guard | URL safety (SSRF) guard wired into the web adapter | ✅ | url-safety.ts + real-web-adapter import |
| H2_prompt_injection | untrusted-content wrapping wired into the planner | ✅ | planner wrapUntrustedContent |
| H3_rbac_and_safety_test | safety hardening test + RBAC middleware decision doc | ✅ | safety-hardening.test.ts + RBAC_AND_WEB_SAFETY.md |
| I1_canonical_doc | canonical runtime doc present | ✅ | docs/CURRENT_RUNTIME_CANONICAL.md |
| I2_db_usage_manifest | DB table usage manifest present | ✅ | docs/DB_TABLE_USAGE.md |
| J1_health_helm_contract | backend liveness/readiness endpoints are aligned with Helm probes and tested | ✅ | server health routes + Helm values + health-contract.test.ts |
| J2_browser_secret_removed | browser bundle is scanned for privileged API key exposure | ✅ | frontend/scripts/check-smoke.mjs + README server-side proxy contract |
| J3_durable_governance_stores | evaluation, learning, and experiment stores fail closed to durable storage in production | ✅ | runtime durable store implementations + durable-governance test |
| J4_durable_llm_budget | backend LLM provider reserves and settles durable resource-ledger budget | ✅ | llm-provider durable budget path + startup guard + tests |
| J5_event_outbox_worker | transactional and signed event-bus outboxes have an executable relay worker | ✅ | outbox-worker entrypoint + script + test + event_bus_outbox migration |
| J6_release_gate_enforces_core_contracts | release gate checks route auth, audit chain, generated reports, and clean-tree behavior | ✅ | Makefile release-gate contract |
| J7_helm_deployment_topology | Helm chart contains backend, frontend, Services, Ingress, autoscaling, disruption budgets, migration job, and outbox worker | ✅ | Helm topology templates + helm-deployment-contract.test.ts |
| J8_forensic_audit_controls | audit controls include requirements-to-behaviour, external dependency, completeness, and post-remediation ledgers | ✅ | forensic audit controls generator + generated ledgers + regression test |
| J9_gate_integrity_controls | release gate includes fake-success scanner and advertised-target validation | ✅ | gate-integrity scanner + advertised target validator + Makefile release-gate wiring |

## Dimensions

| Dimension | Baseline | Target | Gate passed | Score |
|---|---|---|---|---|
| Clean-room runnability | 7 | 9 | ✅ | 9 |
| Documentation accuracy | 6 | 9 | ✅ | 9 |
| Architecture coherence | 6 | 8 | ✅ | 8 |
| Code completeness | 6 | 9 | ✅ | 9 |
| Integration completeness | 5 | 9 | ✅ | 9 |
| Test quality | 7 | 9 | ✅ | 9 |
| Evidence governance | 7 | 9 | ✅ | 9 |
| Calibration loop | 6 | 8 | ✅ | 8 |
| Learning loop | 5 | 8 | ✅ | 8 |
| Autonomy | 3 | 6 | ✅ | 6 |
| Civilization implementation | 4 | 8 | ✅ | 8 |
| Self-improvement | 3 | 7 | ✅ | 7 |
| Safety | 7 | 9 | ✅ | 9 |
| Production readiness | 4 | 8 | ✅ | 8 |
| Real-world usefulness | 3 | 7 | ✅ | 7 |
| Alignment with stated goal | 5 | 9 | ✅ | 9 |
