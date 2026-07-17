from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def _case(control_type: str) -> dict:
    return {
        "case_id": f"test-{control_type}",
        "control_type": control_type,
        "input": {"prompt": f"Validate {control_type}"},
        "expected_authorization_result": True,
    }


def _local_store(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_malformed_response_executes_mock_provider(tmp_path, monkeypatch):
    _local_store(monkeypatch, tmp_path)
    result = runner.execute_protocol_case("test-campaign", _case("malformed_provider_response"))
    assert result["passed"]
    assert result["terminal_status"] == "failed"
    assert result["failure_category"] == "malformed_response"
    assert result["assertion_count"] >= 4


def test_transport_failure_is_not_deterministic_success(tmp_path, monkeypatch):
    _local_store(monkeypatch, tmp_path)
    result = runner.execute_protocol_case("test-campaign", _case("provider_transport_failure"))
    assert result["passed"]
    assert result["terminal_status"] == "failed"
    assert result["failure_category"] == "transport_failure"


def test_timeout_records_timed_out_terminal_state(tmp_path, monkeypatch):
    _local_store(monkeypatch, tmp_path)
    result = runner.execute_protocol_case("test-campaign", _case("timeout_terminal_state"))
    assert result["passed"]
    assert result["terminal_status"] == "timed_out"


def test_protocol_result_fails_any_failed_or_skipped_assertion():
    result = runner.protocol_result(
        _case("request_schema_validation"),
        {},
        {},
        [
            {"name": "ok", "passed": True, "skipped": False},
            {"name": "bad", "passed": False, "skipped": False},
        ],
        {"status": "completed", "audit_references": []},
    )
    assert not result["passed"]
    assert result["failed_assertion_count"] == 1
