import json
import subprocess
from pathlib import Path

import pytest

from scripts import audit_clean_room
from scripts.verify_migration_integrity import validate_static
from scripts.verify_pytest_skips import EnvironmentRequirement, SkipEntry, load_allowlist, validate_report


ROOT = Path(__file__).resolve().parents[1]


def _skip_entry(node_id: str, expiry: str = "2026-10-31") -> SkipEntry:
    return SkipEntry(
        node_id=node_id,
        reason="bounded test fixture",
        classification="other",
        owner="audit",
        mandatory_for_clean_room=False,
        expiry_date=expiry,
        required_environment=[],
    )


def _env_skip_entry(node_id: str, requirement: EnvironmentRequirement, classification: str = "local_clean_room_service") -> SkipEntry:
    return SkipEntry(
        node_id=node_id,
        reason="bounded test fixture",
        classification=classification,
        owner="audit",
        mandatory_for_clean_room=False,
        expiry_date="2026-10-31",
        required_environment=[requirement],
    )


def test_skip_governance_rejects_unapproved_skip():
    report = {"collected": ["tests/test_x.py::test_a"], "skipped": [{"node_id": "tests/test_x.py::test_a", "reason": "skip"}]}
    valid, errors, _ = validate_report(report, [])
    assert not valid
    assert any("unapproved skip" in error for error in errors)


def test_skip_governance_rejects_expired_and_stale_entries():
    report = {"collected": ["tests/test_x.py::test_a"], "skipped": [{"node_id": "tests/test_x.py::test_a", "reason": "skip"}]}
    valid, errors, _ = validate_report(report, [_skip_entry("tests/test_x.py::test_a", "2020-01-01"), _skip_entry("tests/test_missing.py::test_z")])
    assert not valid
    assert any("expired" in error for error in errors)
    assert any("stale skip allowlist entry" in error for error in errors)


def test_skip_governance_rejects_zero_tests_and_xpass():
    report = {"collected": [], "skipped": [], "xpassed": [{"node_id": "tests/test_x.py::test_a", "reason": "xpass"}]}
    valid, errors, _ = validate_report(report, [])
    assert not valid
    assert any("zero tests" in error for error in errors)
    assert any("xpass" in error for error in errors)


def test_skip_governance_rejects_skip_when_required_environment_available(monkeypatch):
    monkeypatch.setenv("AGENTCO_TEST_FLAG", "1")
    report = {"collected": ["tests/test_x.py::test_db"], "skipped": [{"node_id": "tests/test_x.py::test_db", "reason": "database unavailable"}]}
    entry = _env_skip_entry("tests/test_x.py::test_db", EnvironmentRequirement("AGENTCO_TEST_FLAG", "present"))
    valid, errors, _ = validate_report(report, [entry])
    assert not valid
    assert any("SKIP_DESPITE_AVAILABLE_ENVIRONMENT" in error for error in errors)


def test_skip_governance_rejects_database_skip_classified_as_external_network(monkeypatch):
    monkeypatch.delenv("AGENTCO_TEST_DATABASE_URL", raising=False)
    report = {"collected": ["tests/test_x.py::test_db"], "skipped": [{"node_id": "tests/test_x.py::test_db", "reason": "Postgres unavailable"}]}
    entry = _env_skip_entry(
        "tests/test_x.py::test_db",
        EnvironmentRequirement("AGENTCO_TEST_DATABASE_URL", "postgres_reachable"),
        classification="external_network",
    )
    valid, errors, _ = validate_report(report, [entry])
    assert not valid
    assert any("DB_SKIP_CLASSIFIED_EXTERNAL_NETWORK" in error for error in errors)


def test_skip_governance_rejects_wrong_missing_service_reason(monkeypatch):
    monkeypatch.setenv("KAFKA_BROKERS", "127.0.0.1:9")
    report = {"collected": ["tests/test_x.py::test_kafka"], "skipped": [{"node_id": "tests/test_x.py::test_kafka", "reason": "Postgres unavailable"}]}
    entry = _env_skip_entry("tests/test_x.py::test_kafka", EnvironmentRequirement("KAFKA_BROKERS", "kafka_reachable"), classification="live_provider")
    valid, errors, _ = validate_report(report, [entry])
    assert not valid
    assert any("SKIP_REASON_MISMATCH" in error for error in errors)


