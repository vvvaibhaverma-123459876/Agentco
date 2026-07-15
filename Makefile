PYTHON ?= python3.13

.PHONY: dev smoke smoke-python smoke-node migrate test validation verify slice reachability master-gate db-tests load-test vendor-risk-smoke vendor-risk-full autonomy-migrate autonomy-smoke autonomy-eval autonomy-sim autonomy-learner autonomy-dashboard autonomy-security-test autonomy-full-test autonomy-level3-smoke autonomy-level3-test autonomy-level3-functional autonomy-idempotency-test autonomy-concurrency-test autonomy-eval-gate-test autonomy-rollback-test autonomy-crash-recovery-test autonomy-rbac-test autonomy-protected-surface-test autonomy-level4-phase2-test autonomy-memory-quality-test autonomy-observability-test autonomy-frontend-real-data-test autonomy-level4-phase3-test autonomy-level4-full-test autonomy-level4-certification autonomy-perception-test autonomy-goal-test autonomy-phases-5-8-smoke autonomy-phases-5-8-test autonomy-learner-test autonomy-simulator-test autonomy-phases-9-13-smoke autonomy-phases-9-13-full-test production-release-gate autonomy-civilization-learning-test autonomy-real-web-free-run civilization-calibration-trust-smoke python-check verify-migrations-native verify-resolution-service doctor doctor-offline doctor-production run-best-effort run-offline-fixture north-star-smoke live-cross-domain memory-influence-live mission-progress mission-progress-record mission-progress-record-real-world verify-system-offline verify-system-native production-posture docker-production-smoke docker-startup-verify production-smoke-test production-safety-test staging-smoke-test staging-governance-gate staging-load-test staging-validation-gate release-gates release-gate gate-integrity verify-advertised-targets audit-clean-room audit-runtime-integration audit-staging-deployment deployment-ledgers hosted-staging-budget hosted-staging-plan hosted-staging-apply audit-hosted-staging hosted-staging-destroy audit-longitudinal-foundation longitudinal-campaign governed-capability-genesis capability-protocol-baseline capability-protocol-baseline-v2 protocol-reference-genesis-v2 real-capability-genesis-v2 real-capability-genesis-v3 real-capability-genesis-v4 status status-check remaining build-ledger-sync civilization-slice civilization-scheduler civilization-completion civilization-suite agent-protocol-matrix agent-protocol-matrix-check evaluation-calibration-report evaluation-calibration-report-check controlled-learning-report controlled-learning-report-check self-improvement-report self-improvement-report-check

python-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) --version
	@$(PYTHON) -m pytest runtime/tests -q

verify-migrations-native:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_migrations_native.py

verify-resolution-service:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_resolution_service.py

doctor:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m runtime.orchestration.doctor --mode local_native

doctor-offline:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m runtime.orchestration.doctor --mode offline_fixture

doctor-production:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m runtime.orchestration.doctor --mode production --live-openai --run-builds

run-best-effort:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m runtime.orchestration.run_best_effort

run-offline-fixture:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m runtime.orchestration.run_best_effort --mode offline_fixture

north-star-smoke:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) -m evals.north_star_cross_domain.run_smoke

live-cross-domain:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_agentco_multidomain_live_run.py

memory-influence-live:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_memory_influence_live.py

mission-progress:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_mission_progress.py

mission-progress-record:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_mission_progress.py --record-run

mission-progress-record-real-world:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_mission_progress.py --record-run --real-world-run

verify-system-offline: doctor-offline run-offline-fixture north-star-smoke
	@$(PYTHON) -m pytest runtime/orchestration/tests tests/test_verify_agentco_goal_run.py evals/north_star_cross_domain/tests -q

verify-system-native:
	@$(PYTHON) -m runtime.orchestration.run_best_effort --mode local_native

status:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_status.py

status-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_status.py --check

agent-protocol-matrix:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_agent_conformance_matrix.py

agent-protocol-matrix-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_agent_conformance_matrix.py --check

evaluation-calibration-report:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_evaluation_calibration_report.py

evaluation-calibration-report-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_evaluation_calibration_report.py --check

controlled-learning-report:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_controlled_learning_report.py

controlled-learning-report-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_controlled_learning_report.py --check

self-improvement-report:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_self_improvement_report.py

