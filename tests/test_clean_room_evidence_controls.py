import json
import subprocess
from pathlib import Path

import pytest

from scripts import audit_clean_room
from scripts.verify_migration_integrity import validate_static
from scripts.verify_pytest_skips import SkipEntry, validate_report


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
    ledger = tmp_path / "EXECUTION_LEDGER.json"
    ledger.write_text(json.dumps({"commit": "not-head", "final_verdict": "PASS", "commands": [{"name": "x", "exit_code": 0}]}) + "\n")
    proc = subprocess.run(
        ["python3.13", "scripts/verify_execution_ledger.py", str(ledger)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "does not match HEAD" in proc.stdout


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
