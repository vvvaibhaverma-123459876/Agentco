"""
E2E memory lifecycle test — real Postgres, no mocks.

Proves the complete memory pipeline:
  experience → episodic capture → lesson extraction → semantic distillation
  → cross-agent sharing → informed future runs.

All writer/reader/learning-loop methods are synchronous (psycopg2).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

from agents.core.memory import LearningLoop, MemoryReader, MemoryWriter
from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration

ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if DSN:
    try:
        from pg_test_isolation import isolated_dsn

        # Destructive fixture: run in an isolated sibling database so shared
        # backend-migrated tables are never replaced with this suite's schema.
        DSN = isolated_dsn(DSN)
    except Exception:
        DSN = None  # Postgres unreachable; the skip guard below handles it
pytestmark = pytest.mark.skipif(not DSN, reason="real Postgres required")

# Lesson extraction/consolidation call a live LLM (chat + embeddings). Those
# tests are opt-in so a clean environment without working provider credentials
# skips them honestly instead of failing on provider 404s.
RUN_REAL_LLM = os.environ.get("RUN_REAL_LLM_TESTS") == "1"
requires_llm = pytest.mark.skipif(
    not RUN_REAL_LLM,
    reason="requires a live LLM provider; set RUN_REAL_LLM_TESTS=1 with working credentials",
)

_MIGRATION_015 = ROOT / "backend/src/db/migrations/015_agent_memories.sql"
_MIGRATION_011 = ROOT / "backend/src/db/migrations/011_prediction_ledger.sql"
_MIGRATION_RESERVE = ROOT / "reserve/migrations/001_reserve_extension.sql"


def _table_exists(conn, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
            (name,),
        )
        return cur.fetchone() is not None


@pytest.fixture()
def memory_db():
    """
    Prepare clean agent_memories for each test.

    agent_memories is created if absent, then truncated.
    prediction_ledger is created only if it doesn't already exist — it is a
    shared table; we never drop it.
    All teardown only truncates agent_memories rows.
    """
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Ensure agent_memories exists (idempotent — uses IF NOT EXISTS + CREATE OR REPLACE)
        cur.execute(_MIGRATION_015.read_text())
        cur.execute("TRUNCATE agent_memories CASCADE;")

        # Ensure prediction_ledger exists (skip if already present to avoid trigger conflicts)
        if not _table_exists(conn, "prediction_ledger"):
            cur.execute(_MIGRATION_011.read_text())

        # Ensure reserve tables exist
        try:
            cur.execute(_MIGRATION_RESERVE.read_text())
        except Exception:
            pass  # already exists — ignore

        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        try:
            cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
            cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
        except Exception:
            pass
    yield
    with conn.cursor() as cur:
        cur.execute("TRUNCATE agent_memories CASCADE;")
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Schema / immutability
# ─────────────────────────────────────────────────────────────────────────────

def test_memory_schema_is_append_only(memory_db):
    """T2.3 + T2.4 + T2.5: summary/content immutable; DELETE blocked; superseded_by allowed."""
    writer = MemoryWriter(DSN)
    memory_id = writer.write_episodic(
        agent_id="agent-a", task_id="task-1", task_type="scan",
        task_input="scan source", task_output_summary="found one claim",
        predictions_registered=[], sources_consulted=[],
        key_findings=["claim found"], errors_encountered=[],
        confidence_in_output=0.7, duration_seconds=1.0, tokens_used=10,
        domain="tech_news",
    )

    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    with conn.cursor() as cur:
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute("UPDATE agent_memories SET summary='mutated' WHERE id=%s::uuid", (memory_id,))
        conn.rollback()
        with pytest.raises(psycopg2.errors.RaiseException):
            cur.execute("DELETE FROM agent_memories WHERE id=%s::uuid", (memory_id,))
        conn.rollback()

        replacement = writer.write_episodic(
            agent_id="agent-a", task_id="task-2", task_type="scan",
            task_input="scan source", task_output_summary="corrected claim",
            predictions_registered=[], sources_consulted=[],
            key_findings=["corrected"], errors_encountered=[],
            confidence_in_output=0.8, duration_seconds=1.0, tokens_used=10,
            domain="tech_news",
        )
        cur.execute(
            "UPDATE agent_memories SET superseded_by=%s::uuid WHERE id=%s::uuid",
            (replacement, memory_id),
        )
        conn.commit()
        cur.execute("SELECT superseded_by FROM agent_memories WHERE id=%s::uuid", (memory_id,))
        assert str(cur.fetchone()[0]) == replacement
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Writer
# ─────────────────────────────────────────────────────────────────────────────

def test_writer_episodic_and_namespace_isolation(memory_db):
    """T3.1 + T2.6: write episodic; namespace isolation prevents cross-agent reads."""
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)

    writer.write_episodic(
        "agent-a", "task-a", "scan", "input", "agent A found a claim",
        [], [], ["A finding"], [], 0.7, 2.0, 50, "tech_news",
    )
    writer.write_episodic(
        "agent-b", "task-b", "scan", "input", "agent B private claim",
        [], [], ["B finding"], [], 0.7, 2.0, 50, "tech_news",
    )

    memories = reader.retrieve_relevant("agent-a", "scan claims", domain="tech_news")
    summaries = [m["summary"] for m in memories]
    assert any("agent A" in s for s in summaries), "agent-a's episodic missing"
    assert not any("agent B private" in s for s in summaries), "agent-b's namespace leaked"


def test_writer_prediction_lesson(memory_db):
    """T3.2: write_prediction_lesson produces a DB row linked to a prediction_id."""
    writer = MemoryWriter(DSN)
    mid = writer.write_prediction_lesson(
        "research-agent", "pred-001",
        claim="X will happen", stated_confidence=0.8,
        actual_outcome=True, log_score=-0.22,
        lesson="well calibrated", domain_insight="tech predictions reliable",
        calibration_adjustment="none needed", domain="tech_news",
    )
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT prediction_id, memory_type FROM agent_memories WHERE id=%s::uuid", (mid,))
        row = cur.fetchone()
    conn.close()
    assert row[0] == "pred-001"
    assert row[1] == "prediction_lesson"


def test_writer_semantic_supersedes_duplicate(memory_db):
    """T3.3: duplicate semantic fact supersedes old memory via superseded_by."""
    writer = MemoryWriter(DSN)
    first = writer.write_semantic(
        "research-agent", "Pricing changes resolve slowly", ["p1"], 0.6, "tech_news"
    )
    second = writer.write_semantic(
        "research-agent", "Pricing changes resolve slowly", ["p2"], 0.8, "tech_news"
    )
    assert first != second
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT superseded_by FROM agent_memories WHERE id=%s::uuid", (first,))
        assert str(cur.fetchone()[0]) == second
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Reader
# ─────────────────────────────────────────────────────────────────────────────

def test_reader_retrieve_and_timeout(memory_db):
    """T4.1 + T4.2: retrieve returns memories; 1ms timeout does not block."""
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)
    for i in range(3):
        writer.write_episodic(
            "research-agent", f"task-r{i}", "scan", f"input {i}", f"summary {i}",
            [], [], [f"finding {i}"], [], 0.7, 1.0, 10, "tech_news",
        )
    writer.write_prediction_lesson(
        "research-agent", f"pred-r0", "claim", 0.7, True, -0.3,
        "lesson text", "insight", "adjustment", "tech_news"
    )

    mems = reader.retrieve_relevant("research-agent", "scan for tech predictions", domain="tech_news")
    assert len(mems) >= 1
    for m in mems:
        assert m["agent_id"] == "research-agent"

    # access_count must have incremented
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM agent_memories WHERE agent_id='research-agent' AND access_count > 0"
        )
        assert cur.fetchone()[0] >= 1
    conn.close()

    fast = reader.retrieve_relevant("research-agent", "anything", timeout_ms=1)
    assert isinstance(fast, list)  # no raise, no block


def test_reader_track_record_and_format(memory_db):
    """T4.3 + T4.4: track_record aggregates ledger; format_for_system_prompt < 6000 chars."""
    import uuid as _uuid
    # Unique agent_id per run so prediction_ledger rows don't bleed across test sessions
    agent_id = f"track-record-agent-{_uuid.uuid4().hex[:8]}"
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    ledger = PredictionLedger(db=conn)
    reg = PredictionRegistration(
        claim="test claim", probability=0.8,
        confidence_basis={"basis": "test"},
        producing_agent_id=agent_id,
        producing_prompt_version="test",
        resolution_criterion="test passes",
        resolution_date=datetime.now(timezone.utc) - timedelta(days=1),
        ground_truth_source="test_harness",
        horizon_class="short", domain="tech_news", claim_type="general",
    )
    pid = ledger.pre_register(reg)
    with conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
        cur.execute(
            "UPDATE prediction_ledger SET resolved=true, resolved_outcome=true, "
            "resolved_at=NOW(), resolved_by_service='test', brier_score=0.04, log_score=-0.22 "
            "WHERE prediction_id=%s",
            (pid,),
        )
    conn.close()

    writer.write_prediction_lesson(
        agent_id, pid, "test claim resolves", 0.8, True, -0.22,
        "the integration path is reliable", "system_reliability covered",
        "future confidence can be slightly higher", "tech_news",
    )

    track = reader.get_agent_track_record_summary(agent_id, "tech_news")
    assert track["total_predictions"] == 1
    assert track["resolved"] == 1
    assert track["correct"] == 1
    assert track["average_log_score"] is not None

    mems = reader.retrieve_relevant(agent_id, "tech predictions", domain="tech_news")
    prompt = reader.format_for_system_prompt(mems, track)
    assert len(prompt) <= 6000
    assert "1 predictions" in prompt
    assert "integration path is reliable" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# T6 — Learning loop
# ─────────────────────────────────────────────────────────────────────────────

@requires_llm
def test_learning_loop_extracts_lessons(memory_db):
    """T6.1: extract_lessons_from_recent produces at least one semantic memory."""
    writer = MemoryWriter(DSN)
    loop = LearningLoop(DSN)
    for i in range(3):
        writer.write_episodic(
            "research-agent", f"loop-task-{i}", "scan", "input",
            f"episode {i}: found reusable tech fact about pricing changes",
            [], [], [f"Reusable tech fact {i}"], [], 0.7, 1.0, 20, "tech_news",
        )
    extracted = loop.extract_lessons_from_recent("research-agent", since_hours=24)
    assert len(extracted) >= 1, f"Expected >=1 semantic memories, got {extracted}"


@requires_llm
def test_learning_loop_consolidates_semantics(memory_db):
    """T6.2: consolidate_semantic_memories collapses 5 memories to 1."""
    writer = MemoryWriter(DSN)
    loop = LearningLoop(DSN)
    for i in range(5):
        # Use clearly different facts so no Jaccard dedup triggers on write
        writer.write_semantic(
            "research-agent", f"Tech pricing fact number {i} about quarterly changes",
            [], 0.6 + i * 0.02, "tech_news",
        )
    consolidated = loop.consolidate_semantic_memories("research-agent", "tech_news")
    assert consolidated is not None, "Expected a consolidated memory"

    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM agent_memories "
            "WHERE agent_id='research-agent' AND memory_type='semantic' AND superseded_by IS NOT NULL"
        )
        superseded = cur.fetchone()[0]
    conn.close()
    assert superseded >= 4, f"Expected >=4 originals superseded, got {superseded}"


def test_learning_loop_cross_agent_sharing(memory_db):
    """T6.3: research-agent shares lesson with ceo-agent; ceo-agent retrieves it."""
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)
    loop = LearningLoop(DSN)

    lesson_id = writer.write_semantic(
        "research-agent",
        "Well-sourced launch claims resolve TRUE 80%+ of the time",
        [], 0.8, "tech_news",
    )
    shared_ids = loop.cross_agent_lesson_sharing("research-agent", lesson_id, ["ceo-agent"])
    assert len(shared_ids) == 1

    ceo_mems = reader.retrieve_relevant("ceo-agent", "tech news strategy", domain="tech_news")
    assert any(m.get("namespace") == "shared" for m in ceo_mems), \
        f"ceo-agent did not receive shared memory; got: {[m.get('namespace') for m in ceo_mems]}"


# ─────────────────────────────────────────────────────────────────────────────
# T7 — Full lifecycle (Step 7)
# ─────────────────────────────────────────────────────────────────────────────

@requires_llm
def test_full_memory_lifecycle_trace(memory_db):
    """
    End-to-end proof:
      run 1 → no memory → episodic written
      run 2 → prior finding in prompt
      prediction resolved → lesson written
      run 3 → lesson in prompt
      learning loop → semantic distilled
      cross-agent sharing → ceo-agent informed
    """
    writer = MemoryWriter(DSN)
    reader = MemoryReader(DSN)

    # Run 1: no prior memories
    first_memories = reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news")
    first_track = reader.get_agent_track_record_summary("research-agent", "tech_news")
    first_prompt = reader.format_for_system_prompt(first_memories, first_track)
    assert "No previous experience" in first_prompt, f"Expected first-run message, got: {first_prompt}"

    first_episode = writer.write_episodic(
        "research-agent", "run-1", "internet_prediction_scan",
        "scan sources for resolvable claims",
        "found 2 claims and registered 1 prediction",
        ["pred-1"], ["https://example.test"], ["Example launch claim"], [],
        0.82, 4.0, 120, "tech_news",
    )

    # Run 2: prior experience visible
    second_memories = reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news")
    second_prompt = reader.format_for_system_prompt(second_memories, first_track)
    assert ("Example launch claim" in second_prompt or "found 2 claims" in second_prompt), \
        f"Run 2 prompt missing prior findings. Got: {second_prompt}"

    # Resolve prediction → lesson
    lesson_id = writer.write_prediction_lesson(
        "research-agent", "pred-1", "Example launch claim resolves true",
        0.8, True, -0.22,
        "Well-sourced launch claims can be tracked with high confidence.",
        "tech_news claims need source diversity",
        "raise confidence only after independent confirmation",
        "tech_news",
    )

    # Run 3: lesson also visible
    third_memories = reader.retrieve_relevant("research-agent", "internet prediction scan", "tech_news")
    third_track = reader.get_agent_track_record_summary("research-agent", "tech_news")
    third_prompt = reader.format_for_system_prompt(third_memories, third_track)
    assert "Well-sourced launch claims" in third_prompt, \
        f"Run 3 prompt missing lesson. Got: {third_prompt}"

    # Learning loop: extract semantics + share with ceo-agent
    loop = LearningLoop(DSN)
    semantic_ids = loop.extract_lessons_from_recent("research-agent", since_hours=24)
    shared_ids = loop.cross_agent_lesson_sharing("research-agent", lesson_id, ["ceo-agent"])
    ceo_memories = reader.retrieve_relevant("ceo-agent", "tech news planning", "tech_news")

    assert semantic_ids, "No semantic memories extracted from episodes"
    assert shared_ids, "No shared memories written for ceo-agent"
    assert any("Well-sourced launch claims" in m["summary"] for m in ceo_memories), \
        f"ceo-agent missing shared lesson. Memories: {[m['summary'][:60] for m in ceo_memories]}"

    # Write trace
    trace = ROOT / "evals/acceptance/memory_lifecycle_trace.md"
    trace.write_text(
        "# Memory Lifecycle Trace\n\n"
        "First run prompt contained: No previous experience.\n"
        f"First episodic memory: `{first_episode}`.\n"
        "Second run prompt contained prior finding: Example launch claim.\n"
        f"Prediction lesson memory: `{lesson_id}`.\n"
        "Third run prompt contained prediction lesson: Well-sourced launch claims.\n"
        f"Semantic memories extracted: {len(semantic_ids)}.\n"
        f"Shared memories written for ceo-agent: {len(shared_ids)}.\n"
    )
