from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHUTDOWN = ROOT / "backend/src/runtime/shutdown.ts"
SMOKE = ROOT / "backend/src/cli/smoke-durable-execution.ts"
SERVER = ROOT / "backend/src/server.ts"
PACKAGE = ROOT / "backend/package.json"


def test_runtime_shutdown_closes_kafka_and_optional_db_pool():
    source = SHUTDOWN.read_text()

    assert "disconnectProducer" in source
    assert "db.end()" in source
    assert "closeDb" in source
    assert "producerDisconnected" in source
    assert "dbClosed" in source


def test_durable_smoke_uses_shared_shutdown_helper():
    source = SMOKE.read_text()

    assert "durableExecution.enqueue" in source
    assert "durableExecution.run" in source
    assert "shutdownRuntimeResources({ closeDb: true })" in source
    assert "db.end()" not in source


def test_server_signal_path_uses_shared_shutdown_helper():
    source = SERVER.read_text()

    assert "shutdownRuntimeResources({ closeDb: true })" in source


def test_backend_exposes_durable_smoke_script():
    package_json = PACKAGE.read_text()

    assert '"smoke:durable"' in package_json
    assert "KAFKA_RETRIES=0" in package_json
    assert "dist/cli/smoke-durable-execution.js" in package_json


def test_kafka_failed_connect_does_not_poison_singleton():
    source = (ROOT / "backend/src/db/kafka.ts").read_text()

    assert "process.env.KAFKA_RETRIES" in source
    assert "await producer.connect()" in source
    assert "_producer = producer" in source
    assert "await producer.disconnect().catch(() => undefined)" in source
