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
        for tbl in ["causal_links", "trust_lineage", "entity_genealogy", "memory_summaries", "lessons", "precedents", "rulings", "disputes"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/009_disputes.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/012_civilization_memory.sql").read_text())
        cur.execute("INSERT INTO disputes (id, dispute_type, plaintiff_id, defendant_id, status) VALUES ('d1', 'false_claim', 'p', 'd', 'final')")
        cur.execute("INSERT INTO rulings (id, dispute_id, judge_entity_id, ruling, appeal_deadline) VALUES ('r1', 'd1', 'j', 'ruling', NOW())")
    yield conn
    conn.close()


def test_precedent_lesson_and_summary_trace_sources(db) -> None:
    from civilization.services.civilization_memory_service import create_precedent_from_final_ruling, extract_lesson, summarize_memory

    assert create_precedent_from_final_ruling("r1", "false_claim", "False claims require penalty", db)
    assert extract_lesson(["e1", "e2"], "Repeated failures require supervision", db)
    assert summarize_memory(["e1", "e2"], "Two raw events summarized", db)


def test_genealogy_and_trust_lineage_traceable(db) -> None:
    from civilization.services.civilization_memory_service import record_genealogy, record_trust_lineage

    assert record_genealogy("institution", "child", "split", db, parent_entity_id="parent", obligations={"debt": 1})
    assert record_trust_lineage("claim-1", db, agent_id="agent", institution_id="inst", society_id="soc", civilization_id="civ", source_refs=["source"])


def test_manual_memory_injection_cannot_alter_authority(db) -> None:
    from civilization.services.civilization_memory_service import inject_memory_without_authority_change

    summary_id = inject_memory_without_authority_change("manual note", db)
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memory_summaries WHERE id = %s", (summary_id,))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM trust_lineage")
        assert cur.fetchone()[0] == 0
