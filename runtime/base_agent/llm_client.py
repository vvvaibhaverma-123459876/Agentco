"""
LLM client factory — per-tier, config-driven.

Public API
----------
client_for(agent_id)  → correctly-configured client for that agent's tier
client_for_tier(tier) → correctly-configured client for a tier directly
make_client(...)      → backward-compatible global client (uses global LLM_* vars)
clear_client_cache()  → reset cached clients (useful in tests)

Provider routing
----------------
OpenAI-compatible providers (use OpenAI SDK with base_url):
  openai, ollama, together, fireworks, groq, openrouter, deepseek, mistral, anyscale

Native-adapter providers (different wire protocol, adapter in anthropic_adapter.py):
  anthropic → _AnthropicAdapter wraps anthropic.Anthropic()

For a full provider list, see provider_config.OPENAI_COMPATIBLE_PROVIDERS.

Client caching
--------------
Clients are cached per (provider, base_url, api_key) key so we don't rebuild
a network-heavy client object on every agent call.  Call clear_client_cache()
to force rebuild (e.g. after rotating keys at runtime).
"""
from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from runtime.base_agent.provider_config import (
    NATIVE_ADAPTER_PROVIDERS,
    TierConfig,
    resolve_tier_config,
)
from runtime.base_agent.model_tiers import tier_for

# Cache: (provider, base_url, api_key) → client object
_CLIENT_CACHE: dict[tuple[str, str, str], Any] = {}


def client_for(agent_id: str) -> Any:
    """Return the correctly-configured LLM client for *agent_id*'s tier."""
    return client_for_tier(tier_for(agent_id))


def client_for_tier(tier: str) -> Any:
    """Return the correctly-configured LLM client for *tier*."""
    cfg = resolve_tier_config(tier)
    return _get_or_build(cfg)


def make_client(
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenAI:
    """
    Backward-compatible global client factory.
    Uses explicit args first, then LLM_BASE_URL / LLM_API_KEY env vars.
    Prefer client_for(agent_id) for new code.
    """
    resolved_url = base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    resolved_key = api_key or os.environ.get("LLM_API_KEY", "ollama")
    cache_key = ("openai-compat", resolved_url, resolved_key)
    if cache_key not in _CLIENT_CACHE:
        _CLIENT_CACHE[cache_key] = OpenAI(base_url=resolved_url, api_key=resolved_key)
    return _CLIENT_CACHE[cache_key]


def clear_client_cache() -> None:
    """Invalidate all cached clients (e.g. after key rotation or in tests)."""
    _CLIENT_CACHE.clear()


# ---------------------------------------------------------------------------
# Internal builder
# ---------------------------------------------------------------------------

def _get_or_build(cfg: TierConfig) -> Any:
    cache_key = (cfg.provider, cfg.base_url, cfg.api_key)
    if cache_key in _CLIENT_CACHE:
        return _CLIENT_CACHE[cache_key]

    if cfg.provider in NATIVE_ADAPTER_PROVIDERS:
        client = _build_native(cfg)
    else:
        # All OpenAI-compatible providers: just set base_url + api_key
        client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)

    _CLIENT_CACHE[cache_key] = client
    return client


def _build_native(cfg: TierConfig) -> Any:
    if cfg.provider == "anthropic":
        from runtime.base_agent.anthropic_adapter import build as build_anthropic
        return build_anthropic(api_key=cfg.api_key)
    # Future: google, etc.
    from runtime.base_agent.provider_config import ConfigurationError
    raise ConfigurationError(f"No native adapter implemented for provider '{cfg.provider}'")
