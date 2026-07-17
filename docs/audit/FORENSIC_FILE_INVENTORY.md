# Forensic File Inventory

Machine-derived inventory of tracked files. Generated from `git ls-files`; untracked local caches and dependency directories are intentionally excluded.

- Tracked files: `1999`

## Category Counts

| Category | Count |
|---|---:|
| Database migration | 139 |
| Deployment infrastructure | 34 |
| Deprecated code | 48 |
| Development tooling | 143 |
| Documentation | 448 |
| Experimental code | 151 |
| Generated artifact | 116 |
| Production runtime code | 490 |
| Prompt/template | 29 |
| Test infrastructure | 305 |
| Unknown purpose | 96 |

## Top-Level Counts

| Path | Count |
|---|---:|
| `backend` | 505 |
| `docs` | 375 |
| `evals` | 180 |
| `scripts` | 155 |
| `agents` | 111 |
| `audit_artifacts` | 99 |
| `reports` | 64 |
| `tests` | 62 |
| `runtime` | 51 |
| `archive` | 48 |
| `frontend` | 37 |
| `reserve` | 33 |
| `benchmarks` | 32 |
| `calibration` | 30 |
| `infrastructure` | 21 |
| `results` | 20 |
| `selfcoding` | 17 |
| `civilization` | 15 |
| `autonomy` | 13 |
| `learning` | 13 |
| `.github` | 11 |
| `synthesis` | 10 |
| `agentco_capability` | 9 |
| `cross_version_adapters` | 9 |
| `ingestion` | 9 |
| `constitution` | 8 |
| `schemas` | 7 |
| `requirements` | 4 |
| `validation` | 4 |
| `agentco_security` | 2 |
| `dashboard` | 2 |
| `data` | 2 |
| `foundry` | 2 |
| `governance` | 2 |
| `institutions` | 2 |
| `memory_kernel` | 2 |
| `meta` | 2 |
| `provenance` | 2 |
| `self_modification` | 2 |
| `simulation` | 2 |
| `.env.example` | 1 |
| `.env.level3.test` | 1 |
| `.env.production.example` | 1 |
| `.env.staging.example` | 1 |
| `.gitignore` | 1 |
| `.python-version` | 1 |
| `AGENTCO_AUDIT_EXECUTIVE_SUMMARY.md` | 1 |
| `AGENTCO_REPO_AUDIT.md` | 1 |
| `AGENTS.md` | 1 |
| `BUILD_LEDGER.yaml` | 1 |
| `CIVILIZATION_BUILD_LEDGER.yaml` | 1 |
| `LICENSE` | 1 |
| `Makefile` | 1 |
| `README.md` | 1 |
| `ROADMAP.md` | 1 |
| `SETUP_WINDOWS.md` | 1 |
| `SYSTEM.md` | 1 |
| `SYSTEM_CIVILIZATION.md` | 1 |
| `conftest.py` | 1 |
| `docker-compose.staging.yml` | 1 |
| `docker-compose.yml` | 1 |
| `pg_test_isolation.py` | 1 |
| `prompts` | 1 |
| `pytest.ini` | 1 |
| `pytest_skip_report_plugin.py` | 1 |

## Full File Ledger

