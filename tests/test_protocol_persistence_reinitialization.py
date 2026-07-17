from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def test_persistence_reopens_store_and_rejects_corruption(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    case = {"case_id": "persist", "control_type": "storage_persistence", "input": {"prompt": "persist"}, "expected_authorization_result": True}
    result = runner.execute_protocol_case("persist-campaign", case)
    names = {item["name"]: item for item in result["assertions"]}
    assert names["fresh_store_read_retrieves_attempt"]["passed"]
    assert names["corrupted_persisted_state_rejected"]["passed"]
