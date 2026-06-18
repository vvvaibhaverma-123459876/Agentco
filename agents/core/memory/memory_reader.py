"""Memory retrieval and prompt formatting for AgentCo agents."""
from __future__ import annotations

import concurrent.futures
import os
from datetime import datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras


def _dsn(db_url: Optional[str] = None) -> str:
    return db_url or os.environ.get(
        "AGENTCO_TEST_DATABASE_URL",
        os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco"),
    )


def _connect(db_url: Optional[str] = None):
    conn = psycopg2.connect(_dsn(db_url))
    conn.autocommit = True
    return conn


class MemoryReader:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = _dsn(db_url)

    async def retrieve_relevant(
        self,
        agent_id: str,
        task_description: str,
        domain: Optional[str] = None,
        limit: int = 10,
        timeout_ms: int = 500,
    ) -> list[dict]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self._retrieve_sync, agent_id, task_description, domain, limit
            )
            try:
                return future.result(timeout=timeout_ms / 1000)
            except concurrent.futures.TimeoutError:
                return []
            except Exception:
                return []

    async def get_agent_track_record_summary(
        self,
        agent_id: str,
        domain: Optional[str] = None,
    ) -> dict:
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                params = [agent_id]
                domain_clause = ""
                if domain:
                    domain_clause = "AND domain=%s"
                    params.append(domain)
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS total_predictions,
                           COUNT(*) FILTER (WHERE resolved) AS resolved,
                           COUNT(*) FILTER (WHERE resolved AND resolved_outcome) AS correct,
                           AVG(log_score) FILTER (WHERE resolved) AS average_log_score
                      FROM prediction_ledger
                     WHERE producing_agent_id=%s {domain_clause}
                    """,
                    params,
                )
                row = cur.fetchone() or {}

                lesson_params = [agent_id]
                lesson_domain_clause = ""
                if domain:
                    lesson_domain_clause = "AND domain=%s"
                    lesson_params.append(domain)
                cur.execute(
                    f"""
                    SELECT summary
                      FROM agent_memories
                     WHERE agent_id=%s
                       AND memory_type='prediction_lesson'
                       AND superseded_by IS NULL
                       {lesson_domain_clause}
                     ORDER BY created_at DESC
                     LIMIT 5
                    """,
                    lesson_params,
                )
                lessons = [r["summary"] for r in cur.fetchall()]

        total = int(row.get("total_predictions") or 0)
        resolved = int(row.get("resolved") or 0)
        correct = int(row.get("correct") or 0)
        avg_log = row.get("average_log_score")
        return {
            "agent_id": agent_id,
            "domain": domain or "all",
            "total_predictions": total,
            "resolved": resolved,
            "correct": correct,
            "average_log_score": float(avg_log) if avg_log is not None else None,
            "trusted_confidence": None,
            "recent_lessons": lessons,
        }

    def format_for_system_prompt(self, memories: list[dict], track_record: dict) -> str:
        domain = track_record.get("domain", "all")
        if not memories and not track_record.get("total_predictions"):
            return f"No previous experience in this domain ({domain})."

        lines = ["Agent memory context:"]
        lines.append(
            "Track record: "
            f"{track_record.get('total_predictions', 0)} predictions, "
            f"{track_record.get('resolved', 0)} resolved, "
            f"{track_record.get('correct', 0)} correct"
        )
        if track_record.get("average_log_score") is not None:
            lines[-1] += f", avg_log_score={track_record['average_log_score']:.4f}"

        lessons = track_record.get("recent_lessons", [])
        if lessons:
            lines.append("Recent lessons:")
            lines.extend(f"- {lesson[:240]}" for lesson in lessons[:5])

        if memories:
            lines.append("Relevant past experience:")
            for memory in memories[:10]:
                lines.append(
                    f"- [{memory.get('memory_type')}/{memory.get('domain')}] "
                    f"{str(memory.get('summary', ''))[:240]}"
                )

        text = "\n".join(lines)
        words = text.split()
        if len(words) > 1500:
            text = " ".join(words[:1500])
        return text

    def _retrieve_sync(
        self,
        agent_id: str,
        task_description: str,
        domain: Optional[str],
        limit: int,
    ) -> list[dict]:
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                params: list = [agent_id, agent_id]
                domain_clause = ""
                if domain:
                    domain_clause = "AND (domain=%s OR namespace='shared')"
                    params.append(domain)
                cur.execute(
                    f"""
                    SELECT id, agent_id, memory_type, namespace, task_id, prediction_id,
                           domain, summary, content, importance, access_count,
                           created_at, superseded_by
                      FROM agent_memories
                     WHERE (agent_id=%s OR namespace='shared')
                       AND namespace IN (%s, 'shared')
                       AND superseded_by IS NULL
                       AND (expires_at IS NULL OR expires_at > NOW())
                       {domain_clause}
                     ORDER BY
                       CASE WHEN memory_type='prediction_lesson' THEN 0 ELSE 1 END,
                       importance DESC,
                       created_at DESC
                     LIMIT %s
                    """,
                    [*params, limit],
                )
                rows = [dict(row) for row in cur.fetchall()]
                ids = [row["id"] for row in rows]
                if ids:
                    cur.execute(
                        """
                        UPDATE agent_memories
                           SET access_count = access_count + 1,
                               last_accessed_at = %s
                         WHERE id = ANY(%s::uuid[])
                        """,
                        (datetime.now(timezone.utc), ids),
                    )
        for row in rows:
            row["id"] = str(row["id"])
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat()
            if row.get("superseded_by"):
                row["superseded_by"] = str(row["superseded_by"])
        return rows
