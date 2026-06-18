from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

from agents.core.memory import LearningLoop, MemoryReader, MemoryWriter
from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="real Postgres required")


@pytest.fixture()
def memory_db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS agent_memories CASCADE;")
        cur.execute((ROOT / "backend/src/db/migrations/015_agent_memories_lifecycle.sql").read_text())
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
        cur.execute((ROOT / "backend/src/db/migrations/011_prediction_ledger.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/001_reserve_extension.sql").read_text())
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    yield
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS agent_memories CASCADE;")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
    conn.close()


def _run(coro):
    return asyncio.run(coro)


def _prediction(agent_id="research-agent", domain="tech_news"):
    return PredictionRegistration(
        claim="The memory lifecycle test will resolve successfully",
        probability=0.8,
        confidence_basis={"basis": "integration test"},
        producing_agent_id=agent_id,
        producing_prompt_version="test",
        resolution_criterion="test assertion passes",
        resolution_date=datetime.now(timezone.utc) - timedelta(days=1),
        ground_truth_source="external_test_harness",
        horizon_class="short",
        domain=domain,
        claim_type="system_reliability",
    )


def test_memory_schema_is_append_only(memory_db):
    writer = MemoryWriter(DSN)
    memory_id = _run(
        writer.write_episodic(
            agent_id="agent-a",
            task_id="task-1",
            task_type="scan",
            task_input="scan source",
            task_output_summary="found one claim",
            predictions_registered=[],
            sources_consulted=[],
            key_findings=["claim found"],
            errors_encountered=[],
            confidence_in_output=0.7,
            duration_seconds=1.0,
            tokens_used=10,
            domain="tech_news",
        )
    )

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute("UPDATE agent_memories SET summary='mutated' WHERE id=%s", (memory_id,))
        conn.rollback()
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute("DELETE FROM agent_memories WHERE id=%s", (memory_id,))
        conn.rollback()

        replacement = _run(
            writer.write_episodic(
                agent_id="agent-a",
                task_id="task-2",
                task_type="scan",
                task_input="scan source",
                task_output_summary="corrected claim",
                predictions_registered=[],
                sources_consulted=[],
                key_findings=["corrected"],
                errors_encountered=[],
                confidence_in_output=0.8,
                duration_seconds=1.0,
                tokens_used=10,
                domain="tech_news",
            )
        )
        cur.execute("UPDATE agent_memories SET superseded_by=%s WHERE id=%s", (replacement, memory_id))
        cur.execute("SELECT superseded_by FROM agent_memories WHERE id=%s", (memory_id,))
        assert str(cur.fetchone()[0]) == replacement
    conn.close()


def test_writer_reader_and_namespace_isolation(memory_db):
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)
    _run(
        writer.write_episodic(
            "agent-a", "task-a", "scan", "input", "agent A found a claim",
            [], [], ["A finding"], [], 0.7, 2.0, 50, "tech_news",
        )
    )
    _run(
        writer.write_episodic(
            "agent-b", "task-b", "scan", "input", "agent B private claim",
            [], [], ["B finding"], [], 0.7, 2.0, 50, "tech_news",
        )
    )

    memories = _run(reader.retrieve_relevant("agent-a", "scan claims", domain="tech_news"))
    summaries = [m["summary"] for m in memories]
    assert "agent A found a claim" in summaries
    assert "agent B private claim" not in summaries

    timed = _run(reader.retrieve_relevant("agent-a", "scan claims", timeout_ms=1))
    assert isinstance(timed, list)


def test_prediction_lesson_track_record_and_prompt(memory_db):
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    ledger = PredictionLedger(db=conn)
    pid = ledger.pre_register(_prediction())
    with conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
        cur.execute(
            """
            UPDATE prediction_ledger
               SET resolved=true,
                   resolved_outcome=true,
                   resolved_at=NOW(),
                   resolved_by_service='test',
                   brier_score=0.04,
                   log_score=-0.22
             WHERE prediction_id=%s
            """,
            (pid,),
        )
    conn.close()

    _run(
        writer.write_prediction_lesson(
            "research-agent", pid, "memory lifecycle succeeds", 0.8, True, -0.22,
            "The integration path is reliable when migrations are applied first.",
            "system_reliability is well covered",
            "future confidence can be slightly higher",
            "tech_news",
        )
    )
    track = _run(reader.get_agent_track_record_summary("research-agent", "tech_news"))
    assert track["total_predictions"] == 1
    assert track["resolved"] == 1
    assert track["correct"] == 1
    prompt = reader.format_for_system_prompt([], track)
    assert "1 predictions" in prompt
    assert "integration path is reliable" in prompt


