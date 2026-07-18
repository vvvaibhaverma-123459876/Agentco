from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def _local_store(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)


def test_request_schema_rejects_missing_required_field(tmp_path, monkeypatch):
    _local_store(monkeypatch, tmp_path)
    case = {"case_id": "schema-request", "control_type": "request_schema_validation", "input": {"prompt": "schema"}, "expected_authorization_result": True}
    result = runner.execute_protocol_case("schema-test", case)
    names = {item["name"]: item for item in result["assertions"]}
    assert names["actual_request_schema_validated"]["passed"]
    assert names["invalid_request_rejected"]["passed"]


def test_response_schema_rejects_missing_status(tmp_path, monkeypatch):
    _local_store(monkeypatch, tmp_path)
    case = {"case_id": "schema-response", "control_type": "response_schema_validation", "input": {"prompt": "schema"}, "expected_authorization_result": True}
    result = runner.execute_protocol_case("schema-test", case)
    names = {item["name"]: item for item in result["assertions"]}
    assert names["completed_response_schema_validated"]["passed"]
    assert names["mutated_response_rejected"]["passed"]