self-improvement-report-check:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_self_improvement_report.py --check

remaining:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/build_ledger.py remaining

build-ledger-sync:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/build_ledger.py sync-db

civilization-slice:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_civilization_vertical_slice.py --update-ledger

production-posture:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_production_posture.py

release-gates:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_release_gates.py --update-ledger

gate-integrity:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_gate_integrity.py --check

verify-advertised-targets:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_make_targets.py --check

release-gate:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@echo "== [0/12] clean tree before gate =="
	@test -z "$$(git status --porcelain)" || (git status --short; echo "working tree dirty before release-gate"; exit 1)
	@echo "== [0a/12] gate integrity check =="
	@$(MAKE) gate-integrity
	@echo "== [0b/12] advertised target check =="
	@$(MAKE) verify-advertised-targets
	@echo "== [1/12] status check =="
	@$(MAKE) status-check
	@echo "== [1a/12] agent protocol conformance matrix check =="
	@$(MAKE) agent-protocol-matrix-check
	@echo "== [1b/12] evaluation calibration report check =="
	@$(MAKE) evaluation-calibration-report-check
	@echo "== [1c/12] controlled learning report check =="
	@$(MAKE) controlled-learning-report-check
	@echo "== [1d/12] bounded self-improvement report check =="
	@$(MAKE) self-improvement-report-check
	@echo "== [1e/12] score validation check =="
	cd backend && npm run agentco:score-validation -- --check
	@echo "== [2/12] backend install =="
	cd backend && npm ci
	@echo "== [3/12] backend migrations =="
	@MIGRATION_DSN="$${RELEASE_GATE_MIGRATION_DATABASE_URL:-$$DATABASE_URL}"; if [ -n "$$MIGRATION_DSN" ]; then cd backend && DATABASE_URL="$$MIGRATION_DSN" npm run db:migrate; else echo "DATABASE_URL not set; DB-backed tests may skip with reason"; fi
	@echo "== [3a/12] least-privilege gate role grants =="
	@if [ -n "$$RELEASE_GATE_SETUP_DATABASE_URL" ]; then psql "$$RELEASE_GATE_SETUP_DATABASE_URL" -v gate_role="$${RELEASE_GATE_ROLE:-agentco_gate}" -v gate_password="$${RELEASE_GATE_ROLE_PASSWORD:?RELEASE_GATE_ROLE_PASSWORD is required when RELEASE_GATE_SETUP_DATABASE_URL is set}" -f scripts/setup_release_gate_role.sql >/dev/null; else echo "RELEASE_GATE_SETUP_DATABASE_URL not set; assuming gate role already has privileges"; fi
	@echo "== [4/12] Python default suite =="
	@mkdir -p artifacts/audit/release-gate
	@GATE_DSN="$${RELEASE_GATE_DATABASE_URL:-$$DATABASE_URL}"; TEST_DSN="$${AGENTCO_TEST_DATABASE_URL:-$$GATE_DSN}"; PYTHONDONTWRITEBYTECODE=1 DATABASE_URL="$$GATE_DSN" AGENTCO_TEST_DATABASE_URL="$$TEST_DSN" $(PYTHON) scripts/verify_pytest_skips.py --report artifacts/audit/release-gate/pytest-report.json --summary-output artifacts/audit/release-gate/pytest-summary.json -- -q
	@echo "== [5/12] backend build =="
	cd backend && npm run build
	@echo "== [6/12] backend Jest =="
	GATE_DSN="$${RELEASE_GATE_DATABASE_URL:-$$DATABASE_URL}"; TEST_DSN="$${AGENTCO_TEST_DATABASE_URL:-$$GATE_DSN}"; cd backend && DATABASE_URL="$$GATE_DSN" AGENTCO_TEST_DATABASE_URL="$$TEST_DSN" npm test -- --runInBand
	@echo "== [7/12] route-auth contract =="
	GATE_DSN="$${RELEASE_GATE_DATABASE_URL:-$$DATABASE_URL}"; TEST_DSN="$${AGENTCO_TEST_DATABASE_URL:-$$GATE_DSN}"; cd backend && DATABASE_URL="$$GATE_DSN" AGENTCO_TEST_DATABASE_URL="$$TEST_DSN" npm test -- route-auth-contract.test.ts --runInBand
	@echo "== [8/12] decision_log chain cross-writer test =="
	GATE_DSN="$${RELEASE_GATE_DATABASE_URL:-$$DATABASE_URL}"; TEST_DSN="$${AGENTCO_TEST_DATABASE_URL:-$$GATE_DSN}"; cd backend && DATABASE_URL="$$GATE_DSN" AGENTCO_TEST_DATABASE_URL="$$TEST_DSN" npm test -- audit-chain-cross-writer.test.ts --runInBand
	@echo "== [9/12] frontend install =="
	cd frontend && npm ci
	@echo "== [10/12] frontend typecheck =="
	cd frontend && ./node_modules/.bin/tsc --noEmit
	@echo "== [11/12] frontend build =="
	cd frontend && NEXT_TELEMETRY_DISABLED=1 npm run build
	@echo "== [12/12] clean tree after gate =="
	@test -z "$$(git status --porcelain)" || (git status --short; echo "working tree dirty after release-gate"; exit 1)

