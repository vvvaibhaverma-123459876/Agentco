#!/usr/bin/env python3
"""Repair decision_log hash-chain metadata from stored audit row content.

This is for local recovery after a writer bug stored incompatible hash metadata.
It does not edit the audit payload fields; it only recomputes prev_hash and
chain_hash using the backend AuditLogService canonical format.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import timezone
from typing import Any


ZERO_HASH = "0" * 64


def database_url() -> str:
    return (
        os.getenv("SUPERUSER_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://agentco:password@localhost:5432/agentco"
    )


def js_iso_timestamp(value: Any) -> str:
    if hasattr(value, "astimezone"):
        return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return str(value)


def canonical_audit(fields: dict[str, Any]) -> str:
    order = [
        "log_id",
        "timestamp",
        "prev_hash",
        "agent_id",
        "action_type",
        "input_summary",
        "output_summary",
        "confidence_score",
        "risk_level",
        "human_approved",
        "human_approver_id",
        "downstream_events",
        "session_id",
    ]
    canonical = {key: fields[key] for key in order}
    score = canonical.get("confidence_score")
    if isinstance(score, float):
        score = round(score, 3)
        canonical["confidence_score"] = score
    if isinstance(score, float) and score.is_integer():
        canonical["confidence_score"] = int(score)
    return json.dumps(canonical, separators=(",", ":"))


def normalize_uuid_array(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "{}":
            return []
        if stripped.startswith("{") and stripped.endswith("}"):
            return [item for item in stripped[1:-1].split(",") if item]
        return [stripped]
    return [str(event_id) for event_id in value]


def main() -> int:
    try:
        import psycopg2
        import psycopg2.extras
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("psycopg2 is required to repair the decision_log chain") from exc

    with psycopg2.connect(database_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT log_id, agent_id, action_type, input_summary, output_summary,
                       confidence_score, risk_level, human_approved, human_approver_id,
                       downstream_events, session_id, timestamp, chain_hash, prev_hash
                  FROM decision_log
                 WHERE chain_hash ~ '^[0-9a-f]{64}$'
                   AND prev_hash ~ '^[0-9a-f]{64}$'
                 ORDER BY timestamp ASC, log_id ASC
                """
            )
            rows = cur.fetchall()
            updates: list[tuple[str, str, str]] = []
            prev_hash = ZERO_HASH
            for row in rows:
                fields = {
                    "log_id": str(row["log_id"]),
                    "timestamp": js_iso_timestamp(row["timestamp"]),
                    "prev_hash": prev_hash,
                    "agent_id": row["agent_id"],
                    "action_type": row["action_type"],
                    "input_summary": row["input_summary"],
                    "output_summary": row["output_summary"],
                    "confidence_score": round(float(row["confidence_score"]), 3),
                    "risk_level": row["risk_level"],
                    "human_approved": bool(row["human_approved"]),
                    "human_approver_id": str(row["human_approver_id"]) if row["human_approver_id"] else None,
                    "downstream_events": normalize_uuid_array(row["downstream_events"]),
                    "session_id": str(row["session_id"]) if row["session_id"] else None,
                }
                chain_hash = hashlib.sha256((prev_hash + canonical_audit(fields)).encode()).hexdigest()
                if row["prev_hash"] != prev_hash or row["chain_hash"] != chain_hash:
                    updates.append((prev_hash, chain_hash, str(row["log_id"])))
                prev_hash = chain_hash

            if updates:
                cur.execute("ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_update")
                try:
                    cur.executemany(
                        "UPDATE decision_log SET prev_hash = %s, chain_hash = %s WHERE log_id = %s",
                        updates,
                    )
                finally:
                    cur.execute("ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_update")

    print(json.dumps({"rows_checked": len(rows), "rows_repaired": len(updates)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
