from __future__ import annotations

import argparse
import json
from pathlib import Path

import scripts.verify_docker_startup as verifier


def test_docker_startup_reports_blocked_when_daemon_unavailable(monkeypatch):
    def fake_run(command: list[str], timeout: int = 60):
        joined = " ".join(command)
        if command[:2] == ["docker", "info"]:
            return {
                "command": joined,
                "exit_code": 1,
                "status": "failed",
                "output_tail": "Cannot connect to the Docker daemon",
            }
        return {
            "command": joined,
            "exit_code": 0,
            "status": "passed",
            "output_tail": "compose ok",
        }

    monkeypatch.setattr(verifier, "run", fake_run)

    report = verifier.build_report(argparse.Namespace(up_timeout=1, health_timeout=1))

    assert report["success"] is False
    assert report["status"] == "blocked"
    assert report["reason"] == "docker daemon unavailable"
    assert report["compose_config"]["status"] == "passed"
    assert report["checks"] == []


def test_docker_startup_writes_json_and_markdown_reports(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(verifier, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(verifier, "REPORT_JSON", tmp_path / "docker_startup_verification.json")
    monkeypatch.setattr(verifier, "REPORT_MD", tmp_path / "docker_startup_verification.md")
    report = {
        "generated_at": "2026-06-30T00:00:00Z",
        "success": False,
        "status": "blocked",
        "docker_info": {"status": "failed", "output_tail": "daemon unavailable"},
        "checks": [],
    }

    verifier.write_report(report)

    data = json.loads((tmp_path / "docker_startup_verification.json").read_text())
    markdown = (tmp_path / "docker_startup_verification.md").read_text()
    assert data["status"] == "blocked"
    assert "daemon unavailable" in markdown
