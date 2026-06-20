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
        for tbl in [
            "civilization_constitution_memory_events", "emergency_states", "constitutional_amendments", "laws",
            "constitution_versions", "civilization_society_edges", "civilizations",
            "society_reputation_snapshots", "society_memory_events", "society_governance_decisions",
            "society_contracts", "society_institution_edges", "societies",
            "agent_membership_edges", "institution_contracts", "institution_output_reviews",
            "civilization_memory_events", "governance_decisions", "departments", "institutions",
        ]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/006_civilization.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/007_society.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/011_civilization_constitution.sql").read_text())
        cur.execute("INSERT INTO societies (id, name, domain) VALUES ('soc-1', 'Engineering Society', 'engineering')")
    yield conn
    conn.close()


def _civ(db) -> str:
    from civilization.services.civilization_service import create_civilization

    return create_civilization("Agentco Civilization", "founder", "external-approval", 2, {"invariants": ["calibration"]}, db)


def test_civilization_created_and_society_admitted_constitutionally(db) -> None:
    from civilization.services.civilization_service import admit_society

    civ_id = _civ(db)
    amendment_id = admit_society(civ_id, "soc-1", "founder", "external-approval", 2, db)
    assert amendment_id


def test_constitution_version_adopted_and_invalid_amendment_rejected(db) -> None:
    from civilization.services.civilization_service import CivilizationError, adopt_constitution_version

    civ_id = _civ(db)
    with pytest.raises(CivilizationError, match="invalid amendment"):
        adopt_constitution_version(civ_id, "v2", {}, "founder", "", 1, db)
    version_id = adopt_constitution_version(civ_id, "v2", {"rights": ["agents"]}, "founder", "external-approval", 2, db)
    assert version_id


def test_emergency_blocks_high_risk_and_requires_expiry(db) -> None:
    from civilization.services.civilization_service import CivilizationError, declare_emergency, high_risk_blocked_by_emergency

    civ_id = _civ(db)
    with pytest.raises(CivilizationError, match="future expiry"):
        declare_emergency(civ_id, "bad", "operator", datetime.now(timezone.utc) - timedelta(minutes=1), db)
    declare_emergency(civ_id, "global risk", "operator", datetime.now(timezone.utc) + timedelta(hours=1), db)
    assert high_risk_blocked_by_emergency(civ_id, db) is True


def test_cross_society_dispute_binding_and_self_judge_rejected(db) -> None:
    from civilization.services.civilization_service import CivilizationError, constitutional_dispute

    civ_id = _civ(db)
    assert constitutional_dispute(civ_id, "soc-a", "soc-b", "constitutional-court", db) == "binding"
    with pytest.raises(CivilizationError, match="judges its own"):
        constitutional_dispute(civ_id, "soc-a", "soc-b", "soc-b", db)


def test_law_and_memory_records_created(db) -> None:
    from civilization.services.civilization_service import create_law

    civ_id = _civ(db)
    law_id = create_law(civ_id, "SAFETY-1", "Global Safety Law", "No self-certification.", db)
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM laws WHERE id = %s", (law_id,))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT event_type FROM civilization_constitution_memory_events WHERE civilization_id = %s", (civ_id,))
        events = {r[0] for r in cur.fetchall()}
    assert {"constitution_adopted", "law_created"}.issubset(events)
