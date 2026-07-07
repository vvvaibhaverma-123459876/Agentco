from __future__ import annotations

import os
import sys
from pathlib import Path


DEFAULT_RESERVE_TEST_DSN = "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"


def reserve_test_dsn(test_file: str) -> str:
    """Return an isolated reserve test DSN or raise before psycopg2 can use OS defaults."""
    dsn = os.environ.get("AGENTCO_TEST_DATABASE_URL") or DEFAULT_RESERVE_TEST_DSN
    sys.path.insert(0, str(Path(test_file).resolve().parents[2]))
    from pg_test_isolation import isolated_dsn

    isolated = isolated_dsn(dsn)
    if not isolated:
        raise RuntimeError(
            "reserve tests require AGENTCO_TEST_DATABASE_URL or the explicit reserve "
            "test DSN; refusing to call psycopg2.connect(None), which defaults to "
            "the OS username database"
        )
    return isolated
