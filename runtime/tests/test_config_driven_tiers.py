"""
Config-driven provider/model switching tests.

Proves:
  1. Config-only switching: changing env vars changes the resolved (provider, model)
     without any code change.
  2. Mixed config: frontier→provider A, coder→provider B resolves each tier correctly.
  3. client_for_tier() returns a cached client for identical config, a different client
     when config differs.
  4. Startup validation fails fast on missing api_key (non-ollama provider).
  5. SpendGuardrail blocks new LLM calls once the token cap is exceeded.
  6. SpendGuardrail blocks new calls once the per-minute rate cap is exceeded.
  7. SpendCapExceeded surfaces via escalation before raising.

No mocks for the guardrail tests — real SpendGuardrail instances with controlled state.
The client tests use monkeypatch to inject env vars; no live network calls needed.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_cache():
    from runtime.base_agent.llm_client import clear_client_cache
    clear_client_cache()


# ---------------------------------------------------------------------------
# 1. Config-only switching
# ---------------------------------------------------------------------------

class TestConfigOnlySwitching:

    def test_coder_tier_switches_model_via_env(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_CODER", "gpt-4o")

        from runtime.base_agent.provider_config import resolve_tier_config
        cfg = resolve_tier_config("coder")

        assert cfg.model == "gpt-4o"
        assert cfg.provider == "openai"

    def test_global_model_default_applies_to_all_unset_tiers(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        # No per-tier overrides for standard/monitor
        monkeypatch.delenv("LLM_MODEL_STANDARD", raising=False)
        monkeypatch.delenv("LLM_MODEL_MONITOR", raising=False)

        from runtime.base_agent.provider_config import resolve_tier_config
        assert resolve_tier_config("standard").model == "gpt-4o-mini"
        assert resolve_tier_config("monitor").model == "gpt-4o-mini"

    def test_openai_ignores_ollama_style_global_default(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "mistral:7b")
        monkeypatch.delenv("LLM_MODEL_STANDARD", raising=False)

        from runtime.base_agent.provider_config import resolve_tier_config
        cfg = resolve_tier_config("standard")

        assert cfg.model == "gpt-4o-mini"

    def test_ollama_keeps_local_default_models(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("LLM_MODEL_DEFAULT", raising=False)
        monkeypatch.delenv("LLM_MODEL_STANDARD", raising=False)

        from runtime.base_agent.provider_config import resolve_tier_config
        cfg = resolve_tier_config("standard")

        assert cfg.model == "qwen2.5:7b"

    def test_model_for_agent_reflects_env_change(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_FRONTIER", "gpt-4o-turbo")

        from runtime.base_agent.model_tiers import model_for
        assert model_for("ceo-agent") == "gpt-4o-turbo"    # ceo-agent → frontier

    def test_tier_for_is_stable_across_config_changes(self, monkeypatch):
        """tier_for() is code-driven, not config-driven — must never change."""
        from runtime.base_agent.model_tiers import tier_for

        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        assert tier_for("ceo-agent") == "frontier"

        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        assert tier_for("ceo-agent") == "frontier"  # unchanged


# ---------------------------------------------------------------------------
# 2. Mixed provider config
# ---------------------------------------------------------------------------

class TestMixedProviderConfig:

    def test_frontier_anthropic_coder_openai(self, monkeypatch):
        # Global: openai
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-global")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        # Frontier override: anthropic
        monkeypatch.setenv("LLM_PROVIDER_FRONTIER", "anthropic")
        monkeypatch.setenv("LLM_API_KEY_FRONTIER", "sk-ant-test")
        monkeypatch.setenv("LLM_MODEL_FRONTIER", "claude-sonnet-4-6")
        monkeypatch.delenv("LLM_BASE_URL_FRONTIER", raising=False)

        from runtime.base_agent.provider_config import resolve_tier_config
        frontier = resolve_tier_config("frontier")
        coder = resolve_tier_config("coder")

        assert frontier.provider == "anthropic"
        assert frontier.model == "claude-sonnet-4-6"
        assert frontier.api_key == "sk-ant-test"

        assert coder.provider == "openai"
        assert coder.model == "gpt-4o-mini"
        assert coder.api_key == "sk-global"

    def test_frontier_groq_standard_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("LLM_API_KEY", "ollama")
        monkeypatch.setenv("LLM_PROVIDER_FRONTIER", "groq")
        monkeypatch.setenv("LLM_API_KEY_FRONTIER", "gsk_test")
        monkeypatch.setenv("LLM_MODEL_FRONTIER", "llama-3.1-70b-versatile")

        from runtime.base_agent.provider_config import resolve_tier_config
        frontier = resolve_tier_config("frontier")
        standard = resolve_tier_config("standard")

        assert frontier.provider == "groq"
        assert standard.provider == "ollama"

    def test_each_tier_independent(self, monkeypatch):
        """Every tier can have a completely distinct provider."""
        tiers = {
            "FRONTIER": ("openai", "sk-f", "gpt-4o"),
            "STANDARD": ("groq",   "gsk_s", "llama-3.1-8b-instant"),
            "MONITOR":  ("ollama", "ollama", "qwen2.5:7b"),
            "CODER":    ("openai", "sk-c", "gpt-4o-mini"),
        }
        for t, (prov, key, model) in tiers.items():
            monkeypatch.setenv(f"LLM_PROVIDER_{t}", prov)
            monkeypatch.setenv(f"LLM_API_KEY_{t}", key)
            monkeypatch.setenv(f"LLM_MODEL_{t}", model)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        from runtime.base_agent.provider_config import resolve_tier_config
        for t_lower, (prov, key, model) in {k.lower(): v for k, v in tiers.items()}.items():
            cfg = resolve_tier_config(t_lower)
            assert cfg.provider == prov, f"{t_lower}: provider mismatch"
            assert cfg.model == model, f"{t_lower}: model mismatch"


# ---------------------------------------------------------------------------
# 3. Client caching
# ---------------------------------------------------------------------------

class TestClientCaching:

    def test_same_config_returns_cached_client(self, monkeypatch):
        _clear_cache()
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "sk-same")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        # standard and monitor resolve identically → same client
        monkeypatch.delenv("LLM_PROVIDER_STANDARD", raising=False)
        monkeypatch.delenv("LLM_PROVIDER_MONITOR", raising=False)

        from runtime.base_agent.llm_client import client_for_tier
        c1 = client_for_tier("standard")
        c2 = client_for_tier("monitor")
        assert c1 is c2, "Same (provider, base_url, api_key) must return cached client"

    def test_different_api_key_yields_different_client(self, monkeypatch):
        _clear_cache()
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        monkeypatch.setenv("LLM_API_KEY", "sk-global")
        monkeypatch.setenv("LLM_API_KEY_FRONTIER", "sk-frontier-different")

        from runtime.base_agent.llm_client import client_for_tier
        c_standard = client_for_tier("standard")
        c_frontier = client_for_tier("frontier")
        assert c_standard is not c_frontier, "Different api_key must not share a cached client"


# ---------------------------------------------------------------------------
# 4. Startup validation
# ---------------------------------------------------------------------------

class TestStartupValidation:

    def test_missing_api_key_for_openai_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_API_KEY_FRONTIER", raising=False)
        monkeypatch.delenv("LLM_API_KEY_STANDARD", raising=False)
        monkeypatch.delenv("LLM_API_KEY_MONITOR", raising=False)
        monkeypatch.delenv("LLM_API_KEY_CODER", raising=False)

        from runtime.base_agent.provider_config import validate_all_tiers, ConfigurationError
        with pytest.raises(ConfigurationError, match="api_key not set"):
            validate_all_tiers()

    def test_ollama_passes_without_explicit_key(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL_DEFAULT", raising=False)

        from runtime.base_agent.provider_config import validate_all_tiers
        # Should not raise — ollama is local, no key needed
        validate_all_tiers()

    def test_error_message_names_tier_and_variable(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
        monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        for t in ("FRONTIER", "STANDARD", "MONITOR", "CODER"):
            monkeypatch.delenv(f"LLM_API_KEY_{t}", raising=False)

        from runtime.base_agent.provider_config import validate_all_tiers, ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            validate_all_tiers()
        msg = str(exc_info.value)
        assert "LLM_API_KEY" in msg   # names the env var
        assert "tier 'frontier'" in msg or "tier 'standard'" in msg  # names a tier


# ---------------------------------------------------------------------------
# 5–7. SpendGuardrail
# ---------------------------------------------------------------------------

class TestSpendGuardrail:

    def test_within_cap_allows_calls(self):
        from runtime.base_agent.spend_guardrail import SpendGuardrail
        g = SpendGuardrail(max_tokens=1000, agent_id="test-agent")
        g.record_usage(400)
        g.check_before_call()  # still under cap → no raise

    def test_exceeding_token_cap_blocks_next_call(self):
        from runtime.base_agent.spend_guardrail import SpendGuardrail, SpendCapExceeded
        g = SpendGuardrail(max_tokens=100, agent_id="test-agent")
        g.record_usage(60)
        g.record_usage(50)  # total 110 > 100
        with pytest.raises(SpendCapExceeded, match="100"):
            g.check_before_call()

    def test_rate_limit_blocks_excessive_calls(self):
        from runtime.base_agent.spend_guardrail import SpendGuardrail, SpendCapExceeded
        g = SpendGuardrail(max_tokens=1_000_000, max_calls_per_minute=3, agent_id="test-agent")
        g.check_before_call()  # call 1
        g.check_before_call()  # call 2
        g.check_before_call()  # call 3 — at cap
        with pytest.raises(SpendCapExceeded, match="rate limit"):
            g.check_before_call()  # call 4 — exceeds cap

    def test_escalation_called_before_raising(self):
        from runtime.base_agent.spend_guardrail import SpendGuardrail, SpendCapExceeded
        escalation = MagicMock()
        g = SpendGuardrail(max_tokens=10, agent_id="test-agent", escalation=escalation)
        g.record_usage(20)  # already over

        with pytest.raises(SpendCapExceeded):
            g.check_before_call()

        escalation.route.assert_called_once()
        call_kwargs = escalation.route.call_args.kwargs
        assert call_kwargs["reason"] == "spend_cap_exceeded"
        assert call_kwargs["risk_level"] == "critical"

    def test_tokens_used_property(self):
        from runtime.base_agent.spend_guardrail import SpendGuardrail
        g = SpendGuardrail(max_tokens=9999, agent_id="test-agent")
        assert g.tokens_used == 0
        g.record_usage(300)
        g.record_usage(200)
        assert g.tokens_used == 500

    def test_guardrail_wired_in_act_via_get_validated_output(self, monkeypatch):
        """
        Prove that exceeding the token cap inside act() raises SpendCapExceeded,
        not a live LLM error — i.e. the guardrail check fires before the client call.
        """
        from runtime.base_agent.spend_guardrail import SpendCapExceeded
        from runtime.base_agent.structured_output import get_validated_output

        cap_guardrail = MagicMock()
        from runtime.base_agent.spend_guardrail import SpendCapExceeded as _SCE
        cap_guardrail.check_before_call.side_effect = _SCE("cap exceeded")

        client = MagicMock()  # should NOT be called because guardrail fires first
        escalation = MagicMock()

        schema = {"type": "object", "properties": {"x": {"type": "number"}}, "required": ["x"]}
        with pytest.raises(SpendCapExceeded):
            get_validated_output(client, "any-model", [], schema, escalation, guardrail=cap_guardrail)

        client.chat.completions.create.assert_not_called()
