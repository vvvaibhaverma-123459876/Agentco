"""Tests for event envelope validation."""
import pytest
import asyncio
from core.event_subscriber import EventSubscriber, EventPublisher


def make_valid_event(**overrides):
    event = {
        "event_id": "abc-123",
        "event_type": "research.insight.published",
        "producer_agent_id": "research-agent",
        "timestamp": "2026-06-16T12:00:00Z",
        "confidence_score": 0.85,
        "payload": {"insight_id": "i1"},
        "risk_level": "low",
        "requires_ack": False,
    }
    event.update(overrides)
    return event


def test_valid_envelope_dispatches():
    sub = EventSubscriber("pm-agent")
    received = []
    sub.on("research.insight.published", lambda e: received.append(e))
    asyncio.run(sub.dispatch(make_valid_event()))
    assert len(received) == 1


def test_missing_field_raises():
    sub = EventSubscriber("pm-agent")
    event = make_valid_event()
    del event["confidence_score"]
    with pytest.raises(ValueError, match="missing fields"):
        asyncio.run(sub.dispatch(event))


def test_invalid_confidence_raises():
    sub = EventSubscriber("pm-agent")
    with pytest.raises(ValueError, match="confidence_score"):
        asyncio.run(sub.dispatch(make_valid_event(confidence_score=1.5)))


def test_no_handler_does_not_raise():
    sub = EventSubscriber("pm-agent")
    asyncio.run(sub.dispatch(make_valid_event(event_type="unknown.event")))
