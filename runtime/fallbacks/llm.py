"""Fallback LLM adapter declarations."""


def deterministic_llm_fallback() -> dict:
    return {
        "name": "deterministic_fixture_llm",
        "replaces": "openai",
        "classification": "simulated",
        "simulated": True,
        "persistence": "none",
        "production_allowed": False,
    }
