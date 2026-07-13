import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_secret_scanner_does_not_flag_fixture_task_ids():
    proc = subprocess.run(
        ["python3.13", "scripts/scan_committed_secrets.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_runtime_reachability_generator_outputs_authoritative_components():
    proc = subprocess.run(
        ["python3.13", "scripts/generate_runtime_reachability.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ledger = json.loads((ROOT / "docs/audit/current/RUNTIME_COMPONENT_LEDGER.json").read_text())
    components = {item["path"]: item for item in ledger["components"]}
    assert components["backend/src/server.ts"]["classification"] == "authoritative_runtime"
    assert components["backend/src/workers/outbox-worker.ts"]["authoritative_status"] == "authoritative"
    assert any(
        item["path"].startswith("agents/autonomy/") and item["authoritative_status"] == "live_specialist_runtime"
        for item in ledger["components"]
    )


def test_runtime_reachability_generator_classifies_disabled_routes_as_historical():
    subprocess.run(["python3.13", "scripts/generate_runtime_reachability.py"], cwd=ROOT, check=True)
    ledger = json.loads((ROOT / "docs/audit/current/RUNTIME_COMPONENT_LEDGER.json").read_text())
    historical = [item for item in ledger["components"] if ".disabled" in item["path"]]
    assert all(item["classification"] == "historical" for item in historical)


def test_runtime_integration_ledger_requires_cleanup_and_real_services(tmp_path):
    ledger = {
        "run_id": "run-a",
        "commit": "abc",
        "final_verdict": "PASS",
        "services": {
            "postgres": {"container": "pg", "port": 5432},
            "redis": {"container": "redis", "port": 6379},
            "kafka": {"container": "kafka", "port": 9092},
        },
        "commands": [
            {"command_id": "docker-version", "run_id": "run-a", "commit": "abc", "exit_code": 0},
            {"command_id": "outbox-publish-proof", "run_id": "run-a", "commit": "abc", "exit_code": 0},
            {"command_id": "kafka-consume-proof", "run_id": "run-a", "commit": "abc", "exit_code": 0},
        ],
        "cleanup": {"success": True},
    }
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(ledger))
    data = json.loads(path.read_text())
    assert data["cleanup"]["success"] is True
    assert {"postgres", "redis", "kafka"} <= set(data["services"])
    assert {cmd["command_id"] for cmd in data["commands"]} >= {
        "docker-version",
        "outbox-publish-proof",
        "kafka-consume-proof",
    }


def test_kafka_retry_factor_is_randomization_not_multiplier():
    source = (ROOT / "backend/src/db/kafka.ts").read_text()
    assert "KAFKA_RETRY_FACTOR ?? 0.2" in source
    assert "KAFKA_RETRY_MULTIPLIER ?? 2" in source
    assert "retry: { retries, initialRetryTime, factor, multiplier }" in source
