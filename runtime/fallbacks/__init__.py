"""Explicit fallback adapter metadata for AgentCo runtime checks."""


def fallback(name: str, replaces: str, simulated: bool = False) -> dict:
    return {
        "name": name,
        "replaces": replaces,
        "status": "fallback",
        "simulated": simulated,
        "production_allowed": False,
    }


def in_process_event_bus() -> dict:
    return fallback("in_process_event_bus", "kafka")


def memory_cache() -> dict:
    return fallback("memory_cache", "redis")


def env_secret_provider() -> dict:
    return fallback("env_secret_provider", "vault")


def json_metrics_writer() -> dict:
    return fallback("json_metrics_writer", "prometheus_grafana")


def file_backed_ledger() -> dict:
    return fallback("file_backed_smoke_ledger", "postgres", simulated=True)


def deterministic_llm() -> dict:
    return fallback("deterministic_fixture_llm", "openai", simulated=True)
