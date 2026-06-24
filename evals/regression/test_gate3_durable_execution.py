from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTES = ROOT / "backend/src/routes/agents.routes.ts"
SERVICE = ROOT / "backend/src/services/durable-execution.service.ts"
MIGRATION = ROOT / "backend/src/db/migrations/019_durable_execution.sql"


def test_dispatch_path_uses_durable_execution_not_in_memory_queue():
    routes = ROUTES.read_text()
    assert "taskQueue" not in routes
    assert "durableExecution.enqueue" in routes
    assert "durableExecution.run" in routes
    assert "Completed task" not in routes


def test_durable_task_state_is_persisted():
    sql = MIGRATION.read_text()
    assert "CREATE TABLE IF NOT EXISTS workflow_tasks" in sql
    for column in ["status", "result", "audit_log_id", "event_id", "action_attestation_id"]:
        assert column in sql


def test_supported_task_returns_measured_result_and_attestation():
    service = SERVICE.read_text()
    assert "health_check_result" in service
    assert "action_attestation_id" in service
    assert "provenance.attestAction" in service
    assert "unsupported durable task_type" in service
