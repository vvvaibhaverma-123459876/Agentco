"""LLM Provider configuration - imports from runtime."""

from runtime.base_agent.provider_config import (
    ConfigurationError,
    TierConfig,
    resolve_tier_config,
    validate_all_tiers,
)

def get_model(tier: str = "standard") -> str:
    """Get the model name for a tier."""
    config = resolve_tier_config(tier)
    return config.model

def get_config(tier: str = "standard") -> TierConfig:
    """Get the full configuration for a tier."""
    return resolve_tier_config(tier)

def resolve_provider(tier: str = "standard") -> str:
    """Get the provider for a tier."""
    config = resolve_tier_config(tier)
    return config.provider

__all__ = [
    "ConfigurationError",
    "TierConfig",
    "resolve_tier_config",
    "validate_all_tiers",
    "get_model",
    "get_config",
    "resolve_provider",
]
