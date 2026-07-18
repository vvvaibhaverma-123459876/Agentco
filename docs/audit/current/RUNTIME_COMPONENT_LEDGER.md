# Runtime Component Ledger

Tracked structural snapshot input hash `5fb6528e6b23795e8922ba9c6bde4510d949f64d0653b5b7a3c38d0863078978`.

| component_id | path | classification | authoritative_status | process_type | entrypoint | external_dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| agents-autonomy-init-py | agents/autonomy/__init__.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-main-py | agents/autonomy/__main__.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-background-researcher-py | agents/autonomy/background_researcher.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-claim-validator-py | agents/autonomy/claim_validator.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-code-reviewer-py | agents/autonomy/code_reviewer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-comparative-analyst-py | agents/autonomy/comparative_analyst.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-contradiction-hunter-py | agents/autonomy/contradiction_hunter.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-data-analyst-py | agents/autonomy/data_analyst.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-doc-analyzer-py | agents/autonomy/doc_analyzer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-evidence-linker-py | agents/autonomy/evidence_linker.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-evidence-summarizer-py | agents/autonomy/evidence_summarizer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-fetcher-py | agents/autonomy/fetcher.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-quality-auditor-py | agents/autonomy/quality_auditor.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-researcher-py | agents/autonomy/researcher.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-reviewer-py | agents/autonomy/reviewer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-sentiment-analyzer-py | agents/autonomy/sentiment_analyzer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-source-validator-py | agents/autonomy/source_validator.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-specialist-agent-py | agents/autonomy/specialist_agent.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | ['PostgreSQL'] |
| agents-autonomy-synthesizer-py | agents/autonomy/synthesizer.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| agents-autonomy-temporal-analyst-py | agents/autonomy/temporal_analyst.py | authoritative_runtime | live_specialist_runtime | python_specialist_agent | python3.13 -m agents.autonomy.<role> | [] |
| backend-src-adapters-real-web-adapter-ts | backend/src/adapters/real-web-adapter.ts | runtime_support | support | library | None | [] |
| backend-src-adapters-url-safety-ts | backend/src/adapters/url-safety.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-adapters-web-adapter-ts | backend/src/adapters/web-adapter.ts | runtime_support | support | library | None | [] |
| backend-src-agent-registry-ts | backend/src/agent-registry.ts | runtime_support | support | library | None | ['PostgreSQL'] |
| backend-src-auth-identity-lookup-ts | backend/src/auth/identity-lookup.ts | runtime_support | support | library | None | ['PostgreSQL'] |
| backend-src-auth-principal-context-ts | backend/src/auth/principal-context.ts | runtime_support | support | library | None | [] |
| backend-src-auth-request-principal-ts | backend/src/auth/request-principal.ts | runtime_support | support | library | None | [] |
| backend-src-cli-autonomy-ts | backend/src/cli/autonomy.ts | runtime_support | support | library | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-cli-db-table-usage-ts | backend/src/cli/db-table-usage.ts | runtime_support | support | library | None | ['PostgreSQL'] |
| backend-src-cli-run-bounded-learning-ts | backend/src/cli/run-bounded-learning.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-cli-run-longitudinal-learning-ts | backend/src/cli/run-longitudinal-learning.ts | runtime_support | support | library | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-cli-score-validation-ts | backend/src/cli/score-validation.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-cli-smoke-durable-execution-ts | backend/src/cli/smoke-durable-execution.ts | runtime_support | support | library | None | [] |
| backend-src-cli-supervised-free-run-ts | backend/src/cli/supervised-free-run.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-cli-supervised-runtime-ts | backend/src/cli/supervised-runtime.ts | runtime_support | support | library | None | [] |
| backend-src-config-init-py | backend/src/config/__init__.py | runtime_support | support | library | None | [] |
| backend-src-config-provider-config-py | backend/src/config/provider_config.py | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-db-client-ts | backend/src/db/client.ts | runtime_support | support | database_runtime | None | ['PostgreSQL'] |
| backend-src-db-dsn-ts | backend/src/db/dsn.ts | runtime_support | support | database_runtime | None | ['PostgreSQL'] |
| backend-src-db-kafka-ts | backend/src/db/kafka.ts | runtime_support | support | database_runtime | None | ['Kafka'] |
| backend-src-db-migrate-ts | backend/src/db/migrate.ts | runtime_support | support | database_runtime | None | ['PostgreSQL'] |
| backend-src-db-run-migrations-py | backend/src/db/run_migrations.py | runtime_support | support | database_runtime | None | ['PostgreSQL'] |
| backend-src-feature-gates-ts | backend/src/feature-gates.ts | runtime_support | support | library | None | [] |
| backend-src-health-ts | backend/src/health.ts | runtime_support | support | library | None | ['Kafka', 'PostgreSQL'] |
| backend-src-http-errors-ts | backend/src/http-errors.ts | runtime_support | support | library | None | [] |
| backend-src-middleware-civilization-request-validator-ts | backend/src/middleware/civilization-request-validator.ts | runtime_support | support | library | None | [] |
| backend-src-middleware-learning-middleware-ts | backend/src/middleware/learning.middleware.ts | runtime_support | support | library | None | [] |
| backend-src-routes-agents-routes-ts | backend/src/routes/agents.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-audit-routes-ts | backend/src/routes/audit.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-autonomy-dashboard-routes-ts | backend/src/routes/autonomy-dashboard.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | ['PostgreSQL'] |
| backend-src-routes-autonomy-orchestrator-routes-ts | backend/src/routes/autonomy-orchestrator.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | ['PostgreSQL'] |
| backend-src-routes-autonomy-tasks-routes-ts | backend/src/routes/autonomy-tasks.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-capabilities-routes-ts | backend/src/routes/capabilities.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-capability-expansion-routes-ts | backend/src/routes/capability-expansion.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-citizenship-routes-ts | backend/src/routes/citizenship.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-civilization-governance-routes-ts | backend/src/routes/civilization-governance.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-civilization-kernel-routes-ts | backend/src/routes/civilization-kernel.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-civilization-operator-routes-ts | backend/src/routes/civilization-operator.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-civilization-os-routes-ts | backend/src/routes/civilization-os.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-coalition-routes-ts | backend/src/routes/coalition.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-collective-knowledge-routes-ts | backend/src/routes/collective-knowledge.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-credential-routes-ts | backend/src/routes/credential.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-goal-hierarchy-routes-ts | backend/src/routes/goal-hierarchy.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-governance-proposals-routes-ts | backend/src/routes/governance-proposals.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-governance-routes-ts | backend/src/routes/governance.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-identity-routes-ts | backend/src/routes/identity.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-institution-work-assignment-routes-ts | backend/src/routes/institution-work-assignment.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-judiciary-case-routes-ts | backend/src/routes/judiciary-case.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-mission-routes-ts | backend/src/routes/mission.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-override-routes-ts | backend/src/routes/override.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-param-validation-ts | backend/src/routes/param-validation.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-phase3-hardening-routes-ts | backend/src/routes/phase3-hardening.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-resource-ledger-routes-ts | backend/src/routes/resource-ledger.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-safe-evolution-routes-ts | backend/src/routes/safe-evolution.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-society-routes-ts | backend/src/routes/society.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-routes-system-routes-ts | backend/src/routes/system.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | ['PostgreSQL'] |
| backend-src-routes-treasury-routes-ts | backend/src/routes/treasury.routes.ts | authoritative_runtime | authoritative | http_route_module | backend/src/server.ts route registration | [] |
| backend-src-runtime-shutdown-ts | backend/src/runtime/shutdown.ts | runtime_support | support | library | None | ['Kafka'] |
| backend-src-runtime-mode-ts | backend/src/runtime-mode.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-security-ts | backend/src/security.ts | runtime_support | support | library | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-server-ts | backend/src/server.ts | authoritative_runtime | authoritative | backend_http_server | node dist/server.js | [] |
| backend-src-services-action-executor-service-ts | backend/src/services/action-executor.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-adaptive-strategy-service-ts | backend/src/services/adaptive-strategy.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-audit-log-service-ts | backend/src/services/audit-log.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-autonomous-promotion-service-ts | backend/src/services/autonomous-promotion.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-autonomy-action-planner-service-ts | backend/src/services/autonomy-action-planner.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-autonomy-civilization-bridge-service-ts | backend/src/services/autonomy-civilization-bridge.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-autonomy-metrics-service-ts | backend/src/services/autonomy-metrics.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-autonomy-orchestrator-service-ts | backend/src/services/autonomy-orchestrator.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-autonomy-run-service-ts | backend/src/services/autonomy-run.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-bayesian-service-ts | backend/src/services/bayesian.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-belief-demotion-service-ts | backend/src/services/belief-demotion.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-bounded-learning-run-service-ts | backend/src/services/bounded-learning-run.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-calibration-aware-routing-service-ts | backend/src/services/calibration-aware-routing.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-calibration-change-governance-service-ts | backend/src/services/calibration-change-governance.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-calibration-constitution-service-ts | backend/src/services/calibration-constitution.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-calibration-drift-monitor-service-ts | backend/src/services/calibration-drift-monitor.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-candidate-evaluation-service-ts | backend/src/services/candidate-evaluation.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-capability-expansion-gate-service-ts | backend/src/services/capability-expansion-gate.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-capability-expansion-service-ts | backend/src/services/capability-expansion.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-capability-runtime-service-ts | backend/src/services/capability-runtime.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-citizenship-service-ts | backend/src/services/citizenship.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-kernel-service-ts | backend/src/services/civilization-kernel.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-live-flow-service-ts | backend/src/services/civilization-live-flow.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-metrics-service-ts | backend/src/services/civilization-metrics.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-civilization-operator-service-ts | backend/src/services/civilization-operator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-os-service-ts | backend/src/services/civilization-os.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-runtime-service-ts | backend/src/services/civilization-runtime.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-civilization-scheduler-service-ts | backend/src/services/civilization-scheduler.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-civilization-service-ts | backend/src/services/civilization.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-claim-accuracy-tracker-service-ts | backend/src/services/claim-accuracy-tracker.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-claim-grounding-service-ts | backend/src/services/claim-grounding.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-coalition-formation-service-ts | backend/src/services/coalition-formation.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-coalition-service-ts | backend/src/services/coalition.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-collective-knowledge-service-ts | backend/src/services/collective-knowledge.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-confidence-service-ts | backend/src/services/confidence.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-crash-recovery-service-ts | backend/src/services/crash-recovery.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-credential-service-ts | backend/src/services/credential.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-deadlock-detector-service-ts | backend/src/services/deadlock-detector.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-deterministic-benchmark-service-ts | backend/src/services/deterministic-benchmark.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-domain-registry-service-ts | backend/src/services/domain-registry.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-durable-execution-service-ts | backend/src/services/durable-execution.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-dynamic-calibration-service-ts | backend/src/services/dynamic-calibration.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-ensemble-service-ts | backend/src/services/ensemble.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-eval-harness-service-ts | backend/src/services/eval-harness.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-event-bus-service-ts | backend/src/services/event-bus.service.ts | runtime_support | support | service | None | ['Kafka'] |
| backend-src-services-event-log-service-ts | backend/src/services/event-log.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-evidence-registry-service-ts | backend/src/services/evidence-registry.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-evidence-vector-index-service-ts | backend/src/services/evidence-vector-index.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-falsifiable-prediction-service-ts | backend/src/services/falsifiable-prediction.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-generality-metric-tracker-service-ts | backend/src/services/generality-metric-tracker.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-goal-formation-service-ts | backend/src/services/goal-formation.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-goal-hierarchy-service-ts | backend/src/services/goal-hierarchy.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-goal-manager-service-ts | backend/src/services/goal-manager.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-goal-source-discovery-service-ts | backend/src/services/goal-source-discovery.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-governance-rbac-service-ts | backend/src/services/governance-rbac.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-governance-reputation-integration-service-ts | backend/src/services/governance-reputation-integration.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-governance-service-ts | backend/src/services/governance.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-grounded-resolver-service-ts | backend/src/services/grounded-resolver.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-hash-chain-anchor-service-ts | backend/src/services/hash-chain-anchor.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-idempotency-store-service-ts | backend/src/services/idempotency-store.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-identity-authority-service-ts | backend/src/services/identity-authority.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-independent-resolver-service-ts | backend/src/services/independent-resolver.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-input-validator-service-ts | backend/src/services/input-validator.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-institution-claim-vetting-service-ts | backend/src/services/institution-claim-vetting.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-institution-governance-service-ts | backend/src/services/institution-governance.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-institution-work-assignment-service-ts | backend/src/services/institution-work-assignment.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-institutional-knowledge-bridge-service-ts | backend/src/services/institutional-knowledge-bridge.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-institutional-synthesis-service-ts | backend/src/services/institutional-synthesis.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-institutions-service-ts | backend/src/services/institutions.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-integration-service-ts | backend/src/services/integration.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-judiciary-case-service-ts | backend/src/services/judiciary-case.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-judiciary-review-service-ts | backend/src/services/judiciary-review.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-judiciary-service-ts | backend/src/services/judiciary.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-kb-expansion-service-ts | backend/src/services/kb-expansion.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-kill-switch-service-ts | backend/src/services/kill-switch.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-knowledge-persistence-service-ts | backend/src/services/knowledge-persistence.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-learner-service-ts | backend/src/services/learner.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-learning-service-ts | backend/src/services/learning.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-learning-bridge-py | backend/src/services/learning_bridge.py | runtime_support | support | service | None | [] |
| backend-src-services-llm-provider-service-ts | backend/src/services/llm-provider.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-load-test-harness-service-ts | backend/src/services/load-test-harness.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-longitudinal-learning-harness-service-ts | backend/src/services/longitudinal-learning-harness.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-loop-detector-service-ts | backend/src/services/loop-detector.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-memory-promotion-pipeline-service-ts | backend/src/services/memory-promotion-pipeline.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-memory-retrieval-service-ts | backend/src/services/memory-retrieval.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-memory-store-service-ts | backend/src/services/memory-store.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-metrics-service-ts | backend/src/services/metrics.service.ts | runtime_support | support | service | None | ['Kafka'] |
| backend-src-services-mission-service-ts | backend/src/services/mission.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-multi-agent-ensemble-service-ts | backend/src/services/multi-agent-ensemble.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-observability-service-ts | backend/src/services/observability.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-orchestrator-service-ts | backend/src/services/orchestrator.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-override-queue-service-ts | backend/src/services/override-queue.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-perception-service-ts | backend/src/services/perception.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-persistent-agent-registry-service-ts | backend/src/services/persistent-agent-registry.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-persistent-trust-scorer-service-ts | backend/src/services/persistent-trust-scorer.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-planner-service-ts | backend/src/services/planner.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-policy-enforcement-service-ts | backend/src/services/policy-enforcement.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-proof-of-competence-service-ts | backend/src/services/proof-of-competence.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-protected-surface-validator-service-ts | backend/src/services/protected-surface-validator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-provenance-service-ts | backend/src/services/provenance.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-rag-service-ts | backend/src/services/rag.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-rate-limiter-service-ts | backend/src/services/rate-limiter.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-reflection-service-ts | backend/src/services/reflection.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-regression-test-generator-service-ts | backend/src/services/regression-test-generator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-reputation-learning-service-ts | backend/src/services/reputation-learning.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-reputation-scale-service-ts | backend/src/services/reputation-scale.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-resolution-service-service-ts | backend/src/services/resolution-service.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-resource-ledger-service-ts | backend/src/services/resource-ledger.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-reward-calculator-service-ts | backend/src/services/reward-calculator.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-risk-tier-classifier-service-ts | backend/src/services/risk-tier-classifier.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-rollback-service-ts | backend/src/services/rollback.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-run-guard-service-ts | backend/src/services/run-guard.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-safe-evolution-service-ts | backend/src/services/safe-evolution.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-safety-service-ts | backend/src/services/safety.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-saga-coordinator-service-ts | backend/src/services/saga-coordinator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-self-modification-validator-service-ts | backend/src/services/self-modification-validator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-simulator-service-ts | backend/src/services/simulator.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-skill-canary-service-ts | backend/src/services/skill-canary.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-skill-deployment-service-ts | backend/src/services/skill-deployment.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-skill-library-service-ts | backend/src/services/skill-library.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-skill-promotion-loop-service-ts | backend/src/services/skill-promotion-loop.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-skill-retrieval-service-ts | backend/src/services/skill-retrieval.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-society-service-ts | backend/src/services/society.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-source-discovery-service-ts | backend/src/services/source-discovery.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-structured-logger-service-ts | backend/src/services/structured-logger.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-supervised-free-run-service-ts | backend/src/services/supervised-free-run.service.ts | runtime_support | support | service | None | ['LLM provider'] |
| backend-src-services-supervised-runtime-service-ts | backend/src/services/supervised-runtime.service.ts | runtime_support | support | service | None | ['LLM provider', 'PostgreSQL'] |
| backend-src-services-symbolic-service-ts | backend/src/services/symbolic.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-task-engine-service-ts | backend/src/services/task-engine.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-team-activation-service-ts | backend/src/services/team-activation.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trajectory-store-service-ts | backend/src/services/trajectory-store.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-transactional-outbox-service-ts | backend/src/services/transactional-outbox.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-treasury-service-ts | backend/src/services/treasury.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trust-impact-assessment-service-ts | backend/src/services/trust-impact-assessment.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trust-policy-canary-service-ts | backend/src/services/trust-policy-canary.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trust-policy-service-ts | backend/src/services/trust-policy.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trust-reputation-service-ts | backend/src/services/trust-reputation.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-services-trust-scoring-service-ts | backend/src/services/trust-scoring.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-trustworthiness-service-ts | backend/src/services/trustworthiness.service.ts | runtime_support | support | service | None | [] |
| backend-src-services-worker-coordinator-service-ts | backend/src/services/worker-coordinator.service.ts | runtime_support | support | service | None | ['PostgreSQL'] |
| backend-src-types-action-types-ts | backend/src/types/action.types.ts | runtime_support | support | library | None | [] |
| backend-src-types-capability-types-ts | backend/src/types/capability.types.ts | runtime_support | support | library | None | [] |
| backend-src-types-specialist-roles-ts | backend/src/types/specialist-roles.ts | runtime_support | support | library | None | ['LLM provider'] |
| backend-src-workers-civilization-scheduler-worker-ts | backend/src/workers/civilization-scheduler-worker.ts | runtime_support | support | library | None | [] |
| backend-src-workers-outbox-worker-ts | backend/src/workers/outbox-worker.ts | authoritative_runtime | authoritative | worker | npm run agentco:outbox-worker | ['Kafka'] |
| backend-src-workers-task-worker-ts | backend/src/workers/task-worker.ts | runtime_support | support | library | None | [] |
| evals-enterprise-vendor-risk-init-py | evals/enterprise_vendor_risk/__init__.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-adapters-init-py | evals/enterprise_vendor_risk/adapters/__init__.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-adapters-agentco-adapter-py | evals/enterprise_vendor_risk/adapters/agentco_adapter.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-adapters-base-py | evals/enterprise_vendor_risk/adapters/base.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider'] |
| evals-enterprise-vendor-risk-adapters-fake-adapter-py | evals/enterprise_vendor_risk/adapters/fake_adapter.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-adapters-rag-adapter-py | evals/enterprise_vendor_risk/adapters/rag_adapter.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider'] |
| evals-enterprise-vendor-risk-adapters-simulated-llm-adapters-py | evals/enterprise_vendor_risk/adapters/simulated_llm_adapters.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider'] |
| evals-enterprise-vendor-risk-cli-py | evals/enterprise_vendor_risk/cli.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider'] |
| evals-enterprise-vendor-risk-correctness-utils-py | evals/enterprise_vendor_risk/correctness_utils.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider'] |
| evals-enterprise-vendor-risk-leaderboard-py | evals/enterprise_vendor_risk/leaderboard.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-provenance-py | evals/enterprise_vendor_risk/provenance.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-report-py | evals/enterprise_vendor_risk/report.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-run-benchmark-py | evals/enterprise_vendor_risk/run_benchmark.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-score-py | evals/enterprise_vendor_risk/score.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-test-benchmark-py | evals/enterprise_vendor_risk/test_benchmark.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| evals-enterprise-vendor-risk-test-db-persistence-py | evals/enterprise_vendor_risk/test_db_persistence.py | runtime_support | benchmark_support | evaluation_support | None | ['LLM provider', 'PostgreSQL'] |
| evals-enterprise-vendor-risk-validation-framework-py | evals/enterprise_vendor_risk/validation_framework.py | runtime_support | benchmark_support | evaluation_support | None | [] |
| learning-init-py | learning/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-cycle-py | learning/cycle.py | experimental | experimental | python_research_module | None | [] |
| learning-intelligence-agent-init-py | learning/intelligence_agent/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-intelligence-agent-intelligence-agent-py | learning/intelligence_agent/intelligence_agent.py | experimental | experimental | python_research_module | None | [] |
| learning-learning-loop-py | learning/learning_loop.py | experimental | experimental | python_research_module | None | [] |
| learning-memory-agent-init-py | learning/memory_agent/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-memory-agent-memory-agent-py | learning/memory_agent/memory_agent.py | experimental | experimental | python_research_module | None | [] |
| learning-scenario-agent-init-py | learning/scenario_agent/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-scenario-agent-scenario-agent-py | learning/scenario_agent/scenario_agent.py | experimental | experimental | python_research_module | None | [] |
| learning-tests-init-py | learning/tests/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-tests-test-learning-loop-py | learning/tests/test_learning_loop.py | experimental | experimental | python_research_module | None | [] |
| learning-trainer-agent-init-py | learning/trainer_agent/__init__.py | experimental | experimental | python_research_module | None | [] |
| learning-trainer-agent-trainer-agent-py | learning/trainer_agent/trainer_agent.py | experimental | experimental | python_research_module | None | [] |
| runtime-init-py | runtime/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-base-agent-init-py | runtime/base_agent/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-base-agent-agent-manifest-py | runtime/base_agent/agent_manifest.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-base-agent-anthropic-adapter-py | runtime/base_agent/anthropic_adapter.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-base-agent-audit-writer-py | runtime/base_agent/audit_writer.py | runtime_support | support | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-base-agent-base-agent-v2-py | runtime/base_agent/base_agent_v2.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['LLM provider', 'PostgreSQL'] |
| runtime-base-agent-llm-client-py | runtime/base_agent/llm_client.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-base-agent-model-tiers-py | runtime/base_agent/model_tiers.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-base-agent-provider-config-py | runtime/base_agent/provider_config.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-base-agent-spend-guardrail-py | runtime/base_agent/spend_guardrail.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-base-agent-spend-ledger-py | runtime/base_agent/spend_ledger.py | runtime_support | support | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-base-agent-structured-output-py | runtime/base_agent/structured_output.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-confidence-init-py | runtime/confidence/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-confidence-confidence-v2-py | runtime/confidence/confidence_v2.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-controlled-learning-init-py | runtime/controlled_learning/__init__.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-controlled-learning-pipeline-py | runtime/controlled_learning/pipeline.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-controlled-learning-report-py | runtime/controlled_learning/report.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-controlled-learning-schema-py | runtime/controlled_learning/schema.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-escalation-init-py | runtime/escalation/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-escalation-escalation-gate-py | runtime/escalation/escalation_gate.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-evaluation-init-py | runtime/evaluation/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-evaluation-benchmark-py | runtime/evaluation/benchmark.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-evaluation-evaluators-py | runtime/evaluation/evaluators.py | runtime_support | support | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-evaluation-metrics-py | runtime/evaluation/metrics.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-evaluation-report-py | runtime/evaluation/report.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-evaluation-schema-py | runtime/evaluation/schema.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-fallbacks-init-py | runtime/fallbacks/__init__.py | runtime_support | support | python_governance_runtime | None | ['Kafka', 'LLM provider'] |
| runtime-memory-init-py | runtime/memory/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-orchestration-init-py | runtime/orchestration/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-orchestration-doctor-py | runtime/orchestration/doctor.py | runtime_support | support | python_governance_runtime | None | ['Kafka', 'LLM provider', 'PostgreSQL'] |
| runtime-orchestration-modes-py | runtime/orchestration/modes.py | runtime_support | support | python_governance_runtime | None | ['Kafka', 'LLM provider'] |
| runtime-orchestration-run-best-effort-py | runtime/orchestration/run_best_effort.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-orchestration-tests-init-py | runtime/orchestration/tests/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-orchestration-tests-test-modes-py | runtime/orchestration/tests/test_modes.py | runtime_support | support | python_governance_runtime | None | ['Kafka', 'LLM provider', 'PostgreSQL'] |
| runtime-orchestration-tests-test-run-best-effort-py | runtime/orchestration/tests/test_run_best_effort.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-self-improvement-init-py | runtime/self_improvement/__init__.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-self-improvement-experiments-py | runtime/self_improvement/experiments.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-self-improvement-report-py | runtime/self_improvement/report.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-self-improvement-schema-py | runtime/self_improvement/schema.py | authoritative_runtime | authoritative | python_governance_runtime | None | [] |
| runtime-tests-init-py | runtime/tests/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-tests-conftest-py | runtime/tests/conftest.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-tests-test-agent-protocol-conformance-py | runtime/tests/test_agent_protocol_conformance.py | runtime_support | support | python_governance_runtime | None | [] |
| runtime-tests-test-base-agent-v2-py | runtime/tests/test_base_agent_v2.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-tests-test-bounded-self-improvement-py | runtime/tests/test_bounded_self_improvement.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-tests-test-config-driven-tiers-py | runtime/tests/test_config_driven_tiers.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-tests-test-controlled-learning-py | runtime/tests/test_controlled_learning.py | authoritative_runtime | authoritative | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-tests-test-evaluation-calibration-py | runtime/tests/test_evaluation_calibration.py | runtime_support | support | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-tests-test-local-model-setup-py | runtime/tests/test_local_model_setup.py | runtime_support | support | python_governance_runtime | None | ['LLM provider'] |
| runtime-tests-test-runtime-durable-governance-stores-py | runtime/tests/test_runtime_durable_governance_stores.py | runtime_support | support | python_governance_runtime | None | ['PostgreSQL'] |
| runtime-tests-test-spend-guardrail-ledger-py | runtime/tests/test_spend_guardrail_ledger.py | runtime_support | support | python_governance_runtime | None | ['LLM provider', 'PostgreSQL'] |
| runtime-tool-registry-init-py | runtime/tool_registry/__init__.py | runtime_support | support | python_governance_runtime | None | [] |
| synthesis-init-py | synthesis/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-principle-library-init-py | synthesis/principle_library/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-principle-library-principle-library-py | synthesis/principle_library/principle_library.py | experimental | experimental | python_research_module | None | [] |
| synthesis-source-library-init-py | synthesis/source_library/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-synthesis-agent-init-py | synthesis/synthesis_agent/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-synthesis-agent-synthesis-agent-py | synthesis/synthesis_agent/synthesis_agent.py | experimental | experimental | python_research_module | None | [] |
| synthesis-tests-init-py | synthesis/tests/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-tests-test-synthesis-py | synthesis/tests/test_synthesis.py | experimental | experimental | python_research_module | None | [] |
| synthesis-theory-engine-init-py | synthesis/theory_engine/__init__.py | experimental | experimental | python_research_module | None | [] |
| synthesis-theory-engine-theory-engine-py | synthesis/theory_engine/theory_engine.py | experimental | experimental | python_research_module | None | [] |
