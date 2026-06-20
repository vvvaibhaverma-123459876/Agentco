.PHONY: doctor dev dev-minimal dev-full migrate test smoke smoke-real demo business-demo business-sim clean

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
	cd frontend && npm run build

smoke:
	$(PYTHON) scripts/smoke_offline.py

smoke-real:
	DATABASE_URL="$(DATABASE_URL)" LLM_PROVIDER="$${LLM_PROVIDER:-ollama}" LLM_API_KEY="$${LLM_API_KEY:-ollama}" LLM_BASE_URL="$${LLM_BASE_URL:-http://localhost:11434/v1}" $(PYTHON) scripts/smoke_one_task.py

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
