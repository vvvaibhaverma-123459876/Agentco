"""
Learning Extraction Loop — turns episodic experience into semantic knowledge.

Separate from learning/learning_loop.py (which orchestrates the 6-hour cycle).
This module operates on agent_memories: reviews recent episodes and resolved
predictions to extract reusable facts, consolidate scattered observations,
and share high-value lessons across agents.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from agents.core.memory.memory_writer import MemoryWriter
from runtime.base_agent.llm_client import client_for_tier
from runtime.base_agent.provider_config import resolve_tier_config

logger = logging.getLogger(__name__)


def _llm_client() -> Any:
    return client_for_tier("standard")


def _extraction_model() -> str:
    return resolve_tier_config("standard").model


class LearningLoop:
    """
    Reviews episodic memories and resolved predictions to extract semantic knowledge.

    Does NOT require human approval (it only reads and writes to agent_memories,
    not to the prediction ledger or agent config). All extracted facts are
    tagged as memory_type='semantic' with the extraction provenance in content.
    """

    CONSOLIDATION_THRESHOLD = 5   # min semantic memories before consolidation

    def __init__(self, db_url: str):
        self._db_url  = db_url
        self._writer  = MemoryWriter(db_url)
        self._client: Any = None   # lazy

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def extract_lessons_from_recent(
        self,
        agent_id: str,
        since_hours: int = 24,
    ) -> list[str]:
        """
        Review all episodic memories and resolved predictions from the last N hours.
        For each, ask the LLM whether a reusable fact should be remembered.
        Write non-null results as semantic memories.
        Returns list of new semantic memory_ids.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        new_ids: list[str] = []

        # Fetch recent episodic memories
        episodes = self._fetch_episodes(agent_id, since)
        # Fetch recently resolved predictions
        resolved = self._fetch_resolved_predictions(agent_id, since)

        client = self._get_client()

        # Extract from episodes
        for ep in episodes:
            memory_id = self._extract_from_episode(agent_id, ep, client)
            if memory_id:
                new_ids.append(memory_id)

        # Extract from resolved predictions
        for pred in resolved:
            memory_id = self._extract_from_prediction(agent_id, pred, client)
            if memory_id:
                new_ids.append(memory_id)

        logger.info(
            "LearningLoop.extract_lessons_from_recent: agent=%s since=%dh → %d new semantic memories",
            agent_id, since_hours, len(new_ids)
        )
        return new_ids

    def consolidate_semantic_memories(
        self,
        agent_id: str,
        domain: str,
        namespace: Optional[str] = None,
    ) -> Optional[str]:
        """
        If there are 5+ active semantic memories in a domain, consolidate them into
        one higher-confidence summary. Mark originals as superseded.
        Returns consolidated memory_id, or None if < CONSOLIDATION_THRESHOLD.
        """
        ns = namespace or agent_id
        memories = self._fetch_semantic_memories(agent_id, ns, domain)

        if len(memories) < self.CONSOLIDATION_THRESHOLD:
            logger.info(
                "LearningLoop.consolidate: agent=%s domain=%s has %d semantic memories (need %d)",
                agent_id, domain, len(memories), self.CONSOLIDATION_THRESHOLD
            )
            return None

        client = self._get_client()
        facts = [m["content"].get("fact", m["summary"]) for m in memories]
        facts_text = "\n".join(f"- {f}" for f in facts)

        prompt = f"""You are consolidating knowledge for an AI agent.
These are {len(facts)} semantic memories in the '{domain}' domain:

{facts_text}

Write a concise, unified summary (2-4 sentences) that captures the key insight
shared across these observations. Be specific and actionable.

Return ONLY JSON:
{{"consolidated_fact": "...", "confidence": 0.85}}"""

        consolidated_fact = ""
        confidence = 0.7
        try:
            resp = client.chat.completions.create(
                model=_extraction_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw = resp.choices[0].message.content or ""
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
            parsed = json.loads(raw)
            consolidated_fact = parsed.get("consolidated_fact", "")
            confidence = float(parsed.get("confidence", 0.7))
        except Exception as exc:
            logger.warning("LearningLoop.consolidate: LLM failed (%s); using heuristic fallback", exc)

        if not consolidated_fact:
            # Fallback: simple concatenation of the top 3 facts
            consolidated_fact = " | ".join(facts[:3])

        all_evidence = [m.get("id", "") for m in memories]
        consolidated_id = self._writer.write_semantic(
            agent_id=agent_id,
            fact=f"[CONSOLIDATED] {consolidated_fact}",
            evidence_from=all_evidence,
            confidence=confidence,
            domain=domain,
            namespace=ns,
        )

        # Mark all originals as superseded by the consolidated memory
        conn = psycopg2.connect(self._db_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                for m in memories:
                    mid = m.get("id")
                    if mid and mid != consolidated_id:
                        try:
                            cur.execute(
                                "UPDATE agent_memories SET superseded_by = %s WHERE id = %s",
                                (consolidated_id, mid),
                            )
                        except Exception:
                            pass  # already superseded — skip
        finally:
            conn.close()

        logger.info(
            "LearningLoop.consolidate: agent=%s domain=%s consolidated %d → %s",
            agent_id, domain, len(memories), consolidated_id
        )
        return consolidated_id

    def cross_agent_lesson_sharing(
        self,
        source_agent_id: str,
        lesson_memory_id: str,
        target_agent_ids: list[str],
        trust_score: float = 0.5,
    ) -> list[str]:
        """
        Share a high-importance semantic memory with other agents by writing
        a copy to the 'shared' namespace. Each copy carries the source agent's
        trust score as the importance weight.

        trust_score: source agent's trusted_confidence in the lesson's domain
                     (used as importance weight — low-trust sources get low importance).
        Returns list of shared memory_ids.
        """
        # Fetch the original memory
        conn = psycopg2.connect(self._db_url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM agent_memories WHERE id = %s",
                    (lesson_memory_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            logger.warning(
                "LearningLoop.cross_agent_sharing: memory %s not found", lesson_memory_id
            )
            return []

        row = dict(row)
        base_content = dict(row.get("content") or {})
        base_content["shared_by"] = source_agent_id
        base_content["source_trust_score"] = trust_score
        base_content["original_memory_id"] = str(lesson_memory_id)

        shared_ids: list[str] = []
        for target_id in target_agent_ids:
            try:
                mid = self._writer._insert(
                    agent_id=target_id,
                    memory_type=row.get("memory_type", "semantic"),
                    namespace="shared",
                    summary=f"[shared by {source_agent_id}] {row.get('summary', '')}",
                    content=base_content,
                    domain=row.get("domain"),
                    importance=min(trust_score, 0.9),
                )
                shared_ids.append(mid)
                logger.info(
                    "LearningLoop.cross_agent_sharing: %s → %s: memory %s shared as %s",
                    source_agent_id, target_id, lesson_memory_id, mid
                )
            except Exception as exc:
                logger.warning(
                    "LearningLoop.cross_agent_sharing: failed for target=%s: %s",
                    target_id, exc
                )

        return shared_ids

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = _llm_client()
        return self._client

    def _fetch_episodes(self, agent_id: str, since: datetime) -> list[dict]:
        conn = psycopg2.connect(self._db_url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM agent_memories
                    WHERE agent_id = %s
                      AND memory_type = 'episodic'
                      AND created_at >= %s
                      AND superseded_by IS NULL
                    ORDER BY created_at DESC
                    LIMIT 20
                    """,
                    (agent_id, since),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def _fetch_resolved_predictions(self, agent_id: str, since: datetime) -> list[dict]:
        conn = psycopg2.connect(self._db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT prediction_id, claim, domain, probability,
                           resolved_outcome, log_score, brier_score, resolved_at
                    FROM prediction_ledger
                    WHERE producing_agent_id = %s
                      AND resolved = TRUE
                      AND resolved_at >= %s
                      AND post_hoc = FALSE
                    ORDER BY resolved_at DESC
                    LIMIT 10
                    """,
                    (agent_id, since),
                )
                cols = ["prediction_id", "claim", "domain", "probability",
                        "resolved_outcome", "log_score", "brier_score", "resolved_at"]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def _fetch_semantic_memories(self, agent_id: str, namespace: str, domain: str) -> list[dict]:
        conn = psycopg2.connect(self._db_url)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM agent_memories
                    WHERE agent_id = %s
                      AND namespace = %s
                      AND domain = %s
                      AND memory_type = 'semantic'
                      AND superseded_by IS NULL
                    ORDER BY importance DESC
                    """,
                    (agent_id, namespace, domain),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def _extract_from_episode(
        self, agent_id: str, episode: dict, client: Any
    ) -> Optional[str]:
        """Ask LLM if this episode contains a reusable fact. Write if yes."""
        content = episode.get("content") or {}
        summary = episode.get("summary", "")
        domain  = episode.get("domain", "general")
        findings = content.get("key_findings", [])
        ep_summary = f"{summary}\nKey findings: {'; '.join(findings[:5])}"

        prompt = f"""An AI agent completed a task with the following outcome:

{ep_summary[:1000]}

Is there a specific, reusable fact or principle worth remembering for future tasks?
If yes, state it as a single clear sentence. If nothing worth remembering, return null.

Return ONLY JSON:
{{"fact": "...", "confidence": 0.75}}
or
{{"fact": null}}"""

        try:
            resp = client.chat.completions.create(
                model=_extraction_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw = resp.choices[0].message.content or ""
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
            parsed = json.loads(raw)
            fact = parsed.get("fact")
            if not fact:
                return None
            confidence = float(parsed.get("confidence", 0.6))
            evidence_id = str(episode.get("id", ""))
            return self._writer.write_semantic(
                agent_id=agent_id,
                fact=fact,
                evidence_from=[evidence_id] if evidence_id else [],
                confidence=confidence,
                domain=domain,
            )
        except Exception as exc:
            logger.warning("LearningLoop._extract_from_episode: error: %s", exc)
            return None

    def _extract_from_prediction(
        self, agent_id: str, pred: dict, client: Any
    ) -> Optional[str]:
        """Write a prediction lesson from a resolved prediction."""
        claim   = pred.get("claim", "")
        p       = float(pred.get("probability", 0.5))
        outcome = pred.get("resolved_outcome", False)
        log_s   = float(pred.get("log_score") or 0.0)
        domain  = pred.get("domain", "general")

        prompt = f"""An AI agent made a prediction that has now resolved:

Claim: {claim}
Stated confidence: {p:.2f}
Actual outcome: {'TRUE' if outcome else 'FALSE'}
Log score: {log_s:.4f} (higher is better; 0 = perfect)

What should this agent learn? Give:
1. A one-sentence lesson
2. A one-sentence domain insight
3. A calibration adjustment for future predictions in this domain

Return ONLY JSON:
{{"lesson": "...", "domain_insight": "...", "calibration_adjustment": "..."}}"""

        try:
            resp = client.chat.completions.create(
                model=_extraction_model(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw = resp.choices[0].message.content or ""
            raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
            parsed = json.loads(raw)

            return self._writer.write_prediction_lesson(
                agent_id=agent_id,
                prediction_id=str(pred.get("prediction_id", "")),
                claim=claim,
                stated_confidence=p,
                actual_outcome=bool(outcome),
                log_score=log_s,
                lesson=parsed.get("lesson", ""),
                domain_insight=parsed.get("domain_insight", ""),
                calibration_adjustment=parsed.get("calibration_adjustment", ""),
                domain=domain,
            )
        except Exception as exc:
            logger.warning("LearningLoop._extract_from_prediction: error: %s", exc)
            return None