def test_skip_governance_rejects_malformed_environment_condition(tmp_path):
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(json.dumps({
        "skips": [{
            "node_id": "tests/test_x.py::test_a",
            "reason": "bad condition",
            "classification": "other",
            "owner": "audit",
            "mandatory_for_clean_room": False,
            "expiry_date": "2026-10-31",
            "required_environment": [{"name": "FLAG", "condition": "sometimes"}],
        }]
    }))
    with pytest.raises(ValueError, match="malformed required_environment condition"):
        load_allowlist(allowlist)


def test_migration_static_validator_rejects_reordered_duplicate_and_noop(tmp_path):
    (tmp_path / "002_second.sql").write_text("CREATE TABLE second(id int);\n")
    (tmp_path / "001_first.sql").write_text("-- no schema effect\n")
    (tmp_path / "001_first.sql.ignored").write_text("CREATE TABLE ignored(id int);\n")
    findings = validate_static(tmp_path)
    assert any(item.rule == "NO_SCHEMA_EFFECT" for item in findings)


def test_migration_static_validator_rejects_bad_prefix(tmp_path):
    (tmp_path / "migration.sql").write_text("CREATE TABLE bad(id int);\n")
    with pytest.raises(ValueError, match="lacks deterministic ordered prefix"):
        validate_static(tmp_path)


