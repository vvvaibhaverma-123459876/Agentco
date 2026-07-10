from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger(__name__)

CURRENT_DECISION_LOG_SERIALIZATION_VERSION = "v4.sorted-json-versioned-attempt"
DECISION_LOG_CHAIN_LOCK_KEY = "agentco.decision_log.hash_chain"


def _utc_timestamp_ms() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_decision_log_content(fields: dict[str, Any]) -> str:
    """Cross-language canonical JSON for decision_log hash-chain rows."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


class AuditUnavailableError(RuntimeError):
    """Raised when a protected action cannot be durably audited."""


class AuditWriter(Protocol):
    def write(self, entry: Any) -> dict[str, str]:
        """Persist an audit entry and return an acknowledgement."""


class InMemoryAuditWriter:
    """Test-only audit writer that preserves the old process-local behavior."""

    def __init__(self, *, allow_test_mode: bool = False):
        if not allow_test_mode:
            raise AuditUnavailableError("InMemoryAuditWriter requires allow_test_mode=True")
        self.entries: list[Any] = []

    def write(self, entry: Any) -> dict[str, str]:
        self.entries.append(entry)
        return {"log_id": getattr(entry, "trace_id", str(uuid.uuid4())), "backend": "memory"}


class DurableAuditWriter:
    """Postgres-backed writer for the canonical append-only decision_log table."""

    VALID_ACTION_TYPES = {"decision", "api_call", "event_published", "escalation"}

    def __init__(self, dsn: str, *, connect_timeout: int = 3, max_retries: int = 3, retry_backoff_seconds: float = 0.05):
        self._dsn = dsn
        self._connect_timeout = connect_timeout
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    @classmethod
    def from_env(cls) -> "DurableAuditWriter | None":
        dsn = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not dsn:
            return None
        return cls(dsn)

    def write(self, entry: Any) -> dict[str, str]:
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise AuditUnavailableError("psycopg2 is required for DurableAuditWriter") from exc

        data = asdict(entry) if hasattr(entry, "__dataclass_fields__") else dict(entry)
        attempt_id = str(data.get("attempt_id") or uuid.uuid4())
        data["attempt_id"] = attempt_id
        if isinstance(entry, dict):
            entry.setdefault("attempt_id", attempt_id)

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                return self._write_once(data, attempt_id=attempt_id, psycopg2=psycopg2)
            except Exception as exc:
                last_exc = exc
                if attempt == self._max_retries:
                    break
                time.sleep(self._retry_backoff_seconds * attempt)

        logger.error("Durable audit write failed for agent=%s: %s", data.get("agent_id"), last_exc)
        raise AuditUnavailableError(str(last_exc)) from last_exc

    def _write_once(self, data: dict[str, Any], *, attempt_id: str, psycopg2: Any) -> dict[str, str]:
        log_id = str(uuid.uuid4())
        timestamp = _utc_timestamp_ms()
        prev_hash = "0" * 64
        action_type = data.get("action_type", "decision")
        if action_type not in self.VALID_ACTION_TYPES:
            action_type = "escalation" if data.get("outcome") == "blocked" else "decision"
        output_summary = json.dumps(
            {
                "outcome": data.get("outcome"),
                "action_type": data.get("action_type"),
                "override_id": data.get("override_id"),
                "prediction_id": data.get("prediction_id"),
            },
            sort_keys=True,
        )
        downstream_events: list[str] = []
        session_id = data.get("trace_id")
        human_approved = bool(data.get("override_id") and data.get("outcome") == "executed")

        conn = None
        try:
            conn = psycopg2.connect(self._dsn, connect_timeout=self._connect_timeout)
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (DECISION_LOG_CHAIN_LOCK_KEY,))
                    cur.execute(
                        """
                        SELECT chain_hash
                          FROM decision_log
                         WHERE chain_hash ~ '^[0-9a-f]{64}$'
                           AND prev_hash ~ '^[0-9a-f]{64}$'
                         ORDER BY timestamp DESC, log_id DESC
                         LIMIT 1
                        """
                    )
                    row = cur.fetchone()
                    if row:
                        prev_hash = row[0]

                    input_summary = data["description"][:500]
                    output_summary = output_summary[:500]
                    content = canonical_decision_log_content({
                        "serialization_version": CURRENT_DECISION_LOG_SERIALIZATION_VERSION,
                        "attempt_id": attempt_id,
                        "log_id": log_id,
                        "timestamp": timestamp,
                        "prev_hash": prev_hash,
                        "agent_id": data["agent_id"],
                        "action_type": action_type,
                        "input_summary": input_summary,
                        "output_summary": output_summary,
                        "confidence_score": round(float(data["trusted_confidence"]), 3),
                        "risk_level": data["risk_level"],
                        "human_approved": human_approved,
                        "human_approver_id": None,
                        "downstream_events": downstream_events,
                        "session_id": session_id,
                    })
                    chain_hash = hashlib.sha256((prev_hash + content).encode()).hexdigest()
                    cur.execute(
                        """
                        INSERT INTO decision_log
                            (log_id, agent_id, action_type, input_summary, output_summary,
                             confidence_score, risk_level, human_approved, human_approver_id,
                             downstream_events, session_id, timestamp, chain_hash, prev_hash,
                             serialization_version, attempt_id)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (attempt_id) WHERE attempt_id IS NOT NULL DO NOTHING
                        RETURNING log_id, chain_hash
                        """,
                        (
                            log_id,
                            data["agent_id"],
                            action_type,
                            input_summary,
                            output_summary,
                            round(float(data["trusted_confidence"]), 3),
                            data["risk_level"],
                            human_approved,
                            None,
                            downstream_events,
                            session_id,
                            timestamp,
                            chain_hash,
                            prev_hash,
                            CURRENT_DECISION_LOG_SERIALIZATION_VERSION,
                            attempt_id,
                        ),
                    )
                    row = cur.fetchone()
                    if row:
                        return {
                            "log_id": str(row[0]),
                            "chain_hash": row[1],
                            "attempt_id": attempt_id,
                            "backend": "decision_log",
                        }
                    cur.execute(
                        """
                        SELECT log_id, chain_hash
                          FROM decision_log
                         WHERE attempt_id = %s
                        """,
                        (attempt_id,),
                    )
                    existing = cur.fetchone()
                    if existing:
                        return {
                            "log_id": str(existing[0]),
                            "chain_hash": existing[1],
                            "attempt_id": attempt_id,
                            "backend": "decision_log",
                        }
                    raise AuditUnavailableError(f"audit attempt {attempt_id} conflicted but no row was found")
        finally:
            if conn is not None:
                conn.close()
