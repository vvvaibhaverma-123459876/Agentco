#!/usr/bin/env python3
"""Execute one durable AgentCo task without synthetic success paths.

This executor reads from the canonical ``agent_tasks`` view backed by the
backend's real ``workflow_tasks`` table. It never reads the obsolete
``durable_tasks`` name and never fabricates review/decision outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


SUPPORTED_TASK_TYPES = {"llm_call", "calibration", "health_check", "record_observation"}
UNSUPPORTED_TASK_TYPES = {"review", "decision"}


class UnsupportedFeatureError(RuntimeError):
    """Raised when a task type has no production implementation."""


class PayloadValidationError(ValueError):
    """Raised when a task payload does not match the required schema."""


@dataclass(frozen=True)
class Task:
    task_id: str
    agent_id: str
    task_type: str
    payload: dict[str, Any]


def require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for durable task executor runs")
    return database_url


def validate_payload(task_type: str, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise PayloadValidationError("payload must be a JSON object")
    if task_type == "llm_call":
        if not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
            raise PayloadValidationError("llm_call payload requires non-empty string field: prompt")
    elif task_type == "calibration":
        confidence = payload.get("confidence")
        outcome = payload.get("outcome")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            raise PayloadValidationError("calibration payload requires confidence in [0, 1]")
        if outcome not in (0, 1, True, False):
            raise PayloadValidationError("calibration payload requires boolean/binary outcome")
    elif task_type == "health_check":
        return
    elif task_type == "record_observation":
        if "observation" not in payload:
            raise PayloadValidationError("record_observation payload requires field: observation")
    elif task_type in UNSUPPORTED_TASK_TYPES:
        raise UnsupportedFeatureError(
            f"{task_type} task execution is unsupported: no real production service is wired"
        )
    else:
        raise UnsupportedFeatureError(f"unsupported durable task_type: {task_type}")


def execute_task_logic(task: Task) -> dict[str, Any]:
    validate_payload(task.task_type, task.payload)
    if task.task_type == "health_check":
        return {
            "kind": "health_check_result",
            "agent_id": task.agent_id,
            "executed_by": "scripts/execute_durable_task.py",
        }
    if task.task_type == "record_observation":
        return {
            "kind": "observation_recorded",
            "agent_id": task.agent_id,
            "observation": task.payload["observation"],
            "executed_by": "scripts/execute_durable_task.py",
        }
    if task.task_type == "calibration":
        confidence = float(task.payload["confidence"])
        outcome = 1.0 if task.payload["outcome"] in (1, True) else 0.0
        return {
            "kind": "calibration_score",
            "prediction_id": task.payload.get("prediction_id"),
            "confidence": confidence,
            "outcome": outcome,
            "brier_score": (confidence - outcome) ** 2,
            "executed_by": "scripts/execute_durable_task.py",
        }
    if task.task_type == "llm_call":
        return execute_llm_call(task.payload)
    raise UnsupportedFeatureError(f"unsupported durable task_type: {task.task_type}")


def execute_llm_call(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL_DEFAULT") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    if not api_key:
        raise UnsupportedFeatureError("llm_call requires LLM_API_KEY or OPENAI_API_KEY")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": payload.get("system", "Return a concise, factual answer.")},
            {"role": "user", "content": payload["prompt"]},
        ],
        "temperature": float(payload.get("temperature", 0)),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=float(payload.get("timeout_seconds", 30))) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc
    decoded = json.loads(raw)
    content = decoded["choices"][0]["message"]["content"]
    return {
        "kind": "llm_call_result",
        "model": model,
        "latency_ms": round((time.time() - started) * 1000),
        "content": content,
        "usage": decoded.get("usage"),
        "executed_by": "scripts/execute_durable_task.py",
    }


def load_task(conn, task_id: str) -> Task:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT task_id, agent_id, task_type, payload
            FROM agent_tasks
            WHERE task_id = %s AND status IN ('queued', 'running', 'failed')
            """,
            (task_id,),
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"agent task not found or not runnable: {task_id}")
    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
    return Task(str(row["task_id"]), row["agent_id"], row["task_type"], payload)


def mark_running(conn, task_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE workflow_tasks SET status='running', started_at=COALESCE(started_at, now()), claimed_by='python-durable-executor' WHERE task_id=%s",
            (task_id,),
        )
    conn.commit()


def mark_done(conn, task_id: str, result: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE workflow_tasks SET status='done', completed_at=now(), result=%s, error=NULL WHERE task_id=%s",
            (json.dumps(result), task_id),
        )
    conn.commit()


def mark_failed(conn, task_id: str, error: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE workflow_tasks SET status='failed', completed_at=now(), error=%s WHERE task_id=%s",
            (error[:2000], task_id),
        )
    conn.commit()


def run(task_id: str) -> int:
    conn = psycopg2.connect(require_database_url())
    try:
        task = load_task(conn, task_id)
        mark_running(conn, task.task_id)
        try:
            result = execute_task_logic(task)
        except Exception as exc:
            mark_failed(conn, task.task_id, f"{exc.__class__.__name__}: {exc}")
            print(json.dumps({"status": "failed", "task_id": task.task_id, "error": str(exc)}))
            return 2
        mark_done(conn, task.task_id, result)
        print(json.dumps({"status": "done", "task_id": task.task_id, "result_kind": result.get("kind")}))
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    args = parser.parse_args()
    return run(args.task_id)


if __name__ == "__main__":
    sys.exit(main())
