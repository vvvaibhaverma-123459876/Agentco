"""
MemoryWriter — append-only writes to agent_memories.

Three memory types:
  episodic          — what the agent did (post-task capture)
  semantic          — distilled facts (cross-task knowledge)
  prediction_lesson — what a resolved prediction taught the agent

All writes are append-only. Content and summary are immutable once written
(the DB trigger enforce this). To correct a memory, write a new row and
set superseded_by on the old one.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIM   = 1536


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a))
    nb  = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class MemoryWriter:

    def __init__(self, db_url: str):
        self._db_url = db_url
        self._llm_client: Any = None   # lazy-init

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def write_episodic(
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
        namespace: Optional[str] = None,
    ) -> str:
        """Write an episodic memory. Returns memory_id."""
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
        summary = (
            f"Task '{task_type}' completed in {duration_seconds:.0f}s. "
            f"{task_output_summary} "
            f"Key findings: {'; '.join(key_findings[:3]) or 'none'}."
        )
        importance = min(0.9, 0.4 + len(predictions_registered) * 0.05 + confidence_in_output * 0.3)

        return self._insert(
            agent_id=agent_id,
            memory_type="episodic",
            namespace=namespace or agent_id,
            task_id=task_id,
            domain=domain,
            summary=summary,
            content=content,
            importance=importance,
        )

    def write_prediction_lesson(
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
        namespace: Optional[str] = None,
    ) -> str:
        """Write a lesson extracted from a resolved prediction. Returns memory_id."""
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
        outcome_str = "TRUE" if actual_outcome else "FALSE"
        summary = (
            f"Prediction lesson for {domain}: stated {stated_confidence:.2f}, "
            f"outcome={outcome_str}, log_score={log_score:.4f}. "
            f"Lesson: {lesson[:120]}"
        )
        # High-scoring predictions (good calibration) and low-scoring ones both merit learning
        importance = 0.5 + abs(log_score) * 0.2

        return self._insert(
            agent_id=agent_id,
            memory_type="prediction_lesson",
            namespace=namespace or agent_id,
            prediction_id=prediction_id,
            domain=domain,
            summary=summary,
            content=content,
            importance=min(importance, 0.95),
        )

    def write_semantic(
        self,
        agent_id: str,
        fact: str,
        evidence_from: list[str],
        confidence: float,
        domain: str,
        namespace: Optional[str] = None,
    ) -> str:
        """
        Write a distilled semantic fact.

        If a semantically similar memory exists (cosine > 0.92), the new
        memory supersedes the old one (observation_count is incremented).
        Returns the new memory_id.
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        content = {
            "fact": fact,
            "evidence_from": evidence_from,
            "confidence": confidence,
            "first_observed": now_str,
            "observation_count": 1,
        }
        summary = fact[:500]

        # Check for near-duplicate semantic memory
        existing = self._find_similar_semantic(
            agent_id=agent_id,
            namespace=namespace or agent_id,
            domain=domain,
            text=fact,
            threshold=0.92,
        )

        # Build the new row first (may supersede existing)
        old_id: Optional[str] = None
        if existing:
            old_id = existing["id"]
            # Increment observation_count
            old_count = existing["content"].get("observation_count", 1)
            content["observation_count"] = old_count + 1
            content["first_observed"] = existing["content"].get("first_observed", now_str)

        new_id = self._insert(
            agent_id=agent_id,
            memory_type="semantic",
            namespace=namespace or agent_id,
            domain=domain,
            summary=summary,
            content=content,
            importance=min(0.5 + confidence * 0.4 + content["observation_count"] * 0.02, 0.95),
        )

        if old_id:
            self._set_superseded_by(old_id, new_id)
            logger.info(
                "MemoryWriter: semantic memory %s superseded by %s (observation_count=%d)",
                old_id, new_id, content["observation_count"]
            )

        return new_id

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _insert(
        self,
        agent_id: str,
        memory_type: str,
        namespace: str,
        summary: str,
        content: dict,
        domain: Optional[str] = None,
        task_id: Optional[str] = None,
        prediction_id: Optional[str] = None,
        importance: float = 0.5,
    ) -> str:
        embedding = self._embed(summary)  # None if unavailable
        memory_id = str(uuid.uuid4())

        conn = psycopg2.connect(self._db_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_memories
                        (id, agent_id, memory_type, namespace, task_id,
                         prediction_id, domain, summary, content, embedding, importance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        memory_id, agent_id, memory_type, namespace,
                        task_id, prediction_id, domain,
                        summary, Json(content),
                        embedding,   # FLOAT[] or None
                        importance,
                    ),
                )
        finally:
            conn.close()

        logger.info(
            "MemoryWriter: wrote %s memory %s for agent=%s domain=%s",
            memory_type, memory_id, agent_id, domain
        )
        return memory_id

    def _set_superseded_by(self, old_id: str, new_id: str) -> None:
        conn = psycopg2.connect(self._db_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE agent_memories SET superseded_by = %s WHERE id = %s",
                    (new_id, old_id),
                )
        finally:
            conn.close()

    def _find_similar_semantic(
        self,
        agent_id: str,
        namespace: str,
        domain: Optional[str],
        text: str,
        threshold: float = 0.92,
    ) -> Optional[dict]:
        """Return the most similar existing semantic memory, or None."""
        new_emb = self._embed(text)
        conn = psycopg2.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT id, summary, content, embedding
                    FROM agent_memories
                    WHERE agent_id = %s
                      AND namespace = %s
                      AND memory_type = 'semantic'
                      AND superseded_by IS NULL
                """
                params: list = [agent_id, namespace]
                if domain:
                    sql += " AND domain = %s"
                    params.append(domain)
                cur.execute(sql, params)
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            return None

        best_score = 0.0
        best_row   = None
        for row_id, row_summary, row_content, row_emb in rows:
            if new_emb and row_emb:
                score = _cosine(new_emb, row_emb)
            else:
                # Fallback: Jaccard on words
                a = set(text.lower().split())
                b = set(row_summary.lower().split())
                score = len(a & b) / max(len(a | b), 1)

            if score > best_score:
                best_score = score
                best_row = {
                    "id": str(row_id),
                    "summary": row_summary,
                    "content": row_content,
                    "embedding": row_emb,
                }

        if best_score >= threshold:
            return best_row
        return None

    def _embed(self, text: str) -> Optional[list[float]]:
        """Call OpenAI text-embedding-3-small. Returns None on any error."""
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            if self._llm_client is None:
                from openai import OpenAI
                base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
                self._llm_client = OpenAI(api_key=api_key, base_url=base_url)
            resp = self._llm_client.embeddings.create(
                model=_EMBEDDING_MODEL,
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception as exc:
            logger.warning("MemoryWriter: embedding failed (non-blocking): %s", exc)
            return None
