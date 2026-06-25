.PHONY: doctor dev dev-minimal dev-full migrate test verify verify-core verify-backend verify-frontend verify-calibration verify-resolution verify-reserve verify-dispatch verify-security verify-epistemic verify-jurisdiction verify-civilization verify-demo verify-acceptance smoke smoke-real demo business-demo business-sim clean

PYTHON ?= python3
DATABASE_URL ?= postgresql://agentco:password@localhost:5432/agentco
BUSINESS_SIM_ARGS ?=

doctor:
	$(PYTHON) scripts/doctor.py

dev: dev-minimal

dev-minimal:
	docker compose --profile minimal up -d
	$(MAKE) migrate

dev-full:
	docker compose --profile full up -d
	$(MAKE) migrate

migrate:
	DATABASE_URL="$(DATABASE_URL)" $(PYTHON) backend/src/db/run_migrations.py

test:
	$(PYTHON) -m pytest calibration runtime reserve tests evals learning synthesis
	$(MAKE) migrate
	cd backend && DATABASE_URL="$(DATABASE_URL)" SUPERUSER_DATABASE_URL="$(DATABASE_URL)" npm test
	cd backend && npm run build
	cd frontend && npm test
	cd frontend && npm run build

verify: verify-core verify-backend verify-frontend verify-calibration verify-resolution verify-reserve verify-dispatch verify-security verify-epistemic verify-jurisdiction verify-civilization verify-demo verify-acceptance

verify-core:
	$(PYTHON) -m pytest tests/test_resolution_independence_engine.py reserve/tests/test_proof_of_calibration.py reserve/tests/test_ed25519_signing.py

verify-backend:
	cd backend && npm test -- credential-canonical.test.ts credential-routes.test.ts task-dispatch.test.ts
	cd backend && npm run build

verify-frontend:
	cd frontend && npm test
	cd frontend && npm run build

verify-calibration:
	$(PYTHON) -m pytest calibration reserve/tests tests/test_resolution_independence_engine.py

verify-resolution:
	$(PYTHON) -m pytest tests/test_resolution_independence_engine.py tests/integration/test_resolution_evidence_snapshots.py

verify-reserve:
	$(PYTHON) -m pytest reserve/tests/test_canonical_credential_issuer_service.py reserve/tests/test_ed25519_signing.py

verify-dispatch:
	cd backend && npm test -- task-dispatch.test.ts

verify-security:
	cd backend && npm test -- service-identity.test.ts security.test.ts rbac.test.ts

verify-epistemic:
	$(PYTHON) -m pytest tests/test_epistemic_engine_foundation.py tests/test_epistemic_disputes_and_precedent.py

verify-jurisdiction:
	$(PYTHON) -m pytest tests/test_jurisdiction_authority.py

verify-civilization:
	$(PYTHON) -m pytest tests/civilization tests/civilization/test_institution_kernel_lifecycle_services.py

verify-demo:
	$(MAKE) smoke

verify-acceptance:
	$(PYTHON) -m json.tool evals/acceptance/latest_core_acceptance.json >/dev/null

smoke:
	$(PYTHON) scripts/smoke_offline.py

smoke-real:
	DATABASE_URL="$(DATABASE_URL)" LLM_PROVIDER="$${LLM_PROVIDER:-ollama}" LLM_API_KEY="$${LLM_API_KEY:-ollama}" LLM_BASE_URL="$${LLM_BASE_URL:-http://localhost:11434/v1}" $(PYTHON) scripts/smoke_one_task.py

.PHONY: verify-system verify-system-offline
verify-system:
	$(PYTHON) scripts/verify_openai_connectivity.py
	$(PYTHON) scripts/verify_agentco_goal_run.py

verify-system-offline:
	AGENTCO_VERIFY_OFFLINE=1 $(PYTHON) scripts/verify_agentco_goal_run.py --offline

demo:
	$(PYTHON) examples/civilization_constitution_demo/run_demo.py

business-demo: migrate
	DATABASE_URL="$(DATABASE_URL)" $(PYTHON) scripts/demo_business_bikeshare_calibration.py

business-sim: migrate
	DATABASE_URL="$(DATABASE_URL)" $(PYTHON) scripts/run_pawdent_business_simulation.py $(BUSINESS_SIM_ARGS)

clean:
	@printf "This will run docker compose down -v and delete local volumes. Type 'agentco-clean' to continue: "; \
	read confirm; \
	if [ "$$confirm" = "agentco-clean" ]; then docker compose down -v; else echo "Aborted."; fi
