from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_STORE = ROOT / "artifacts" / "capability-runtime" / "attempts"


def database_url() -> str | None:
    return os.getenv("AGENTCO_CAPABILITY_DATABASE_URL") or os.getenv("DATABASE_URL")


def _local_path(attempt_id: str) -> Path:
    safe = "".join(ch for ch in attempt_id if ch.isalnum() or ch in "-_")
    root = Path(os.getenv("AGENTCO_CAPABILITY_STORE_DIR", str(DEFAULT_LOCAL_STORE)))
    return root / f"{safe}.json"


def write_attempt(response: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    dsn = database_url()
    if dsn:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO capability_attempts
                      (attempt_id, request_id, status, task_type, actor_id, tenant, request_json, response_json, request_hash, response_hash)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
                    ON CONFLICT (attempt_id) DO UPDATE
                    SET status = EXCLUDED.status, response_json = EXCLUDED.response_json, completed_at = now()
                    """,
                    [
                        response["attempt_id"],
                        response["request_id"],
                        response["status"],
                        response.get("task_type"),
                        response.get("actor", {}).get("id"),
                        response.get("tenant"),
                        json.dumps(response.get("request", {}), sort_keys=True),
                        json.dumps(response, sort_keys=True),
                        hashlib.sha256(json.dumps(response.get("request", {}), sort_keys=True).encode()).hexdigest(),
                        hashlib.sha256(json.dumps(response, sort_keys=True, default=str).encode()).hexdigest(),
                    ],
                )
        refs.append({"type": "postgres", "table": "capability_attempts", "id": response["attempt_id"]})
    else:
        path = _local_path(response["attempt_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(response, indent=2, sort_keys=True) + "\n")
        try:
            display_path = str(path.relative_to(ROOT))
        except ValueError:
            display_path = str(path)
        refs.append({"type": "local_json", "path": display_path})
    return {"audit_references": refs}


def read_attempt(attempt_id: str) -> dict[str, Any] | None:
    dsn = database_url()
    if dsn:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT response_json FROM capability_attempts WHERE attempt_id = %s", [attempt_id])
                row = cur.fetchone()
                return dict(row["response_json"]) if row else None
    path = _local_path(attempt_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def read_attempt_from_store(attempt_id: str, store_dir: str | Path) -> dict[str, Any] | None:
    safe = "".join(ch for ch in attempt_id if ch.isalnum() or ch in "-_")
    path = Path(store_dir) / f"{safe}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def cancel_stored_attempt(attempt_id: str) -> dict[str, Any]:
    existing = read_attempt(attempt_id)
    if not existing:
        return {"status": "unsupported", "attempt_id": attempt_id, "failure": {"message": "attempt not found"}}
    if existing.get("status") in {"completed", "failed", "timed_out", "denied", "budget_exceeded"}:
        return existing
    existing["status"] = "cancelled"
    write_attempt(existing)
    return existing