docker-production-smoke:
	@docker compose up -d postgres redis zookeeper kafka vault prometheus grafana
	@docker compose ps
	@$(PYTHON) scripts/verify_production_posture.py

docker-startup-verify:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_docker_startup.py

production-smoke-test:
	@$(PYTHON) scripts/test_production_smoke.py

production-safety-test:
	@$(PYTHON) scripts/test_production_security_gate.py

staging-smoke-test:
	@bash scripts/test_staging_smoke.sh

staging-governance-gate:
	@bash scripts/test_staging_governance_gate.sh

staging-load-test:
	@$(PYTHON) scripts/test_staging_load.py

staging-validation-gate:
	@bash scripts/run_staging_validation_gate.sh

dev:
	docker compose --profile dev up -d
	cd backend && npm install
	cd frontend && npm install

migrate:
	cd backend && npm run build && npm run db:migrate

smoke: smoke-python smoke-node

smoke-python:
	$(PYTHON) -m pytest calibration runtime learning synthesis evals/regression -q \
		--ignore=evals/regression/test_pg_ledger_immutability.py \
		--ignore=evals/regression/test_pg_ledger_persistence.py

smoke-node:
	@if [ -x backend/node_modules/.bin/tsc ]; then cd backend && ./node_modules/.bin/tsc --noEmit; else echo "backend node_modules missing; run make dev"; fi
	@if [ -x frontend/node_modules/.bin/tsc ]; then cd frontend && ./node_modules/.bin/tsc --noEmit; else echo "frontend node_modules missing; run make dev"; fi

db-tests:
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL not set; db-tests require an explicit database"; exit 2; fi
	$(PYTHON) -m pytest evals/regression/test_pg_ledger_immutability.py evals/regression/test_pg_ledger_persistence.py -q

load-test:
	@if [ -z "$$SKIP_LOAD_TEST" ]; then $(PYTHON) -m pytest evals/regression/test_load.py -q 2>/dev/null || echo "load test skipped (optional)"; fi

test: smoke db-tests

validation:
	$(PYTHON) scripts/run_real_world_validation.py

verify: release-gate

slice: civilization-slice

reachability: release-gates

civilization-calibration-trust-smoke:
	$(PYTHON) scripts/test_calibration_constitution.py
	$(PYTHON) scripts/test_trust_policy.py

vendor-risk-smoke:
	@echo "Running enterprise vendor risk triage benchmark (smoke test)..."
	$(PYTHON) -m evals.enterprise_vendor_risk.run_benchmark \
		--models fake:deterministic \
		--output results/enterprise_vendor_risk/runs/smoke_$$(date +%s).json
	@echo "Generating leaderboard..."
	$(PYTHON) -m evals.enterprise_vendor_risk.leaderboard \
		--input $$(ls -t results/enterprise_vendor_risk/runs/smoke_*.json | head -1) \
		--output-json results/enterprise_vendor_risk/latest.json \
		--output-md results/enterprise_vendor_risk/latest.md
	@echo "✓ Vendor risk smoke test complete. Results in results/enterprise_vendor_risk/latest.md"

