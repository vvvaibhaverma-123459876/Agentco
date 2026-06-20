from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in ["penalties", "precedents", "appeals", "rulings", "dispute_evidence", "disputes"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/009_disputes.sql").read_text())
    yield conn
    conn.close()


def test_dispute_opened_from_challenge_and_evidence_submitted(db) -> None:
    from civilization.services.dispute_service import open_dispute_from_challenge, submit_evidence

    dispute_id = open_dispute_from_challenge("review-1", "plaintiff", "defendant", db, critical=True)
    evidence_id = submit_evidence(dispute_id, "plaintiff", {"hash": "abc"}, db)
    assert dispute_id and evidence_id


def test_conflicted_judge_rejected_ruling_appeal_and_precedent(db) -> None:
    from civilization.services.dispute_service import (
        DisputeError,
        finalize_dispute,
        issue_ruling,
        open_dispute,
        submit_appeal,
    )

    dispute_id = open_dispute("false_claim", "plaintiff", "defendant", db)
    with pytest.raises(DisputeError, match="conflicted"):
        issue_ruling(dispute_id, "defendant", "liable", {}, db)
    ruling_id = issue_ruling(dispute_id, "judge", "defendant liable", {"defendant": {"type": "reputation", "amount": -0.2}}, db)
    appeal_id = submit_appeal(ruling_id, "defendant", "new evidence", db)
    precedent_id = finalize_dispute(dispute_id, db)
    assert ruling_id and appeal_id and precedent_id


def test_late_appeal_rejected_and_penalty_recorded(db) -> None:
    from civilization.services.dispute_service import DisputeError, issue_ruling, open_dispute, submit_appeal

    dispute_id = open_dispute("security_failure", "plaintiff", "defendant", db)
    ruling_id = issue_ruling(dispute_id, "judge", "liable", {"defendant": {"type": "budget", "amount": -1}}, db, appeal_window_hours=1)
    with db.cursor() as cur:
        cur.execute("UPDATE rulings SET appeal_deadline = %s WHERE id = %s", (datetime.now(timezone.utc) - timedelta(minutes=1), ruling_id))
    with pytest.raises(DisputeError, match="late appeal"):
        submit_appeal(ruling_id, "defendant", "too late", db)
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM penalties WHERE dispute_id = %s", (dispute_id,))
        assert cur.fetchone()[0] == 1


def test_unresolved_critical_dispute_blocks_release(db) -> None:
    from civilization.services.dispute_service import critical_dispute_blocks_release, finalize_dispute, issue_ruling, open_dispute_from_challenge

    dispute_id = open_dispute_from_challenge("output-1", "plaintiff", "defendant", db, critical=True)
    assert critical_dispute_blocks_release("output-1", db) is True
    issue_ruling(dispute_id, "judge", "resolved", {}, db)
    finalize_dispute(dispute_id, db)
    assert critical_dispute_blocks_release("output-1", db) is False
