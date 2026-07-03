# Score Validation (signal-gated)

Generated 2026-07-03T05:48:03.091Z at commit `d41bbb2b08b0b3bd1095614dfe60659732cbb200`.

Scores are estimates gated on structural signals (presence of the required services, migrations, CLIs, tests, and docs). They do NOT execute the test suites; run `make verify-clean-room` for behavioral proof.

**Acceptance checks:** 21/21 pass.
**Estimated score:** 76.3/100 (122/160).
**Claims 80+ :** false

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

## Dimensions

| Dimension | Baseline | Target | Gate passed | Score |
|---|---|---|---|---|
| Clean-room runnability | 7 | 9 | ✅ | 9 |
| Documentation accuracy | 6 | 8 | ✅ | 8 |
| Architecture coherence | 6 | 8 | ✅ | 8 |
| Code completeness | 6 | 8 | ✅ | 8 |
| Integration completeness | 5 | 8 | ✅ | 8 |
| Test quality | 7 | 8 | ✅ | 8 |
| Evidence governance | 7 | 8 | ✅ | 8 |
| Calibration loop | 6 | 8 | ✅ | 8 |
| Learning loop | 5 | 8 | ✅ | 8 |
| Autonomy | 3 | 6 | ✅ | 6 |
| Civilization implementation | 4 | 8 | ✅ | 8 |
| Self-improvement | 3 | 7 | ✅ | 7 |
| Safety | 7 | 8 | ✅ | 8 |
| Production readiness | 4 | 6 | ✅ | 6 |
| Real-world usefulness | 3 | 6 | ✅ | 6 |
| Alignment with stated goal | 5 | 8 | ✅ | 8 |