def test_execution_ledger_rejects_wrong_commit(tmp_path):
    (tmp_path / "out.txt").write_text("")
    (tmp_path / "err.txt").write_text("")
    ledger = tmp_path / "EXECUTION_LEDGER.json"
    ledger.write_text(json.dumps({
        "run_id": "run-a",
        "commit": "not-head",
        "final_verdict": "PASS",
        "cleanup": {"success": True},
        "test_summary": {"pytest_exit_code": 0, "collected": 1},
        "skip_summary": {"skip_classifications": {}},
        "commands": [{
            "command_id": "docker-version",
            "run_id": "run-a",
            "commit": "not-head",
            "exit_code": 0,
            "stdout_artifact": "out.txt",
            "stderr_artifact": "err.txt",
            "argv": ["docker", "--version"],
        }],
    }) + "\n")
    proc = subprocess.run(
        ["python3.13", "scripts/verify_execution_ledger.py", str(ledger)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "does not match HEAD" in proc.stdout


def test_execution_ledger_rejects_missing_records_other_run_and_secret(tmp_path):
    (tmp_path / "out.txt").write_text("")
    (tmp_path / "err.txt").write_text("")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    ledger = tmp_path / "EXECUTION_LEDGER.json"
    ledger.write_text(json.dumps({
        "run_id": "run-a",
        "commit": head,
        "final_verdict": "PASS",
        "cleanup": {"success": True},
        "test_summary": {"pytest_exit_code": 0, "collected": 1},
        "skip_summary": {"skip_classifications": {}},
        "commands": [{
            "command_id": "docker-version",
            "run_id": "run-b",
            "commit": head,
            "exit_code": 0,
            "stdout_artifact": "out.txt",
            "stderr_artifact": "err.txt",
            "argv": ["docker", "run", "-e", "POSTGRES_PASSWORD=secret"],
        }],
    }) + "\n")
    proc = subprocess.run(
        ["python3.13", "scripts/verify_execution_ledger.py", str(ledger)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "another run" in proc.stdout
    assert "unredacted secret" in proc.stdout
    assert "missing required command ids" in proc.stdout


def test_execution_ledger_rejects_missing_test_and_skip_summaries(tmp_path):
    (tmp_path / "out.txt").write_text("")
    (tmp_path / "err.txt").write_text("")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    ledger = tmp_path / "EXECUTION_LEDGER.json"
    ledger.write_text(json.dumps({
        "run_id": "run-a",
        "commit": head,
        "final_verdict": "PASS",
        "cleanup": {"success": True},
        "commands": [{
            "command_id": "docker-version",
            "run_id": "run-a",
            "commit": head,
            "exit_code": 0,
            "stdout_artifact": "out.txt",
            "stderr_artifact": "err.txt",
            "argv": ["docker", "--version"],
        }],
    }) + "\n")
    proc = subprocess.run(
        ["python3.13", "scripts/verify_execution_ledger.py", str(ledger)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "ledger missing test_summary" in proc.stdout
    assert "ledger missing skip_summary" in proc.stdout


def test_command_runner_records_failure_without_success(tmp_path):
    state = audit_clean_room.CleanRoomState(
        run_id="unit",
        run_dir=tmp_path,
        commands_dir=tmp_path / "commands",
        migration_dir=tmp_path / "migration-results",
        test_dir=tmp_path / "test-results",
        container="no-container",
        volume="no-volume",
        database="no-db",
        username="agentco",
        password="password",
        host_port="5432",
    )
    state.commands_dir.mkdir()
    with pytest.raises(RuntimeError):
        audit_clean_room.run_command(state, "intentional-failure", ["python3.13", "-c", "raise SystemExit(7)"], cwd=ROOT)
    assert state.commands[-1].exit_code == 7


def test_command_runner_redacts_secret_argv(tmp_path):
    state = audit_clean_room.CleanRoomState(
        run_id="unit",
        run_dir=tmp_path,
        commands_dir=tmp_path / "commands",
        migration_dir=tmp_path / "migration-results",
        test_dir=tmp_path / "test-results",
        container="no-container",
        volume="no-volume",
        database="no-db",
        username="agentco",
        password="password",
        host_port="5432",
    )
    state.commands_dir.mkdir()
    audit_clean_room.run_command(
        state,
        "redaction-probe",
        ["python3.13", "-c", "print('ok')", "postgresql://user:secret@localhost/db", "POSTGRES_PASSWORD=secret"],
        cwd=ROOT,
    )
    serialized = json.dumps(state.commands[-1].__dict__)
    assert "secret@localhost" not in serialized
    assert "POSTGRES_PASSWORD=secret" not in serialized
    assert "<redacted>" in serialized


def test_cleanup_failure_marks_state_failed(tmp_path, monkeypatch):
    state = audit_clean_room.CleanRoomState(
        run_id="unit",
        run_dir=tmp_path,
        commands_dir=tmp_path / "commands",
        migration_dir=tmp_path / "migration-results",
        test_dir=tmp_path / "test-results",
        container="still-there",
        volume="still-there",
        database="db",
        username="agentco",
        password="password",
        host_port="5432",
    )
    state.commands_dir.mkdir()

    def fake_run_command(state, command_id, command, cwd=None, env=None, required=True):
        code = 0
        if command_id in {"cleanup-verify-container-removed", "cleanup-verify-volume-removed"}:
            code = 0
        state.commands.append(type("Record", (), {"command_id": command_id, "exit_code": code})())
        return code

    monkeypatch.setattr(audit_clean_room, "run_command", fake_run_command)
    assert audit_clean_room.cleanup(state) is False
    assert state.cleanup["success"] is False


def test_gate_integrity_negative_fixture_blocks_continue_on_error(tmp_path):
    subprocess.check_call(["git", "init"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("jobs:\n  test:\n    steps:\n      - continue-on-error: true\n")
    (tmp_path / "Makefile").write_text("release-gate:\n\tpython3.13 scripts/verify_gate_integrity.py --check\n")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "audit@example.com"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "Audit"], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-m", "fixture"], cwd=tmp_path, stdout=subprocess.DEVNULL)
    proc = subprocess.run(
        ["python3.13", str(ROOT / "scripts" / "verify_gate_integrity.py"), "--check", "--root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "success" in proc.stdout
