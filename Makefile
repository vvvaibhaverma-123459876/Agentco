.PHONY: dev smoke smoke-python smoke-node migrate test validation master-gate

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

test: smoke

validation:
	python3 scripts/run_real_world_validation.py

master-gate: smoke validation
	cd backend && npm run build
	cd frontend && npm run build