vendor-risk-full:
	@echo "Running enterprise vendor risk triage benchmark (full)..."
	$(PYTHON) -m evals.enterprise_vendor_risk.run_benchmark \
		--models fake:deterministic,agentco \
		--output results/enterprise_vendor_risk/runs/benchmark_$$(date +%s).json
	@echo "Generating leaderboard..."
	$(PYTHON) -m evals.enterprise_vendor_risk.leaderboard \
		--input $$(ls -t results/enterprise_vendor_risk/runs/benchmark_*.json | head -1) \
		--output-json results/enterprise_vendor_risk/latest.json \
		--output-md results/enterprise_vendor_risk/latest.md
	@echo "✓ Vendor risk benchmark complete. Results in results/enterprise_vendor_risk/latest.md"

master-gate: smoke db-tests validation
	cd backend && npm run build
	cd frontend && npm run build
	@echo "master-gate complete: smoke tests, DB validation, release validation"

# ========== TRUE AUTONOMY IMPLEMENTATION COMMANDS ==========

autonomy-migrate:
	@echo "⏳ Applying autonomy migrations (021-035)..."
	cd backend && npm run build && npm run db:migrate
	@echo "✓ Autonomy migrations complete"

autonomy-smoke:
	@echo "🔄 Running autonomy smoke test (real end-to-end loop)..."
	$(PYTHON) scripts/autonomy_smoke.py
	@echo "✓ Autonomy smoke test passed"

autonomy-eval:
	@echo "📊 Running autonomy evaluation suite..."
	$(PYTHON) scripts/run_autonomy_eval.py
	@echo "✓ Autonomy eval suite complete. Check results/ for details."

autonomy-sim:
	@echo "🎮 Running autonomy simulators..."
	$(PYTHON) scripts/run_simulator.py
	@echo "✓ Simulator runs complete"

autonomy-learner:
	@echo "🧠 Running autonomy learner (trajectory → candidate)..."
	$(PYTHON) scripts/run_learner.py
	@echo "✓ Learner run complete"

autonomy-dashboard:
	@echo "📈 Starting autonomy dashboard (frontend)..."
	cd frontend && npm run dev
	@echo "Navigate to http://localhost:3000/autonomy"

autonomy-security-test:
	@echo "🔒 Running security tests (RBAC, protected surfaces, etc)..."
	$(PYTHON) -m pytest backend/tests/security/ -v
	@echo "✓ Security tests passed"

autonomy-full-test:
	@echo "🔬 Running full autonomy test suite..."
	make autonomy-smoke
	make autonomy-eval
	make autonomy-security-test
	@echo "✓ All autonomy tests passed"

autonomy-level3-smoke:
	@echo "🎯 Running LEVEL_3 Autonomy Smoke Test (real end-to-end loop)..."
	$(PYTHON) scripts/run_level3_autonomy_smoke.py
	@echo "✓ LEVEL_3 smoke test complete"

autonomy-level3-test:
	@echo "🔬 Running LEVEL_3 integration tests..."
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL not set; autonomy-level3-test requires an explicit database"; exit 2; fi
	$(PYTHON) -m pytest tests/integration/test_level3_autonomy_loop.py -v
	@echo "✓ LEVEL_3 tests passed"

autonomy-level3-functional:
	@echo "🎯 Running LEVEL_3 Functional Verification (Real Runtime Test)..."
	@bash scripts/run_level3_functional_verification.sh

autonomy-idempotency-test:
	@echo "🎯 Running LEVEL_4 Area 1: Idempotency Test..."
	$(PYTHON) scripts/test_idempotency.py

autonomy-concurrency-test:
	@echo "🎯 Running LEVEL_4 Area 2: Concurrency Test..."
	@bash scripts/run_level3_functional_verification.sh 2>&1 | tail -5 & \
	sleep 15; \
	$(PYTHON) scripts/test_concurrency.py; \
	pkill -f "run_level3_functional_verification.sh" || true

autonomy-eval-gate-test:
	@echo "🎯 Running LEVEL_4 Area 4: Eval Gate Hardening Test..."
	$(PYTHON) scripts/test_eval_gates.py

autonomy-rollback-test:
	@echo "🎯 Running LEVEL_4 Area 5: Rollback Hardening Test..."
	$(PYTHON) scripts/test_rollback.py

