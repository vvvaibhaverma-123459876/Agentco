from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Protocol

logger = logging.getLogger(__name__)


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

    def __init__(self, dsn: str, *, connect_timeout: int = 3):
        self._dsn = dsn
        self._connect_timeout = connect_timeout

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
        log_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
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

                    content = json.dumps(
                        {
                            "log_id": log_id,
                            "timestamp": timestamp,
                            "prev_hash": prev_hash,
                            "agent_id": data["agent_id"],
                            "action_type": action_type,
                            "input_summary": data["description"],
                            "output_summary": output_summary,
                            "confidence_score": round(float(data["trusted_confidence"]), 3),
                            "risk_level": data["risk_level"],
                            "human_approved": human_approved,
                            "human_approver_id": None,
                            "downstream_events": downstream_events,
                            "session_id": session_id,
                        },
                        separators=(",", ":"),
                    )
                    chain_hash = hashlib.sha256((prev_hash + content).encode()).hexdigest()
                    cur.execute(
                        """
                        INSERT INTO decision_log
                            (log_id, agent_id, action_type, input_summary, output_summary,
                             confidence_score, risk_level, human_approved, human_approver_id,
                             downstream_events, session_id, timestamp, chain_hash, prev_hash)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING log_id
                        """,
                        (
                            log_id,
                            data["agent_id"],
                            action_type,
                            data["description"][:500],
                            output_summary[:500],
                            round(float(data["trusted_confidence"]), 3),
                            data["risk_level"],
                            human_approved,
                            None,
                            downstream_events,
                            session_id,
                            timestamp,
                            chain_hash,
                            prev_hash,
                        ),
                    )
            return {"log_id": log_id, "chain_hash": chain_hash, "backend": "decision_log"}
        except Exception as exc:
            logger.error("Durable audit write failed for agent=%s", data.get("agent_id"), exc_info=True)
            raise AuditUnavailableError(str(exc)) from exc
        finally:
            if conn is not None:
                conn.close()
