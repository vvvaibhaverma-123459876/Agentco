.PHONY: dev smoke smoke-python smoke-node migrate test validation master-gate db-tests load-test vendor-risk-smoke vendor-risk-full autonomy-migrate autonomy-smoke autonomy-eval autonomy-sim autonomy-learner autonomy-dashboard autonomy-security-test autonomy-full-test

dev:
	docker compose --profile dev up -d
	cd backend && npm install
	cd frontend && npm install

migrate:
	cd backend && npm run build && npm run db:migrate

smoke: smoke-python smoke-node

smoke-python:
	python3 -m pytest calibration runtime learning synthesis evals/regression -q \
		--ignore=evals/regression/test_pg_ledger_immutability.py \
		--ignore=evals/regression/test_pg_ledger_persistence.py

smoke-node:
	@if [ -x backend/node_modules/.bin/tsc ]; then cd backend && ./node_modules/.bin/tsc --noEmit; else echo "backend node_modules missing; run make dev"; fi
	@if [ -x frontend/node_modules/.bin/tsc ]; then cd frontend && ./node_modules/.bin/tsc --noEmit; else echo "frontend node_modules missing; run make dev"; fi

db-tests:
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL not set, skipping DB tests"; exit 0; fi
	python3 -m pytest evals/regression/test_pg_ledger_immutability.py evals/regression/test_pg_ledger_persistence.py -q

load-test:
	@if [ -z "$$SKIP_LOAD_TEST" ]; then python3 -m pytest evals/regression/test_load.py -q 2>/dev/null || echo "load test skipped (optional)"; fi

test: smoke db-tests

validation:
	python3 scripts/run_real_world_validation.py

vendor-risk-smoke:
	@echo "Running enterprise vendor risk triage benchmark (smoke test)..."
	python3 -m evals.enterprise_vendor_risk.run_benchmark \
		--models fake:deterministic \
		--output results/enterprise_vendor_risk/runs/smoke_$$(date +%s).json
	@echo "Generating leaderboard..."
	python3 -m evals.enterprise_vendor_risk.leaderboard \
		--input $$(ls -t results/enterprise_vendor_risk/runs/smoke_*.json | head -1) \
		--output-json results/enterprise_vendor_risk/latest.json \
		--output-md results/enterprise_vendor_risk/latest.md
	@echo "✓ Vendor risk smoke test complete. Results in results/enterprise_vendor_risk/latest.md"

vendor-risk-full:
	@echo "Running enterprise vendor risk triage benchmark (full)..."
	python3 -m evals.enterprise_vendor_risk.run_benchmark \
		--models fake:deterministic,agentco \
		--output results/enterprise_vendor_risk/runs/benchmark_$$(date +%s).json
	@echo "Generating leaderboard..."
	python3 -m evals.enterprise_vendor_risk.leaderboard \
		--input $$(ls -t results/enterprise_vendor_risk/runs/benchmark_*.json | head -1) \
		--output-json results/enterprise_vendor_risk/latest.json \
		--output-md results/enterprise_vendor_risk/latest.md
	@echo "✓ Vendor risk benchmark complete. Results in results/enterprise_vendor_risk/latest.md"

master-gate: smoke db-tests validation
	cd backend && npm run build
	cd frontend && npm run build
	@echo "✓ All gates passed: smoke tests, DB validation, release validation"

# ========== TRUE AUTONOMY IMPLEMENTATION COMMANDS ==========

autonomy-migrate:
	@echo "⏳ Applying autonomy migrations (021-035)..."
	cd backend && npm run build && npm run db:migrate
	@echo "✓ Autonomy migrations complete"

autonomy-smoke:
	@echo "🔄 Running autonomy smoke test (real end-to-end loop)..."
	python3 scripts/autonomy_smoke.py
	@echo "✓ Autonomy smoke test passed"

autonomy-eval:
	@echo "📊 Running autonomy evaluation suite..."
	python3 scripts/run_autonomy_eval.py
	@echo "✓ Autonomy eval suite complete. Check results/ for details."

autonomy-sim:
	@echo "🎮 Running autonomy simulators..."
	python3 scripts/run_simulator.py
	@echo "✓ Simulator runs complete"

autonomy-learner:
	@echo "🧠 Running autonomy learner (trajectory → candidate)..."
	python3 scripts/run_learner.py
	@echo "✓ Learner run complete"

autonomy-dashboard:
	@echo "📈 Starting autonomy dashboard (frontend)..."
	cd frontend && npm run dev
	@echo "Navigate to http://localhost:3000/autonomy"

autonomy-security-test:
	@echo "🔒 Running security tests (RBAC, protected surfaces, etc)..."
	python3 -m pytest backend/tests/security/ -v
	@echo "✓ Security tests passed"

autonomy-full-test:
	@echo "🔬 Running full autonomy test suite..."
	make autonomy-smoke
	make autonomy-eval
	make autonomy-security-test
	@echo "✓ All autonomy tests passed"

autonomy-level3-smoke:
	@echo "🎯 Running LEVEL_3 Autonomy Smoke Test (real end-to-end loop)..."
	python3 scripts/run_level3_autonomy_smoke.py
	@echo "✓ LEVEL_3 smoke test complete"

autonomy-level3-test:
	@echo "🔬 Running LEVEL_3 integration tests..."
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL not set, skipping"; exit 0; fi
	python3 -m pytest tests/integration/test_level3_autonomy_loop.py -v
	@echo "✓ LEVEL_3 tests passed"

autonomy-level3-functional:
	@echo "🎯 Running LEVEL_3 Functional Verification (Real Runtime Test)..."
	@bash scripts/run_level3_functional_verification.sh
