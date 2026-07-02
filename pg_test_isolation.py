"""
Isolated-database helper for destructive Postgres test fixtures.

Several Python suites rebuild civilization tables (institutions, departments,
decision_log, prediction_ledger, ...) from the reserve migration set, whose
schema intentionally differs from the backend migration chain. Running them
against the shared backend database silently replaces backend-migrated tables
and breaks every backend suite that runs afterwards.

These fixtures must therefore run in their own database. `isolated_dsn`
derives a sibling database from the configured test DSN (``<dbname>_pyciv``),
creates it on first use, and returns a DSN pointing at it.
"""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def isolated_dsn(base_dsn: str, suffix: str = "pyciv") -> str:
    """Return a DSN for an isolated sibling database, creating it if needed."""
    import psycopg2

    parsed = urlparse(base_dsn)
    base_name = parsed.path.lstrip("/") or "postgres"
    isolated_name = f"{base_name}_{suffix}"

    conn = psycopg2.connect(base_dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (isolated_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{isolated_name}"')
    finally:
        conn.close()

    return urlunparse(parsed._replace(path=f"/{isolated_name}"))
