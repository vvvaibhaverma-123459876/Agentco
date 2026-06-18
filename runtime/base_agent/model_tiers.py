"""
Agent-to-tier map — the STABLE property of each agent.

WHAT THIS MODULE OWNS:
  AGENT_TIER   — maps agent_id → tier name.  This is a deployment-invariant
                 property of the agent; it does not change when you switch provider.
  tier_for()   — look up which tier an agent belongs to.
  model_for()  — look up the model name for an agent (reads from env-driven config).

WHAT THIS MODULE DOES NOT OWN:
  Which model/provider serves a tier — that lives in provider_config.py and
  is resolved from environment variables.  Changing provider or model is a
  config edit, never a code edit here.

Backward-compatible export:
  MODEL_TIERS  — dict-like object where MODEL_TIERS[tier] → resolved model name.
                 Reads from env vars on every access so monkeypatch works in tests.
"""
from __future__ import annotations

from runtime.base_agent.provider_config import resolve_tier_config

# ---------------------------------------------------------------------------
# Agent → tier assignment  (stable; never changes for deployed code)
# ---------------------------------------------------------------------------
AGENT_TIER: dict[str, str] = {
    # Strategic / synthesis / calibration-reasoning
    "ceo-agent":           "frontier",
    "synthesis-agent":     "frontier",
    "config-agent":        "frontier",
    "calibration-reasoner":"frontier",
    # Coding
    "coder-agent":         "coder",
    "reviewer-agent":      "coder",
    # High-frequency monitors
    "support-agent":       "monitor",
    "performance-agent":   "monitor",
    # Everything else → "standard"
}

_VALID_TIERS = ("frontier", "standard", "monitor", "coder")


def tier_for(agent_id: str) -> str:
    """Return the tier name for *agent_id* (defaults to 'standard')."""
    return AGENT_TIER.get(agent_id, "standard")


def model_for(agent_id: str) -> str:
    """
    Return the model name for *agent_id*, resolved from config.

    Reads LLM_MODEL_<TIER> (or LLM_MODEL_DEFAULT) so any model change is a
    config edit, not a code edit.
    """
    tier = tier_for(agent_id)
    return resolve_tier_config(tier).model


# ---------------------------------------------------------------------------
# Backward-compatible MODEL_TIERS dict-like export
# ---------------------------------------------------------------------------
class _LazyTierModels:
    """
    Reads tier→model from env vars on every access.
    Supports MODEL_TIERS["frontier"] and MODEL_TIERS.items() used in tests.
    """
    _TIERS = _VALID_TIERS

    def __getitem__(self, tier: str) -> str:
        return resolve_tier_config(tier).model

    def __iter__(self):
        return iter(self._TIERS)

    def items(self):
        return [(t, self[t]) for t in self._TIERS]

    def __contains__(self, tier: object) -> bool:
        return tier in self._TIERS


MODEL_TIERS: _LazyTierModels = _LazyTierModels()
