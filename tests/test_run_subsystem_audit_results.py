from __future__ import annotations

from scripts import run_subsystem_audit_results as runner
from scripts.verify_subsystem_audit_results import REQUIRED_SUBSYSTEMS


def test_subsystem_audit_runner_covers_all_required_subsystems():
    assert set(runner.EVIDENCE_MAP) == set(REQUIRED_SUBSYSTEMS)


def test_subsystem_audit_runner_links_known_blocking_findings_to_owners(monkeypatch):
    monkeypatch.setattr(runner, "load_findings", lambda: {"HST-001": {"finding_id": "HST-001", "status": "open_blocking"}})

    entry = runner.subsystem_entry("infra_deployment", runner.load_findings())

    assert entry["audit_status"] == "failed"
    assert entry["findings"][0]["finding_id"] == "HST-001"


def test_subsystem_audit_runner_missing_evidence_fails(monkeypatch):
    monkeypatch.setattr(runner, "EVIDENCE_MAP", {"l0_runtime_substrate": ["missing/file.txt"]})

    entry = runner.subsystem_entry("l0_runtime_substrate", {})

    assert entry["audit_status"] == "failed"
    assert entry["missing_evidence_paths"] == ["missing/file.txt"]