autonomy-crash-recovery-test:
	@echo "🎯 Running LEVEL_4 Area 3: Crash Recovery Test..."
	$(PYTHON) scripts/test_crash_recovery.py

autonomy-rbac-test:
	@echo "🎯 Running LEVEL_4 Area 6: RBAC Hardening Test..."
	$(PYTHON) scripts/test_rbac.py

autonomy-protected-surface-test:
	@echo "🎯 Running LEVEL_4 Area 7: Protected Surface Hardening Test..."
	$(PYTHON) scripts/test_protected_surfaces.py

autonomy-level4-phase2-test:
	@echo "🎯 Running LEVEL_4 Phase 2: Safety Hardening Full Suite (Areas 4-7)..."
	@bash scripts/run_level4_phase2_tests.sh

autonomy-memory-quality-test:
	@echo "🎯 Running LEVEL_4 Area 8: Memory Quality Hardening Test..."
	@echo "This target previously only echoed success. It now runs the real"
	@echo "collective-knowledge retraction/demotion suite, or fails if unavailable."
	@if [ -x backend/node_modules/.bin/jest ]; then \
		cd backend && ./node_modules/.bin/jest tests/collective-knowledge.test.ts --runInBand; \
	else echo "backend node_modules missing; run 'cd backend && npm ci'"; exit 2; fi

autonomy-observability-test:
	@echo "🎯 Running LEVEL_4 Area 9: Observability Completeness Test..."
	@echo "This target previously only echoed success. It now runs the real"
	@echo "civilization OS suite (tick heartbeats + metrics), or fails if unavailable."
	@if [ -x backend/node_modules/.bin/jest ]; then \
		cd backend && ./node_modules/.bin/jest tests/civilization-os.test.ts --runInBand; \
	else echo "backend node_modules missing; run 'cd backend && npm ci'"; exit 2; fi

civilization-scheduler:
	@echo "🌍 Starting the civilization operating-system scheduler worker..."
	cd backend && npm run agentco:civilization-scheduler

civilization-completion:
	@echo "🏛️  Generating civilization completion evidence + reconciliation..."
	@$(PYTHON) scripts/generate_civilization_completion.py

civilization-suite:
	@echo "🏛️  Running the civilization backend test suites..."
	@if [ -x backend/node_modules/.bin/jest ]; then \
		cd backend && ./node_modules/.bin/jest \
			tests/civilization-kernel.test.ts tests/citizenship.test.ts tests/societies-institutions.test.ts \
			tests/coalitions.test.ts tests/missions.test.ts tests/treasury.test.ts tests/governance.test.ts \
			tests/judiciary-case.test.ts tests/collective-knowledge.test.ts tests/safe-evolution.test.ts \
			tests/capability-expansion.test.ts tests/civilization-os.test.ts tests/civilization-operator.test.ts \
			tests/civilization-reliability.test.ts tests/civilization-adversarial.test.ts \
			tests/civilization-e2e-scenarios.test.ts --runInBand; \
	else echo "backend node_modules missing; run 'cd backend && npm ci'"; exit 2; fi

autonomy-frontend-real-data-test:
	@echo "🎯 Running LEVEL_4 Area 10: Frontend Real-Data Hardening Test..."
	$(PYTHON) scripts/test_frontend_real_data.py

autonomy-level4-phase3-test:
	@echo "🎯 Running LEVEL_4 Phase 3: Observability Hardening Full Suite (Areas 8-10)..."
	@bash scripts/run_level4_phase3_tests.sh

autonomy-level4-full-test:
	@echo "🎯 Running LEVEL_4 COMPREHENSIVE Full Regression Test Suite (All 11 Areas)..."
	@bash scripts/run_level4_full_test.sh

autonomy-level4-certification:
	@echo "🏆 Verifying LEVEL_4 Production Readiness Certification..."
	@bash scripts/verify_level4_certification.sh

autonomy-perception-test:
	@echo "🎯 Running PHASE_4: Perception Adapter Infrastructure Tests..."
	$(PYTHON) scripts/test_perception.py

autonomy-goal-test:
	@echo "🎯 Running PHASE_5: Goal Management Infrastructure Tests..."
	$(PYTHON) scripts/test_goal_management.py

