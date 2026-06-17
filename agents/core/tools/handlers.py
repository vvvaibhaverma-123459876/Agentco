"""
Real tool handlers for AgentCo.

Each handler is an async callable that receives tool_input (dict) and returns a result.
Handlers that need DB access use the same DATABASE_URL env var as the calibration layer.
Permission enforcement (which agent can call which tool) is done by tool_registry.execute_tool()
BEFORE dispatching to a handler — handlers do NOT re-check agent identity.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import psycopg2

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"
)


def _conn():
    return psycopg2.connect(_DB_URL)


# ──────────────────────────────────────────────────────────────────────────────
# AUDIT LOG tool  — agents write structured audit entries via this tool
# ──────────────────────────────────────────────────────────────────────────────

async def handle_audit_log(inp: dict[str, Any]) -> dict:
    """Write an entry to the decision_log table. Returns log_id."""
    required = ["agent_id", "action_type", "input_summary", "output_summary",
                "confidence_score", "risk_level"]
    for f in required:
        if f not in inp:
            raise ValueError(f"audit_log tool: missing required field '{f}'")

    import hashlib  # stdlib
    conn = _conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        # Fetch last chain hash
        cur.execute("SELECT chain_hash FROM decision_log ORDER BY timestamp DESC, log_id DESC LIMIT 1")
        row = cur.fetchone()
        prev_hash = row[0] if row else "0" * 64

        import uuid
        log_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        content = json.dumps({
            "log_id": log_id, "timestamp": timestamp,
            "prev_hash": prev_hash, **inp
        })
        chain_hash = hashlib.sha256((prev_hash + content).encode()).hexdigest()

        cur.execute(
            """INSERT INTO decision_log
               (log_id, agent_id, action_type, input_summary, output_summary,
                confidence_score, risk_level, human_approved, session_id,
                timestamp, chain_hash, prev_hash)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (log_id, inp["agent_id"], inp["action_type"],
             inp["input_summary"][:500], inp["output_summary"][:500],
             float(inp["confidence_score"]), inp["risk_level"],
             bool(inp.get("human_approved", False)),
             inp.get("session_id"),
             timestamp, chain_hash, prev_hash)
        )
    conn.close()
    logger.info("TOOL audit_log: wrote log_id=%s for agent=%s", log_id, inp["agent_id"])
    return {"log_id": log_id, "chain_hash": chain_hash[:16] + "..."}


# ──────────────────────────────────────────────────────────────────────────────
# EVENT BUS tool — agents publish events via this tool
# ──────────────────────────────────────────────────────────────────────────────

async def handle_event_bus(inp: dict[str, Any]) -> dict:
    """Publish a signed event to Kafka + event_history. Returns event_id."""
    import uuid, hmac, hashlib
    required = ["event_type", "producer_agent_id", "payload", "confidence_score",
                "risk_level", "requires_ack"]
    for f in required:
        if f not in inp:
            raise ValueError(f"event_bus tool: missing required field '{f}'")

    event_id = inp.get("event_id") or str(uuid.uuid4())
    timestamp = inp.get("timestamp") or datetime.now(timezone.utc).isoformat()
    signing_key = os.environ.get("EVENT_BUS_SIGNING_KEY", "dev-key-replace-in-production")

    event = {
        "event_id": event_id,
        "event_type": inp["event_type"],
        "producer_agent_id": inp["producer_agent_id"],
        "timestamp": timestamp,
        "confidence_score": float(inp["confidence_score"]),
        "payload": inp["payload"],
        "correlation_id": inp.get("correlation_id"),
        "risk_level": inp["risk_level"],
        "requires_ack": bool(inp["requires_ack"]),
        "ttl_seconds": int(inp.get("ttl_seconds", 86400)),
    }
    signature = hmac.new(signing_key.encode(), json.dumps(event).encode(), hashlib.sha256).hexdigest()
    signed = {**event, "signature": signature}

    # Produce to Kafka
    from kafka import KafkaProducer
    brokers = os.environ.get("KAFKA_BROKERS", "localhost:9092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=brokers.split(","),
            value_serializer=lambda v: json.dumps(v).encode(),
            request_timeout_ms=5000,
        )
        topic_map = {
            "research": "agentco.research", "product": "agentco.product",
            "engineering": "agentco.events", "audit": "agentco.audit",
        }
        domain = inp["event_type"].split(".")[0]
        topic = topic_map.get(domain, "agentco.events")
        producer.send(topic, key=event_id.encode(), value=signed)
        producer.flush(timeout=5)
        producer.close()
    except Exception as e:
        logger.warning("TOOL event_bus: Kafka publish failed (continuing): %s", e)

    # Persist to event_history
    conn = _conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO event_history
               (event_id, event_type, producer_agent_id, timestamp, confidence_score,
                payload, correlation_id, risk_level, requires_ack, ttl_seconds)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (event_id) DO NOTHING""",
            (event_id, event["event_type"], event["producer_agent_id"],
             event["timestamp"], event["confidence_score"],
             json.dumps(event["payload"]), event.get("correlation_id"),
             event["risk_level"], event["requires_ack"], event["ttl_seconds"])
        )
    conn.close()
    logger.info("TOOL event_bus: published event_id=%s type=%s", event_id, inp["event_type"])
    return {"event_id": event_id, "topic": topic, "signature": signature[:16] + "..."}


# ──────────────────────────────────────────────────────────────────────────────
# SHARED KNOWLEDGE tool — research/voice/ceo/cfo/coo can write; all can read
# ──────────────────────────────────────────────────────────────────────────────

async def handle_shared_knowledge_read(inp: dict[str, Any]) -> dict:
    """Read from shared_knowledge (full-text fallback; vector search if embedding svc up)."""
    q = inp.get("query", "")
    top_k = int(inp.get("top_k", 5))
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT key, content, tags, confidence_score
               FROM shared_knowledge
               WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
                  OR content ILIKE %s
               ORDER BY confidence_score DESC LIMIT %s""",
            (q, f"%{q}%", top_k)
        )
        rows = cur.fetchall()
    conn.close()
    results = [{"key": r[0], "content": r[1], "tags": r[2], "confidence_score": float(r[3])}
               for r in rows]
    return {"results": results, "count": len(results)}


