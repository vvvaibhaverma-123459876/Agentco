from __future__ import annotations

import scripts.run_governed_capability_genesis as runner


def test_provider_preflight_does_not_mark_unverified_provider_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "example.test")
    monkeypatch.delenv("AGENTCO_PROVIDER_PREFLIGHT_ALLOW_MODEL_CALL", raising=False)
    result = runner.preflight_provider("openai_compatible")
    assert result["provider_preflight"] == "unavailable_external_verification"
    assert result["provider_reachable"] == "not_verified"
    assert result["model_access_verified"] == "not_verified"
    assert result["execution_attempted"] is False
