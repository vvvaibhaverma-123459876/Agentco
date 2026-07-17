from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def test_timeout_settles_reserved_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    case = {"case_id": "timeout-budget", "control_type": "timeout_terminal_state", "input": {"prompt": "timeout"}, "expected_authorization_result": True}
    result = runner.execute_protocol_case("budget-campaign", case)
    names = {item["name"]: item for item in result["assertions"]}
    assert names["budget_reserved"]["passed"]
    assert names["budget_settled"]["passed"]
    assert names["timeout_reservation_released"]["passed"]
