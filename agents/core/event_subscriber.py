"""Kafka event subscription framework for AgentCo agents."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

# All Kafka topics per the spec event catalog
KAFKA_TOPICS = {
    "research": "agentco.research",
    "product": "agentco.product",
    "engineering": "agentco.engineering",
    "sales": "agentco.sales",
    "cx": "agentco.cx",
    "finance": "agentco.finance",
    "people": "agentco.people",
    "legal": "agentco.legal",
    "override": "agentco.override",
}

EventHandler = Callable[[dict[str, Any]], None]


class EventSubscriber:
    """Agents use this to subscribe to Kafka topics and register event handlers."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def dispatch(self, raw_event: dict[str, Any]) -> None:
        """Dispatch a received event to registered handlers after validating the envelope."""
        self._validate_envelope(raw_event)
        event_type = raw_event["event_type"]
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("[%s] No handlers for event %s", self.agent_id, event_type)
            return
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(raw_event)
                else:
                    handler(raw_event)
            except Exception:
                logger.exception("[%s] Handler error for event %s", self.agent_id, event_type)

    def _validate_envelope(self, event: dict) -> None:
        required = {"event_id", "event_type", "producer_agent_id", "timestamp", "confidence_score", "payload", "risk_level", "requires_ack"}
        missing = required - event.keys()
        if missing:
            raise ValueError(f"Malformed event envelope — missing fields: {missing}")
        score = event.get("confidence_score")
        if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
            raise ValueError(f"Invalid confidence_score in event: {score!r}")


class EventPublisher:
    """Publishes events to Kafka. All events must conform to the spec envelope."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    async def publish(self, event_type: str, payload: dict, confidence_score: float, risk_level: str, requires_ack: bool = False, correlation_id: str | None = None) -> str:
        import uuid
        from datetime import datetime

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "producer_agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence_score": confidence_score,
            "payload": payload,
            "risk_level": risk_level,
            "requires_ack": requires_ack,
            "ttl_seconds": 86400,
        }
        if correlation_id:
            event["correlation_id"] = correlation_id

        logger.info("[PUBLISH] %s → %s (confidence=%.2f)", self.agent_id, event_type, confidence_score)
        # In production: await kafka_producer.send(topic, json.dumps(event).encode())
        return event["event_id"]
