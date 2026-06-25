"""Fallback event bus adapter declarations."""


def in_process_event_bus_fallback() -> dict:
    return {
        "name": "in_process_event_bus",
        "replaces": "kafka",
        "classification": "fallback",
        "simulated": False,
        "persistence": "process_memory",
        "production_allowed": False,
    }
