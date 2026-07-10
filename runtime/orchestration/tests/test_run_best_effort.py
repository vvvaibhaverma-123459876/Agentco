import json
import os
import subprocess
import sys
from pathlib import Path

from runtime.orchestration import run_best_effort
from runtime.orchestration.doctor import Check


ROOT = Path(__file__).resolve().parents[3]


def _checks_without_openai() -> list[Check]:
    return [
        Check("python", "real", "3.13"),
        Check("node", "real", "node"),
        Check("npm", "real", "npm"),
        Check("postgres", "real", "postgres"),
        Check("migrations", "real", "migrations"),
        Check("core_db_schema", "real", "schema"),
        Check("filesystem_reports", "real", "reports"),
        Check("sensitive_route_auth", "real", "auth"),
        Check("openai_connectivity", "missing", "no key"),
    ]


def test_best_effort_does_not_silently_use_fixture_llm(monkeypatch):
    monkeypatch.setattr(run_best_effort, "collect_checks", lambda *args, **kwargs: _checks_without_openai())
    written = {}
    monkeypatch.setattr(run_best_effort, "write_report", lambda report: written.update(report))

    code = run_best_effort.main(["--mode", "local_native"])

    assert code == 1
    assert written["run_best_effort"]["completed"] is False
    assert "requires --allow-offline-fallback" in written["run_best_effort"]["blocked_reason"]


def test_best_effort_requires_explicit_offline_fallback(monkeypatch):
    monkeypatch.setattr(run_best_effort, "collect_checks", lambda *args, **kwargs: _checks_without_openai())
    monkeypatch.setattr(run_best_effort, "run_goal", lambda mode: (0, '{"success": true}'))
    written = {}
    monkeypatch.setattr(run_best_effort, "write_report", lambda report: written.update(report))

    code = run_best_effort.main(["--mode", "local_native", "--allow-offline-fallback"])

    assert code == 0
    assert written["run_best_effort"]["selected_runtime_mode"] == "offline_fixture"
    assert any(f["fallback"] == "deterministic_fixture_llm" for f in written["fallbacks_used"])


def test_best_effort_production_never_downgrades_to_offline(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    monkeypatch.setattr(run_best_effort, "collect_checks", lambda *args, **kwargs: [
        Check("python", "real", "3.13"),
        Check("filesystem_reports", "real", "reports"),
        Check("postgres", "missing", "no postgres"),
    ])
    written = {}
    monkeypatch.setattr(run_best_effort, "write_report", lambda report: written.update(report))

    code = run_best_effort.main(["--mode", "production", "--allow-offline-fallback"])

    assert code == 1
    assert written["run_best_effort"]["completed"] is False
    assert "cannot downgrade" in written["run_best_effort"]["blocked_reason"]


def test_run_best_effort_offline_fixture_exits_successfully(tmp_path):
    env = {**os.environ, "AGENTCO_REPORT_DIR": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, "-m", "runtime.orchestration.run_best_effort", "--mode", "offline_fixture"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((tmp_path / "doctor_report.json").read_text())
    assert report["selected_runtime_mode"] == "offline_fixture"
    assert report["run_best_effort"]["completed"] is True
