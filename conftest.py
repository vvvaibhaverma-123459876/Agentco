"""
Root pytest configuration.

Puts both the repository root and the agents/ package directory on sys.path so
tests resolve `runtime.*`, `calibration.*`, `learning.*`, `synthesis.*` (rooted
at the repo) and the V1 `core.*` / `executive.*` packages (rooted at agents/),
regardless of whether pytest is invoked from the repo root or from agents/.

Also ensures DATABASE_URL is set for all tests that hit real Postgres.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, ROOT / "agents"):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)

# Set DATABASE_URL from AGENTCO_TEST_DATABASE_URL if available, otherwise use
# the correct local default (port 5432).  This runs at collection time so every
# module that reads os.environ["DATABASE_URL"] at import or fixture setup sees
# the right value without needing a manual export.
_DEFAULT_DB_URL = "postgresql://agentco:password@localhost:5432/agentco"
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = os.environ.get(
        "AGENTCO_TEST_DATABASE_URL", _DEFAULT_DB_URL
    )
os.environ.setdefault("AGENTCO_TEST_AUDIT_WRITER", "1")
# In the sandbox the server listens on port 5433 via Unix socket /tmp.
# Rewrite the URL so tests connect to the running instance without any
# manual export.  AGENTCO_TEST_DATABASE_URL always takes precedence if set.
if "AGENTCO_TEST_DATABASE_URL" not in os.environ:
    import psycopg2 as _pg
    try:
        _pg.connect(os.environ["DATABASE_URL"]).close()
    except Exception:
        # Standard port unreachable — try the sandbox socket URL
        _sandbox_url = "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"
        try:
            _pg.connect(_sandbox_url).close()
            os.environ["DATABASE_URL"] = _sandbox_url
        except Exception:
            pass  # leave DATABASE_URL as-is; tests will skip or fail with a clear error


# ---------------------------------------------------------------------------
# Live-LLM test gating (clean-room integrity).
#
# Tests that require a live LLM provider must be marked with
# @pytest.mark.live_llm. They are skipped unless RUN_REAL_LLM_TESTS=1 AND a
# provider credential is configured. This mirrors the backend Jest convention
# so `make test` / `make master-gate` pass on machines without keys, while
# live suites remain runnable explicitly.
# ---------------------------------------------------------------------------
import pytest as _pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_llm: test requires a live LLM provider; opt in with "
        "RUN_REAL_LLM_TESTS=1 and provider credentials",
    )
    config.addinivalue_line(
        "markers",
        "live_web: test requires live internet access; opt in with RUN_REAL_WEB_TESTS=1",
    )


def _live_llm_enabled() -> bool:
    if os.environ.get("RUN_REAL_LLM_TESTS") != "1":
        return False
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def pytest_collection_modifyitems(config, items):
    skip_llm = _pytest.mark.skip(
        reason="live LLM test skipped: set RUN_REAL_LLM_TESTS=1 with provider credentials"
    )
    skip_web = _pytest.mark.skip(
        reason="live web test skipped: set RUN_REAL_WEB_TESTS=1"
    )
    for item in items:
        if "live_llm" in item.keywords and not _live_llm_enabled():
            item.add_marker(skip_llm)
        if "live_web" in item.keywords and os.environ.get("RUN_REAL_WEB_TESTS") != "1":
            item.add_marker(skip_web)
