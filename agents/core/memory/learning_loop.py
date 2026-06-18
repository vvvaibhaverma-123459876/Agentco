"""Experiential learning loop for persistent agent memories."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
import psycopg2.extras

from .memory_writer import MemoryWriter


def _dsn(db_url: Optional[str] = None) -> str:
    return db_url or os.environ.get(
        "AGENTCO_TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco"),
    )


def _connect(db_url: Optional[str] = None):
    conn = psycopg2.connect(_dsn(db_url))
    conn.autocommit = True
    return conn


class LearningLoop:
    """Turns episodic memories into reusable semantic memories."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = _dsn(db_url)
        self.writer = MemoryWriter(self.db_url)

    async def extract_lessons_from_recent(
        self,
        agent_id: str,
        since_hours: int = 24,
    ) -> list[str]:
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, domain, summary, content
                      FROM agent_memories
                     WHERE agent_id=%s
                       AND namespace=%s
                       AND memory_type='episodic'
                       AND created_at >= %s
                       AND superseded_by IS NULL
                     ORDER BY created_at DESC
                    """,
                    (agent_id, agent_id, since),
                )
                episodes = [dict(row) for row in cur.fetchall()]

        memory_ids = []
        for episode in episodes:
            content = dict(episode["content"])
            findings = content.get("key_findings") or []
            if findings:
                fact = str(findings[0])
            elif episode.get("summary"):
                fact = f"Past task outcome: {episode['summary']}"
            else:
                continue
            memory_id = await self.writer.write_semantic(
                agent_id=agent_id,
                fact=fact,
                evidence_from=[str(episode["id"])],
                confidence=float(content.get("confidence_in_output") or 0.6),
                domain=episode.get("domain") or "general",
            )
            memory_ids.append(memory_id)
        return memory_ids

    async def consolidate_semantic_memories(
        self,
        agent_id: str,
        domain: str,
    ) -> Optional[str]:
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, summary, content, importance
                      FROM agent_memories
                     WHERE agent_id=%s
                       AND namespace=%s
                       AND memory_type='semantic'
                       AND domain=%s
                       AND superseded_by IS NULL
                     ORDER BY created_at ASC
                    """,
                    (agent_id, agent_id, domain),
                )
                rows = [dict(row) for row in cur.fetchall()]
        if len(rows) < 5:
            return None

        facts = [row["summary"] for row in rows]
        confidence = min(1.0, sum(float(row["importance"] or 0.5) for row in rows) / len(rows) + 0.1)
        consolidated = await self.writer.write_semantic(
            agent_id=agent_id,
            fact="; ".join(facts),
            evidence_from=[str(row["id"]) for row in rows],
            confidence=confidence,
            domain=domain,
        )
        with _connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_memories
                       SET superseded_by=%s
                     WHERE id = ANY(%s::uuid[])
                    """,
                    (consolidated, [str(row["id"]) for row in rows]),
                )
        return consolidated

    async def cross_agent_lesson_sharing(
        self,
        source_agent_id: str,
        lesson_memory_id: str,
        target_agent_ids: list[str],
    ) -> list[str]:
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT memory_type, domain, summary, content, importance
                      FROM agent_memories
                     WHERE id=%s AND agent_id=%s
                    """,
                    (lesson_memory_id, source_agent_id),
                )
                source = cur.fetchone()
        if not source:
            return []

        shared_ids = []
        for target_agent_id in target_agent_ids:
            content = dict(source["content"])
            content["shared_from_agent_id"] = source_agent_id
            content["source_memory_id"] = lesson_memory_id
            with _connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO agent_memories
                            (agent_id, memory_type, namespace, domain, summary, content, importance)
                        VALUES (%s, %s, 'shared', %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            target_agent_id,
                            source["memory_type"],
                            source["domain"],
                            source["summary"],
                            psycopg2.extras.Json(content),
                            float(source["importance"] or 0.5),
                        ),
                    )
                    shared_ids.append(str(cur.fetchone()[0]))
        return shared_ids
