"""Fallback secret provider adapter declarations."""


def env_secret_provider_fallback() -> dict:
    return {
        "name": "env_secret_provider",
        "replaces": "vault",
        "classification": "fallback",
        "simulated": False,
        "persistence": "environment",
        "production_allowed": False,
    }