async def handle_shared_knowledge_write(inp: dict[str, Any]) -> dict:
    """Write to shared_knowledge. Permission already enforced by tool_registry."""
    required = ["key", "content", "confidence_score", "agent_id"]
    for f in required:
        if f not in inp:
            raise ValueError(f"shared_knowledge tool: missing '{f}'")
    conn = _conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO shared_knowledge (key, content, tags, source_agent_id, confidence_score)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (key) DO UPDATE
                 SET content=EXCLUDED.content, tags=EXCLUDED.tags,
                     confidence_score=EXCLUDED.confidence_score, updated_at=NOW()""",
            (inp["key"], inp["content"], inp.get("tags", []),
             inp["agent_id"], float(inp["confidence_score"]))
        )
    conn.close()
    return {"ok": True, "key": inp["key"]}


# ──────────────────────────────────────────────────────────────────────────────
# AGENT MEMORY tool — per-agent namespaced read/write
# ──────────────────────────────────────────────────────────────────────────────

async def handle_memory_read(inp: dict[str, Any]) -> dict:
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT value FROM agent_memory
               WHERE agent_id=%s AND namespace=%s AND key=%s
                 AND (expires_at IS NULL OR expires_at > NOW())""",
            (inp["agent_id"], inp.get("namespace", "default"), inp["key"])
        )
        row = cur.fetchone()
    conn.close()
    return {"value": row[0] if row else None, "found": row is not None}


async def handle_memory_write(inp: dict[str, Any]) -> dict:
    conn = _conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO agent_memory (agent_id, namespace, key, value, ttl_seconds)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (agent_id, namespace, key)
               DO UPDATE SET value=%s, ttl_seconds=%s, updated_at=NOW()""",
            (inp["agent_id"], inp.get("namespace", "default"), inp["key"],
             json.dumps(inp["value"]), inp.get("ttl_seconds"),
             json.dumps(inp["value"]), inp.get("ttl_seconds"))
        )
    conn.close()
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# PROMPT REGISTRY tool — read versioned prompts
# ──────────────────────────────────────────────────────────────────────────────

async def handle_prompt_registry_read(inp: dict[str, Any]) -> dict:
    conn = _conn()
    with conn.cursor() as cur:
        if "version" in inp:
            cur.execute(
                "SELECT * FROM prompt_registry WHERE agent_id=%s AND version=%s",
                (inp["agent_id"], inp["version"])
            )
        else:
            cur.execute(
                "SELECT * FROM prompt_registry WHERE agent_id=%s ORDER BY created_at DESC LIMIT 1",
                (inp["agent_id"],)
            )
        row = cur.fetchone()
        cols = [d[0] for d in cur.description] if cur.description else []
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, **dict(zip(cols, row))}


# ──────────────────────────────────────────────────────────────────────────────
# HUMAN OVERRIDE tool — enqueue for approval
# ──────────────────────────────────────────────────────────────────────────────

async def handle_human_override(inp: dict[str, Any]) -> dict:
    """Enqueue a human override request. Returns request_id; action is BLOCKED."""
    import uuid
    required = ["agent_id", "action", "risk_level", "context"]
    for f in required:
        if f not in inp:
            raise ValueError(f"human_override tool: missing '{f}'")

    sla_map = {
        "config_change": 4, "spend_approval": 2, "strategic_pivot": 8,
        "breach_suspected": 0.5, "rollback_failure": 0.25, "default": 4
    }
    sla_hours = sla_map.get(inp["action"], sla_map["default"])
    expires_at = datetime.now(timezone.utc).timestamp() + sla_hours * 3600

    conn = _conn()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO override_queue
               (agent_id, action, risk_score, risk_level, context, sla_hours, expires_at)
               VALUES (%s,%s,%s,%s,%s,%s, to_timestamp(%s))
               RETURNING request_id, expires_at""",
            (inp["agent_id"], inp["action"],
             float(inp.get("risk_score", 0)), inp["risk_level"],
             json.dumps(inp["context"]), sla_hours, expires_at)
        )
        row = cur.fetchone()
    conn.close()
    request_id = str(row[0])
    logger.warning("TOOL human_override: queued request_id=%s agent=%s action=%s",
                   request_id, inp["agent_id"], inp["action"])
    return {"request_id": request_id, "status": "pending", "sla_hours": sla_hours,
            "message": "Action is BLOCKED pending human approval"}