def test_semantic_duplicate_supersedes_old_memory(memory_db):
    writer = MemoryWriter(DSN)
    first = _run(writer.write_semantic("research-agent", "Pricing changes resolve slowly", ["p1"], 0.6, "tech_news"))
    second = _run(writer.write_semantic("research-agent", "Pricing changes resolve slowly", ["p2"], 0.8, "tech_news"))
    assert first != second

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT superseded_by FROM agent_memories WHERE id=%s", (first,))
        assert str(cur.fetchone()[0]) == second
    conn.close()


def test_learning_loop_extracts_consolidates_and_shares(memory_db):
    writer = MemoryWriter(DSN)
    loop = LearningLoop(DSN)
    for i in range(5):
        _run(
            writer.write_episodic(
                "research-agent", f"task-{i}", "scan", "input",
                f"episode {i}", [], [], [f"Reusable fact {i}"], [], 0.7, 1.0, 20, "tech_news",
            )
        )
    extracted = _run(loop.extract_lessons_from_recent("research-agent", since_hours=24))
    assert len(extracted) >= 1

    consolidated = _run(loop.consolidate_semantic_memories("research-agent", "tech_news"))
    assert consolidated is not None

    shared = _run(loop.cross_agent_lesson_sharing("research-agent", consolidated, ["ceo-agent"]))
    assert len(shared) == 1
    reader = MemoryReader(DSN)
    memories = _run(reader.retrieve_relevant("ceo-agent", "tech news strategy", "tech_news"))
    assert any(m["namespace"] == "shared" for m in memories)


def test_full_memory_lifecycle_trace(memory_db):
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)

    first_memories = _run(reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news"))
    first_track = _run(reader.get_agent_track_record_summary("research-agent", "tech_news"))
    first_prompt = reader.format_for_system_prompt(first_memories, first_track)
    assert "No previous experience" in first_prompt

    first_episode = _run(
        writer.write_episodic(
            "research-agent", "run-1", "internet_prediction_scan",
            "scan sources for resolvable claims",
            "found 2 claims and registered 1 prediction",
            ["pred-1"], ["https://example.test"], ["Example launch claim"], [], 0.82, 4.0, 120, "tech_news",
        )
    )

    second_memories = _run(reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news"))
    second_prompt = reader.format_for_system_prompt(second_memories, first_track)
    assert "Example launch claim" in second_prompt or "found 2 claims" in second_prompt

    lesson_id = _run(
        writer.write_prediction_lesson(
            "research-agent", "pred-1", "Example launch claim resolves true",
            0.8, True, -0.22,
            "Well-sourced launch claims can be tracked with high confidence.",
            "tech_news claims need source diversity",
            "raise confidence only after independent confirmation",
            "tech_news",
        )
    )
    third_memories = _run(reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news"))
    third_prompt = reader.format_for_system_prompt(third_memories, first_track)
    assert "Well-sourced launch claims" in third_prompt

    loop = LearningLoop(DSN)
    semantic_ids = _run(loop.extract_lessons_from_recent("research-agent"))
    shared_ids = _run(loop.cross_agent_lesson_sharing("research-agent", lesson_id, ["ceo-agent"]))
    ceo_memories = _run(reader.retrieve_relevant("ceo-agent", "tech news planning", "tech_news"))
    assert semantic_ids
    assert shared_ids
    assert any("Well-sourced launch claims" in m["summary"] for m in ceo_memories)

    trace = ROOT / "evals/acceptance/memory_lifecycle_trace.md"
    trace.write_text(
        "\n".join([
            "# Memory Lifecycle Trace",
            "",
            "First run prompt contained: No previous experience.",
            f"First episodic memory: `{first_episode}`.",
            "Second run prompt contained prior finding: Example launch claim.",
            f"Prediction lesson memory: `{lesson_id}`.",
            "Third run prompt contained prediction lesson: Well-sourced launch claims.",
            f"Semantic memories extracted: {len(semantic_ids)}.",
            f"Shared memories written for ceo-agent: {len(shared_ids)}.",
        ]) + "\n"
    )
