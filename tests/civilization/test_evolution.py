from __future__ import annotations

import os
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
        for tbl in ["lifecycle_events", "society_lifecycle", "institution_lifecycle"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/013_lifecycle_evolution.sql").read_text())
    yield conn
    conn.close()


def test_trial_required_and_high_risk_blocked_until_active(db) -> None:
    from civilization.services.evolution_service import EvolutionError, activate_after_trial, high_risk_allowed, start_trial

    assert high_risk_allowed("inst-1", db) is False
    with pytest.raises(EvolutionError, match="trial period"):
        activate_after_trial("inst-1", "external", db)
    start_trial("inst-1", "external", db)
    assert high_risk_allowed("inst-1", db) is False
    activate_after_trial("inst-1", "external", db)
    assert high_risk_allowed("inst-1", db) is True


def test_low_reputation_probation_suspension_and_retirement_memory(db) -> None:
    from civilization.services.evolution_service import institution_state, low_reputation_triggers_probation, retire_institution, suspend_institution

    low_reputation_triggers_probation("inst-1", -3.0, -2.0, db)
    assert institution_state("inst-1", db)["lifecycle_state"] == "probation"
    suspend_institution("inst-1", "critical failure", db)
    assert institution_state("inst-1", db)["lifecycle_state"] == "suspended"
    retire_institution("inst-1", "obsolete", db)
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM lifecycle_events WHERE entity_id = 'inst-1' AND event_type = 'retired'")
        assert cur.fetchone()[0] == 1


def test_merge_transfers_obligations_and_split_preserves_lineage(db) -> None:
    from civilization.services.evolution_service import merge_institutions, split_institution

    merge_institutions(["old-a", "old-b"], "new", {"debt": 2}, db)
    split_institution("parent", ["child-a", "child-b"], db)
    with db.cursor() as cur:
        cur.execute("SELECT event_type FROM lifecycle_events")
        events = {r[0] for r in cur.fetchall()}
    assert {"merge_obligation_transferred", "split_lineage_preserved"}.issubset(events)


def test_self_admission_rejected(db) -> None:
    from civilization.services.evolution_service import EvolutionError, start_trial

    with pytest.raises(EvolutionError, match="self-admission"):
        start_trial("inst-1", "inst-1", db)
