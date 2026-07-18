from __future__ import annotations

import json

from scripts.verify_subsystem_audit_results import REQUIRED_SUBSYSTEMS, verify_results


def _entry(**overrides):
    item = {
        "audit_status": "passed",
        "tool_exit_code": 0,
        "agent_output_tokens": 120,
        "started_at": "2026-07-19T00:00:00Z",
        "completed_at": "2026-07-19T00:00:01Z",
        "evidence_paths": ["artifacts/subsystem-audit/example.json"],
        "findings": [],
    }
    item.update(overrides)
    return item


def _payload(**overrides):
    payload = {
        "required_subsystem_count": len(REQUIRED_SUBSYSTEMS),
        "completed_subsystem_count": len(REQUIRED_SUBSYSTEMS),
        "subsystems": {subsystem_id: _entry() for subsystem_id in REQUIRED_SUBSYSTEMS},
        "synthesis": _entry(),
    }
    payload.update(overrides)
    return payload


def test_verify_subsystem_audit_results_accepts_complete_nonzero_audit(tmp_path):
    path = tmp_path / "SUBSYSTEM_AUDIT_RESULTS.json"
    path.write_text(json.dumps(_payload()))

    assert verify_results(path) == []


def test_verify_subsystem_audit_results_requires_artifact(tmp_path):
    findings = verify_results(tmp_path / "missing.json")

    assert findings[0].startswith("SUBSYSTEM_AUDIT_RESULTS_MISSING")


def test_verify_subsystem_audit_results_rejects_zero_token_subsystem(tmp_path):
    subsystems = {subsystem_id: _entry() for subsystem_id in REQUIRED_SUBSYSTEMS}
    subsystems["infra_deployment"] = _entry(agent_output_tokens=0)
    path = tmp_path / "SUBSYSTEM_AUDIT_RESULTS.json"
    path.write_text(json.dumps(_payload(subsystems=subsystems)))

    findings = verify_results(path)

    assert "SUBSYSTEM_AUDIT_ZERO_OUTPUT_TOKENS:infra_deployment" in findings


def test_verify_subsystem_audit_results_rejects_open_findings(tmp_path):
    subsystems = {subsystem_id: _entry() for subsystem_id in REQUIRED_SUBSYSTEMS}
    subsystems["capability_runtime_protocol"] = _entry(
        findings=[
            {
                "finding_id": "CAP-001",
                "status": "open_blocking",
            }
        ]
    )
    path = tmp_path / "SUBSYSTEM_AUDIT_RESULTS.json"
    path.write_text(json.dumps(_payload(subsystems=subsystems)))

    findings = verify_results(path)

    assert "SUBSYSTEM_AUDIT_OPEN_FINDING:capability_runtime_protocol:CAP-001" in findings


def test_verify_subsystem_audit_results_requires_synthesis(tmp_path):
    payload = _payload()
    payload.pop("synthesis")
    path = tmp_path / "SUBSYSTEM_AUDIT_RESULTS.json"
    path.write_text(json.dumps(payload))

    findings = verify_results(path)

    assert "SUBSYSTEM_AUDIT_SYNTHESIS_MISSING" in findings
