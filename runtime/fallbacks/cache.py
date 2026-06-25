"""Fallback cache adapter declarations."""


def memory_cache_fallback() -> dict:
    return {
        "name": "memory_cache",
        "replaces": "redis",
        "classification": "fallback",
        "simulated": False,
        "persistence": "process_memory",
        "production_allowed": False,
    }
