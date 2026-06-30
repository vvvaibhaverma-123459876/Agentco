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


SUPPORTED_TASK_TYPES = {"llm_call", "calibration", "health_check", "record_observation", "review", "decision"}


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
    elif task_type == "review":
        if not isinstance(payload.get("subject"), str) or not payload["subject"].strip():
            raise PayloadValidationError("review payload requires non-empty string field: subject")
        if not isinstance(payload.get("criteria"), list) or not payload["criteria"]:
            raise PayloadValidationError("review payload requires non-empty array field: criteria")
    elif task_type == "decision":
        if not isinstance(payload.get("options"), list) or len(payload["options"]) < 2:
            raise PayloadValidationError("decision payload requires at least two options")
        if not isinstance(payload.get("criteria"), list) or not payload["criteria"]:
            raise PayloadValidationError("decision payload requires non-empty array field: criteria")
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
    if task.task_type == "review":
        return execute_review(task.payload)
    if task.task_type == "decision":
        return execute_decision(task.payload)
    raise UnsupportedFeatureError(f"unsupported durable task_type: {task.task_type}")


def execute_llm_call(payload: dict[str, Any]) -> dict[str, Any]:
    decoded, latency_ms, model = call_openai_json(
        [
            {"role": "system", "content": payload.get("system", "Return JSON with fields answer and confidence.")},
            {"role": "user", "content": payload["prompt"]},
        ],
        timeout_seconds=float(payload.get("timeout_seconds", 30)),
    )
    return {
        "kind": "llm_call_result",
        "model": model,
        "latency_ms": latency_ms,
        "answer": decoded.get("answer", decoded),
        "confidence": _confidence(decoded.get("confidence", 0)),
        "usage": decoded.get("usage"),
        "executed_by": "scripts/execute_durable_task.py",
    }


def execute_review(payload: dict[str, Any]) -> dict[str, Any]:
    decoded, latency_ms, model = call_openai_json(
        [
            {
                "role": "system",
                "content": (
                    "You are AgentCo Review Service. Return JSON keys: decision, findings, "
                    "required_changes, confidence, evidence_ids_used. decision must be approve, "
                    "changes_requested, reject, or escalate."
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
        timeout_seconds=float(payload.get("timeout_seconds", 30)),
    )
    decision = str(decoded.get("decision", "")).lower()
    if decision not in {"approve", "changes_requested", "reject", "escalate"}:
        raise RuntimeError(f"review service returned invalid decision: {decision}")
    return {
        "kind": "review_result",
        "decision": decision,
        "findings": decoded.get("findings", []),
        "required_changes": decoded.get("required_changes", []),
        "confidence": _confidence(decoded.get("confidence", 0)),
        "evidence_ids_used": decoded.get("evidence_ids_used", []),
        "model": model,
        "latency_ms": latency_ms,
        "executed_by": "scripts/execute_durable_task.py",
    }


def execute_decision(payload: dict[str, Any]) -> dict[str, Any]:
    decoded, latency_ms, model = call_openai_json(
        [
            {
                "role": "system",
                "content": (
                    "You are AgentCo Decision Service. Return JSON keys: selected_option, "
                    "rationale, confidence, evidence_ids_used, escalation_required. selected_option "
                    "must exactly match a provided option unless escalation_required is true."
                ),
            },
            {"role": "user", "content": json.dumps(payload)},
        ],
        timeout_seconds=float(payload.get("timeout_seconds", 30)),
    )
    options = payload["options"]
    selected = decoded.get("selected_option")
    escalation_required = decoded.get("escalation_required") is True
    if not escalation_required and selected not in options:
        raise RuntimeError(f"decision service returned option not present in payload: {selected}")
    return {
        "kind": "decision_result",
        "selected_option": None if escalation_required else selected,
        "rationale": str(decoded.get("rationale", "")),
        "confidence": _confidence(decoded.get("confidence", 0)),
        "evidence_ids_used": decoded.get("evidence_ids_used", []),
        "escalation_required": escalation_required,
        "model": model,
        "latency_ms": latency_ms,
        "executed_by": "scripts/execute_durable_task.py",
    }


def call_openai_json(messages: list[dict[str, str]], timeout_seconds: float) -> tuple[dict[str, Any], int, str]:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL_DEFAULT") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    if not api_key:
        raise UnsupportedFeatureError("llm_call requires LLM_API_KEY or OPENAI_API_KEY")

    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc
    decoded = json.loads(raw)
    content = json.loads(decoded["choices"][0]["message"]["content"])
    if decoded.get("usage"):
        content["usage"] = decoded["usage"]
    return content, round((time.time() - started) * 1000), model


def _confidence(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, numeric))


def load_task(conn, task_id: str) -> Task:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT agent_tasks.task_id,
                   agent_tasks.agent_id,
                   agent_tasks.task_type,
                   agent_tasks.payload
            FROM agent_tasks
            JOIN agent_identities ON agent_identities.agent_key = agent_tasks.agent_id
            JOIN actors ON actors.id = agent_identities.actor_id
            WHERE task_id = %s
              AND agent_tasks.status IN ('queued', 'running', 'failed')
              AND agent_identities.status = 'active'
              AND actors.actor_type = 'agent'
              AND actors.status = 'active'
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
