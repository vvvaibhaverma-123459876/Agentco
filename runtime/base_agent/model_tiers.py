"""
Model-tier map — single source of truth for agent→model assignment.
All models are local open-weight models served via Ollama (Apache-2.0 / MIT licensed).
Swap providers by changing these values; no agent code needs to change.
"""

MODEL_TIERS: dict[str, str] = {
    # Strategic / synthesis / calibration-reasoning  (was claude-opus-4-x)
    "frontier": "phi4",
    # Standard department agents  (was claude-sonnet-4-x)
    "standard": "qwen2.5:7b",
    # High-frequency monitors  (was claude-haiku)
    "monitor": "qwen2.5:7b",
    # Coding agents
    "coder": "qwen2.5-coder:7b",
}

# Explicit per-agent tier overrides; everything else defaults to "standard".
AGENT_TIER: dict[str, str] = {
    "ceo-agent": "frontier",
    "synthesis-agent": "frontier",
    "config-agent": "frontier",
    "calibration-reasoner": "frontier",
    "coder-agent": "coder",
    "reviewer-agent": "coder",
    "support-agent": "monitor",
    "performance-agent": "monitor",
}


def model_for(agent_id: str) -> str:
    """Return the Ollama model name for the given agent."""
    tier = AGENT_TIER.get(agent_id, "standard")
    return MODEL_TIERS[tier]