| Path | Category |
|---|---|
| `.env.example` | Development tooling |
| `.env.level3.test` | Development tooling |
| `.env.production.example` | Development tooling |
| `.env.staging.example` | Development tooling |
| `.github/workflows/capability-runtime-audit.yml` | Deployment infrastructure |
| `.github/workflows/ci.yml` | Deployment infrastructure |
| `.github/workflows/civilization-completion.yml` | Deployment infrastructure |
| `.github/workflows/clean-room-audit.yml` | Deployment infrastructure |
| `.github/workflows/constitution.yml` | Deployment infrastructure |
| `.github/workflows/cross-version-evaluation.yml` | Deployment infrastructure |
| `.github/workflows/deploy.yml` | Deployment infrastructure |
| `.github/workflows/hosted-staging-audit.yml` | Deployment infrastructure |
| `.github/workflows/longitudinal-evidence.yml` | Deployment infrastructure |
| `.github/workflows/runtime-integration-audit.yml` | Deployment infrastructure |
| `.github/workflows/staging-deployment-audit.yml` | Deployment infrastructure |
| `.gitignore` | Development tooling |
| `.python-version` | Development tooling |
| `AGENTCO_AUDIT_EXECUTIVE_SUMMARY.md` | Unknown purpose |
| `AGENTCO_REPO_AUDIT.md` | Unknown purpose |
| `AGENTS.md` | Unknown purpose |
| `BUILD_LEDGER.yaml` | Unknown purpose |
| `CIVILIZATION_BUILD_LEDGER.yaml` | Unknown purpose |
| `LICENSE` | Development tooling |
| `Makefile` | Development tooling |
| `README.md` | Unknown purpose |
| `ROADMAP.md` | Unknown purpose |
| `SETUP_WINDOWS.md` | Unknown purpose |
| `SYSTEM.md` | Unknown purpose |
| `SYSTEM_CIVILIZATION.md` | Unknown purpose |
| `agentco_capability/__init__.py` | Unknown purpose |
| `agentco_capability/__main__.py` | Unknown purpose |
| `agentco_capability/evidence.py` | Unknown purpose |
| `agentco_capability/models.py` | Unknown purpose |
| `agentco_capability/providers.py` | Unknown purpose |
| `agentco_capability/runtime.py` | Unknown purpose |
| `agentco_capability/scoring.py` | Unknown purpose |
| `agentco_capability/storage.py` | Unknown purpose |
| `agentco_capability/tools.py` | Unknown purpose |
| `agentco_security/__init__.py` | Production runtime code |
| `agentco_security/env_guard.py` | Production runtime code |
| `agents/__init__.py` | Production runtime code |
| `agents/autonomy/__init__.py` | Production runtime code |
| `agents/autonomy/__main__.py` | Production runtime code |
| `agents/autonomy/background_researcher.py` | Production runtime code |
| `agents/autonomy/claim_validator.py` | Production runtime code |
| `agents/autonomy/code_reviewer.py` | Production runtime code |
| `agents/autonomy/comparative_analyst.py` | Production runtime code |
| `agents/autonomy/contradiction_hunter.py` | Production runtime code |
| `agents/autonomy/data_analyst.py` | Production runtime code |
| `agents/autonomy/doc_analyzer.py` | Production runtime code |
| `agents/autonomy/evidence_linker.py` | Production runtime code |
| `agents/autonomy/evidence_summarizer.py` | Production runtime code |
| `agents/autonomy/fetcher.py` | Production runtime code |
| `agents/autonomy/quality_auditor.py` | Production runtime code |
| `agents/autonomy/researcher.py` | Production runtime code |
| `agents/autonomy/reviewer.py` | Production runtime code |
| `agents/autonomy/sentiment_analyzer.py` | Production runtime code |
| `agents/autonomy/source_validator.py` | Production runtime code |
| `agents/autonomy/specialist_agent.py` | Production runtime code |
| `agents/autonomy/synthesizer.py` | Production runtime code |
| `agents/autonomy/temporal_analyst.py` | Production runtime code |
| `agents/calibration_updater.py` | Production runtime code |
| `agents/civilization_service.py` | Production runtime code |
| `agents/conftest.py` | Production runtime code |
| `agents/core/__init__.py` | Production runtime code |
| `agents/core/base_agent.py` | Production runtime code |
| `agents/core/confidence_scorer.py` | Production runtime code |
| `agents/core/event_subscriber.py` | Production runtime code |
| `agents/core/memory/__init__.py` | Production runtime code |
| `agents/core/memory/learning_loop.py` | Production runtime code |
| `agents/core/memory/memory_reader.py` | Production runtime code |
| `agents/core/memory/memory_writer.py` | Production runtime code |
| `agents/core/memory/tests/__init__.py` | Test infrastructure |
| `agents/core/memory_client.py` | Production runtime code |
| `agents/core/tool_registry.py` | Production runtime code |
| `agents/core/tools/__init__.py` | Production runtime code |
| `agents/core/tools/handlers.py` | Production runtime code |
| `agents/core/tools/registry_setup.py` | Production runtime code |
| `agents/core/tools/web_scraper.py` | Production runtime code |
| `agents/core/types.py` | Production runtime code |
| `agents/customer_experience/__init__.py` | Production runtime code |
| `agents/db/__init__.py` | Production runtime code |
| `agents/db/connection.py` | Production runtime code |
| `agents/design/__init__.py` | Production runtime code |
| `agents/dynamic/__init__.py` | Production runtime code |
| `agents/engineering/__init__.py` | Production runtime code |
| `agents/engineering/coder_agent_v2.py` | Production runtime code |
| `agents/engineering/devops_agent_v2.py` | Production runtime code |
| `agents/engineering/reviewer_agent_v2.py` | Production runtime code |
| `agents/executive/__init__.py` | Production runtime code |
| `agents/executive/ceo_agent_v2.py` | Production runtime code |
| `agents/executive/cfo_agent_v2.py` | Production runtime code |
| `agents/executive/coo_agent_v2.py` | Production runtime code |
| `agents/ingestion_real.py` | Production runtime code |
| `agents/legal/__init__.py` | Production runtime code |
| `agents/legal/privacy_agent_v2.py` | Production runtime code |
| `agents/marketing/__init__.py` | Production runtime code |
| `agents/orchestrator_client.py` | Production runtime code |
| `agents/people_ops/__init__.py` | Production runtime code |
| `agents/people_ops/config_agent_v2.py` | Production runtime code |
| `agents/product/__init__.py` | Production runtime code |
| `agents/product/pm_agent_v2.py` | Production runtime code |
| `agents/prompts/customer_experience/success_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/customer_experience/support_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/customer_experience/voice_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/design/ab_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/design/brand_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/design/ux_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/engineering/architect_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/engineering/coder_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/engineering/devops_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/engineering/reviewer_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/executive/ceo_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/executive/cfo_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/executive/coo_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/legal/contract_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/legal/privacy_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/legal/risk_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/marketing/ads_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/marketing/analytics_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/marketing/content_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/marketing/seo_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/people_ops/config_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/people_ops/performance_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/people_ops/recruiter_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/product/pm_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/product/prioritizer_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/product/research_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/sales/ae_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/sales/revops_agent_v1.0.0.md` | Prompt/template |
| `agents/prompts/sales/sdr_agent_v1.0.0.md` | Prompt/template |
| `agents/pyproject.toml` | Production runtime code |
| `agents/registry.py` | Production runtime code |
| `agents/requirements.txt` | Production runtime code |
| `agents/sales/__init__.py` | Production runtime code |
| `agents/test_orchestrator_response_shape.py` | Test infrastructure |
| `agents/tests/__init__.py` | Test infrastructure |
| `agents/tests/conftest.py` | Test infrastructure |
| `agents/tests/engineering/__init__.py` | Test infrastructure |
| `agents/tests/executive/__init__.py` | Test infrastructure |
| `agents/tests/integration/__init__.py` | Test infrastructure |
| `agents/tests/integration/test_agent_dispatch_e2e.py` | Test infrastructure |
| `agents/tests/integration/test_tool_execution_real.py` | Test infrastructure |
| `agents/tests/test_base_agent.py` | Test infrastructure |
| `agents/tests/test_confidence_scorer.py` | Test infrastructure |
| `agents/tests/test_event_subscriber.py` | Test infrastructure |
| `agents/tests/test_phase65_v1_severity_reachability.py` | Test infrastructure |
| `agents/tests/test_specialist_real_web_actions.py` | Test infrastructure |
| `agents/tests/test_specialist_server_runtime.py` | Test infrastructure |
| `agents/tests/test_v2_department_agents.py` | Test infrastructure |
| `agents/tests/test_v2_operating_slice.py` | Test infrastructure |
| `archive/agents_v1/README.md` | Deprecated code |
| `archive/agents_v1/agents/customer_experience/success_agent.py` | Deprecated code |
| `archive/agents_v1/agents/customer_experience/support_agent.py` | Deprecated code |
| `archive/agents_v1/agents/customer_experience/voice_agent.py` | Deprecated code |
| `archive/agents_v1/agents/design/ab_agent.py` | Deprecated code |
| `archive/agents_v1/agents/design/brand_agent.py` | Deprecated code |
| `archive/agents_v1/agents/design/ux_agent.py` | Deprecated code |
| `archive/agents_v1/agents/engineering/architect_agent.py` | Deprecated code |
| `archive/agents_v1/agents/engineering/coder_agent.py` | Deprecated code |
| `archive/agents_v1/agents/engineering/devops_agent.py` | Deprecated code |
| `archive/agents_v1/agents/engineering/reviewer_agent.py` | Deprecated code |
| `archive/agents_v1/agents/executive/ceo_agent.py` | Deprecated code |
| `archive/agents_v1/agents/executive/cfo_agent.py` | Deprecated code |
| `archive/agents_v1/agents/executive/coo_agent.py` | Deprecated code |
| `archive/agents_v1/agents/legal/contract_agent.py` | Deprecated code |
| `archive/agents_v1/agents/legal/privacy_agent.py` | Deprecated code |
| `archive/agents_v1/agents/legal/risk_agent.py` | Deprecated code |
| `archive/agents_v1/agents/marketing/ads_agent.py` | Deprecated code |
| `archive/agents_v1/agents/marketing/analytics_agent.py` | Deprecated code |
| `archive/agents_v1/agents/marketing/content_agent.py` | Deprecated code |
| `archive/agents_v1/agents/marketing/seo_agent.py` | Deprecated code |
| `archive/agents_v1/agents/people_ops/config_agent.py` | Deprecated code |
| `archive/agents_v1/agents/people_ops/performance_agent.py` | Deprecated code |
| `archive/agents_v1/agents/people_ops/recruiter_agent.py` | Deprecated code |
| `archive/agents_v1/agents/product/pm_agent.py` | Deprecated code |
| `archive/agents_v1/agents/product/prioritizer_agent.py` | Deprecated code |
| `archive/agents_v1/agents/product/research_agent.py` | Deprecated code |
| `archive/agents_v1/agents/sales/ae_agent.py` | Deprecated code |
| `archive/agents_v1/agents/sales/revops_agent.py` | Deprecated code |
| `archive/agents_v1/agents/sales/sdr_agent.py` | Deprecated code |
| `archive/agents_v1/tests/agents/engineering/test_devops_agent.py` | Deprecated code |
| `archive/agents_v1/tests/agents/executive/test_ceo_agent.py` | Deprecated code |
| `archive/evals_regression_theater/README.md` | Deprecated code |
| `archive/evals_regression_theater/test_5min_established_facts.py` | Deprecated code |
| `archive/evals_regression_theater/test_action_loop_integration.py` | Deprecated code |
| `archive/evals_regression_theater/test_autonomous_learning_5min.py` | Deprecated code |
| `archive/evals_regression_theater/test_civilization_integration.py` | Deprecated code |
| `archive/evals_regression_theater/test_civilization_load.py` | Deprecated code |
| `archive/evals_regression_theater/test_comprehensive_gap_analysis.py` | Deprecated code |
| `archive/evals_regression_theater/test_institutions_evolution.py` | Deprecated code |
| `archive/evals_regression_theater/test_knowledge_retention.py` | Deprecated code |
| `archive/evals_regression_theater/test_model_benchmark_comparison.py` | Deprecated code |
| `archive/evals_regression_theater/test_model_comparison.py` | Deprecated code |
| `archive/evals_regression_theater/test_phase1_2_fixes.py` | Deprecated code |
| `archive/evals_regression_theater/test_phase3_dynamic_calibration.py` | Deprecated code |
| `archive/evals_regression_theater/test_phases_2_4_integration.py` | Deprecated code |
| `archive/evals_regression_theater/test_rag_accuracy_improvement.py` | Deprecated code |
| `archive/test_openai_integration_1min.py` | Deprecated code |
| `audit_artifacts/autonomy_open_world_5min/b4f4e467/analysis.json` | Generated artifact |
| `audit_artifacts/autonomy_open_world_5min/e618c07b/analysis.json` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/2e7f1df9-df2/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/2e7f1df9-df2/run_summary.json` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/42861d03/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/42861d03/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/42861d03/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/42861d03/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/42861d03/web_searches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/claims.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/learning_events.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/53a90eb9/web_searches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/54f030c1/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/54f030c1/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/54f030c1/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/actions.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/claims.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/failures.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/strategy_changes.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/8b995f89/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/claims.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/learning.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/d7ae85a4/web_searches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/claims.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e3fc9adc/web_searches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e8bd4b64/final_report.md` | Documentation |
| `audit_artifacts/autonomy_real_web_free_run/e8bd4b64/goals.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e8bd4b64/llm_calls.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e8bd4b64/web_fetches.jsonl` | Generated artifact |
| `audit_artifacts/autonomy_real_web_free_run/e8bd4b64/web_searches.jsonl` | Generated artifact |
| `audit_artifacts/civilization_free_run/2fae178e-3374-403b-84d1-d525994d3837/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/2fae178e-3374-403b-84d1-d525994d3837/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/35c21a36-9043-4040-8519-a6be7d9c8d6a/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/35c21a36-9043-4040-8519-a6be7d9c8d6a/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/3933c78a-86ca-483e-890f-4dfa2a309776/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/3933c78a-86ca-483e-890f-4dfa2a309776/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/4a628dae-a54d-41fb-a1f6-0c323867e4ac/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/4a628dae-a54d-41fb-a1f6-0c323867e4ac/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/4b922ca9-9f45-4339-9a48-90bae0d103d2/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/4b922ca9-9f45-4339-9a48-90bae0d103d2/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/527f57e4-9974-422d-806a-42398a16b10e/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/527f57e4-9974-422d-806a-42398a16b10e/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/7b7bbf8b-4378-4b00-a258-bfa58df8e381/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/7b7bbf8b-4378-4b00-a258-bfa58df8e381/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/8f94c7a5-67c3-4cb7-878f-0b8a6f4c5af7/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/8f94c7a5-67c3-4cb7-878f-0b8a6f4c5af7/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/97439e8c-771b-4c98-939b-7932bbf1b5f9/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/97439e8c-771b-4c98-939b-7932bbf1b5f9/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/99c7daf2-daa8-4ee7-bec1-61aa3a296d05/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/99c7daf2-daa8-4ee7-bec1-61aa3a296d05/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/9ad9888c-0f3a-497e-af0b-d1d11d9be6b2/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/9ad9888c-0f3a-497e-af0b-d1d11d9be6b2/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/b03b785c-d273-4273-b77d-f4a90fcfbb5c/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/b03b785c-d273-4273-b77d-f4a90fcfbb5c/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/b5b55d21-3392-48d6-b2b9-18386f94f66d/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/b5b55d21-3392-48d6-b2b9-18386f94f66d/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/c5c48466-73d8-4062-88a9-f63e09d9b1ee/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/c5c48466-73d8-4062-88a9-f63e09d9b1ee/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/d1d27c14-4b2c-4beb-aeb9-4a4be5e42499/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/d1d27c14-4b2c-4beb-aeb9-4a4be5e42499/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/d49be48c-7b3a-447c-999c-17dde2ef26c2/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/d49be48c-7b3a-447c-999c-17dde2ef26c2/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/e789162c-b757-4a89-bad0-785ae3b2d60b/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/e789162c-b757-4a89-bad0-785ae3b2d60b/result.json` | Generated artifact |
| `audit_artifacts/civilization_free_run/ebb0d979-9a19-4324-943e-a6caaec7a530/report.md` | Documentation |
| `audit_artifacts/civilization_free_run/ebb0d979-9a19-4324-943e-a6caaec7a530/result.json` | Generated artifact |
| `audit_artifacts/production_blocker_remediation/COMPILATION_STATUS.md` | Documentation |
| `audit_artifacts/production_blocker_remediation/COMPILATION_SUCCESS_FINAL_REPORT.md` | Documentation |
| `audit_artifacts/production_blocker_remediation/FINAL_AUDIT_REPORT.md` | Documentation |
| `audit_artifacts/production_blocker_remediation/INTEGRATED_VS_DEAD_CODE.md` | Documentation |
| `audit_artifacts/production_blocker_remediation/STEP_1_FINAL_REPORT.md` | Documentation |
| `audit_artifacts/production_deployment_execution/build_plan.sh` | Generated artifact |
| `audit_artifacts/production_deployment_execution/build_simulation_results.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/canary_rollout_results.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/deployment_summary.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/migrations_execution_log.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/openai_integration_test.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/pre_deploy_snapshot.json` | Generated artifact |
| `audit_artifacts/production_deployment_execution/preflight_checklist.md` | Documentation |
| `audit_artifacts/production_release_gate/01_BACKEND_SECURITY_TEST_RESULT.txt` | Documentation |
| `audit_artifacts/production_release_gate/CRITICAL_BLOCKERS.md` | Documentation |
| `audit_artifacts/true_autonomy_validation/AUDIT_LOG.md` | Documentation |
| `audit_artifacts/true_autonomy_validation/CRITICAL_GAPS.md` | Documentation |
| `audit_artifacts/true_autonomy_validation/FINAL_VERDICT.md` | Documentation |
| `autonomy/__init__.py` | Production runtime code |
| `autonomy/decision_engine.py` | Production runtime code |
| `autonomy/execution.py` | Production runtime code |
| `autonomy/feedback_loop.py` | Production runtime code |
| `autonomy/goal_manager.py` | Production runtime code |
| `autonomy/institutional_contracts.py` | Production runtime code |
| `autonomy/integration.py` | Production runtime code |
| `autonomy/llm_service.py` | Production runtime code |
| `autonomy/measurement.py` | Production runtime code |
| `autonomy/objective.py` | Production runtime code |
| `autonomy/perception_adapter.py` | Production runtime code |
| `autonomy/realtime_integration.py` | Production runtime code |
| `autonomy/self_correction.py` | Production runtime code |
| `backend/Dockerfile` | Development tooling |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782272951648/result.json` | Production runtime code |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782272951648/summary.txt` | Production runtime code |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782273010438/result.json` | Production runtime code |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782273010438/summary.txt` | Production runtime code |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782274281558/result.json` | Production runtime code |
| `backend/audit_artifacts/autonomy_unconstrained_5min/run_1782274281558/summary.txt` | Production runtime code |
| `backend/audit_artifacts/production_blocker_remediation/error_categories.txt` | Production runtime code |
| `backend/audit_artifacts/production_blocker_remediation/typescript_errors_raw.txt` | Production runtime code |
| `backend/jest.config.ts` | Development tooling |
| `backend/learning_run_learning_run_1782299703222.json` | Production runtime code |
| `backend/learning_run_learning_run_1782300767438.json` | Production runtime code |
| `backend/learning_run_learning_run_1782300969220.json` | Production runtime code |
| `backend/learning_run_learning_run_1782300978795.json` | Production runtime code |
| `backend/learning_run_learning_run_1782301080838.json` | Production runtime code |
| `backend/package-lock.json` | Development tooling |
| `backend/package.json` | Development tooling |
| `backend/scripts/autonomy-1min-realworld-test.ts` | Production runtime code |
| `backend/scripts/autonomy-real-world-2min-unconstrained.ts` | Production runtime code |
| `backend/scripts/autonomy-real-world-5min-unconstrained.ts` | Production runtime code |
| `backend/src/adapters/real-web-adapter.ts` | Production runtime code |
| `backend/src/adapters/url-safety.ts` | Production runtime code |
| `backend/src/adapters/web-adapter.ts` | Production runtime code |
| `backend/src/agent-registry.ts` | Production runtime code |
| `backend/src/cli/autonomy.ts` | Production runtime code |
| `backend/src/cli/db-table-usage.ts` | Production runtime code |
| `backend/src/cli/run-bounded-learning.ts` | Production runtime code |
| `backend/src/cli/run-longitudinal-learning.ts` | Production runtime code |
| `backend/src/cli/score-validation.ts` | Production runtime code |
| `backend/src/cli/smoke-durable-execution.ts` | Production runtime code |
| `backend/src/cli/supervised-free-run.ts` | Production runtime code |
| `backend/src/cli/supervised-runtime.ts` | Production runtime code |
| `backend/src/config/__init__.py` | Production runtime code |
| `backend/src/config/provider_config.py` | Production runtime code |
| `backend/src/db/client.ts` | Production runtime code |
| `backend/src/db/dsn.ts` | Production runtime code |
| `backend/src/db/kafka.ts` | Production runtime code |
| `backend/src/db/migrate.ts` | Production runtime code |
| `backend/src/db/migrations/001_agent_state.sql` | Database migration |
| `backend/src/db/migrations/002_agent_memory.sql` | Database migration |
| `backend/src/db/migrations/003_shared_knowledge.sql` | Database migration |
| `backend/src/db/migrations/004_decision_log.sql` | Database migration |
| `backend/src/db/migrations/005_event_history.sql` | Database migration |
| `backend/src/db/migrations/006_prompt_registry.sql` | Database migration |
| `backend/src/db/migrations/007_performance_metrics.sql` | Database migration |
| `backend/src/db/migrations/008_customer_data.sql` | Database migration |
| `backend/src/db/migrations/009_trust_scores.sql` | Database migration |
| `backend/src/db/migrations/010_beliefs.sql` | Database migration |
| `backend/src/db/migrations/011_prediction_ledger.sql` | Database migration |
| `backend/src/db/migrations/012_decision_log_chain.sql` | Database migration |
| `backend/src/db/migrations/013_override_queue.sql` | Database migration |
| `backend/src/db/migrations/014_decision_log_immutability_triggers.sql` | Database migration |
| `backend/src/db/migrations/015_agent_memories.sql` | Database migration |
| `backend/src/db/migrations/016_resolution_service_role.sql` | Database migration |
| `backend/src/db/migrations/017_agent_memories_lifecycle.sql` | Database migration |
| `backend/src/db/migrations/018_refoundation_canonical_schema.sql` | Database migration |
| `backend/src/db/migrations/019_durable_execution.sql` | Database migration |
| `backend/src/db/migrations/021_observability_traces.sql` | Database migration |
| `backend/src/db/migrations/022_autonomy_tasks.sql` | Database migration |
| `backend/src/db/migrations/023_autonomy_episodes.sql` | Database migration |
| `backend/src/db/migrations/024_perception_infrastructure.sql` | Database migration |
| `backend/src/db/migrations/025_goal_management_clean.sql` | Database migration |
| `backend/src/db/migrations/026_civilization_learning_entities.sql` | Database migration |
| `backend/src/db/migrations/027_calibration_constitution.sql` | Database migration |
| `backend/src/db/migrations/028_trust_policy_versions.sql` | Database migration |
| `backend/src/db/migrations/029_calibration_change_requests.sql` | Database migration |
| `backend/src/db/migrations/030_trust_impact_assessment.sql` | Database migration |
| `backend/src/db/migrations/031_trust_reputation_ledger.sql` | Database migration |
| `backend/src/db/migrations/032_calibration_drift_monitor.sql` | Database migration |
| `backend/src/db/migrations/033_artifacts.sql` | Database migration |
| `backend/src/db/migrations/034_learner_infrastructure.sql` | Database migration |
| `backend/src/db/migrations/040_governance_rbac.sql` | Database migration |
| `backend/src/db/migrations/050_autonomy_action_loop.sql` | Database migration |
| `backend/src/db/migrations/051_fix_fk_constraints.sql` | Database migration |
| `backend/src/db/migrations/051_team_activations.sql` | Database migration |
| `backend/src/db/migrations/052_specialist_http_endpoint.sql` | Database migration |
| `backend/src/db/migrations/052b_institutions.sql` | Database migration |
| `backend/src/db/migrations/053_work_assignment_schema.sql` | Database migration |
| `backend/src/db/migrations/054_goal_hierarchies.sql` | Database migration |
| `backend/src/db/migrations/055_deadlock_prevention.sql` | Database migration |
| `backend/src/db/migrations/056_production_deployment.sql` | Database migration |
| `backend/src/db/migrations/057_reputation_learning.sql` | Database migration |
| `backend/src/db/migrations/058_adaptive_strategy.sql` | Database migration |
| `backend/src/db/migrations/058_bounded_learning.sql` | Database migration |
| `backend/src/db/migrations/059_calibration_framework.sql` | Database migration |
| `backend/src/db/migrations/059_governance_reputation_integration.sql` | Database migration |
| `backend/src/db/migrations/060_coalition_formation.sql` | Database migration |
| `backend/src/db/migrations/061_add_goal_depth_column.sql` | Database migration |
| `backend/src/db/migrations/062_runtime_schema_compatibility.sql` | Database migration |
| `backend/src/db/migrations/063_runtime_schema_compatibility_followup.sql` | Database migration |
| `backend/src/db/migrations/064_department_reputation_score.sql` | Database migration |
| `backend/src/db/migrations/065_reputation_audit_compatibility.sql` | Database migration |
| `backend/src/db/migrations/066_reward_schema_compatibility.sql` | Database migration |
| `backend/src/db/migrations/067_reward_legacy_defaults.sql` | Database migration |
| `backend/src/db/migrations/068_learner_schema_compatibility.sql` | Database migration |
| `backend/src/db/migrations/069_trajectory_success_compatibility.sql` | Database migration |
| `backend/src/db/migrations/070_eval_schema_compatibility.sql` | Database migration |
| `backend/src/db/migrations/071_eval_run_timestamp_default.sql` | Database migration |
| `backend/src/db/migrations/072_specialist_schema_compatibility.sql` | Database migration |
| `backend/src/db/migrations/073_evidence_content_text.sql` | Database migration |
| `backend/src/db/migrations/074_governance_coalition_formations.sql` | Database migration |
| `backend/src/db/migrations/075_agent_tasks_canonical_view.sql` | Database migration |
| `backend/src/db/migrations/076_build_ledger.sql` | Database migration |
| `backend/src/db/migrations/077_civilization_vertical_slice.sql` | Database migration |
| `backend/src/db/migrations/078_agent_membership_id_compatibility.sql` | Database migration |
| `backend/src/db/migrations/079_identity_authority.sql` | Database migration |
| `backend/src/db/migrations/080_event_log.sql` | Database migration |
| `backend/src/db/migrations/081_resource_ledger.sql` | Database migration |
| `backend/src/db/migrations/082_resource_reservations.sql` | Database migration |
| `backend/src/db/migrations/083_transactional_outbox.sql` | Database migration |
| `backend/src/db/migrations/084_authority_chain.sql` | Database migration |
| `backend/src/db/migrations/085_authority_chain_decision_actor_compatibility.sql` | Database migration |
| `backend/src/db/migrations/086_key_ring.sql` | Database migration |
| `backend/src/db/migrations/087_hash_chain_anchors.sql` | Database migration |
| `backend/src/db/migrations/088_evidence_registry_events.sql` | Database migration |
| `backend/src/db/migrations/089_department_institution_compatibility.sql` | Database migration |
| `backend/src/db/migrations/090_department_parent_type_compatibility.sql` | Database migration |
| `backend/src/db/migrations/091_department_institution_trigger_restore.sql` | Database migration |
| `backend/src/db/migrations/092_agent_task_events_canonical_view.sql` | Database migration |
| `backend/src/db/migrations/093_resolution_service_role_grant_repair.sql` | Database migration |
| `backend/src/db/migrations/094_prediction_ledger_hardness_compatibility.sql` | Database migration |
| `backend/src/db/migrations/095_prediction_ledger_reserve_fields_compatibility.sql` | Database migration |
| `backend/src/db/migrations/096_idempotency_store.sql` | Database migration |
| `backend/src/db/migrations/097_self_modification_validation_compatibility.sql` | Database migration |
| `backend/src/db/migrations/098_governance_kill_switch.sql` | Database migration |
| `backend/src/db/migrations/099_trajectory_simulation_compatibility.sql` | Database migration |
| `backend/src/db/migrations/100_saga_coordinator.sql` | Database migration |
| `backend/src/db/migrations/101_evidence_vector_index.sql` | Database migration |
| `backend/src/db/migrations/102_domain_registry.sql` | Database migration |
| `backend/src/db/migrations/103_generality_metric_tracker.sql` | Database migration |
| `backend/src/db/migrations/104_candidate_regression_tests.sql` | Database migration |
| `backend/src/db/migrations/105_skill_library.sql` | Database migration |
| `backend/src/db/migrations/106_proof_of_competence.sql` | Database migration |
| `backend/src/db/migrations/107_capability_expansion_gate.sql` | Database migration |
| `backend/src/db/migrations/108_skill_promotion_loop.sql` | Database migration |
| `backend/src/db/migrations/109_judiciary.sql` | Database migration |
| `backend/src/db/migrations/110_skill_usage_events.sql` | Database migration |
| `backend/src/db/migrations/111_self_improvement_loop.sql` | Database migration |
| `backend/src/db/migrations/112_fix_goal_completion_metric_uuid.sql` | Database migration |
| `backend/src/db/migrations/113_institutional_knowledge_promotions.sql` | Database migration |
| `backend/src/db/migrations/114_self_memory_retrievable.sql` | Database migration |
| `backend/src/db/migrations/115_autonomous_promotions.sql` | Database migration |
| `backend/src/db/migrations/116_persistent_agents.sql` | Database migration |
| `backend/src/db/migrations/117_artifact_lineage_identity.sql` | Database migration |
| `backend/src/db/migrations/118_contradictions_and_demotions.sql` | Database migration |
| `backend/src/db/migrations/119_source_relevance.sql` | Database migration |
| `backend/src/db/migrations/120_prediction_ledger_registration_invariants.sql` | Database migration |
| `backend/src/db/migrations/121_runtime_schema_drift_repairs.sql` | Database migration |
| `backend/src/db/migrations/122_reward_schema_drift_repairs.sql` | Database migration |
| `backend/src/db/migrations/123_reward_calculation_schema_drift_repairs.sql` | Database migration |
| `backend/src/db/migrations/124_eval_schema_drift_repairs.sql` | Database migration |
| `backend/src/db/migrations/125_decision_log_protocol_version.sql` | Database migration |
| `backend/src/db/migrations/126_decision_log_attempt_id.sql` | Database migration |
| `backend/src/db/migrations/127_runtime_governance_artifacts.sql` | Database migration |
| `backend/src/db/migrations/128_event_bus_outbox.sql` | Database migration |
| `backend/src/db/migrations/129_civilization_kernel.sql` | Database migration |
| `backend/src/db/migrations/129_longitudinal_mission_evidence.sql` | Database migration |
| `backend/src/db/migrations/130_citizenship.sql` | Database migration |
| `backend/src/db/migrations/131_societies_and_institution_charters.sql` | Database migration |
| `backend/src/db/migrations/132_institution_coalitions.sql` | Database migration |
| `backend/src/db/migrations/133_missions.sql` | Database migration |
| `backend/src/db/migrations/134_civilization_economy.sql` | Database migration |
| `backend/src/db/migrations/135_governance.sql` | Database migration |
| `backend/src/db/migrations/136_judiciary.sql` | Database migration |
| `backend/src/db/migrations/137_collective_epistemics.sql` | Database migration |
| `backend/src/db/migrations/138_safe_evolution.sql` | Database migration |
| `backend/src/db/migrations/139_capability_expansion.sql` | Database migration |
| `backend/src/db/migrations/140_civilization_os.sql` | Database migration |
| `backend/src/db/migrations/140_governed_capability_runtime.sql` | Database migration |
| `backend/src/db/rollbacks/018_refoundation_canonical_schema.down.sql` | Production runtime code |
| `backend/src/db/run_migrations.py` | Production runtime code |
| `backend/src/db/unsupported_migrations/020_evaluation_manifests.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/025_autonomy_goals.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/025_goal_management.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/026_autonomy_plans.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/026_phases_5_8_integrated.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/027_phases_9_13_integrated.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/027_reward_system.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/028_civilization_learning_structure.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/028_eval_harness.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/029_learner_infrastructure.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/029_rollback_infrastructure.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/030_self_modification.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/031_artifact_registry.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/033_rbac.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/034_policy_control.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/035_canary_deployment.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/035_simulator_infrastructure.sql.disabled` | Production runtime code |
| `backend/src/db/unsupported_migrations/README.md` | Production runtime code |
| `backend/src/feature-gates.ts` | Production runtime code |
| `backend/src/health.ts` | Production runtime code |
| `backend/src/http-errors.ts` | Production runtime code |
| `backend/src/middleware/civilization-request-validator.ts` | Production runtime code |
| `backend/src/middleware/learning.middleware.ts` | Production runtime code |
| `backend/src/routes/agents.routes.ts` | Production runtime code |
| `backend/src/routes/audit.routes.ts` | Production runtime code |
| `backend/src/routes/autonomy-dashboard.routes.ts` | Production runtime code |
| `backend/src/routes/autonomy-orchestrator.routes.ts` | Production runtime code |
| `backend/src/routes/autonomy-tasks.routes.ts` | Production runtime code |
| `backend/src/routes/capabilities.routes.ts` | Production runtime code |
| `backend/src/routes/capability-expansion.routes.ts` | Production runtime code |
| `backend/src/routes/citizenship.routes.ts` | Production runtime code |
| `backend/src/routes/civilization-governance.routes.ts` | Production runtime code |
| `backend/src/routes/civilization-kernel.routes.ts` | Production runtime code |
| `backend/src/routes/civilization-operator.routes.ts` | Production runtime code |
| `backend/src/routes/civilization-os.routes.ts` | Production runtime code |
| `backend/src/routes/coalition.routes.ts` | Production runtime code |
| `backend/src/routes/collective-knowledge.routes.ts` | Production runtime code |
| `backend/src/routes/credential.routes.ts` | Production runtime code |
| `backend/src/routes/evals.routes.ts.disabled` | Production runtime code |
| `backend/src/routes/goal-hierarchy.routes.ts` | Production runtime code |
| `backend/src/routes/goal.routes.ts.disabled` | Production runtime code |
| `backend/src/routes/governance-proposals.routes.ts` | Production runtime code |
| `backend/src/routes/governance.routes.ts` | Production runtime code |
| `backend/src/routes/identity.routes.ts` | Production runtime code |
| `backend/src/routes/institution-work-assignment.routes.ts` | Production runtime code |
| `backend/src/routes/judiciary-case.routes.ts` | Production runtime code |
| `backend/src/routes/mission.routes.ts` | Production runtime code |
| `backend/src/routes/override.routes.ts` | Production runtime code |
| `backend/src/routes/param-validation.ts` | Production runtime code |
| `backend/src/routes/phase3-hardening.routes.ts` | Production runtime code |
| `backend/src/routes/phases-6-8.routes.ts.disabled` | Production runtime code |
| `backend/src/routes/phases-9-13.routes.ts.disabled` | Production runtime code |
| `backend/src/routes/resource-ledger.routes.ts` | Production runtime code |
| `backend/src/routes/safe-evolution.routes.ts` | Production runtime code |
| `backend/src/routes/society.routes.ts` | Production runtime code |
| `backend/src/routes/system.routes.ts` | Production runtime code |
| `backend/src/routes/treasury.routes.ts` | Production runtime code |
| `backend/src/runtime-mode.ts` | Production runtime code |
| `backend/src/runtime/shutdown.ts` | Production runtime code |
| `backend/src/security.ts` | Production runtime code |
| `backend/src/server.ts` | Production runtime code |
| `backend/src/services/action-executor.service.ts` | Production runtime code |
| `backend/src/services/adaptive-strategy.service.ts` | Production runtime code |
| `backend/src/services/audit-log.service.ts` | Production runtime code |
| `backend/src/services/autonomous-promotion.service.ts` | Production runtime code |
| `backend/src/services/autonomy-action-planner.service.ts` | Production runtime code |
| `backend/src/services/autonomy-civilization-bridge.service.ts` | Production runtime code |
| `backend/src/services/autonomy-metrics.service.ts` | Production runtime code |
| `backend/src/services/autonomy-orchestrator.service.ts` | Production runtime code |
| `backend/src/services/autonomy-run.service.ts` | Production runtime code |
| `backend/src/services/bayesian.service.ts` | Production runtime code |
| `backend/src/services/belief-demotion.service.ts` | Production runtime code |
| `backend/src/services/bounded-learning-run.service.ts` | Production runtime code |
| `backend/src/services/calibration-aware-routing.service.ts` | Production runtime code |
| `backend/src/services/calibration-change-governance.service.ts` | Production runtime code |
| `backend/src/services/calibration-constitution.service.ts` | Production runtime code |
| `backend/src/services/calibration-drift-monitor.service.ts` | Production runtime code |
| `backend/src/services/candidate-evaluation.service.ts` | Production runtime code |
| `backend/src/services/capability-expansion-gate.service.ts` | Production runtime code |
| `backend/src/services/capability-expansion.service.ts` | Production runtime code |
| `backend/src/services/capability-runtime.service.ts` | Production runtime code |
| `backend/src/services/citizenship.service.ts` | Production runtime code |
| `backend/src/services/civilization-kernel.service.ts` | Production runtime code |
| `backend/src/services/civilization-live-flow.service.ts` | Production runtime code |
| `backend/src/services/civilization-metrics.service.ts` | Production runtime code |
| `backend/src/services/civilization-operator.service.ts` | Production runtime code |
| `backend/src/services/civilization-os.service.ts` | Production runtime code |
| `backend/src/services/civilization-runtime.service.ts` | Production runtime code |
| `backend/src/services/civilization-scheduler.service.ts` | Production runtime code |
| `backend/src/services/civilization.service.ts` | Production runtime code |
| `backend/src/services/claim-accuracy-tracker.service.ts` | Production runtime code |
| `backend/src/services/claim-grounding.service.ts` | Production runtime code |
| `backend/src/services/coalition-formation.service.ts` | Production runtime code |
| `backend/src/services/coalition.service.ts` | Production runtime code |
| `backend/src/services/collective-knowledge.service.ts` | Production runtime code |
| `backend/src/services/confidence.service.ts` | Production runtime code |
| `backend/src/services/crash-recovery.service.ts` | Production runtime code |
| `backend/src/services/credential.service.ts` | Production runtime code |
| `backend/src/services/deadlock-detector.service.ts` | Production runtime code |
| `backend/src/services/deterministic-benchmark.service.ts` | Production runtime code |
| `backend/src/services/domain-registry.service.ts` | Production runtime code |
| `backend/src/services/durable-execution.service.ts` | Production runtime code |
| `backend/src/services/dynamic-calibration.service.ts` | Production runtime code |
| `backend/src/services/ensemble.service.ts` | Production runtime code |
| `backend/src/services/eval-harness.service.ts` | Production runtime code |
| `backend/src/services/event-bus.service.ts` | Production runtime code |
| `backend/src/services/event-log.service.ts` | Production runtime code |
| `backend/src/services/evidence-registry.service.ts` | Production runtime code |
| `backend/src/services/evidence-vector-index.service.ts` | Production runtime code |
| `backend/src/services/falsifiable-prediction.service.ts` | Production runtime code |
| `backend/src/services/generality-metric-tracker.service.ts` | Production runtime code |
| `backend/src/services/goal-formation.service.ts` | Production runtime code |
| `backend/src/services/goal-hierarchy.service.ts` | Production runtime code |
| `backend/src/services/goal-manager.service.ts` | Production runtime code |
| `backend/src/services/goal-source-discovery.service.ts` | Production runtime code |
| `backend/src/services/governance-rbac.service.ts` | Production runtime code |
| `backend/src/services/governance-reputation-integration.service.ts` | Production runtime code |
| `backend/src/services/governance.service.ts` | Production runtime code |
| `backend/src/services/grounded-resolver.service.ts` | Production runtime code |
| `backend/src/services/hash-chain-anchor.service.ts` | Production runtime code |
| `backend/src/services/idempotency-store.service.ts` | Production runtime code |
| `backend/src/services/identity-authority.service.ts` | Production runtime code |
| `backend/src/services/independent-resolver.service.ts` | Production runtime code |
| `backend/src/services/input-validator.service.ts` | Production runtime code |
| `backend/src/services/institution-claim-vetting.service.ts` | Production runtime code |
| `backend/src/services/institution-governance.service.ts` | Production runtime code |
| `backend/src/services/institution-work-assignment.service.ts` | Production runtime code |
| `backend/src/services/institutional-knowledge-bridge.service.ts` | Production runtime code |
| `backend/src/services/institutional-synthesis.service.ts` | Production runtime code |
| `backend/src/services/institutions.service.ts` | Production runtime code |
| `backend/src/services/integration.service.ts` | Production runtime code |
| `backend/src/services/judiciary-case.service.ts` | Production runtime code |
| `backend/src/services/judiciary-review.service.ts` | Production runtime code |
| `backend/src/services/judiciary.service.ts` | Production runtime code |
| `backend/src/services/kb-expansion.service.ts` | Production runtime code |
| `backend/src/services/kill-switch.service.ts` | Production runtime code |
| `backend/src/services/knowledge-persistence.service.ts` | Production runtime code |
| `backend/src/services/learner.service.ts` | Production runtime code |
| `backend/src/services/learning.service.ts` | Production runtime code |
| `backend/src/services/learning_bridge.py` | Production runtime code |
| `backend/src/services/llm-provider.service.ts` | Production runtime code |
| `backend/src/services/load-test-harness.service.ts` | Production runtime code |
| `backend/src/services/longitudinal-learning-harness.service.ts` | Production runtime code |
| `backend/src/services/loop-detector.service.ts` | Production runtime code |
| `backend/src/services/memory-promotion-pipeline.service.ts` | Production runtime code |
| `backend/src/services/memory-retrieval.service.ts` | Production runtime code |
| `backend/src/services/memory-store.service.ts` | Production runtime code |
| `backend/src/services/metrics.service.ts` | Production runtime code |
| `backend/src/services/mission.service.ts` | Production runtime code |
| `backend/src/services/multi-agent-ensemble.service.ts` | Production runtime code |
| `backend/src/services/observability.service.ts` | Production runtime code |
| `backend/src/services/orchestrator.service.ts` | Production runtime code |
| `backend/src/services/override-queue.service.ts` | Production runtime code |
| `backend/src/services/perception.service.ts` | Production runtime code |
| `backend/src/services/persistent-agent-registry.service.ts` | Production runtime code |
| `backend/src/services/persistent-trust-scorer.service.ts` | Production runtime code |
| `backend/src/services/planner.service.ts` | Production runtime code |
| `backend/src/services/policy-enforcement.service.ts` | Production runtime code |
| `backend/src/services/proof-of-competence.service.ts` | Production runtime code |
| `backend/src/services/protected-surface-validator.service.ts` | Production runtime code |
| `backend/src/services/provenance.service.ts` | Production runtime code |
| `backend/src/services/rag.service.ts` | Production runtime code |
| `backend/src/services/rate-limiter.service.ts` | Production runtime code |
| `backend/src/services/reflection.service.ts` | Production runtime code |
| `backend/src/services/regression-test-generator.service.ts` | Production runtime code |
| `backend/src/services/reputation-learning.service.ts` | Production runtime code |
| `backend/src/services/reputation-scale.service.ts` | Production runtime code |
| `backend/src/services/resolution-service.service.ts` | Production runtime code |
| `backend/src/services/resource-ledger.service.ts` | Production runtime code |
| `backend/src/services/reward-calculator.service.ts` | Production runtime code |
| `backend/src/services/risk-tier-classifier.service.ts` | Production runtime code |
| `backend/src/services/rollback.service.ts` | Production runtime code |
| `backend/src/services/run-guard.service.ts` | Production runtime code |
| `backend/src/services/safe-evolution.service.ts` | Production runtime code |
| `backend/src/services/safety.service.ts` | Production runtime code |
| `backend/src/services/saga-coordinator.service.ts` | Production runtime code |
| `backend/src/services/self-modification-validator.service.ts` | Production runtime code |
| `backend/src/services/simulator.service.ts` | Production runtime code |
| `backend/src/services/skill-canary.service.ts` | Production runtime code |
| `backend/src/services/skill-deployment.service.ts` | Production runtime code |
| `backend/src/services/skill-library.service.ts` | Production runtime code |
| `backend/src/services/skill-promotion-loop.service.ts` | Production runtime code |
| `backend/src/services/skill-retrieval.service.ts` | Production runtime code |
| `backend/src/services/society.service.ts` | Production runtime code |
| `backend/src/services/source-discovery.service.ts` | Production runtime code |
| `backend/src/services/structured-logger.service.ts` | Production runtime code |
| `backend/src/services/supervised-free-run.service.ts` | Production runtime code |
| `backend/src/services/supervised-runtime.service.ts` | Production runtime code |
| `backend/src/services/symbolic.service.ts` | Production runtime code |
| `backend/src/services/task-engine.service.ts` | Production runtime code |
| `backend/src/services/team-activation.service.ts` | Production runtime code |
| `backend/src/services/trajectory-store.service.ts` | Production runtime code |
| `backend/src/services/transactional-outbox.service.ts` | Production runtime code |
| `backend/src/services/treasury.service.ts` | Production runtime code |
| `backend/src/services/trust-impact-assessment.service.ts` | Production runtime code |
| `backend/src/services/trust-policy-canary.service.ts` | Production runtime code |
| `backend/src/services/trust-policy.service.ts` | Production runtime code |
| `backend/src/services/trust-reputation.service.ts` | Production runtime code |
| `backend/src/services/trust-scoring.service.ts` | Production runtime code |
| `backend/src/services/trustworthiness.service.ts` | Production runtime code |
| `backend/src/services/worker-coordinator.service.ts` | Production runtime code |
| `backend/src/types/action.types.ts` | Production runtime code |
| `backend/src/types/capability.types.ts` | Production runtime code |
| `backend/src/types/specialist-roles.ts` | Production runtime code |
| `backend/src/workers/civilization-scheduler-worker.ts` | Production runtime code |
| `backend/src/workers/outbox-worker.ts` | Production runtime code |
| `backend/src/workers/task-worker.ts` | Production runtime code |
| `backend/tests/action-loop.test.ts` | Test infrastructure |
| `backend/tests/adapters-and-reflection.test.ts` | Test infrastructure |
| `backend/tests/agent-registry.test.ts` | Test infrastructure |
| `backend/tests/agentco-5min-vetting.test.ts` | Test infrastructure |
| `backend/tests/api-safety-gates.test.ts` | Test infrastructure |
| `backend/tests/audit-chain-cross-writer.test.ts` | Test infrastructure |
| `backend/tests/autonomous-promotion.test.ts` | Test infrastructure |
| `backend/tests/autonomy-action-planner-env.test.ts` | Test infrastructure |
| `backend/tests/autonomy-run-reuse.test.ts` | Test infrastructure |
| `backend/tests/bounded-goal-formation-e2e.test.ts` | Test infrastructure |
| `backend/tests/bounded-learning-cli-guard.test.ts` | Test infrastructure |
| `backend/tests/bounded-learning-integration.test.ts` | Test infrastructure |
| `backend/tests/bounded-learning-production-guard.test.ts` | Test infrastructure |
| `backend/tests/bounded-learning-real-web-smoke.test.ts` | Test infrastructure |
| `backend/tests/calibration-constitution.test.ts` | Test infrastructure |
| `backend/tests/calibration-driven-planning.test.ts` | Test infrastructure |
| `backend/tests/calibration-registration-invariants.test.ts` | Test infrastructure |
| `backend/tests/capability-expansion-gate.test.ts` | Test infrastructure |
| `backend/tests/capability-expansion.test.ts` | Test infrastructure |
| `backend/tests/capability-runtime.test.ts` | Test infrastructure |
| `backend/tests/citizenship.test.ts` | Test infrastructure |
| `backend/tests/civilization-adversarial.test.ts` | Test infrastructure |
| `backend/tests/civilization-aware-rag.test.ts` | Test infrastructure |
| `backend/tests/civilization-e2e-scenarios.test.ts` | Test infrastructure |
| `backend/tests/civilization-kernel.test.ts` | Test infrastructure |
| `backend/tests/civilization-learning-backbone-e2e.test.ts` | Test infrastructure |
| `backend/tests/civilization-learning-backbone-live.test.ts` | Test infrastructure |
| `backend/tests/civilization-learning-e2e.test.ts` | Test infrastructure |
| `backend/tests/civilization-live-flow-e2e.test.ts` | Test infrastructure |
| `backend/tests/civilization-operator.test.ts` | Test infrastructure |
| `backend/tests/civilization-os.test.ts` | Test infrastructure |
| `backend/tests/civilization-real-routing.test.ts` | Test infrastructure |
| `backend/tests/civilization-reliability.test.ts` | Test infrastructure |
| `backend/tests/civilization-runtime-live-e2e.test.ts` | Test infrastructure |
| `backend/tests/civilization-runtime-reachability.test.ts` | Test infrastructure |
| `backend/tests/civilization-runtime-routes.test.ts` | Test infrastructure |
| `backend/tests/civilization-scheduler.test.ts` | Test infrastructure |
| `backend/tests/claim-grounding.test.ts` | Test infrastructure |
| `backend/tests/coalitions.test.ts` | Test infrastructure |
| `backend/tests/collective-knowledge.test.ts` | Test infrastructure |
| `backend/tests/contradiction-learning-e2e.test.ts` | Test infrastructure |
| `backend/tests/d1-source-discovery-slice.test.ts` | Test infrastructure |
| `backend/tests/domain-registry.test.ts` | Test infrastructure |
| `backend/tests/dsn-routing.test.ts` | Test infrastructure |
| `backend/tests/durable-execution-real-tasks.test.ts` | Test infrastructure |
| `backend/tests/ensemble-live-adapter.test.ts` | Test infrastructure |
| `backend/tests/event-bus-outbox.test.ts` | Test infrastructure |
| `backend/tests/event-log.test.ts` | Test infrastructure |
| `backend/tests/evidence-registry.test.ts` | Test infrastructure |
| `backend/tests/evidence-vector-index.test.ts` | Test infrastructure |
| `backend/tests/falsifiable-calibration-e2e.test.ts` | Test infrastructure |
| `backend/tests/feature-gates.test.ts` | Test infrastructure |
| `backend/tests/full-autonomy-integration.test.ts` | Test infrastructure |
| `backend/tests/generality-metric-tracker.test.ts` | Test infrastructure |
| `backend/tests/goal-formation-supervised-free-run.test.ts` | Test infrastructure |
| `backend/tests/goal-relevant-source-discovery-e2e.test.ts` | Test infrastructure |
| `backend/tests/governance-coalition-integration.test.ts` | Test infrastructure |
| `backend/tests/governance.test.ts` | Test infrastructure |
| `backend/tests/grounded-resolver.test.ts` | Test infrastructure |
| `backend/tests/hash-chain-anchor.test.ts` | Test infrastructure |
| `backend/tests/health-contract.test.ts` | Test infrastructure |
| `backend/tests/helm-deployment-contract.test.ts` | Test infrastructure |
| `backend/tests/idempotency-store.test.ts` | Test infrastructure |
| `backend/tests/identity-authority.test.ts` | Test infrastructure |
| `backend/tests/institution-claim-vetting.test.ts` | Test infrastructure |
| `backend/tests/institutional-synthesis.test.ts` | Test infrastructure |
| `backend/tests/integration/audit-log.test.ts` | Test infrastructure |
| `backend/tests/integration/event-bus.test.ts` | Test infrastructure |
| `backend/tests/integration/memory-store.test.ts` | Test infrastructure |
| `backend/tests/integration/override-queue.test.ts` | Test infrastructure |
| `backend/tests/judiciary-case.test.ts` | Test infrastructure |
| `backend/tests/judiciary.test.ts` | Test infrastructure |
| `backend/tests/key-hygiene.test.ts` | Test infrastructure |
| `backend/tests/kill-switch.test.ts` | Test infrastructure |
| `backend/tests/learning-candidate-registry.test.ts` | Test infrastructure |
| `backend/tests/llm-provider.test.ts` | Test infrastructure |
| `backend/tests/longitudinal-learning-harness.test.ts` | Test infrastructure |
| `backend/tests/main-loop-kill-switch.test.ts` | Test infrastructure |
| `backend/tests/memory-retrieval.test.ts` | Test infrastructure |
| `backend/tests/missions.test.ts` | Test infrastructure |
| `backend/tests/multi-agent-ensemble-live-adapter.test.ts` | Test infrastructure |
| `backend/tests/orchestrator-real-metrics.test.ts` | Test infrastructure |
| `backend/tests/outbox-worker.test.ts` | Test infrastructure |
| `backend/tests/persistent-agents.test.ts` | Test infrastructure |
| `backend/tests/phase1-integration.test.ts` | Test infrastructure |
| `backend/tests/phase2-long-term-coordination.test.ts` | Test infrastructure |
| `backend/tests/phase3-hardening.test.ts` | Test infrastructure |
| `backend/tests/phase4-production-deployment.test.ts` | Test infrastructure |
| `backend/tests/phase5-calibration-groundwork.test.ts` | Test infrastructure |
| `backend/tests/planner-claim-bias.test.ts` | Test infrastructure |
| `backend/tests/prompt-injection-e2e.test.ts` | Test infrastructure |
| `backend/tests/proof-of-competence.test.ts` | Test infrastructure |
| `backend/tests/protected-surface-enforcer.test.ts` | Test infrastructure |
| `backend/tests/rag-real-retrieval.test.ts` | Test infrastructure |
| `backend/tests/red-team-corpus.test.ts` | Test infrastructure |
| `backend/tests/regression-test-generator.test.ts` | Test infrastructure |
| `backend/tests/reputation-adaptive-integration.test.ts` | Test infrastructure |
| `backend/tests/resource-ledger.test.ts` | Test infrastructure |
| `backend/tests/risk-tier-classifier.test.ts` | Test infrastructure |
| `backend/tests/route-auth-contract.test.ts` | Test infrastructure |
| `backend/tests/runtime-mode.test.ts` | Test infrastructure |
| `backend/tests/safe-evolution.test.ts` | Test infrastructure |
| `backend/tests/safety-hardening.test.ts` | Test infrastructure |
| `backend/tests/saga-coordinator.test.ts` | Test infrastructure |
| `backend/tests/security.test.ts` | Test infrastructure |
| `backend/tests/self-improvement-closed-loop-e2e.test.ts` | Test infrastructure |
| `backend/tests/self-memory-loop.test.ts` | Test infrastructure |
| `backend/tests/setup-after-env.ts` | Test infrastructure |
| `backend/tests/setup-env.ts` | Test infrastructure |
| `backend/tests/skill-consumption-e2e.test.ts` | Test infrastructure |
| `backend/tests/skill-library.test.ts` | Test infrastructure |
| `backend/tests/skill-promotion-loop.test.ts` | Test infrastructure |
| `backend/tests/societies-institutions.test.ts` | Test infrastructure |
| `backend/tests/source-discovery.test.ts` | Test infrastructure |
| `backend/tests/specialist-integration.test.ts` | Test infrastructure |
| `backend/tests/specialist-spawning.test.ts` | Test infrastructure |
| `backend/tests/support/migration-db.ts` | Test infrastructure |
| `backend/tests/support/mock-data.ts` | Test infrastructure |
| `backend/tests/support/mock-web-adapter.ts` | Test infrastructure |
| `backend/tests/system-routes.test.ts` | Test infrastructure |
| `backend/tests/task-worker.test.ts` | Test infrastructure |
| `backend/tests/team-activation.test.ts` | Test infrastructure |
| `backend/tests/transactional-outbox.test.ts` | Test infrastructure |
| `backend/tests/treasury.test.ts` | Test infrastructure |
| `backend/tests/trust-impact-real-metrics.test.ts` | Test infrastructure |
| `backend/tests/working-eyes.test.ts` | Test infrastructure |
| `backend/tsconfig.json` | Development tooling |
| `benchmarks/README.md` | Unknown purpose |
| `benchmarks/capability_genesis_v2/development/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v2/fixtures/fixtures.json` | Unknown purpose |
| `benchmarks/capability_genesis_v2/hidden/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v2/registry.json` | Unknown purpose |
| `benchmarks/capability_genesis_v2/rubrics/rubrics.json` | Unknown purpose |
| `benchmarks/capability_genesis_v2/validation/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/development/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/fixtures/fixtures.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/hidden/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/registry.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/rubrics/rubrics.json` | Unknown purpose |
| `benchmarks/capability_genesis_v3/validation/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/development/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/fixtures/fixtures.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/hidden/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/registry.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/rubrics/rubrics.json` | Unknown purpose |
| `benchmarks/capability_genesis_v4/validation/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/development/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/fixtures/fixtures.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/hidden/cases.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/registry.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/rubrics/rubrics.json` | Unknown purpose |
| `benchmarks/capability_genesis_v5/validation/cases.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v1/cases/cases.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v1/registry.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v2/cases/cases.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v2/registry.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v3/cases/cases.json` | Unknown purpose |
| `benchmarks/capability_protocol_baseline_v3/registry.json` | Unknown purpose |
| `benchmarks/registry.json` | Unknown purpose |
| `calibration/BENCHMARK_ANALYSIS.md` | Production runtime code |
| `calibration/__init__.py` | Production runtime code |
| `calibration/benchmarks/model_comparison_results.json` | Production runtime code |
| `calibration/decay/__init__.py` | Production runtime code |
| `calibration/decay/decay_tracker.py` | Production runtime code |
| `calibration/evidence/__init__.py` | Production runtime code |
| `calibration/evidence/evidence_kernel.py` | Production runtime code |
| `calibration/firewall/__init__.py` | Production runtime code |
| `calibration/firewall/firewall.py` | Production runtime code |
| `calibration/ledger/__init__.py` | Production runtime code |
| `calibration/ledger/prediction_ledger.py` | Production runtime code |
| `calibration/ledger/schema.sql` | Database migration |
| `calibration/resolution/__init__.py` | Production runtime code |
| `calibration/resolution/resolution_service.py` | Production runtime code |
| `calibration/resolution/source_independence.py` | Production runtime code |
| `calibration/scoring/__init__.py` | Production runtime code |
| `calibration/scoring/scoring_module.py` | Production runtime code |
| `calibration/self_audit/__init__.py` | Production runtime code |
| `calibration/self_audit/self_audit.py` | Production runtime code |
| `calibration/surprise/__init__.py` | Production runtime code |
| `calibration/surprise/surprise_register.py` | Production runtime code |
| `calibration/tests/__init__.py` | Test infrastructure |
| `calibration/tests/test_ledger_immutability.py` | Test infrastructure |
| `calibration/trust/__init__.py` | Production runtime code |
| `calibration/trust/trust_controller.py` | Production runtime code |
| `calibration/trustworthiness_engine.py` | Production runtime code |
| `calibration/uncertainty/__init__.py` | Production runtime code |
| `calibration/uncertainty/schema.py` | Production runtime code |
| `calibration/uncertainty/test_schema.py` | Test infrastructure |
| `calibration/uncertainty/uncertainty_stack.py` | Production runtime code |
| `civilization/__init__.py` | Production runtime code |
| `civilization/contracts/engineering.yaml` | Production runtime code |
| `civilization/contracts/security.yaml` | Production runtime code |
| `civilization/controls.yaml` | Production runtime code |
| `civilization/domain/__init__.py` | Production runtime code |
| `civilization/domain/entities.py` | Production runtime code |
| `civilization/reputation_weights.yaml` | Production runtime code |
| `civilization/services/__init__.py` | Production runtime code |
| `civilization/services/controls_cache.py` | Production runtime code |
| `civilization/services/governance_service.py` | Production runtime code |
| `civilization/services/institution_service.py` | Production runtime code |
| `civilization/services/memory_service.py` | Production runtime code |
| `civilization/services/reputation_service.py` | Production runtime code |
| `civilization/services/review_service.py` | Production runtime code |
| `civilization/services/structured_logger.py` | Production runtime code |
| `conftest.py` | Unknown purpose |
| `constitution/CONVENTIONS.md` | Unknown purpose |
| `constitution/GENERALIZATION_REPORT.md` | Unknown purpose |
| `constitution/INDEX.md` | Unknown purpose |
| `constitution/TEMPLATE.md` | Unknown purpose |
| `constitution/invariants.yaml` | Unknown purpose |
| `constitution/volumes/VOL-00-vision.md` | Unknown purpose |
| `constitution/volumes/VOL-01-constitutional-core.md` | Unknown purpose |
| `constitution/volumes/VOL-32-security-and-threat-model.md` | Unknown purpose |
| `cross_version_adapters/__init__.py` | Unknown purpose |
| `cross_version_adapters/backend_runtime_adapter.py` | Unknown purpose |
| `cross_version_adapters/base.py` | Unknown purpose |
| `cross_version_adapters/data_analysis_adapter.py` | Unknown purpose |
| `cross_version_adapters/governance_adapter.py` | Unknown purpose |
| `cross_version_adapters/memory_adapter.py` | Unknown purpose |
| `cross_version_adapters/python_agent_adapter.py` | Unknown purpose |
| `cross_version_adapters/recovery_adapter.py` | Unknown purpose |
| `cross_version_adapters/unsupported_adapter.py` | Unknown purpose |
| `dashboard/src/app/calibration/page.tsx` | Production runtime code |
| `dashboard/src/types/calibration.ts` | Production runtime code |
| `data/external/bike_sharing/bike_sharing_dataset.zip` | Generated artifact |
| `data/external/bike_sharing/hour.csv` | Generated artifact |
| `docker-compose.staging.yml` | Deployment infrastructure |
| `docker-compose.yml` | Deployment infrastructure |
| `docs/AGENTCO_OPEN_WORLD_5MIN_ANALYSIS.md` | Documentation |
| `docs/AUTONOMY_ACTION_LOOP.md` | Documentation |
| `docs/AUTONOMY_REAL_WEB_FREE_RUN_REPORT.md` | Documentation |
| `docs/AUTONOMY_WITH_SPECIALISTS.md` | Documentation |
| `docs/BOUNDED_LEARNING_RUN_COMPLETE.md` | Documentation |
| `docs/CALIBRATION_STEP1_PROGRESS.md` | Documentation |
| `docs/CALIBRATION_STEP2_COMPLETE.md` | Documentation |
| `docs/CIVILIZATION_ARCHITECTURE.md` | Documentation |
| `docs/CIVILIZATION_ARCHITECTURE_AND_CODEX_BUILD_PLAN.md` | Documentation |
| `docs/CIVILIZATION_CALIBRATION_TRUST_IMPLEMENTATION_PLAN.md` | Documentation |
| `docs/CIVILIZATION_GOVERNANCE_FINAL_SPEC.md` | Documentation |
| `docs/CIVILIZATION_LEARNING_ARCHITECTURE.md` | Documentation |
| `docs/CIVILIZATION_LEARNING_BACKBONE.md` | Documentation |
| `docs/CIVILIZATION_MIGRATION_AUDIT.md` | Documentation |
| `docs/CIVILIZATION_TRUST_RUNTIME_VERIFICATION_REPORT.md` | Documentation |
| `docs/CIVILIZATION_TRUST_RUNTIME_VERIFICATION_SCORECARD.json` | Documentation |
| `docs/CODEX_BUILD_PLAN.md` | Documentation |
| `docs/COMPONENT_INTEGRATION_PLAN.md` | Documentation |
| `docs/CONTINUATION_STATE.md` | Documentation |
| `docs/CURRENT_IMPLEMENTATION_REALITY.md` | Documentation |
| `docs/CURRENT_RUNTIME_CANONICAL.md` | Documentation |
| `docs/DB_TABLE_USAGE.md` | Documentation |
| `docs/FIXING_HALLUCINATION_AND_EVIDENCE.md` | Documentation |
| `docs/HARDENING_IMPLEMENTATION_PLAN.md` | Documentation |
| `docs/INVESTIGATION_ACCOUNT.md` | Documentation |
| `docs/LEARNING_LAYER_INTEGRATION.md` | Documentation |
| `docs/LEVEL_1_TO_LEVEL_3_EXECUTION_PLAN.md` | Documentation |
| `docs/LEVEL_3_AUTONOMY_VALIDATION_REPORT.md` | Documentation |
| `docs/LEVEL_3_FUNCTIONAL_VERIFICATION_REPORT.md` | Documentation |
| `docs/LEVEL_3_REPAIR_PLAN.md` | Documentation |
| `docs/LEVEL_3_RUNTIME_BLOCKER_ASSESSMENT.md` | Documentation |
| `docs/LEVEL_3_VERIFICATION_REPORT.md` | Documentation |
| `docs/LEVEL_3_VERIFICATION_SCORECARD.json` | Documentation |
| `docs/LEVEL_4_HARDENING.md` | Documentation |
| `docs/LEVEL_4_HARDENING_PLAN.md` | Documentation |
| `docs/LLM_PROVIDER_INTEGRATION.md` | Documentation |
| `docs/MANUAL_MERGE_INSTRUCTIONS.md` | Documentation |
| `docs/OPTION_D_D1_STATUS.md` | Documentation |
| `docs/PHASE5_GROUNDWORK_COMPLETE.md` | Documentation |
| `docs/PHASES_5_8_IMPLEMENTATION.md` | Documentation |
| `docs/PHASES_5_8_SUMMARY.txt` | Documentation |
| `docs/PHASES_5_8_VERIFICATION_BEFORE_PHASE_9.md` | Documentation |
| `docs/PHASES_9_13_IMPLEMENTATION_REPORT.md` | Documentation |
| `docs/PHASE_4_PERCEPTION_VERIFICATION_REPORT.md` | Documentation |
| `docs/PHASE_5_GOAL_MANAGEMENT.md` | Documentation |
| `docs/PRODUCTION_BUILD_ARTIFACTS_REPORT.md` | Documentation |
| `docs/PRODUCTION_CANARY_DEPLOYMENT_PLAN.md` | Documentation |
| `docs/PRODUCTION_DEPLOYMENT_EXECUTION_REPORT.md` | Documentation |
| `docs/PRODUCTION_DEPLOYMENT_FINAL_STATUS.md` | Documentation |
| `docs/PRODUCTION_DEPLOYMENT_GUIDE.md` | Documentation |
| `docs/PRODUCTION_DEPLOYMENT_READINESS_REPORT.md` | Documentation |
| `docs/PRODUCTION_DEPLOYMENT_SCORECARD.json` | Documentation |
| `docs/PRODUCTION_MIGRATIONS_EXECUTION_PLAN.md` | Documentation |
| `docs/PRODUCTION_POST_DEPLOY_VALIDATION.md` | Documentation |
| `docs/PRODUCTION_PROMOTION_CHECKLIST.md` | Documentation |
| `docs/PRODUCTION_PROMOTION_CHECKLIST_COMPLETED.md` | Documentation |
| `docs/PRODUCTION_READINESS_DECISION.md` | Documentation |
| `docs/PRODUCTION_READINESS_HONEST_REPORT.md` | Documentation |
| `docs/PRODUCTION_READINESS_SUMMARY.md` | Documentation |
| `docs/RBAC_AND_WEB_SAFETY.md` | Documentation |
| `docs/REAL_WORLD_PROOF_PLAN.md` | Documentation |
| `docs/STAGING_48_HOUR_BURN_IN_PLAN.md` | Documentation |
| `docs/STAGING_DEPLOYMENT_GUIDE.md` | Documentation |
| `docs/STAGING_VALIDATION_SCORECARD.json` | Documentation |
| `docs/TRUE_AUTONOMY_ARCHITECTURE.md` | Documentation |
| `docs/TRUE_AUTONOMY_ARCHITECTURE_SCORECARD.json` | Documentation |
| `docs/TRUE_AUTONOMY_ARCHITECTURE_VALIDATION_REPORT.md` | Documentation |
| `docs/TRUE_AUTONOMY_GAP_REGISTER.md` | Documentation |
| `docs/TRUE_AUTONOMY_IMPLEMENTATION_COMPLETE.md` | Documentation |
| `docs/TRUE_AUTONOMY_IMPLEMENTATION_PLAN.md` | Documentation |
| `docs/TRUE_AUTONOMY_INTEGRATION.md` | Documentation |
| `docs/TRUSTWORTHINESS_PLATFORM_STATUS.md` | Documentation |
| `docs/agentco_vs_llms_vendor_risk_benchmark.md` | Documentation |
| `docs/architecture/agentco_architecture.md` | Documentation |
| `docs/audit/02_agents.md` | Documentation |
| `docs/audit/03_capabilities_vs_reality.md` | Documentation |
| `docs/audit/AGENT_PROTOCOL_CONFORMANCE_MATRIX.json` | Documentation |
| `docs/audit/CONTROLLED_LEARNING_REPORT.json` | Documentation |
| `docs/audit/EVALUATION_CALIBRATION_REPORT.json` | Documentation |
| `docs/audit/FORENSIC_AUDIT_CONTROLS.json` | Documentation |
| `docs/audit/FORENSIC_AUDIT_CONTROLS.md` | Documentation |
| `docs/audit/FORENSIC_FILE_INVENTORY.json` | Documentation |
| `docs/audit/FORENSIC_FILE_INVENTORY.md` | Documentation |
| `docs/audit/FORENSIC_REMEDIATION_STATUS_2026_07_12.md` | Documentation |
| `docs/audit/PHASE10_NOTES.md` | Documentation |
| `docs/audit/PHASE11_NOTES.md` | Documentation |
| `docs/audit/PHASE12_NOTES.md` | Documentation |
| `docs/audit/PHASE2_REGRESSION_VERDICTS.md` | Documentation |
| `docs/audit/PHASE3_NOTES.md` | Documentation |
| `docs/audit/PHASE5_NOTES.md` | Documentation |
| `docs/audit/PHASE6_NOTES.md` | Documentation |
| `docs/audit/PHASE7.5_NOTES.md` | Documentation |
| `docs/audit/PHASE7_NOTES.md` | Documentation |
| `docs/audit/PHASE8_DESIGN.md` | Documentation |
| `docs/audit/PHASE9_NOTES.md` | Documentation |
| `docs/audit/PYTEST_COLLECTION_DELTA.md` | Documentation |
| `docs/audit/PYTHON_TEST_TRIAGE.md` | Documentation |
| `docs/audit/ROUTE_SENSITIVITY_MATRIX.md` | Documentation |
| `docs/audit/SELF_IMPROVEMENT_EXPERIMENT_REPORT.json` | Documentation |
| `docs/audit/V1_SEVERITY_REACHABILITY.md` | Documentation |
| `docs/audit/current/ACTUAL_DEPLOYMENT_TOPOLOGY.json` | Documentation |
| `docs/audit/current/ACTUAL_DEPLOYMENT_TOPOLOGY.md` | Documentation |
| `docs/audit/current/ACTUAL_RUNTIME_ARCHITECTURE.json` | Documentation |
| `docs/audit/current/ACTUAL_RUNTIME_ARCHITECTURE.md` | Documentation |
| `docs/audit/current/ADAPTER_DEVELOPMENT_V2_REPORT.json` | Documentation |
| `docs/audit/current/ADAPTER_DEVELOPMENT_V2_REPORT.md` | Documentation |
| `docs/audit/current/AUTHORITATIVE_IMPLEMENTATIONS.md` | Documentation |
| `docs/audit/current/BACKUP_RESTORE_VERIFICATION.md` | Documentation |
| `docs/audit/current/BASELINE_COMMAND_RESULTS.json` | Documentation |
| `docs/audit/current/BASELINE_EXECUTION_REPORT.md` | Documentation |
| `docs/audit/current/BASELINE_FINDINGS.json` | Documentation |
| `docs/audit/current/BATCH07_EVIDENCE_INVALIDATION.json` | Documentation |
| `docs/audit/current/BATCH07_EVIDENCE_INVALIDATION.md` | Documentation |
| `docs/audit/current/BATCH07_MAIN_RECONCILIATION.json` | Documentation |
| `docs/audit/current/BATCH07_MAIN_RECONCILIATION.md` | Documentation |
| `docs/audit/current/BATCH_08D_CORRECTED_EVIDENCE_RECORD.md` | Documentation |
| `docs/audit/current/BATCH_08E_INDEPENDENT_AUDIT.md` | Documentation |
| `docs/audit/current/BENCHMARK_GOVERNANCE_POLICY.json` | Documentation |
| `docs/audit/current/BENCHMARK_GOVERNANCE_POLICY.md` | Documentation |
| `docs/audit/current/BENCHMARK_REGISTRY.json` | Documentation |
| `docs/audit/current/BENCHMARK_REGISTRY.md` | Documentation |
| `docs/audit/current/CAPABILITY_VECTOR_SPECIFICATION.json` | Documentation |
| `docs/audit/current/CAPABILITY_VECTOR_SPECIFICATION.md` | Documentation |
| `docs/audit/current/CAPABILITY_VS_PRIMITIVE_CLASSIFICATION.json` | Documentation |
| `docs/audit/current/CAPABILITY_VS_PRIMITIVE_CLASSIFICATION.md` | Documentation |
| `docs/audit/current/CIVILIZATION_CLAIM_VERIFICATION_MATRIX.json` | Documentation |
| `docs/audit/current/CIVILIZATION_CLAIM_VERIFICATION_MATRIX.md` | Documentation |
| `docs/audit/current/CI_BASELINE_RECONCILIATION.md` | Documentation |
| `docs/audit/current/CLAIM_EVIDENCE_MATRIX.json` | Documentation |
| `docs/audit/current/CLAIM_EVIDENCE_MATRIX.md` | Documentation |
| `docs/audit/current/CROSS_DOMAIN_TRANSFER_MATRIX.json` | Documentation |
| `docs/audit/current/CROSS_DOMAIN_TRANSFER_MATRIX.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_ADAPTER_COMPATIBILITY_MATRIX.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_ADAPTER_COMPATIBILITY_MATRIX.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_ANCESTRY_REPORT.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_ANCESTRY_REPORT.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_DECISION.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_DECISION.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_FINDINGS.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_FINDINGS.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_HEALTH_MATRIX.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_HEALTH_MATRIX.md` | Documentation |
| `docs/audit/current/CROSS_VERSION_PROMOTION_POLICY.json` | Documentation |
| `docs/audit/current/CROSS_VERSION_PROMOTION_POLICY.md` | Documentation |
| `docs/audit/current/DEPLOYMENT_COMPONENT_LEDGER.json` | Documentation |
| `docs/audit/current/DEPLOYMENT_COMPONENT_LEDGER.md` | Documentation |
| `docs/audit/current/DEPLOYMENT_OPERATIONAL_FINDINGS.json` | Documentation |
| `docs/audit/current/DEPLOYMENT_OPERATIONAL_FINDINGS.md` | Documentation |
| `docs/audit/current/FILE_AUDIT_LEDGER_BATCH03.json` | Documentation |
| `docs/audit/current/GATE_INTEGRITY_EXCEPTIONS.json` | Documentation |
| `docs/audit/current/GCR_004_AND_V2_INVALIDATION_AUDIT.md` | Documentation |
| `docs/audit/current/GENESIS_V5_HOLD_REPROOF.md` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V1_INVALIDATION.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V1_INVALIDATION.md` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V2_FREEZE.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V2_LIMITATIONS.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V2_LIMITATIONS.md` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V3_FREEZE.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V4_FREEZE.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V1_INVALIDATION.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V1_INVALIDATION.md` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V2_INVALIDATION.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V2_INVALIDATION.md` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_RUNTIME_FINDINGS.json` | Documentation |
| `docs/audit/current/GOVERNED_CAPABILITY_RUNTIME_FINDINGS.md` | Documentation |
| `docs/audit/current/HOSTED_BACKUP_RESTORE_VERIFICATION.md` | Documentation |
| `docs/audit/current/HOSTED_DNS_TLS_VERIFICATION.md` | Documentation |
| `docs/audit/current/HOSTED_ENVIRONMENT_GAP_ANALYSIS.md` | Documentation |
| `docs/audit/current/HOSTED_IDENTITY_ACCESS_MATRIX.json` | Documentation |
| `docs/audit/current/HOSTED_IDENTITY_ACCESS_MATRIX.md` | Documentation |
| `docs/audit/current/HOSTED_LOAD_AUTOSCALING_VERIFICATION.md` | Documentation |
| `docs/audit/current/HOSTED_OBSERVABILITY_ALERT_MATRIX.json` | Documentation |
| `docs/audit/current/HOSTED_OBSERVABILITY_ALERT_MATRIX.md` | Documentation |
| `docs/audit/current/HOSTED_STAGING_BUDGET_POLICY.json` | Documentation |
| `docs/audit/current/HOSTED_STAGING_BUDGET_POLICY.md` | Documentation |
| `docs/audit/current/HOSTED_STAGING_COMPONENT_LEDGER.json` | Documentation |
| `docs/audit/current/HOSTED_STAGING_COMPONENT_LEDGER.md` | Documentation |
| `docs/audit/current/HOSTED_STAGING_EXECUTION_CONTRACT.json` | Documentation |
| `docs/audit/current/HOSTED_STAGING_EXECUTION_CONTRACT.md` | Documentation |
| `docs/audit/current/HOSTED_STAGING_FINDINGS.json` | Documentation |
| `docs/audit/current/HOSTED_STAGING_FINDINGS.md` | Documentation |
| `docs/audit/current/HOSTED_STAGING_TOPOLOGY.json` | Documentation |
| `docs/audit/current/HOSTED_STAGING_TOPOLOGY.md` | Documentation |
| `docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json` | Documentation |
| `docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.md` | Documentation |
| `docs/audit/current/INTEGRATION_CONTRACT_MATRIX.json` | Documentation |
| `docs/audit/current/INTEGRATION_CONTRACT_MATRIX.md` | Documentation |
| `docs/audit/current/LIVE_PROVIDER_VERIFICATION_MATRIX.json` | Documentation |
| `docs/audit/current/LIVE_PROVIDER_VERIFICATION_MATRIX.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_CALIBRATION_REPORT.json` | Documentation |
| `docs/audit/current/LONGITUDINAL_CALIBRATION_REPORT.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_COMPARISON_POLICY.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_EVIDENCE_TIERS.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_HISTORY_STORAGE_CONTRACT.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_MERGE_ACTIVATION_PLAN.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_MILESTONE_POLICY.json` | Documentation |
| `docs/audit/current/LONGITUDINAL_MILESTONE_POLICY.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_MISSION_FINDINGS.json` | Documentation |
| `docs/audit/current/LONGITUDINAL_MISSION_FINDINGS.md` | Documentation |
| `docs/audit/current/LONGITUDINAL_RUN_PROTOCOL.md` | Documentation |
| `docs/audit/current/MAINLINE_RECONCILIATION_FINDINGS.json` | Documentation |
| `docs/audit/current/MAINLINE_RECONCILIATION_FINDINGS.md` | Documentation |
| `docs/audit/current/MIGRATION_IDENTITY_LEDGER.json` | Documentation |
| `docs/audit/current/MIGRATION_IDENTITY_LEDGER.md` | Documentation |
| `docs/audit/current/MISSION_CLAIM_DECOMPOSITION.json` | Documentation |
| `docs/audit/current/MISSION_CLAIM_DECOMPOSITION.md` | Documentation |
| `docs/audit/current/OBSERVABILITY_ALERT_MATRIX.json` | Documentation |
| `docs/audit/current/OBSERVABILITY_ALERT_MATRIX.md` | Documentation |
| `docs/audit/current/PROTOCOL_V3_REPROOF.md` | Documentation |
| `docs/audit/current/PROVIDER_TRUST_BOUNDARY_AUDIT.md` | Documentation |
| `docs/audit/current/REAL_CROSS_VERSION_DECISION.json` | Documentation |
| `docs/audit/current/REAL_CROSS_VERSION_DECISION.md` | Documentation |
| `docs/audit/current/RECONCILED_SUBJECT_MANIFEST.json` | Documentation |
| `docs/audit/current/REMEDIATION_02A_CLEAN_ROOM_EVIDENCE.md` | Documentation |
| `docs/audit/current/REMEDIATION_02B_CLEAN_ROOM_CLOSURE.md` | Documentation |
| `docs/audit/current/REMEDIATION_03_RUNTIME_ARCHITECTURE_INTEGRATION.md` | Documentation |
| `docs/audit/current/REMEDIATION_04_DEPLOYMENT_OPERATIONAL_RESILIENCE.md` | Documentation |
| `docs/audit/current/REMEDIATION_05_HOSTED_STAGING_LIVE_PROVIDERS.md` | Documentation |
| `docs/audit/current/REMEDIATION_06A_LONGITUDINAL_REMOTE_CLOSURE.md` | Documentation |
| `docs/audit/current/REMEDIATION_06_LONGITUDINAL_MISSION_EVIDENCE_FOUNDATION.md` | Documentation |
| `docs/audit/current/REMEDIATION_07B_REAL_CROSS_VERSION_EVALUATION.md` | Documentation |
| `docs/audit/current/REMEDIATION_07C_SUBJECT_NATIVE_CROSS_VERSION.md` | Documentation |
| `docs/audit/current/REMEDIATION_07D_EVIDENCE_BINDING_AND_V2.md` | Documentation |
| `docs/audit/current/REMEDIATION_07E_FINAL_EVIDENCE_SEMANTIC_CLOSURE.md` | Documentation |
| `docs/audit/current/REMEDIATION_07_CROSS_VERSION_CIVILIZATION_EVALUATION.md` | Documentation |
| `docs/audit/current/REMEDIATION_08_GOVERNED_CAPABILITY_RUNTIME.md` | Documentation |
| `docs/audit/current/ROLLBACK_VERIFICATION.md` | Documentation |
| `docs/audit/current/RUNTIME_COMPONENT_LEDGER.json` | Documentation |
| `docs/audit/current/RUNTIME_COMPONENT_LEDGER.md` | Documentation |
| `docs/audit/current/RUNTIME_INTEGRATION_FINDINGS.json` | Documentation |
| `docs/audit/current/RUNTIME_INTEGRATION_FINDINGS.md` | Documentation |
| `docs/audit/current/RUNTIME_REACHABILITY.json` | Documentation |
| `docs/audit/current/RUNTIME_REACHABILITY.md` | Documentation |
| `docs/audit/current/STACKED_PR_INTEGRATION_PLAN.md` | Documentation |
| `docs/audit/current/SUBJECT_ADAPTER_FREEZE_MANIFEST.json` | Documentation |
| `docs/audit/current/SUBJECT_ADAPTER_V2_FREEZE_MANIFEST.json` | Documentation |
| `docs/audit/current/SUBJECT_EXECUTION_PROTOCOL.md` | Documentation |
| `docs/audit/current/SUBJECT_INTERFACE_INVENTORY.json` | Documentation |
| `docs/audit/current/SUBJECT_INTERFACE_INVENTORY.md` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_DECISION.json` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_DECISION.md` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_RESULTS.json` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_RESULTS.md` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_V2_DECISION.json` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_V2_DECISION.md` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_V2_RESULTS.json` | Documentation |
| `docs/audit/current/SUBJECT_NATIVE_CROSS_VERSION_V2_RESULTS.md` | Documentation |
| `docs/audit/current/TEST_SKIP_ALLOWLIST.json` | Documentation |
| `docs/audit/current/THREE_VERSION_INTERFACE_INTERSECTION.json` | Documentation |
| `docs/audit/current/THREE_VERSION_INTERFACE_INTERSECTION.md` | Documentation |
| `docs/civilization/CANONICAL_RUNTIME_MAP.md` | Documentation |
| `docs/civilization/OUTSTANDING_GATES.md` | Documentation |
| `docs/civilization/PLAN_AND_PROGRESS.md` | Documentation |
| `docs/civilization/canonical_runtime_map.json` | Documentation |
| `docs/civilization_migration_map.md` | Documentation |
| `docs/history/5MIN_TEST_FINAL_REPORT.md` | Documentation |
| `docs/history/5MIN_TEST_RESULTS_SUMMARY.md` | Documentation |
| `docs/history/AGENTCO_COMPLETE_GUIDE.md` | Documentation |
| `docs/history/AGENTCO_FINAL_SYSTEM_STATUS.md` | Documentation |
| `docs/history/ARCHITECTURE_DETAILED.md` | Documentation |
| `docs/history/ARCHITECTURE_PHASES_2_4.md` | Documentation |
| `docs/history/ARCHITECTURE_THROUGH_TEST_RESULTS.md` | Documentation |
| `docs/history/AUTONOMY_ACTION_LOOP_IMPLEMENTATION.md` | Documentation |
| `docs/history/AUTONOMY_BUG_FIXES_FINAL_REPORT.md` | Documentation |
| `docs/history/AUTONOMY_GOVERNANCE_INTEGRATION_FINAL.md` | Documentation |
| `docs/history/AUTONOMY_QUICKSTART.md` | Documentation |
| `docs/history/BENCHMARK_RESULTS_SUMMARY.md` | Documentation |
| `docs/history/BUG_FIXES_REFERENCE.md` | Documentation |
| `docs/history/CALIBRATION_ROADMAP.md` | Documentation |
| `docs/history/CHANGELOG_AUTONOMY_FIXES.md` | Documentation |
| `docs/history/CIVILIZATION_ARCHITECTURE.md` | Documentation |
| `docs/history/CIVILIZATION_GOVERNANCE_PROJECT_COMPLETE.md` | Documentation |
| `docs/history/CIVILIZATION_INTEGRATION_PLAN.md` | Documentation |
| `docs/history/CIVILIZATION_TRUST_VERIFICATION_COMPLETE.md` | Documentation |
| `docs/history/CIVILIZATION_VALIDATION_REPORT.md` | Documentation |
| `docs/history/COMPLETE_IMPLEMENTATION_STATUS.md` | Documentation |
| `docs/history/COMPLETE_SYSTEM_DOCUMENTATION.md` | Documentation |
| `docs/history/COMPLETION_SUMMARY.md` | Documentation |
| `docs/history/CRITICAL_BUGS_COMPLETE_ANALYSIS.md` | Documentation |
| `docs/history/DEMO_COMPONENTS_AUDIT.md` | Documentation |
| `docs/history/DEPLOYMENT_AND_OPERATIONS_GUIDE.md` | Documentation |
| `docs/history/DOCUMENTATION_INDEX.md` | Documentation |
| `docs/history/FINAL_DELIVERY_SUMMARY.md` | Documentation |
| `docs/history/FINAL_IMPLEMENTATION_REPORT.md` | Documentation |
| `docs/history/FINAL_INTEGRATION_SUMMARY.md` | Documentation |
| `docs/history/FINAL_REPORT.txt` | Documentation |
| `docs/history/FIVE_BUGS_HARDENING.md` | Documentation |
| `docs/history/FIXES_IMPLEMENTATION_PLAN.md` | Documentation |
| `docs/history/FUNCTIONAL_VERIFICATION_BLOCKER.md` | Documentation |
| `docs/history/GATE_1_ASSESSMENT_REPORT.md` | Documentation |
| `docs/history/GATE_1_HARDENING_COMPLETE.md` | Documentation |
| `docs/history/HARDENING_REPORT.md` | Documentation |
| `docs/history/IMPLEMENTATION_COMPLETE_SUMMARY.txt` | Documentation |
| `docs/history/IMPLEMENTATION_REPORT.md` | Documentation |
| `docs/history/IMPLEMENTATION_STATUS_CORRECTED.md` | Documentation |
| `docs/history/IMPLEMENTATION_STATUS_REPORT.md` | Documentation |
| `docs/history/IMPLEMENTATION_SUMMARY.md` | Documentation |
| `docs/history/LEARNING_INTEGRATION_SUMMARY.md` | Documentation |
| `docs/history/LEVEL_3_IMPLEMENTATION_SUMMARY.md` | Documentation |
| `docs/history/LEVEL_3_REPAIR_STATUS.md` | Documentation |
| `docs/history/LLM_INTEGRATION_GAPS.md` | Documentation |
| `docs/history/MULTI_AGENT_AUTONOMY_ENHANCEMENTS_SUMMARY.md` | Documentation |
| `docs/history/PARTS_C_D_E_FINAL_STATUS.md` | Documentation |
| `docs/history/PART_A_COMPLETE_PART_B_PENDING.md` | Documentation |
| `docs/history/PART_A_VERIFICATION_COMPLETE.md` | Documentation |
| `docs/history/PART_B_RUNTIME_INTEGRATION_COMPLETE.md` | Documentation |
| `docs/history/PART_C_GOVERNANCE_RBAC_COMPLETE.md` | Documentation |
| `docs/history/PART_D_E_COMPLETE_FINAL.md` | Documentation |
| `docs/history/PHASE3_COMPLETE_FINAL_SUMMARY.md` | Documentation |
| `docs/history/PHASE_1_INTEGRATION_COMPLETE.md` | Documentation |
| `docs/history/PHASE_2_LONG_TERM_COORDINATION_COMPLETE.md` | Documentation |
| `docs/history/PHASE_3_DEFECTS_RESOLVED.md` | Documentation |
| `docs/history/PHASE_3_HARDENING_COMPLETE.md` | Documentation |
| `docs/history/PHASE_3a_COMPLETE.md` | Documentation |
| `docs/history/PHASE_3b_COMPLETE.md` | Documentation |
| `docs/history/PHASE_3c_COMPLETE.md` | Documentation |
| `docs/history/PLAN_REFINEMENT_SUMMARY.md` | Documentation |
| `docs/history/PRODUCTION_DEPLOYMENT_COMPLETE.txt` | Documentation |
| `docs/history/PRODUCTION_DEPLOYMENT_FINAL_VERDICT.txt` | Documentation |
| `docs/history/PRODUCTION_DEPLOYMENT_PLAN.md` | Documentation |
| `docs/history/PRODUCTION_READINESS.md` | Documentation |
| `docs/history/PRODUCTION_STATUS_2026_06_24.md` | Documentation |
| `docs/history/PROJECT_COMPLETION_SUMMARY.md` | Documentation |
| `docs/history/PROJECT_DELIVERY_COMPLETE.md` | Documentation |
| `docs/history/README.md` | Documentation |
| `docs/history/REAL_WORLD_VALIDATION_REPORT.md` | Documentation |
| `docs/history/SELF_EXTENSION_DELIVERY.md` | Documentation |
| `docs/history/SELF_EXTENSION_IMPLEMENTATION_SUMMARY.md` | Documentation |
| `docs/history/SELF_EXTENSION_RUNBOOK.md` | Documentation |
| `docs/history/STAGING_VALIDATION_REPORT.md` | Documentation |
| `docs/history/SYSTEM_FIXES_COMPLETED.md` | Documentation |
| `docs/history/SYSTEM_REPAIR_REPORT.md` | Documentation |
| `docs/history/SYSTEM_STATE_HONEST_INVENTORY.md` | Documentation |
| `docs/history/SYSTEM_STATUS.md` | Documentation |
| `docs/history/TEST_RESULTS_1MIN_REALWORLD.md` | Documentation |
| `docs/history/TEST_RESULTS_REAL_LLM.md` | Documentation |
| `docs/history/TRUSTWORTHINESS_PLATFORM_PHASE1_DELIVERABLE.md` | Documentation |
| `docs/history/VALIDATION_TEMPLATE.md` | Documentation |
| `docs/history/VETTING_FIXES_APPLIED.md` | Documentation |
| `docs/history/VETTING_REPORT.md` | Documentation |
| `docs/history/WEAKNESS_ANALYSIS_& RECOMMENDATIONS.md` | Documentation |
| `docs/history/claims-for-validation.csv` | Documentation |
| `docs/history/latest.json` | Documentation |
| `docs/history/latest.md` | Documentation |
| `docs/history/learning_run_learning_run_1782301493122.json` | Documentation |
| `docs/history/learning_run_learning_run_1782301526470.json` | Documentation |
| `docs/history/learning_run_learning_run_1782301548630.json` | Documentation |
| `docs/history/learning_run_learning_run_1782301553480.json` | Documentation |
| `docs/history/learning_run_learning_run_1782301557613.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302581578.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302924921.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302942165.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302949141.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302956152.json` | Documentation |
| `docs/history/learning_run_learning_run_1782302965432.json` | Documentation |
| `docs/launch_readiness_audit.md` | Documentation |
| `docs/memory_audit.md` | Documentation |
| `docs/refoundation/AGENTCO_TRUE_NORTH.md` | Documentation |
| `docs/refoundation/BUILD_PLAN.md` | Documentation |
| `docs/refoundation/BUILD_STATE.json` | Documentation |
| `docs/refoundation/CURRENT_STATE_AUDIT.md` | Documentation |
| `docs/refoundation/FAILED_TESTS.md` | Documentation |
| `docs/refoundation/IMPLEMENTATION_MATRIX.md` | Documentation |
| `docs/refoundation/LAYER_CONTRACTS.md` | Documentation |
| `docs/refoundation/NEXT_ACTIONS.md` | Documentation |
| `docs/refoundation/NEXT_CODEX_PROMPT.md` | Documentation |
| `docs/refoundation/NORTH_STAR.md` | Documentation |
| `docs/refoundation/REPO_TRUTH_LEDGER.md` | Documentation |
| `docs/refoundation/SESSION_HANDOFF.md` | Documentation |
| `docs/refoundation/TESTING.md` | Documentation |
| `docs/refoundation/VALIDATION_PLAN.md` | Documentation |
| `docs/runnability_audit.md` | Documentation |
| `docs/runtime_capability_contract.md` | Documentation |
| `evals/__init__.py` | Experimental code |
| `evals/acceptance/__init__.py` | Experimental code |
| `evals/acceptance/accelerated_business_agent_calls.csv` | Experimental code |
| `evals/acceptance/accelerated_business_decisions.jsonl` | Experimental code |
| `evals/acceptance/accelerated_business_run.md` | Experimental code |
| `evals/acceptance/accelerated_business_summary.json` | Experimental code |
| `evals/acceptance/business_bikeshare_calibration_demo.md` | Experimental code |
| `evals/acceptance/demo_real_transcript.md` | Experimental code |
| `evals/acceptance/demo_transcript.md` | Experimental code |
| `evals/acceptance/first_real_prediction_trace.md` | Experimental code |
| `evals/acceptance/five_minute_run_trace.md` | Experimental code |
| `evals/acceptance/internet_predictions.md` | Experimental code |
| `evals/acceptance/memory_lifecycle_trace.md` | Experimental code |
| `evals/acceptance/memory_vs_amnesia_comparison.md` | Experimental code |
| `evals/acceptance/oracle_layer_trace.md` | Experimental code |
| `evals/acceptance/pawdent_agent_decisions.jsonl` | Experimental code |
| `evals/acceptance/pawdent_business_run.md` | Experimental code |
| `evals/acceptance/pawdent_calibration_ledger.csv` | Experimental code |
| `evals/acceptance/pawdent_monthly_financials.csv` | Experimental code |
| `evals/acceptance/pawdent_summary.json` | Experimental code |
| `evals/acceptance/proof_of_calibration_trace.md` | Experimental code |
| `evals/acceptance/recomputation_trace.md` | Experimental code |
| `evals/acceptance/seeded_false_belief_trace.md` | Experimental code |
| `evals/acceptance/staking_and_decisions_trace.md` | Experimental code |
| `evals/acceptance/tamper_evidence_trace.md` | Experimental code |
| `evals/acceptance/verifiable_calibration_demo.md` | Experimental code |
| `evals/agent_benchmarks/__init__.py` | Experimental code |
| `evals/audit/audit_report_2026-06-16.md` | Experimental code |
| `evals/conftest.py` | Experimental code |
| `evals/core/__init__.py` | Experimental code |
| `evals/core/graders.py` | Experimental code |
| `evals/core/runner.py` | Experimental code |
| `evals/core/schema.py` | Experimental code |
| `evals/core/test_graders.py` | Test infrastructure |
| `evals/core/test_runner.py` | Test infrastructure |
| `evals/core/test_schema.py` | Test infrastructure |
| `evals/enterprise_vendor_risk/__init__.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/__init__.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/agentco_adapter.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/base.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/fake_adapter.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/rag_adapter.py` | Experimental code |
| `evals/enterprise_vendor_risk/adapters/simulated_llm_adapters.py` | Experimental code |
| `evals/enterprise_vendor_risk/cli.py` | Experimental code |
| `evals/enterprise_vendor_risk/correctness_utils.py` | Experimental code |
| `evals/enterprise_vendor_risk/dataset.jsonl` | Experimental code |
| `evals/enterprise_vendor_risk/leaderboard.py` | Experimental code |
| `evals/enterprise_vendor_risk/provenance.py` | Experimental code |
| `evals/enterprise_vendor_risk/report.py` | Experimental code |
| `evals/enterprise_vendor_risk/run_benchmark.py` | Experimental code |
| `evals/enterprise_vendor_risk/score.py` | Experimental code |
| `evals/enterprise_vendor_risk/test_benchmark.py` | Test infrastructure |
| `evals/enterprise_vendor_risk/test_db_persistence.py` | Test infrastructure |
| `evals/enterprise_vendor_risk/validation_framework.py` | Experimental code |
| `evals/experiments/B2B_SAAS_EXPERIMENT_RESULTS.md` | Experimental code |
| `evals/experiments/B2B_SAAS_FROZEN_MODEL.md` | Experimental code |
| `evals/experiments/B2B_SAAS_PRE_REGISTERED_HYPOTHESIS.md` | Experimental code |
| `evals/experiments/CORRECTED_FINDINGS.md` | Experimental code |
| `evals/experiments/DIAGNOSTIC_RESULTS.md` | Experimental code |
| `evals/experiments/EXPERIMENT_SUMMARY.md` | Experimental code |
| `evals/experiments/FINAL_COMPREHENSIVE_FINDINGS.md` | Experimental code |
| `evals/experiments/INTEGRITY_FRAMEWORK.md` | Experimental code |
| `evals/experiments/INVESTIGATION_SUMMARY.md` | Experimental code |
| `evals/experiments/NSE_PHASE1_ROOT_CAUSE_PRE_REGISTRATION.md` | Experimental code |
| `evals/experiments/NSE_PHASE2_EXTENDED_MARKET_PRE_REGISTRATION.md` | Experimental code |
| `evals/experiments/NSE_PHASE3_TO_5_PRE_REGISTRATION.md` | Experimental code |
| `evals/experiments/NSE_PHASE6_BETTER_AGENTS_PRE_REGISTRATION.md` | Experimental code |
| `evals/experiments/NSE_THREE_ARM_FINAL_REPORT.md` | Experimental code |
| `evals/experiments/NSE_THREE_ARM_PRE_REGISTRATION.md` | Experimental code |
| `evals/experiments/NSE_WALK_FORWARD_ARCHITECTURE.md` | Experimental code |
| `evals/experiments/NSE_WALK_FORWARD_HYPOTHESIS.md` | Experimental code |
| `evals/experiments/PREREQUISITES_COMPLETE.md` | Experimental code |
| `evals/experiments/PREREQUISITE_2_GATE.md` | Experimental code |
| `evals/experiments/PREREQUISITE_2_GATE_PASSED.md` | Experimental code |
| `evals/experiments/STOP_1_REAL_DATA_RESULTS.json` | Experimental code |
| `evals/experiments/STOP_1_RESULTS.json` | Experimental code |
| `evals/experiments/TEST_VALIDITY_ANALYSIS.md` | Experimental code |
| `evals/experiments/b2b_saas_control_arm.json` | Experimental code |
| `evals/experiments/b2b_saas_control_monthly.csv` | Experimental code |
| `evals/experiments/b2b_saas_four_arm_monthly.csv` | Experimental code |
| `evals/experiments/b2b_saas_four_arm_results.json` | Experimental code |
| `evals/experiments/b2b_saas_soft_weighting_results.json` | Experimental code |
| `evals/experiments/diagnostic_weighting_tests.json` | Experimental code |
| `evals/experiments/investigation_findings.md` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/CANONICAL_NSE_TRUST_WEIGHTING_RESULTS.md` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/FROZEN_NSE_DATA_SOURCE.md` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/canonical_nse_trust_weighting_results.json` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/daily_pnl.csv` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/position_ledger.csv` | Experimental code |
| `evals/experiments/nse_canonical_trust_weighting_results/prediction_ledger.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/bank_nifty_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/bank_nifty_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/hdfcbank_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/hdfcbank_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/icicibank_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/icicibank_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/infy_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/infy_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/nifty_50_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/nifty_50_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/reliance_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/reliance_synthetic.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/tcs_REAL.csv` | Experimental code |
| `evals/experiments/nse_data_frozen/tcs_synthetic.csv` | Experimental code |
| `evals/experiments/nse_phase1_root_cause_results/PHASE1_ROOT_CAUSE_RESULTS.md` | Experimental code |
| `evals/experiments/nse_phase1_root_cause_results/phase1_prediction_diagnostics.csv` | Experimental code |
| `evals/experiments/nse_phase1_root_cause_results/phase1_root_cause_results.json` | Experimental code |
| `evals/experiments/nse_phase1_root_cause_results/phase1_test_trust_history.csv` | Experimental code |
| `evals/experiments/nse_phase2_extended_market_results/PHASE2_EXTENDED_MARKET_RESULTS.md` | Experimental code |
| `evals/experiments/nse_phase2_extended_market_results/phase2_extended_market_results.json` | Experimental code |
| `evals/experiments/nse_phase2_extended_market_results/phase2_market_window_cells.csv` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/PHASE3_TO_5_RESULTS.md` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/phase3_to_5_policy_summary.csv` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/phase3_to_5_results.json` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/phase5_docs/internal_lessons.md` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/phase5_docs/open_source_toolkit.md` | Experimental code |
| `evals/experiments/nse_phase3_to_5_results/phase5_docs/research_paper_draft.md` | Experimental code |
| `evals/experiments/nse_phase6_better_agents_results/PHASE6_BETTER_AGENTS_RESULTS.md` | Experimental code |
| `evals/experiments/nse_phase6_better_agents_results/phase6_better_agents_results.json` | Experimental code |
| `evals/experiments/nse_phase6_better_agents_results/phase6_daily_pnl.csv` | Experimental code |
| `evals/experiments/nse_phase6_better_agents_results/phase6_prediction_ledger.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/METADATA.json` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/bank_nifty_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/hdfcbank_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/icicibank_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/infy_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/nifty_50_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/reliance_REAL.csv` | Experimental code |
| `evals/experiments/nse_phase6_data_frozen/tcs_REAL.csv` | Experimental code |
| `evals/experiments/nse_trust_weighting_hypothesis.md` | Experimental code |
| `evals/experiments/nse_walkforward_results/prediction_ledger.csv` | Experimental code |
| `evals/experiments/nse_walkforward_results/summary.json` | Experimental code |
| `evals/experiments/trust_weighting_arm_c_details.json` | Experimental code |
| `evals/experiments/trust_weighting_arm_d_details.json` | Experimental code |
| `evals/experiments/trust_weighting_hypothesis.md` | Experimental code |
| `evals/experiments/trust_weighting_results.md` | Experimental code |
| `evals/experiments/trust_weighting_seed_details.json` | Experimental code |
| `evals/experiments/trust_weighting_summary_stats.json` | Experimental code |
| `evals/financial_calibration_toolkit/__init__.py` | Experimental code |
| `evals/financial_calibration_toolkit/calibration_analyzer.py` | Experimental code |
| `evals/financial_calibration_toolkit/nse_data_loader.py` | Experimental code |
| `evals/financial_calibration_toolkit/trust_scoring.py` | Experimental code |
| `evals/financial_calibration_toolkit/walk_forward_engine.py` | Experimental code |
| `evals/north_star_cross_domain/__init__.py` | Experimental code |
| `evals/north_star_cross_domain/run_smoke.py` | Experimental code |
| `evals/north_star_cross_domain/tests/test_smoke.py` | Test infrastructure |
| `evals/real_world/test_xdr_tb_civilization_solver.py` | Test infrastructure |
| `evals/real_world/xdr_tb_crisis_problem.md` | Experimental code |
| `evals/registry/__init__.py` | Experimental code |
| `evals/registry/benchmarks.yaml` | Experimental code |
| `evals/registry/datasets/halueval_sample.jsonl` | Experimental code |
| `evals/registry/datasets/simpleqa_sample.jsonl` | Experimental code |
| `evals/registry/datasets/truthfulqa_sample.jsonl` | Experimental code |
| `evals/registry/registry.py` | Experimental code |
| `evals/registry/test_registry.py` | Test infrastructure |
| `evals/regression/__init__.py` | Experimental code |
| `evals/regression/test_audit_findings.py` | Test infrastructure |
| `evals/regression/test_canonical_schema_gate1.py` | Test infrastructure |
| `evals/regression/test_evidence_kernel_gate2.py` | Test infrastructure |
| `evals/regression/test_gate10_governance_policy.py` | Test infrastructure |
| `evals/regression/test_gate11_institutions.py` | Test infrastructure |
| `evals/regression/test_gate12_simulation.py` | Test infrastructure |
| `evals/regression/test_gate13_self_modification.py` | Test infrastructure |
| `evals/regression/test_gate14_model_foundry.py` | Test infrastructure |
| `evals/regression/test_gate15_validation.py` | Test infrastructure |
| `evals/regression/test_gate16_operator_console.py` | Test infrastructure |
| `evals/regression/test_gate17_ci_master.py` | Test infrastructure |
| `evals/regression/test_gate3_durable_execution.py` | Test infrastructure |
| `evals/regression/test_gate4_provenance_attestation.py` | Test infrastructure |
| `evals/regression/test_gate5_uncertainty_stack.py` | Test infrastructure |
| `evals/regression/test_gate6_memory_kernel.py` | Test infrastructure |
| `evals/regression/test_gate7_ingestion.py` | Test infrastructure |
| `evals/regression/test_gate8_learning_loop.py` | Test infrastructure |
| `evals/regression/test_gate9_agent_kernel.py` | Test infrastructure |
| `evals/regression/test_load.py` | Test infrastructure |
| `evals/regression/test_nse_lookahead_prevention.py` | Test infrastructure |
| `evals/regression/test_pg_ledger_immutability.py` | Test infrastructure |
| `evals/regression/test_pg_ledger_persistence.py` | Test infrastructure |
| `evals/regression/test_v2_regression.py` | Test infrastructure |
| `evals/system_benchmarks/__init__.py` | Experimental code |
| `foundry/__init__.py` | Production runtime code |
| `foundry/traces.py` | Production runtime code |
| `frontend/.dockerignore` | Production runtime code |
| `frontend/.eslintrc.json` | Development tooling |
| `frontend/Dockerfile` | Development tooling |
| `frontend/eslint.config.mjs` | Development tooling |
| `frontend/next-env.d.ts` | Production runtime code |
| `frontend/next.config.js` | Production runtime code |
| `frontend/package-lock.json` | Development tooling |
| `frontend/package.json` | Development tooling |
| `frontend/public/.gitkeep` | Production runtime code |
| `frontend/scripts/check-smoke.mjs` | Production runtime code |
| `frontend/src/app/api/[...path]/route.ts` | Production runtime code |
| `frontend/src/app/api/health/route.ts` | Production runtime code |
| `frontend/src/app/audit/page.tsx` | Production runtime code |
| `frontend/src/app/autonomy/page.tsx` | Production runtime code |
| `frontend/src/app/civilization/page.tsx` | Production runtime code |
| `frontend/src/app/config/page.tsx` | Production runtime code |
| `frontend/src/app/dashboard/page.tsx` | Production runtime code |
| `frontend/src/app/evals/page.tsx` | Production runtime code |
| `frontend/src/app/events/page.tsx` | Production runtime code |
| `frontend/src/app/finance/page.tsx` | Production runtime code |
| `frontend/src/app/globals.css` | Production runtime code |
| `frontend/src/app/governance/page.tsx` | Production runtime code |
| `frontend/src/app/incidents/page.tsx` | Production runtime code |
| `frontend/src/app/layout.tsx` | Production runtime code |
| `frontend/src/app/override/page.tsx` | Production runtime code |
| `frontend/src/app/page.tsx` | Production runtime code |
| `frontend/src/app/performance/page.tsx` | Production runtime code |
| `frontend/src/app/validation/page.tsx` | Production runtime code |
| `frontend/src/components/ErrorBoundary.tsx` | Production runtime code |
| `frontend/src/components/Sidebar.tsx` | Production runtime code |
| `frontend/src/lib/api.ts` | Production runtime code |
| `frontend/src/lib/api/auth.ts` | Production runtime code |
| `frontend/src/lib/api/autonomy.ts` | Production runtime code |
| `frontend/src/lib/api/url.ts` | Production runtime code |
| `frontend/src/types/index.ts` | Production runtime code |
| `frontend/tailwind.config.ts` | Production runtime code |
| `frontend/tsconfig.json` | Development tooling |
| `governance/__init__.py` | Production runtime code |
| `governance/policy.py` | Production runtime code |
| `infrastructure/grafana/provisioning/datasources/prometheus.yml` | Deployment infrastructure |
| `infrastructure/kafka/topics.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/Chart.lock` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/Chart.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/_helpers.tpl` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/civilization-scheduler-deployment.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/deployment.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/frontend-deployment.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/hpa.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/ingress.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/migration-job.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/outbox-worker-deployment.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/pdb.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/serviceaccount.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/templates/services.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/helm/agentco/values.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/namespaces.yaml` | Deployment infrastructure |
| `infrastructure/kubernetes/network-policies.yaml` | Deployment infrastructure |
| `infrastructure/otel/config.yaml` | Deployment infrastructure |
| `infrastructure/prometheus/prometheus.yml` | Deployment infrastructure |
| `infrastructure/vault/policies.hcl` | Deployment infrastructure |
| `ingestion/__init__.py` | Production runtime code |
| `ingestion/adapters/__init__.py` | Production runtime code |
| `ingestion/adapters/code_adapter.py` | Production runtime code |
| `ingestion/adapters/text_adapter.py` | Production runtime code |
| `ingestion/adapters/web_adapter.py` | Production runtime code |
| `ingestion/base.py` | Production runtime code |
| `ingestion/claim_extractor.py` | Production runtime code |
| `ingestion/pipeline.py` | Production runtime code |
| `ingestion/source_registry.py` | Production runtime code |
| `institutions/__init__.py` | Production runtime code |
| `institutions/society.py` | Production runtime code |
| `learning/__init__.py` | Production runtime code |
| `learning/cycle.py` | Production runtime code |
| `learning/intelligence_agent/__init__.py` | Production runtime code |
| `learning/intelligence_agent/intelligence_agent.py` | Production runtime code |
| `learning/learning_loop.py` | Production runtime code |
| `learning/memory_agent/__init__.py` | Production runtime code |
| `learning/memory_agent/memory_agent.py` | Production runtime code |
| `learning/scenario_agent/__init__.py` | Production runtime code |
| `learning/scenario_agent/scenario_agent.py` | Production runtime code |
| `learning/tests/__init__.py` | Test infrastructure |
| `learning/tests/test_learning_loop.py` | Test infrastructure |
| `learning/trainer_agent/__init__.py` | Production runtime code |
| `learning/trainer_agent/trainer_agent.py` | Production runtime code |
| `memory_kernel/__init__.py` | Production runtime code |
| `memory_kernel/memory_kernel.py` | Production runtime code |
| `meta/decision_log.md` | Unknown purpose |
| `meta/failure_modes.md` | Unknown purpose |
| `pg_test_isolation.py` | Unknown purpose |
| `prompts/agentco_resume_prompt.txt` | Unknown purpose |
| `provenance/__init__.py` | Production runtime code |
| `provenance/attestation.py` | Production runtime code |
| `pytest.ini` | Development tooling |
| `pytest_skip_report_plugin.py` | Unknown purpose |
| `reports/civilization_completion/latest/FINAL_CIVILIZATION_COMPLETION_REPORT.md` | Documentation |
| `reports/civilization_completion/latest/civilization_build_ledger.json` | Generated artifact |
| `reports/civilization_completion/latest/completion_manifest.json` | Generated artifact |
| `reports/civilization_completion/latest/completion_reconciliation.json` | Generated artifact |
| `reports/civilization_completion/latest/component_reachability.json` | Generated artifact |
| `reports/civilization_completion/latest/deployment_smoke.json` | Generated artifact |
| `reports/civilization_completion/latest/migration_verification.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_A_civilization_formation.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_B_cross_institution_mission.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_C_governance_changes_behaviour.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_D_judiciary_and_appeal.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_E_learning_and_promotion.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_F_domain_expansion.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_G_restart_and_replay.json` | Generated artifact |
| `reports/civilization_completion/latest/scenario_H_emergency_state.json` | Generated artifact |
| `reports/civilization_completion/latest/test_summary.json` | Generated artifact |
| `reports/system_run/latest/AGENTCO_POST_FIX_VERIFICATION_REPORT.md` | Documentation |
| `reports/system_run/latest/LIVE_OPENAI_SYSTEM_BEHAVIOR_REPORT.md` | Documentation |
| `reports/system_run/latest/MIGRATION_STATUS_REPORT.md` | Documentation |
| `reports/system_run/latest/MOCK_FALLBACK_ISOLATION_REPORT.md` | Documentation |
| `reports/system_run/latest/NO_STUB_AND_SCHEMA_INTEGRITY_REPORT.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_INFRA_SMOKE_REPORT.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_1.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_10.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_11.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_2.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_3.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_4.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_5.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_6.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_7.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_8.md` | Documentation |
| `reports/system_run/latest/PRODUCTION_READINESS_MODULE_9.md` | Documentation |
| `reports/system_run/latest/RUNTIME_INTEGRITY_FINAL_VERIFICATION.md` | Documentation |
| `reports/system_run/latest/build_ledger_report.json` | Generated artifact |
| `reports/system_run/latest/civilization_vertical_slice.json` | Generated artifact |
| `reports/system_run/latest/civilization_vertical_slice.md` | Documentation |
| `reports/system_run/latest/docker_startup_verification.json` | Generated artifact |
| `reports/system_run/latest/docker_startup_verification.md` | Documentation |
| `reports/system_run/latest/doctor_report.json` | Generated artifact |
| `reports/system_run/latest/doctor_report.md` | Documentation |
| `reports/system_run/latest/gate_integrity.json` | Generated artifact |
| `reports/system_run/latest/gate_integrity.md` | Documentation |
| `reports/system_run/latest/goal_run.json` | Generated artifact |
| `reports/system_run/latest/goal_run.md` | Documentation |
| `reports/system_run/latest/live_cross_domain_goal_run.json` | Generated artifact |
| `reports/system_run/latest/live_cross_domain_goal_run.md` | Documentation |
| `reports/system_run/latest/longitudinal_learning_report.json` | Generated artifact |
| `reports/system_run/latest/longitudinal_learning_report.md` | Documentation |
| `reports/system_run/latest/make_target_validation.json` | Generated artifact |
| `reports/system_run/latest/make_target_validation.md` | Documentation |
| `reports/system_run/latest/memory_influence_verification.json` | Generated artifact |
| `reports/system_run/latest/memory_influence_verification.md` | Documentation |
| `reports/system_run/latest/migration_verification.json` | Generated artifact |
| `reports/system_run/latest/mission_progress_verification.json` | Generated artifact |
| `reports/system_run/latest/mission_progress_verification.md` | Documentation |
| `reports/system_run/latest/openai_connectivity.json` | Generated artifact |
| `reports/system_run/latest/performance_summary.json` | Generated artifact |
| `reports/system_run/latest/production_posture_verification.json` | Generated artifact |
| `reports/system_run/latest/release_gate_verification.json` | Generated artifact |
| `reports/system_run/latest/release_gate_verification.md` | Documentation |
| `reports/system_run/latest/resolution_service_verification.json` | Generated artifact |
| `reports/system_run/latest/score_validation.json` | Generated artifact |
| `reports/system_run/latest/score_validation.md` | Documentation |
| `requirements/README.md` | Development tooling |
| `requirements/requirements-dev.txt` | Development tooling |
| `requirements/requirements-runtime.txt` | Development tooling |
| `requirements/requirements.lock.txt` | Development tooling |
| `reserve/__init__.py` | Production runtime code |
| `reserve/chain/__init__.py` | Production runtime code |
| `reserve/chain/commitment_chain.py` | Production runtime code |
| `reserve/credentials/__init__.py` | Production runtime code |
| `reserve/credentials/proof_of_calibration.py` | Production runtime code |
| `reserve/decisions/__init__.py` | Production runtime code |
| `reserve/decisions/weighted_decision.py` | Production runtime code |
| `reserve/keys/agentco_reserve_public.pem` | Production runtime code |
| `reserve/migrations/001_reserve_extension.sql` | Database migration |
| `reserve/migrations/002_staking.sql` | Database migration |
| `reserve/migrations/003_oracle_layer.sql` | Database migration |
| `reserve/migrations/004_ed25519_signature.sql` | Database migration |
| `reserve/migrations/005_prediction_chain.sql` | Database migration |
| `reserve/migrations/006_civilization.sql` | Database migration |
| `reserve/migrations/__init__.py` | Database migration |
| `reserve/oracle/__init__.py` | Production runtime code |
| `reserve/oracle/oracle_layer.py` | Production runtime code |
| `reserve/scoring/__init__.py` | Production runtime code |
| `reserve/scoring/scoring_function.py` | Production runtime code |
| `reserve/staking/__init__.py` | Production runtime code |
| `reserve/staking/staking.py` | Production runtime code |
| `reserve/tests/__init__.py` | Test infrastructure |
| `reserve/tests/dsn.py` | Test infrastructure |
| `reserve/tests/test_agent_reserve_integration.py` | Test infrastructure |
| `reserve/tests/test_ed25519_signing.py` | Test infrastructure |
| `reserve/tests/test_independent_recomputation.py` | Test infrastructure |
| `reserve/tests/test_key_independence_safe.py` | Test infrastructure |
| `reserve/tests/test_oracle_layer.py` | Test infrastructure |
| `reserve/tests/test_proof_of_calibration.py` | Test infrastructure |
| `reserve/tests/test_staking_and_decisions.py` | Test infrastructure |
| `reserve/tests/test_tamper_evidence.py` | Test infrastructure |
| `reserve/tools/recompute_credential.py` | Production runtime code |
| `reserve/tools/seed_civilization.py` | Production runtime code |
| `results/autonomous_advancement/latest_learning_advancement.md` | Documentation |
| `results/autonomous_advancement/learning_advancement_20260622_194220.json` | Generated artifact |
| `results/autonomy_openai/autonomy_openai_1min_20260622_202304.json` | Generated artifact |
| `results/autonomy_tests/true_autonomy_20260622_202800.json` | Generated artifact |
| `results/autonomy_validation/self_correction_20260622_202730.json` | Generated artifact |
| `results/complex_multidomain/report.json` | Generated artifact |
| `results/enterprise_vendor_risk/README.md` | Documentation |
| `results/enterprise_vendor_risk/latest.json` | Generated artifact |
| `results/enterprise_vendor_risk/latest.md` | Documentation |
| `results/enterprise_vendor_risk/runs/smoke_1782128710.json` | Generated artifact |
| `results/enterprise_vendor_risk/runs/smoke_1782128915.json` | Generated artifact |
| `results/evolution_tests/evolution_20260622_195530.json` | Generated artifact |
| `results/evolution_tests/evolution_20260622_200300.json` | Generated artifact |
| `results/evolution_tests/evolution_20260622_201628.json` | Generated artifact |
| `results/integration/realtime_integration_20260622_202545.json` | Generated artifact |
| `results/learning_runs/integrated_5min_20260622_194159.json` | Generated artifact |
| `results/live_cross_domain/latest.json` | Generated artifact |
| `results/live_cross_domain/latest.md` | Documentation |
| `results/north_star_cross_domain/latest.json` | Generated artifact |
| `results/north_star_cross_domain/latest.md` | Documentation |
| `runtime/__init__.py` | Production runtime code |
| `runtime/base_agent/__init__.py` | Production runtime code |
| `runtime/base_agent/agent_manifest.py` | Production runtime code |
| `runtime/base_agent/anthropic_adapter.py` | Production runtime code |
| `runtime/base_agent/audit_writer.py` | Production runtime code |
| `runtime/base_agent/base_agent_v2.py` | Production runtime code |
| `runtime/base_agent/llm_client.py` | Production runtime code |
| `runtime/base_agent/model_tiers.py` | Production runtime code |
| `runtime/base_agent/provider_config.py` | Production runtime code |
| `runtime/base_agent/spend_guardrail.py` | Production runtime code |
| `runtime/base_agent/spend_ledger.py` | Production runtime code |
| `runtime/base_agent/structured_output.py` | Production runtime code |
| `runtime/confidence/__init__.py` | Production runtime code |
| `runtime/confidence/confidence_v2.py` | Production runtime code |
| `runtime/controlled_learning/__init__.py` | Production runtime code |
| `runtime/controlled_learning/pipeline.py` | Production runtime code |
| `runtime/controlled_learning/report.py` | Production runtime code |
| `runtime/controlled_learning/schema.py` | Production runtime code |
| `runtime/escalation/__init__.py` | Production runtime code |
| `runtime/escalation/escalation_gate.py` | Production runtime code |
| `runtime/evaluation/__init__.py` | Production runtime code |
| `runtime/evaluation/benchmark.py` | Production runtime code |
| `runtime/evaluation/evaluators.py` | Production runtime code |
| `runtime/evaluation/metrics.py` | Production runtime code |
| `runtime/evaluation/report.py` | Production runtime code |
| `runtime/evaluation/schema.py` | Production runtime code |
| `runtime/fallbacks/__init__.py` | Production runtime code |
| `runtime/memory/__init__.py` | Production runtime code |
| `runtime/orchestration/__init__.py` | Production runtime code |
| `runtime/orchestration/doctor.py` | Production runtime code |
| `runtime/orchestration/modes.py` | Production runtime code |
| `runtime/orchestration/run_best_effort.py` | Production runtime code |
| `runtime/orchestration/tests/__init__.py` | Test infrastructure |
| `runtime/orchestration/tests/test_modes.py` | Test infrastructure |
| `runtime/orchestration/tests/test_run_best_effort.py` | Test infrastructure |
| `runtime/self_improvement/__init__.py` | Production runtime code |
| `runtime/self_improvement/experiments.py` | Production runtime code |
| `runtime/self_improvement/report.py` | Production runtime code |
| `runtime/self_improvement/schema.py` | Production runtime code |
| `runtime/tests/__init__.py` | Test infrastructure |
| `runtime/tests/conftest.py` | Test infrastructure |
| `runtime/tests/test_agent_protocol_conformance.py` | Test infrastructure |
| `runtime/tests/test_base_agent_v2.py` | Test infrastructure |
| `runtime/tests/test_bounded_self_improvement.py` | Test infrastructure |
| `runtime/tests/test_config_driven_tiers.py` | Test infrastructure |
| `runtime/tests/test_controlled_learning.py` | Test infrastructure |
| `runtime/tests/test_evaluation_calibration.py` | Test infrastructure |
| `runtime/tests/test_local_model_setup.py` | Test infrastructure |
| `runtime/tests/test_runtime_durable_governance_stores.py` | Test infrastructure |
| `runtime/tests/test_spend_guardrail_ledger.py` | Test infrastructure |
| `runtime/tool_registry/__init__.py` | Production runtime code |
| `schemas/agentco_capability_request.schema.json` | Unknown purpose |
| `schemas/agentco_capability_response.schema.json` | Unknown purpose |
| `schemas/cross_version_campaign.schema.json` | Unknown purpose |
| `schemas/longitudinal_history.schema.json` | Unknown purpose |
| `schemas/longitudinal_run_manifest.schema.json` | Unknown purpose |
| `schemas/subject_benchmark_request.schema.json` | Unknown purpose |
| `schemas/subject_benchmark_response.schema.json` | Unknown purpose |
| `scripts/agentco_evolution_test.py` | Development tooling |
| `scripts/agentco_integration_audit.py` | Development tooling |
| `scripts/aggregate_longitudinal_history.py` | Development tooling |
| `scripts/audit_clean_room.py` | Development tooling |
| `scripts/audit_llm_integration.py` | Development tooling |
| `scripts/audit_runtime_integration.py` | Development tooling |
| `scripts/audit_staging_deployment.py` | Development tooling |
| `scripts/autonomous_10min_advancement.py` | Development tooling |
| `scripts/autonomous_prediction_loop.py` | Development tooling |
| `scripts/autonomy_open_world_5min.py` | Development tooling |
| `scripts/autonomy_openai_1min_test.py` | Development tooling |
| `scripts/autonomy_real_web_free_run.py` | Development tooling |
| `scripts/autonomy_real_world_2min_unconstrained.py` | Development tooling |
| `scripts/autonomy_smoke.py` | Development tooling |
| `scripts/b2b_saas_agents.py` | Development tooling |
| `scripts/build_ledger.py` | Development tooling |
| `scripts/calculate_longitudinal_milestones.py` | Development tooling |
| `scripts/check_resolutions.py` | Development tooling |
| `scripts/civilization_free_run.py` | Development tooling |
| `scripts/compare_cross_version_campaign.py` | Development tooling |
| `scripts/compare_longitudinal_runs.py` | Development tooling |
| `scripts/complete_autonomy_test.py` | Development tooling |
| `scripts/complex_multidomain_run.py` | Development tooling |
| `scripts/comprehensive_system_diagnosis.py` | Development tooling |
| `scripts/constitution/check_constitution.py` | Development tooling |
| `scripts/create_capability_genesis_freeze.py` | Development tooling |
| `scripts/demo_business_bikeshare_calibration.py` | Development tooling |
| `scripts/demo_company_in_action.py` | Development tooling |
| `scripts/demo_real_calibration.py` | Development tooling |
| `scripts/demo_verifiable_calibration.py` | Development tooling |
| `scripts/execute_durable_task.py` | Development tooling |
| `scripts/gate0_check.py` | Development tooling |
| `scripts/generate_agent_conformance_matrix.py` | Development tooling |
| `scripts/generate_civilization_completion.py` | Development tooling |
| `scripts/generate_controlled_learning_report.py` | Development tooling |
| `scripts/generate_evaluation_calibration_report.py` | Development tooling |
| `scripts/generate_forensic_audit_controls.py` | Development tooling |
| `scripts/generate_forensic_inventory.py` | Development tooling |
| `scripts/generate_runtime_reachability.py` | Development tooling |
| `scripts/generate_self_improvement_report.py` | Development tooling |
| `scripts/generate_status.py` | Development tooling |
| `scripts/hosted_staging_audit.py` | Development tooling |
| `scripts/hourly_codex_resume.sh` | Development tooling |
| `scripts/longitudinal_foundation.py` | Development tooling |
| `scripts/nse_canonical_trust_weighting_test.py` | Development tooling |
| `scripts/nse_data_fetcher.py` | Development tooling |
| `scripts/nse_data_real_fetch.py` | Development tooling |
| `scripts/nse_data_stop_1.py` | Development tooling |
| `scripts/nse_data_stop_1_fixed.py` | Development tooling |
| `scripts/nse_phase1_root_cause.py` | Development tooling |
| `scripts/nse_phase2_extended_market.py` | Development tooling |
| `scripts/nse_phase3_to_5_pipeline.py` | Development tooling |
| `scripts/nse_phase6_better_agents.py` | Development tooling |
| `scripts/nse_three_arm_walkforward.py` | Development tooling |
| `scripts/repair_decision_log_hash_chain.py` | Development tooling |
| `scripts/run_accelerated_business_simulation.py` | Development tooling |
| `scripts/run_autonomy_eval.py` | Development tooling |
| `scripts/run_b2b_saas_four_arm_experiment.py` | Development tooling |
| `scripts/run_b2b_saas_simulation.py` | Development tooling |
| `scripts/run_b2b_saas_soft_weighting.py` | Development tooling |
| `scripts/run_cross_version_campaign.py` | Development tooling |
| `scripts/run_diagnostic_weighting_tests.py` | Development tooling |
| `scripts/run_first_real_prediction.py` | Development tooling |
| `scripts/run_fitness_subscription_simulation.py` | Development tooling |
| `scripts/run_full_autonomy_loop_with_specialists.sh` | Development tooling |
| `scripts/run_governed_capability_genesis.py` | Development tooling |
| `scripts/run_integrated_learning_5min.py` | Development tooling |
| `scripts/run_learner.py` | Development tooling |
| `scripts/run_level3_autonomy_smoke.py` | Development tooling |
| `scripts/run_level3_functional_verification.sh` | Development tooling |
| `scripts/run_level3_real_smoke.py` | Development tooling |
| `scripts/run_level4_full_test.sh` | Development tooling |
| `scripts/run_level4_phase2_tests.sh` | Development tooling |
| `scripts/run_level4_phase3_tests.sh` | Development tooling |
| `scripts/run_local_agent.py` | Development tooling |
| `scripts/run_longitudinal_campaign.py` | Development tooling |
| `scripts/run_pawdent_business_simulation.py` | Development tooling |
| `scripts/run_real_world_validation.py` | Development tooling |
| `scripts/run_staging_validation_gate.sh` | Development tooling |
| `scripts/run_subject_native_cross_version_campaign.py` | Development tooling |
| `scripts/scan_committed_secrets.py` | Development tooling |
| `scripts/setup_release_gate_role.sql` | Development tooling |
| `scripts/smoke_frontend_auth.sh` | Development tooling |
| `scripts/smoke_one_task.py` | Development tooling |
| `scripts/system_integration_validation.py` | Development tooling |
| `scripts/test_autonomy_governance_integration.py` | Test infrastructure |
| `scripts/test_calibration_change_governance.py` | Test infrastructure |
| `scripts/test_calibration_constitution.py` | Test infrastructure |
| `scripts/test_calibration_drift_monitor.py` | Test infrastructure |
| `scripts/test_civilization_adversarial_trust.py` | Test infrastructure |
| `scripts/test_civilization_api.py` | Test infrastructure |
| `scripts/test_civilization_integration.py` | Test infrastructure |
| `scripts/test_civilization_learning.py` | Test infrastructure |
| `scripts/test_civilization_smoke.py` | Test infrastructure |
| `scripts/test_concurrency.py` | Test infrastructure |
| `scripts/test_crash_recovery.py` | Test infrastructure |
| `scripts/test_eval_gates.py` | Test infrastructure |
| `scripts/test_frontend_real_data.py` | Test infrastructure |
| `scripts/test_goal_management.py` | Test infrastructure |
| `scripts/test_governance_api.py` | Test infrastructure |
| `scripts/test_governance_integration.py` | Test infrastructure |
| `scripts/test_governance_rbac.py` | Test infrastructure |
| `scripts/test_idempotency.py` | Test infrastructure |
| `scripts/test_perception.py` | Test infrastructure |
| `scripts/test_phases_5_8.py` | Test infrastructure |
| `scripts/test_phases_9_13.py` | Test infrastructure |
| `scripts/test_production_security_gate.py` | Test infrastructure |
| `scripts/test_production_smoke.py` | Test infrastructure |
| `scripts/test_protected_surfaces.py` | Test infrastructure |
| `scripts/test_rbac.py` | Test infrastructure |
| `scripts/test_realtime_integration.py` | Test infrastructure |
| `scripts/test_rollback.py` | Test infrastructure |
| `scripts/test_self_correction.py` | Test infrastructure |
| `scripts/test_staging_dr.sh` | Test infrastructure |
| `scripts/test_staging_governance_gate.sh` | Test infrastructure |
| `scripts/test_staging_load.py` | Test infrastructure |
| `scripts/test_staging_smoke.sh` | Test infrastructure |
| `scripts/test_trust_impact_assessment.py` | Test infrastructure |
| `scripts/test_trust_policy.py` | Test infrastructure |
| `scripts/test_trust_policy_canary.py` | Test infrastructure |
| `scripts/test_trust_reputation.py` | Test infrastructure |
| `scripts/true_autonomy_test.py` | Development tooling |
| `scripts/verify_agentco_goal_run.py` | Development tooling |
| `scripts/verify_agentco_multidomain_live_run.py` | Development tooling |
| `scripts/verify_benchmark_governance.py` | Development tooling |
| `scripts/verify_campaign_evidence_binding.py` | Development tooling |
| `scripts/verify_capability_genesis_artifact.py` | Development tooling |
| `scripts/verify_capability_genesis_freeze.py` | Development tooling |
| `scripts/verify_civilization_vertical_slice.py` | Development tooling |
| `scripts/verify_cross_version_campaign.py` | Development tooling |
| `scripts/verify_cross_version_harness_independence.py` | Development tooling |
| `scripts/verify_docker_startup.py` | Development tooling |
| `scripts/verify_execution_ledger.py` | Development tooling |
| `scripts/verify_gate_integrity.py` | Development tooling |
| `scripts/verify_hosted_staging_budget.py` | Development tooling |
| `scripts/verify_level3_architecture.py` | Development tooling |
| `scripts/verify_level3_db_evidence.py` | Development tooling |
| `scripts/verify_level4_certification.sh` | Development tooling |
| `scripts/verify_longitudinal_evidence.py` | Development tooling |
| `scripts/verify_make_targets.py` | Development tooling |
| `scripts/verify_memory_influence_live.py` | Development tooling |
| `scripts/verify_migration_identity.py` | Development tooling |
| `scripts/verify_migration_integrity.py` | Development tooling |
| `scripts/verify_migrations_native.py` | Development tooling |
| `scripts/verify_mission_progress.py` | Development tooling |
| `scripts/verify_openai_connectivity.py` | Development tooling |
| `scripts/verify_production_posture.py` | Development tooling |
| `scripts/verify_pytest_skips.py` | Development tooling |
| `scripts/verify_release_gates.py` | Development tooling |
| `scripts/verify_resolution_service.py` | Development tooling |
| `scripts/verify_subject_answer_ownership.py` | Development tooling |
| `scripts/verify_subject_request_consumption.py` | Development tooling |
| `scripts/verify_subject_runtime_evidence.py` | Development tooling |
| `scripts/wait_for_postgres.sh` | Development tooling |
| `scripts/web_scraper_free.py` | Development tooling |
| `self_modification/__init__.py` | Production runtime code |
| `self_modification/kernel.py` | Production runtime code |
| `selfcoding/BREACH_TEST_RESULTS.md` | Unknown purpose |
| `selfcoding/SELF_EXTENSION_BUILD_SUMMARY.md` | Unknown purpose |
| `selfcoding/__init__.py` | Unknown purpose |
| `selfcoding/coder/__init__.py` | Unknown purpose |
| `selfcoding/coder/build_spec.py` | Unknown purpose |
| `selfcoding/coder/qwen_coder.py` | Unknown purpose |
| `selfcoding/planner/__init__.py` | Unknown purpose |
| `selfcoding/planner/openai_planner.py` | Unknown purpose |
| `selfcoding/resolver/SEALED_RESOLVER_SPEC.md` | Unknown purpose |
| `selfcoding/resolver/__init__.py` | Unknown purpose |
| `selfcoding/resolver/sealed_resolver.py` | Unknown purpose |
| `selfcoding/run_self_extension.py` | Unknown purpose |
| `selfcoding/sandbox/__init__.py` | Unknown purpose |
| `selfcoding/sandbox/run_generated.py` | Unknown purpose |
| `selfcoding/test_coder_sandbox_integration.py` | Test infrastructure |
| `selfcoding/tests/test_wall_holds.py` | Test infrastructure |
| `selfcoding/verify_wall_under_live_code.py` | Unknown purpose |
| `simulation/__init__.py` | Experimental code |
| `simulation/world_lab.py` | Experimental code |
| `synthesis/__init__.py` | Production runtime code |
| `synthesis/principle_library/__init__.py` | Production runtime code |
| `synthesis/principle_library/principle_library.py` | Production runtime code |
| `synthesis/source_library/__init__.py` | Production runtime code |
| `synthesis/synthesis_agent/__init__.py` | Production runtime code |
| `synthesis/synthesis_agent/synthesis_agent.py` | Production runtime code |
| `synthesis/tests/__init__.py` | Test infrastructure |
| `synthesis/tests/test_synthesis.py` | Test infrastructure |
| `synthesis/theory_engine/__init__.py` | Production runtime code |
| `synthesis/theory_engine/theory_engine.py` | Production runtime code |
| `tests/civilization/test_contract_validation.py` | Test infrastructure |
| `tests/civilization/test_governance.py` | Test infrastructure |
| `tests/civilization/test_migration.py` | Test infrastructure |
| `tests/civilization/test_review_and_reputation.py` | Test infrastructure |
| `tests/conftest.py` | Test infrastructure |
| `tests/e2e/conftest.py` | Test infrastructure |
| `tests/e2e/test_institution_operating_loop.py` | Test infrastructure |
| `tests/e2e/test_memory_lifecycle.py` | Test infrastructure |
| `tests/integration/test_resolution_service_role_migration.py` | Test infrastructure |
| `tests/integration/test_web_scraper_hardened.py` | Test infrastructure |
| `tests/test_build_ledger.py` | Test infrastructure |
| `tests/test_capability_anti_gaming.py` | Test infrastructure |
| `tests/test_capability_anti_hardcoding.py` | Test infrastructure |
| `tests/test_capability_freeze_binding.py` | Test infrastructure |
| `tests/test_capability_freeze_integrity.py` | Test infrastructure |
| `tests/test_capability_genesis_v2.py` | Test infrastructure |
| `tests/test_capability_genesis_v3.py` | Test infrastructure |
| `tests/test_capability_genesis_v4.py` | Test infrastructure |
| `tests/test_capability_genesis_v5.py` | Test infrastructure |
| `tests/test_capability_preflight.py` | Test infrastructure |
| `tests/test_capability_provider_adapters.py` | Test infrastructure |
| `tests/test_capability_runtime.py` | Test infrastructure |
| `tests/test_civilization_free_run_positive_path.py` | Test infrastructure |
| `tests/test_civilization_vertical_slice.py` | Test infrastructure |
| `tests/test_clean_room_evidence_controls.py` | Test infrastructure |
| `tests/test_compose_bind_sources.py` | Test infrastructure |
| `tests/test_cross_version_campaign.py` | Test infrastructure |
| `tests/test_data_capability_workspace.py` | Test infrastructure |
| `tests/test_db_client_runtime_config.py` | Test infrastructure |
| `tests/test_domain_scorers.py` | Test infrastructure |
| `tests/test_durable_runtime_cleanup.py` | Test infrastructure |
| `tests/test_execute_durable_task.py` | Test infrastructure |
| `tests/test_forensic_inventory.py` | Test infrastructure |
| `tests/test_gate_integrity_controls.py` | Test infrastructure |
| `tests/test_hosted_staging_controls.py` | Test infrastructure |
| `tests/test_longitudinal_foundation.py` | Test infrastructure |
| `tests/test_longitudinal_remote_closure.py` | Test infrastructure |
| `tests/test_migration_inventory.py` | Test infrastructure |
| `tests/test_pawdent_business_simulation.py` | Test infrastructure |
| `tests/test_protocol_baseline.py` | Test infrastructure |
| `tests/test_protocol_baseline_v2.py` | Test infrastructure |
| `tests/test_protocol_baseline_v3.py` | Test infrastructure |
| `tests/test_protocol_budget_settlement.py` | Test infrastructure |
| `tests/test_protocol_control_execution.py` | Test infrastructure |
| `tests/test_protocol_persistence_reinitialization.py` | Test infrastructure |
| `tests/test_protocol_schema_validation.py` | Test infrastructure |
| `tests/test_protocol_secret_redaction.py` | Test infrastructure |
| `tests/test_runtime_integration_controls.py` | Test infrastructure |
| `tests/test_software_capability_workspace.py` | Test infrastructure |
| `tests/test_specialist_agent.py` | Test infrastructure |
| `tests/test_specialist_isolation_verification.py` | Test infrastructure |
| `tests/test_staging_deployment_controls.py` | Test infrastructure |
| `tests/test_trust_monotonicity.py` | Test infrastructure |
| `tests/test_verify_agentco_goal_run.py` | Test infrastructure |
| `tests/test_verify_agentco_multidomain_live_run.py` | Test infrastructure |
| `tests/test_verify_docker_startup.py` | Test infrastructure |
| `tests/test_verify_memory_influence_live.py` | Test infrastructure |
| `tests/test_verify_migrations_native.py` | Test infrastructure |
| `tests/test_verify_mission_progress.py` | Test infrastructure |
| `tests/test_verify_production_posture.py` | Test infrastructure |
| `tests/test_verify_release_gates.py` | Test infrastructure |
| `tests/test_weighting_floor_fix.py` | Test infrastructure |
| `validation/__init__.py` | Generated artifact |
| `validation/reports/validation_report.json` | Generated artifact |
| `validation/reports/validation_report.md` | Generated artifact |
| `validation/suite.py` | Generated artifact |