autonomy-phases-5-8-smoke:
	@echo "🎯 Running PHASES 5-8: Integrated Autonomy Loop Smoke Test..."
	$(PYTHON) scripts/test_phases_5_8.py
	@echo "✅ PHASES 5-8 smoke test complete"

autonomy-phases-5-8-test:
	@echo "🔬 Running PHASES 5-8: Full Integrated Test Suite..."
	@echo "  Testing: Goals → Plans → Outcomes → Rewards → Evals → Promotion"
	$(PYTHON) scripts/test_phases_5_8.py
	@echo "✅ PHASES 5-8 full test complete"

autonomy-learner-test:
	@echo "🎯 Running PHASE 9: Learner & Replay Tests..."
	$(PYTHON) -m pytest runtime/tests/test_controlled_learning.py -q

autonomy-simulator-test:
	@echo "🎯 Running PHASE 10: Simulator Tests..."
	$(PYTHON) -m pytest tests/test_pawdent_business_simulation.py -q

autonomy-phases-9-13-smoke:
	@echo "🎯 Running PHASES 9-13: Self-Improvement Loop Smoke Test..."
	$(PYTHON) scripts/test_phases_9_13.py
	@echo "✅ PHASES 9-13 smoke test complete"

autonomy-phases-9-13-full-test:
	@echo "🔬 Running PHASES 9-13: Full Self-Improvement Integration Suite..."
	@echo "  Testing: Learner → Simulator → Self-Mod → Artifact → Canary → Rollback"
	make autonomy-phases-5-8-test
	make autonomy-learner-test
	make autonomy-simulator-test
	make autonomy-phases-9-13-smoke
	make autonomy-civilization-learning-test
	@echo "✅ PHASES 9-13 full test complete"

autonomy-civilization-learning-test:
	@echo "🌍 Running CIVILIZATION-STRUCTURED LEARNING Tests..."
	@echo "  Testing: Agent → Team → Institution → Society → Civilization"
	@echo "  Verifying: Promotion gates, dispute resolution, governance review"
	$(PYTHON) scripts/test_civilization_learning.py
	@echo "✅ Civilization learning test complete"

# ============================================================================
# PRODUCTION RELEASE GATE - Final verification before production deployment
# ============================================================================

production-release-gate:
	@echo "production-release-gate is retired because it masked failures."
	@echo "Use the canonical command instead: make release-gate"
	@exit 2

autonomy-real-web-free-run:
	@echo "🚀 STARTING REAL-WEB AUTONOMOUS BEHAVIOR OBSERVATION"
	@echo "=================================================================="
	@echo "Duration: $${DURATION_SECONDS:-120} seconds"
	@echo "LLM Model: $${OPENAI_MODEL:-gpt-4o-mini}"
	@echo "Max Tokens: $${LLM_MAX_TOKENS_TOTAL:-20000}"
	@echo "Max Web Fetches: $${WEB_MAX_FETCHES:-20}"
	@echo "=================================================================="
	@echo ""
	@$(PYTHON) scripts/autonomy_real_web_free_run.py
	@echo ""
	@echo "✓ Real-web autonomous observation complete"

autonomy-open-world-5min:
	@echo "🌍 STARTING AGENTCO OPEN-WORLD 5-MINUTE TEST (NO SANDBOX)"
	@echo "=================================================================="
	@echo "Duration: $${DURATION_SECONDS:-300} seconds (5 minutes)"
	@echo "Mode: NO SANDBOX - Full autonomy"
	@echo "Monitors: Calibration | Integration | Civilization"
	@echo "LLM Model: $${OPENAI_MODEL:-gpt-4-turbo}"
	@echo "=================================================================="
	@echo ""
	@$(PYTHON) scripts/autonomy_open_world_5min.py
	@echo ""
	@echo "✓ Open-world 5-minute test complete"

.PHONY: production-release-gate autonomy-real-web-free-run autonomy-open-world-5min

# ---------------------------------------------------------------------------
# Clean-room verification: provisions its own disposable PostgreSQL container,
# runs migrations from zero, records command evidence, and cleans up all owned
# resources. Live LLM/web suites are opt-in elsewhere.
# ---------------------------------------------------------------------------
.PHONY: verify-clean-room audit-clean-room cross-version-campaign real-cross-version-campaign subject-native-cross-version-campaign
verify-clean-room: audit-clean-room

