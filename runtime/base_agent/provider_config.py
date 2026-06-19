"""
Per-tier LLM provider configuration.

Resolves (provider, base_url, api_key, model) for each tier from environment variables.
The AGENT_TIER map (which agent maps to which tier) stays in model_tiers.py — that's
a stable property of the agent. This module owns the deployment question: which
provider+model serves a tier.

Resolution order (highest priority first) for tier T:
  1. LLM_PROVIDER_<T> / LLM_BASE_URL_<T> / LLM_API_KEY_<T>
  2. LLM_PROVIDER     / LLM_BASE_URL     / LLM_API_KEY
  3. built-in defaults per provider

Model resolution follows the selected provider scope:
  LLM_MODEL_<T> -> LLM_MODEL_DEFAULT -> provider tier default
  If a leaked tier model is clearly incompatible with the selected provider
  (for example, ollama-style "mistral:7b" with provider "openai"), the global
  default wins.

OpenAI-compatible providers (use OpenAI SDK with base_url, no adapter):
  openai, ollama, together, fireworks, groq, openrouter, deepseek, mistral, anyscale

Native-adapter providers (different wire format, thin adapter translates):
  anthropic   — uses anthropic SDK; adapter in anthropic_adapter.py
  google      — NOT YET SUPPORTED; raises ConfigurationError
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

OPENAI_COMPATIBLE_PROVIDERS = frozenset({
    "openai", "ollama", "together", "fireworks", "groq",
    "openrouter", "deepseek", "mistral", "anyscale",
})
NATIVE_ADAPTER_PROVIDERS = frozenset({"anthropic"})
UNSUPPORTED_PROVIDERS = frozenset({"google"})

_VALID_TIERS = ("frontier", "standard", "monitor", "coder")

# Default base URLs per provider when LLM_BASE_URL is not set
_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai":     "https://api.openai.com/v1",
    "anthropic":  "https://api.anthropic.com",
    "ollama":     "http://localhost:11434/v1",
    "together":   "https://api.together.xyz/v1",
    "fireworks":  "https://api.fireworks.ai/inference/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek":   "https://api.deepseek.com/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "anyscale":   "https://api.endpoints.anyscale.com/v1",
}

# Default api_key per provider (only for keyless local providers)
_DEFAULT_API_KEYS: dict[str, str] = {
    "ollama": "ollama",
}

# Default models per tier per provider (used when neither tier-level nor global model is set)
_DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "openai":    {"frontier": "gpt-4o",  "standard": "gpt-4o-mini", "monitor": "gpt-4o-mini", "coder": "gpt-4o-mini"},
    "anthropic": {"frontier": "claude-sonnet-4-6", "standard": "claude-haiku-4-5-20251001",
                  "monitor": "claude-haiku-4-5-20251001", "coder": "claude-sonnet-4-6"},
    "ollama":    {"frontier": "phi4", "standard": "qwen2.5:7b", "monitor": "qwen2.5:7b", "coder": "qwen2.5-coder:7b"},
    "groq":      {"frontier": "llama-3.1-70b-versatile", "standard": "llama-3.1-8b-instant",
                  "monitor": "llama-3.1-8b-instant", "coder": "llama-3.1-70b-versatile"},
}
_DEFAULT_MODELS_FALLBACK = {"frontier": "gpt-4o", "standard": "gpt-4o-mini",
                             "monitor": "gpt-4o-mini", "coder": "gpt-4o-mini"}


class ConfigurationError(RuntimeError):
    """Raised on missing or invalid LLM configuration."""


@dataclass(frozen=True)
class TierConfig:
    """Fully-resolved configuration for one tier."""
    tier: str
    provider: str
    base_url: str
    api_key: str
    model: str

    @property
    def is_openai_compatible(self) -> bool:
        return self.provider in OPENAI_COMPATIBLE_PROVIDERS


def _model_is_compatible(provider: str, model: str) -> bool:
    """Reject only obvious cross-provider leftovers from the local shell."""
    if provider == "openai" and ":" in model:
        return False
    return True


def resolve_tier_config(tier: str) -> TierConfig:
    """
    Resolve the (provider, base_url, api_key, model) for *tier* from environment variables.

    Resolution order:
      provider/base_url/api_key: LLM_<FIELD>_<TIER> → LLM_<FIELD> → built-in default
      model: LLM_MODEL_<TIER> → LLM_MODEL_DEFAULT → provider tier default
    """
    if tier not in _VALID_TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Valid: {_VALID_TIERS}")
    T = tier.upper()

    tier_provider = os.environ.get(f"LLM_PROVIDER_{T}")
    global_provider = os.environ.get("LLM_PROVIDER")
    provider = tier_provider or global_provider or "openai"

    if provider in UNSUPPORTED_PROVIDERS:
        raise ConfigurationError(
            f"Provider '{provider}' is not yet supported. "
            f"OpenAI-compatible: {sorted(OPENAI_COMPATIBLE_PROVIDERS)}. "
            f"Native-adapter: {sorted(NATIVE_ADAPTER_PROVIDERS)}."
        )

    base_url = (
        os.environ.get(f"LLM_BASE_URL_{T}")
        or os.environ.get("LLM_BASE_URL")
        or _DEFAULT_BASE_URLS.get(provider, "")
    )

    api_key = (
        os.environ.get(f"LLM_API_KEY_{T}")
        or os.environ.get("LLM_API_KEY")
        or _DEFAULT_API_KEYS.get(provider, "")
    )

    provider_defaults = _DEFAULT_MODELS.get(provider, _DEFAULT_MODELS_FALLBACK)
    tier_model = os.environ.get(f"LLM_MODEL_{T}")
    global_model = os.environ.get("LLM_MODEL_DEFAULT")
    if tier_model and _model_is_compatible(provider, tier_model):
        model = tier_model
    elif global_model and _model_is_compatible(provider, global_model):
        model = global_model
    else:
        model = provider_defaults.get(tier, "gpt-4o-mini")

    return TierConfig(tier=tier, provider=provider, base_url=base_url, api_key=api_key, model=model)


def validate_all_tiers() -> None:
    """
    Validate the resolved config for every tier.  Call this at startup to fail fast
    rather than discovering missing config on the first live LLM call.

    Skips validation for 'ollama' provider (local, no key required by convention).
    Raises ConfigurationError listing ALL missing fields, not just the first.
    """
    errors: list[str] = []
    for tier in _VALID_TIERS:
        try:
            cfg = resolve_tier_config(tier)
        except ConfigurationError as exc:
            errors.append(f"  tier '{tier}': {exc}")
            continue

        if cfg.provider == "ollama":
            # Local provider — base_url and key are optional (have defaults)
            if not cfg.model:
                errors.append(
                    f"  tier '{tier}': model not set "
                    f"(set LLM_MODEL_{tier.upper()} or LLM_MODEL_DEFAULT)"
                )
            continue

        if not cfg.api_key:
            errors.append(
                f"  tier '{tier}': api_key not set "
                f"(set LLM_API_KEY_{tier.upper()} or LLM_API_KEY)"
            )
        if not cfg.base_url:
            errors.append(
                f"  tier '{tier}': base_url not set "
                f"(set LLM_BASE_URL_{tier.upper()} or LLM_BASE_URL)"
            )
        if not cfg.model:
            errors.append(
                f"  tier '{tier}': model not set "
                f"(set LLM_MODEL_{tier.upper()} or LLM_MODEL_DEFAULT)"
            )

    if errors:
        raise ConfigurationError(
            "LLM configuration errors (fix before running agents):\n" + "\n".join(errors)
        )
