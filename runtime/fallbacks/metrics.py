"""Fallback metrics adapter declarations."""


def json_metrics_fallback() -> dict:
    return {
        "name": "json_metrics_writer",
        "replaces": "prometheus_grafana",
        "classification": "fallback",
        "simulated": False,
        "persistence": "reports/system_run/latest",
        "production_allowed": False,
    }
