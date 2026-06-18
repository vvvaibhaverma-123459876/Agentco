"""Append-only memory writer for episodic, semantic, and prediction lessons."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

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


def _jsonb(value: dict[str, Any]) -> psycopg2.extras.Json:
    return psycopg2.extras.Json(value, dumps=json.dumps)


class MemoryWriter:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = _dsn(db_url)

    async def write_episodic(
        self,
        agent_id: str,
        task_id: str,
        task_type: str,
        task_input: str,
        task_output_summary: str,
        predictions_registered: list[str],
        sources_consulted: list[str],
        key_findings: list[str],
        errors_encountered: list[str],
        confidence_in_output: float,
        duration_seconds: float,
        tokens_used: int,
        domain: str = "general",
    ) -> str:
        content = {
            "task_type": task_type,
            "task_input": task_input,
            "task_output_summary": task_output_summary,
            "predictions_registered": predictions_registered,
            "sources_consulted": sources_consulted,
            "duration_seconds": duration_seconds,
            "tokens_used": tokens_used,
            "key_findings": key_findings,
            "errors_encountered": errors_encountered,
            "confidence_in_output": confidence_in_output,
        }
        return self._insert(
            agent_id=agent_id,
            memory_type="episodic",
            namespace=agent_id,
            task_id=task_id,
            prediction_id=None,
            domain=domain,
            summary=task_output_summary,
            content=content,
            importance=min(1.0, max(0.0, confidence_in_output)),
        )

    async def write_prediction_lesson(
        self,
        agent_id: str,
        prediction_id: str,
        claim: str,
        stated_confidence: float,
        actual_outcome: bool,
        log_score: float,
        lesson: str,
        domain_insight: str,
        calibration_adjustment: str,
        domain: str,
    ) -> str:
        content = {
            "prediction_id": prediction_id,
            "claim": claim,
            "stated_confidence": stated_confidence,
            "actual_outcome": actual_outcome,
            "log_score": log_score,
            "lesson": lesson,
            "domain_insight": domain_insight,
            "calibration_adjustment": calibration_adjustment,
        }
        return self._insert(
            agent_id=agent_id,
            memory_type="prediction_lesson",
            namespace=agent_id,
            task_id=None,
            prediction_id=prediction_id,
            domain=domain,
            summary=lesson,
            content=content,
            importance=0.8,
        )

    async def write_semantic(
        self,
        agent_id: str,
        fact: str,
        evidence_from: list[str],
        confidence: float,
        domain: str,
    ) -> str:
        existing = self._find_similar_semantic(agent_id, fact, domain)
        observation_count = 1
        superseded_id = None
        if existing:
            superseded_id, existing_content = existing
            observation_count = int(existing_content.get("observation_count", 1)) + 1

        content = {
            "fact": fact,
            "evidence_from": evidence_from,
            "confidence": confidence,
            "first_observed": datetime.now(timezone.utc).date().isoformat(),
            "observation_count": observation_count,
        }
        memory_id = self._insert(
            agent_id=agent_id,
            memory_type="semantic",
            namespace=agent_id,
            task_id=None,
            prediction_id=None,
            domain=domain,
            summary=fact,
            content=content,
            importance=min(1.0, max(0.0, confidence)),
        )
        if superseded_id:
            self._mark_superseded(superseded_id, memory_id)
        return memory_id

    def _insert(
        self,
        agent_id: str,
        memory_type: str,
        namespace: str,
        task_id: Optional[str],
        prediction_id: Optional[str],
        domain: str,
        summary: str,
        content: dict[str, Any],
        importance: float,
    ) -> str:
        with _connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_memories
                        (agent_id, memory_type, namespace, task_id, prediction_id,
                         domain, summary, content, importance)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        agent_id, memory_type, namespace, task_id, prediction_id,
                        domain, summary, _jsonb(content), importance,
                    ),
                )
                return str(cur.fetchone()[0])

    def _find_similar_semantic(self, agent_id: str, fact: str, domain: str) -> Optional[tuple[str, dict]]:
        # Embeddings are optional. Until an embedding is available, exact
        # normalized fact matching gives deterministic duplicate handling.
        with _connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, content
                      FROM agent_memories
                     WHERE agent_id=%s
                       AND namespace=%s
                       AND memory_type='semantic'
                       AND domain=%s
                       AND superseded_by IS NULL
                       AND lower(summary)=lower(%s)
                     ORDER BY created_at DESC
                     LIMIT 1
                    """,
                    (agent_id, agent_id, domain, fact),
                )
                row = cur.fetchone()
        if not row:
            return None
        return str(row["id"]), dict(row["content"])

    def _mark_superseded(self, old_id: str, new_id: str) -> None:
        with _connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE agent_memories SET superseded_by=%s WHERE id=%s",
                    (new_id, old_id),
                )
