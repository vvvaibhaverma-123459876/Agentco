"""
Phase A — Independent Recomputation Test.

Proves that any third party can reproduce a stored credential's score from raw
public prediction_ledger rows using only the published algorithm.  No access to
the signing key, no reuse of the in-memory score object.

This is the proof that "independently recomputable" means more than "the same
process can call the function twice" — it means an entirely separate code path,
starting from raw DB rows, converges to identical numbers.

Test environment: real Postgres (AGENTCO_TEST_DATABASE_URL must be set).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set — real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Fixture — fresh tables with Reserve extension applied
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE")
        cur.execute("DROP TABLE IF EXISTS resolution_evidence_snapshots CASCADE")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE")
        cur.execute((ROOT / "backend/src/db/migrations/011_prediction_ledger.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/001_reserve_extension.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/004_ed25519_signature.sql").read_text())
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
        cur.execute((ROOT / "backend/src/db/migrations/017_resolution_evidence_snapshots.sql").read_text())
    yield conn
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE")
        cur.execute("DROP TABLE IF EXISTS resolution_evidence_snapshots CASCADE")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE")
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _register_and_resolve(db, agent_id: str, n: int, probability: float, outcome: bool) -> list[str]:
    """Register n predictions and resolve them all via the resolution_service role."""
    from calibration import create_calibration_engine
    cal = create_calibration_engine(db=db)
    past = datetime.now(timezone.utc) - timedelta(days=2)

    pids = []
    for i in range(n):
        pid = cal["ledger"].pre_register(
            __import__(
                "calibration.ledger.prediction_ledger",
                fromlist=["PredictionRegistration"],
            ).PredictionRegistration(
                claim=f"recomputation test claim {i}",
                probability=probability,
                confidence_basis={"basis": "test"},
                producing_agent_id=agent_id,
                producing_prompt_version="1.0.0",
                resolution_criterion="test criterion",
                resolution_date=past,
                ground_truth_source="external_test",
                horizon_class="short",
                domain="testing",
                claim_type="forecast",
            )
        )
        pids.append(pid)

    # Resolve as resolution_service
    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    res_cal = create_calibration_engine(db=res_conn)

    for pid in pids:
        rec = cal["ledger"].get(pid)
        if res_cal["ledger"].get(pid) is None:
            res_cal["ledger"]._in_memory[pid] = rec
        res_cal["resolution"].resolve(
            prediction_id=pid,
            outcome=outcome,
            ground_truth_source="external_test",
            evidence={"source": "recomputation_test"},
        )
        res_cal["ledger"].persist_resolution(res_cal["ledger"].get(pid))
    res_conn.close()

    # Refresh primary ledger cache
    cal["ledger"]._in_memory.clear()
    cal["ledger"]._load_from_db()
    return pids


def _issue_and_persist_credential(db, agent_id: str):
    """Issue and persist a credential via the normal engine path."""
    from calibration import create_calibration_engine
    from reserve import create_reserve_engine

    cal = create_calibration_engine(db=db)
    engine = create_reserve_engine(ledger=cal["ledger"], db=db)
    # refresh_credential() already calls persist_credential internally.
    return engine.refresh_credential(agent_id)


def _raw_recompute_from_db(db, agent_id: str) -> dict:
    """
    Independent recomputation path.

    Reads RAW prediction_ledger rows and applies the published algorithm.
    Does NOT import the in-memory ReserveScore or credential objects.
    Uses ONLY: psycopg2 cursor + the standalone recompute() from
    reserve/tools/recompute_credential.py (which itself has no secret deps).
    """
    # Import the reference recomputer (the standalone, public tool).
    sys.path.insert(0, str(ROOT))
    from reserve.tools.recompute_credential import _fetch_rows, recompute  # type: ignore[import]
    rows = _fetch_rows(DSN, agent_id)
    return recompute(rows)


# ---------------------------------------------------------------------------
# The actual test
# ---------------------------------------------------------------------------
def test_stored_credential_score_matches_independent_recomputation(db):
    """
    Issues a credential via the normal path, then recomputes the score from
    raw DB rows via an independent code path.  Asserts every numeric field
    matches to 8 decimal places — proving the operator cannot embed a
    different score than what the ledger rows dictate.
    """
    agent_id = "recomputation-proof-agent"
    _register_and_resolve(db, agent_id, n=5, probability=0.75, outcome=True)

    # --- Path 1: normal issuance (uses in-memory objects) ---
    cred = _issue_and_persist_credential(db, agent_id)

    # --- Path 2: independent recomputation (raw rows → published algorithm) ---
    recomputed = _raw_recompute_from_db(db, agent_id)

    # --- Assert they match field for field ---
    assert abs(cred.overall_log_score - recomputed["overall_log_score"]) < 1e-8, (
        f"overall_log_score mismatch: credential={cred.overall_log_score} "
        f"recomputed={recomputed['overall_log_score']}"
    )
    assert abs(cred.overall_brier_score - recomputed["overall_brier_score"]) < 1e-8, (
        f"overall_brier_score mismatch"
    )
    assert cred.sample_count == recomputed["total_sample_count"], (
        f"sample_count mismatch: credential={cred.sample_count} "
        f"recomputed={recomputed['total_sample_count']}"
    )
    assert cred.algorithm == recomputed["algorithm"], "algorithm string mismatch"

    # Per-cell comparison
    assert len(cred.cells) == len(recomputed["cells"]), "cell count mismatch"
    for stored_cell in cred.cells:
        rc = next(
            (c for c in recomputed["cells"]
             if c["domain"] == stored_cell.domain
             and c["horizon_class"] == stored_cell.horizon_class),
            None,
        )
        assert rc is not None, f"recomputed missing cell ({stored_cell.domain}, {stored_cell.horizon_class})"
        assert abs(stored_cell.weighted_log_score - rc["weighted_log_score"]) < 1e-8
        assert abs(stored_cell.weighted_brier_score - rc["weighted_brier_score"]) < 1e-8
        assert stored_cell.sample_count == rc["sample_count"]

    # Emit trace data for evals/acceptance/recomputation_trace.md
    print("\n[recomputation] agent_id:", agent_id)
    print("[recomputation] sample_count:", cred.sample_count)
    print("[recomputation] credential overall_log_score:", round(cred.overall_log_score, 8))
    print("[recomputation] recomputed  overall_log_score:", round(recomputed["overall_log_score"], 8))
    print("[recomputation] MATCH: True (delta < 1e-8)")
    print("[recomputation] algorithm:", cred.algorithm)
    print("[recomputation] cells stored:", [(c.domain, c.horizon_class, round(c.weighted_log_score, 6)) for c in cred.cells])
    print("[recomputation] cells recomp:", [(c["domain"], c["horizon_class"], round(c["weighted_log_score"], 6)) for c in recomputed["cells"]])
