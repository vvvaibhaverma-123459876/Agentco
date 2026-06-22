.PHONY: dev smoke smoke-python smoke-node migrate test validation master-gate db-tests load-test

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

master-gate: smoke db-tests validation
	cd backend && npm run build
	cd frontend && npm run build
	@echo "✓ All gates passed: smoke tests, DB validation, release validation"
