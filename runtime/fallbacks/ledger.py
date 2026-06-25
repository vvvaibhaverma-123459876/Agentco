"""Fallback ledger adapter declarations."""


def file_backed_ledger_fallback() -> dict:
    return {
        "name": "file_backed_smoke_ledger",
        "replaces": "postgres_prediction_ledger",
        "classification": "fallback",
        "simulated": True,
        "persistence": "reports/system_run/latest",
        "production_allowed": False,
    }
