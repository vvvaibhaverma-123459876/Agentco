# Running AgentCo locally on Windows (HP Omen, RTX 5050)

This brings the whole stack up on a single Windows machine with **no cloud API
key** — all models run locally via [Ollama](https://ollama.com), and every
epistemic invariant is enforced by a real Postgres instance.

Copy-paste the PowerShell blocks in order.

---

## 0. Prerequisites

| Tool | Notes |
|------|-------|
| Docker Desktop | WSL2 backend enabled. Provides Postgres (and the rest of the stack). |
| Python 3.12 | `python --version` should report 3.12.x. |
| Ollama | Install from https://ollama.com/download — it uses the GPU automatically. |
| Git | To clone the repo. |

> **VRAM note (8 GB):** `qwen2.5:7b` and `qwen2.5-coder:7b` (~5 GB at Q4) fit
> comfortably. The `frontier` tier defaults to `phi4` (14B, ~9 GB) which is tight
> on 8 GB — Ollama will offload some layers to CPU (slower but works). To stay
> fully on-GPU, override the frontier tier to a smaller model (see step 4).

---

## 1. Clone and create the Python environment

```powershell
git clone https://github.com/vvvaibhaverma-123459876/Agentco.git
cd Agentco
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r agents\requirements.txt
```

## 2. Start Postgres (and Redis) via Docker Desktop

The full `docker-compose.yml` also defines Kafka, Vault, Prometheus, Grafana,
etc. For a local agent run you only need Postgres; start just that (and Redis):

```powershell
docker compose up -d postgres redis
docker compose ps        # wait until postgres is "healthy"
```

> The whole stack (`docker compose up -d`) works too, but it is heavy on an
> 8 GB-VRAM laptop that is also running Ollama. Start narrow first.

## 3. Apply the database migrations

Migrations live in `backend/src/db/migrations` and must be applied in order.
Run them through the Postgres container:

```powershell
Get-ChildItem backend\src\db\migrations\*.sql | Sort-Object Name | ForEach-Object {
    Write-Host "applying $($_.Name)"
    Get-Content $_.FullName | docker exec -i agentco-postgres psql -U agentco -d agentco -v ON_ERROR_STOP=1
}
```

All 11 migrations should apply with no `ERROR`. Migration `011_prediction_ledger.sql`
installs the immutability trigger that makes the prediction ledger append-only.

## 4. Pull the local models

```powershell
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
ollama pull phi4            # frontier tier; large — see VRAM note
ollama list
```

Optional — if `phi4` is too heavy for 8 GB, point the frontier tier at a smaller
model for this session:

```powershell
$env:LLM_FRONTIER_MODEL = "qwen2.5:7b"   # (only honoured if you wire it; default tier is phi4)
```

> The model-tier map is `runtime/base_agent/model_tiers.py`
> (`model_for(agent_id)` is the single source of truth — there are no hardcoded
> cloud model ids anywhere in the codebase).

## 5. Configure environment variables

```powershell
$env:LLM_BASE_URL = "http://localhost:11434/v1"   # Ollama's OpenAI-compatible endpoint
$env:LLM_API_KEY  = "ollama"                       # any non-empty string
$env:DATABASE_URL = "postgresql://agentco:password@localhost:5432/agentco"
```

(See `.env.example` for the full list.)

## 6. Run the test suite (the invariant gate)

```powershell
# Unit + V2 suite (no DB needed — uses the in-memory fallback)
python -m pytest agents\tests calibration runtime learning synthesis evals\regression\test_audit_findings.py evals\regression\test_v2_regression.py -q

# Real-Postgres invariant tests (raw UPDATE/DELETE rejected by the DB)
$env:AGENTCO_TEST_DATABASE_URL = $env:DATABASE_URL
python -m pytest evals\regression\test_pg_ledger_immutability.py evals\regression\test_pg_ledger_persistence.py -q
```

Everything must be green. The Postgres tests prove the ledger immutability
invariant is enforced **by the database**, not just by application code.

## 7. Run one agent end-to-end against Ollama + Postgres

```powershell
python scripts\run_local_agent.py          # DB persistence only (fast)
python scripts\run_local_agent.py --llm    # also make a real Ollama structured call
```

This pre-registers a falsifiable claim (persisted to `prediction_ledger`), runs
an action through the `trusted_confidence` + escalation gates, resolves the claim
through the `resolution_service` role, and shows the Trust Controller ingesting
the calibration signal — all against the live database.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` on 5432 | `docker compose ps` — wait for postgres `healthy`; check Docker Desktop is running. |
| `relation "prediction_ledger" does not exist` | Re-run step 3 (migrations). |
| Ollama call times out / very slow | First call loads the model into VRAM; subsequent calls are fast. On 8 GB, prefer the 7B models. |
| `ModuleNotFoundError: runtime` | Run pytest from the repo root (the root `conftest.py` sets up the path). |
| migration `011` role error during resolution | The demo script auto-creates and grants the `resolution_service` role; ensure `DATABASE_URL` can create roles. |