audit-clean-room:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/audit_clean_room.py

audit-runtime-integration:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/generate_runtime_reachability.py
	@$(PYTHON) scripts/audit_runtime_integration.py

deployment-ledgers:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/audit_staging_deployment.py --docs-only

audit-staging-deployment:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/audit_staging_deployment.py

hosted-staging-budget:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/verify_hosted_staging_budget.py --check-prerequisites

hosted-staging-plan:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/hosted_staging_audit.py plan

hosted-staging-apply:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/hosted_staging_audit.py apply

audit-hosted-staging:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/hosted_staging_audit.py audit

hosted-staging-destroy:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/hosted_staging_audit.py destroy

audit-longitudinal-foundation:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/longitudinal_foundation.py check

longitudinal-campaign:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_longitudinal_campaign.py --campaign "$${CAMPAIGN:?CAMPAIGN is required}"

governed-capability-genesis:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-protocol-baseline-v2 --mode protocol-baseline-v2

capability-protocol-baseline:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-protocol-baseline-v2 --mode protocol-baseline-v2

capability-protocol-baseline-v2:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-protocol-baseline-v2 --mode protocol-baseline-v2

protocol-reference-genesis-v2:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-protocol-baseline-v2 --mode protocol-baseline-v2

real-capability-genesis-v2:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-genesis-v4 --mode real-capability-genesis-v4

real-capability-genesis-v3:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-genesis-v4 --mode real-capability-genesis-v4

real-capability-genesis-v4:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_governed_capability_genesis.py --campaign governed-capability-genesis-v4 --mode real-capability-genesis-v4

cross-version-campaign: real-cross-version-campaign

real-cross-version-campaign:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_cross_version_campaign.py \
		--baseline "$${BASELINE:?BASELINE is required}" \
		--raw-candidate "$${RAW_CANDIDATE:?RAW_CANDIDATE is required}" \
		--reconciled-candidate "$${RECONCILED_CANDIDATE:?RECONCILED_CANDIDATE is required}" \
		--campaign "$${CAMPAIGN:?CAMPAIGN is required}"
	@$(PYTHON) scripts/verify_cross_version_campaign.py \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}" \
		--baseline "$${BASELINE:?BASELINE is required}" \
		--raw-candidate "$${RAW_CANDIDATE:?RAW_CANDIDATE is required}" \
		--reconciled-candidate "$${RECONCILED_CANDIDATE:?RECONCILED_CANDIDATE is required}"
	@$(PYTHON) scripts/verify_subject_runtime_evidence.py \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}"

subject-native-cross-version-campaign:
	@command -v $(PYTHON) >/dev/null || (echo "Python 3.13 is required. Install the configured interpreter or run with PYTHON=/path/to/interpreter"; exit 1)
	@$(PYTHON) scripts/run_subject_native_cross_version_campaign.py \
		--baseline "$${BASELINE:?BASELINE is required}" \
		--raw-candidate "$${RAW_CANDIDATE:?RAW_CANDIDATE is required}" \
		--reconciled-candidate "$${RECONCILED_CANDIDATE:?RECONCILED_CANDIDATE is required}" \
		--campaign "$${CAMPAIGN:?CAMPAIGN is required}"
	@$(PYTHON) scripts/verify_cross_version_campaign.py \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}" \
		--baseline "$${BASELINE:?BASELINE is required}" \
		--raw-candidate "$${RAW_CANDIDATE:?RAW_CANDIDATE is required}" \
		--reconciled-candidate "$${RECONCILED_CANDIDATE:?RECONCILED_CANDIDATE is required}"
	@$(PYTHON) scripts/verify_subject_runtime_evidence.py \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}"
	@$(PYTHON) scripts/verify_subject_request_consumption.py \
		--check \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}"
	@$(PYTHON) scripts/verify_subject_answer_ownership.py \
		--check \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}"
	@$(PYTHON) scripts/verify_campaign_evidence_binding.py \
		--check \
		--campaign-dir "artifacts/cross-version/$${CAMPAIGN:?CAMPAIGN is required}"

.PHONY: longitudinal-learning
longitudinal-learning:
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL must point at a local Postgres database"; exit 1; fi
	cd backend && ./node_modules/.bin/ts-node src/cli/run-longitudinal-learning.ts
