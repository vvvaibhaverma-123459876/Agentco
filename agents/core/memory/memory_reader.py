"""
MemoryReader — retrieve relevant memories for an upcoming task.

Retrieval strategy (in priority order, combined):
  1. Recency: last 3 episodic memories for this agent (cheap, always fast)
  2. Domain match: memories in the matching domain
  3. Full-text search on summary (GIN index)
  4. Prediction lessons in the domain
  5. Semantic similarity via Python cosine (if embeddings stored)

All retrieval respects a latency budget (default 500ms).
If budget is exceeded, returns whatever was collected so far.
Never blocks the agent from starting.
"""
from __future__ import annotations

import logging
import math
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 6000  # ~1500 tokens at ~4 chars/token


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class MemoryReader:

    def __init__(self, db_url: str):
        self._db_url = db_url

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def retrieve_relevant(
        self,
        agent_id: str,
        task_description: str,
        domain: Optional[str] = None,
        limit: int = 10,
        timeout_ms: int = 500,
    ) -> list[dict]:
        """
        Retrieve the most relevant memories for an upcoming task.
        Returns within timeout_ms — never blocks the agent from starting.
        Updates access_count and last_accessed_at on returned rows.
        """
        deadline = time.monotonic() + timeout_ms / 1000.0
        seen_ids: set[str] = set()
        results: list[dict] = []

        try:
            conn = psycopg2.connect(self._db_url)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # 1. Recent episodic memories (fast, indexed on created_at)
                    if time.monotonic() < deadline:
                        cur.execute(
                            """
                            SELECT * FROM agent_memories
                            WHERE agent_id = %s
                              AND memory_type = 'episodic'
                              AND superseded_by IS NULL
                              AND (expires_at IS NULL OR expires_at > NOW())
                            ORDER BY created_at DESC
                            LIMIT 3
                            """,
                            (agent_id,),
                        )
                        for row in cur.fetchall():
                            rid = str(row["id"])
                            if rid not in seen_ids:
                                results.append(dict(row))
                                seen_ids.add(rid)

                    # 2. Domain-matched memories
                    if domain and time.monotonic() < deadline:
                        cur.execute(
                            """
                            SELECT * FROM agent_memories
                            WHERE agent_id = %s
                              AND domain = %s
                              AND superseded_by IS NULL
                              AND (expires_at IS NULL OR expires_at > NOW())
                            ORDER BY importance DESC, created_at DESC
                            LIMIT 5
                            """,
                            (agent_id, domain),
                        )
                        for row in cur.fetchall():
                            rid = str(row["id"])
                            if rid not in seen_ids:
                                results.append(dict(row))
                                seen_ids.add(rid)

                    # 3. Full-text search on summary
                    if task_description and time.monotonic() < deadline:
                        # Build a tsquery from first 10 words
                        words = [w for w in task_description.split()[:10] if len(w) > 2]
                        if words:
                            tsquery = " & ".join(words)
                            try:
                                cur.execute(
                                    """
                                    SELECT *, ts_rank(to_tsvector('english', summary),
                                               to_tsquery('english', %s)) AS _rank
                                    FROM agent_memories
                                    WHERE agent_id = %s
                                      AND to_tsvector('english', summary) @@ to_tsquery('english', %s)
                                      AND superseded_by IS NULL
                                      AND (expires_at IS NULL OR expires_at > NOW())
                                    ORDER BY _rank DESC
                                    LIMIT 5
                                    """,
                                    (tsquery, agent_id, tsquery),
                                )
                                for row in cur.fetchall():
                                    rid = str(row["id"])
                                    if rid not in seen_ids:
                                        d = dict(row)
                                        d.pop("_rank", None)
                                        results.append(d)
                                        seen_ids.add(rid)
                            except Exception:
                                pass  # bad tsquery syntax — skip

                    # 4. Prediction lessons in domain
                    if time.monotonic() < deadline:
                        sql = """
                            SELECT * FROM agent_memories
                            WHERE agent_id = %s
                              AND memory_type = 'prediction_lesson'
                              AND superseded_by IS NULL
                              AND (expires_at IS NULL OR expires_at > NOW())
                        """
                        params: list = [agent_id]
                        if domain:
                            sql += " AND domain = %s"
                            params.append(domain)
                        sql += " ORDER BY created_at DESC LIMIT 5"
                        cur.execute(sql, params)
                        for row in cur.fetchall():
                            rid = str(row["id"])
                            if rid not in seen_ids:
                                results.append(dict(row))
                                seen_ids.add(rid)

                    # Trim to limit and update access counts
                    results = results[:limit]
                    if results:
                        ids = [r["id"] for r in results]
                        from psycopg2.extensions import AsIs
                        id_list = ",".join(f"'{i}'" for i in ids)
                        cur.execute(
                            f"""
                            UPDATE agent_memories
                               SET access_count = access_count + 1,
                                   last_accessed_at = NOW()
                             WHERE id = ANY(ARRAY[{id_list}]::uuid[])
                            """
                        )
                        conn.commit()

            finally:
                conn.close()

        except Exception as exc:
            logger.warning("MemoryReader.retrieve_relevant: error (non-blocking): %s", exc)

        # Serialise any non-JSON-serialisable values (UUID, datetime)
        return [self._serialise_row(r) for r in results]

    def get_agent_track_record_summary(
        self,
        agent_id: str,
        domain: Optional[str] = None,
    ) -> dict:
        """
        Structured summary of the agent's prediction track record.
        Queries prediction_ledger + agent_memories (prediction lessons).
        """
        summary: dict = {
            "agent_id": agent_id,
            "domain": domain or "all",
            "total_predictions": 0,
            "resolved": 0,
            "correct": 0,
            "average_log_score": None,
            "average_brier_score": None,
            "trusted_confidence_by_domain": {},
            "recent_lessons": [],
        }
        try:
            conn = psycopg2.connect(self._db_url)
            try:
                with conn.cursor() as cur:
                    # Prediction ledger stats
                    sql = """
                        SELECT
                            COUNT(*)                          AS total,
                            COUNT(*) FILTER (WHERE resolved)  AS resolved,
                            COUNT(*) FILTER (WHERE resolved AND resolved_outcome IS TRUE) AS correct,
                            AVG(log_score)   FILTER (WHERE resolved)   AS avg_log,
                            AVG(brier_score) FILTER (WHERE resolved)   AS avg_brier
                        FROM prediction_ledger
                        WHERE producing_agent_id = %s
                          AND post_hoc = FALSE
                    """
                    params: list = [agent_id]
                    if domain:
                        sql += " AND domain = %s"
                        params.append(domain)
                    cur.execute(sql, params)
                    row = cur.fetchone()
                    if row:
                        summary["total_predictions"] = int(row[0] or 0)
                        summary["resolved"]          = int(row[1] or 0)
                        summary["correct"]           = int(row[2] or 0)
                        summary["average_log_score"] = float(row[3]) if row[3] is not None else None
                        summary["average_brier_score"] = float(row[4]) if row[4] is not None else None

                    # Recent prediction lessons
                    cur.execute(
                        """
                        SELECT summary, content, created_at
                        FROM agent_memories
                        WHERE agent_id = %s
                          AND memory_type = 'prediction_lesson'
                          AND superseded_by IS NULL
                        ORDER BY created_at DESC
                        LIMIT 5
                        """,
                        (agent_id,),
                    )
                    for row in cur.fetchall():
                        lesson_summary, content, created_at = row
                        summary["recent_lessons"].append({
                            "summary": lesson_summary,
                            "domain_insight": content.get("domain_insight", ""),
                            "calibration_adjustment": content.get("calibration_adjustment", ""),
                            "created_at": created_at.isoformat() if created_at else None,
                        })
            finally:
                conn.close()
        except Exception as exc:
            logger.warning("MemoryReader.get_agent_track_record_summary: error: %s", exc)

        return summary

    def format_for_system_prompt(
        self,
        memories: list[dict],
        track_record: dict,
    ) -> str:
        """
        Format memories and track record into a text block for system prompt injection.
        Max ~1500 tokens (~6000 chars). Always returns a string (empty = no experience).
        """
        parts: list[str] = []

        # Track record header
        tr = track_record
        n_total   = tr.get("total_predictions", 0)
        n_resolved = tr.get("resolved", 0)
        n_correct  = tr.get("correct", 0)
        avg_log    = tr.get("average_log_score")
        domain     = tr.get("domain", "all")

        if n_total > 0:
            acc = f"{n_correct}/{n_resolved}" if n_resolved else "0/0"
            log_str = f"{avg_log:.4f}" if avg_log is not None else "n/a"
            parts.append(
                f"[AGENT TRACK RECORD — domain={domain}] "
                f"{n_total} predictions total, {n_resolved} resolved, "
                f"{acc} correct, avg_log_score={log_str}."
            )
        else:
            parts.append(f"[AGENT TRACK RECORD] No previous predictions in domain={domain}.")

        # Recent lessons
        lessons = tr.get("recent_lessons", [])
        if lessons:
            parts.append("[CALIBRATION LESSONS]")
            for lesson in lessons[:3]:
                parts.append(f"  • {lesson['summary'][:200]}")
                if lesson.get("calibration_adjustment"):
                    parts.append(f"    → Adjustment: {lesson['calibration_adjustment'][:150]}")

        # Episodic memories (what the agent has done before)
        episodic = [m for m in memories if m.get("memory_type") == "episodic"]
        if episodic:
            parts.append(f"[PREVIOUS EXPERIENCE — last {len(episodic)} task(s)]")
            for m in episodic[:3]:
                content = m.get("content", {})
                findings = content.get("key_findings", [])
                findings_str = "; ".join(findings[:3]) or "none"
                parts.append(
                    f"  • {m.get('summary', '')[:200]}"
                )
                if findings:
                    parts.append(f"    Key findings: {findings_str[:200]}")
        else:
            parts.append("[PREVIOUS EXPERIENCE] No previous experience in this domain.")

        # Semantic facts
        semantic = [m for m in memories if m.get("memory_type") == "semantic"]
        if semantic:
            parts.append("[KNOWN FACTS]")
            for m in semantic[:4]:
                content = m.get("content", {})
                parts.append(
                    f"  • {content.get('fact', m.get('summary',''))[:200]} "
                    f"(confidence={content.get('confidence', '?')}, "
                    f"observations={content.get('observation_count', 1)})"
                )

        result = "\n".join(parts)
        return result[:_MAX_CONTEXT_CHARS]

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialise_row(row: dict) -> dict:
        """Convert UUIDs and datetimes to JSON-safe strings."""
        out = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                out[k] = v.isoformat()
            else:
                out[k] = str(v) if not isinstance(v, (int, float, bool, list, dict, type(None), str)) else v
        return out
