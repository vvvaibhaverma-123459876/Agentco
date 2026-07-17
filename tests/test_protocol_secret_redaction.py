from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def test_secret_canary_not_persisted_in_protocol_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    case = {"case_id": "secret", "control_type": "secret_redaction", "input": {"prompt": "secret"}, "expected_authorization_result": True}
    result = runner.execute_protocol_case("secret-campaign", case)
    assert result["passed"]
    serialized = str(result)
    assert "SECRET_CANARY_DO_NOT_LEAK_08D" not in serialized
