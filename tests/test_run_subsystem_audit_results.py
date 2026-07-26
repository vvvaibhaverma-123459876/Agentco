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
    assert entry["active_findings"][0]["finding_id"] == "HST-001"
    assert entry["historical_findings"] == []


def test_subsystem_audit_runner_separates_historical_findings(monkeypatch):
    monkeypatch.setattr(
        runner,
        "load_findings",
        lambda: {
            "GCR-008": {"finding_id": "GCR-008", "status": "superseded_by_v7_attempt_2"},
            "GCR-010": {"finding_id": "GCR-010", "status": "open_hold_for_more_evidence"},
        },
    )

    entry = runner.subsystem_entry("capability_runtime_protocol", runner.load_findings())

    assert entry["audit_status"] == "failed"
    assert [item["finding_id"] for item in entry["findings"]] == ["GCR-008", "GCR-010"]
    assert [item["finding_id"] for item in entry["active_findings"]] == ["GCR-010"]
    assert [item["finding_id"] for item in entry["historical_findings"]] == ["GCR-008"]


def test_subsystem_audit_runner_missing_evidence_fails(monkeypatch):
    monkeypatch.setattr(runner, "EVIDENCE_MAP", {"l0_runtime_substrate": ["missing/file.txt"]})

    entry = runner.subsystem_entry("l0_runtime_substrate", {})

    assert entry["audit_status"] == "failed"
    assert entry["missing_evidence_paths"] == ["missing/file.txt"]
