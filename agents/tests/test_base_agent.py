"""Tests for BaseAgent core guarantees."""
import pytest
from unittest.mock import AsyncMock, patch

from core.base_agent import BaseAgent, GovernanceUnavailableError
from core.types import AgentOutput, RiskLevel
from core.confidence_scorer import validate_confidence_attached
from runtime.base_agent.audit_writer import AuditUnavailableError, InMemoryAuditWriter


def test_validate_confidence_attached_passes():
    validate_confidence_attached({"confidence_score": 0.85})


def test_validate_confidence_attached_missing():
    with pytest.raises(ValueError, match="confidence_score missing"):
        validate_confidence_attached({"content": "hello"})


def test_validate_confidence_attached_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        validate_confidence_attached({"confidence_score": 1.5})


def test_agent_output_trust_levels():
    cases = [
        (0.95, "verified"),
        (0.80, "trusted"),
        (0.60, "provisional"),
        (0.40, "unverified"),
        (0.20, "rejected"),
    ]
    for score, expected_trust in cases:
        output = AgentOutput(content={}, confidence_score=score, risk_level=RiskLevel.LOW, rationale="test")
        assert output.trust_level().value == expected_trust, f"score={score}"


def test_risk_level_from_confidence():
    from core.confidence_scorer import compute_risk_level
    assert compute_risk_level(0.95, "general") == RiskLevel.LOW
    assert compute_risk_level(0.60, "general") == RiskLevel.MEDIUM
    assert compute_risk_level(0.40, "general") == RiskLevel.HIGH
    assert compute_risk_level(0.20, "config_change") == RiskLevel.CRITICAL


class _FailingAuditWriter:
    def write(self, entry):
        raise AuditUnavailableError("audit unavailable")


class _ConcreteV1Agent(BaseAgent):
    AGENT_ID = "v1-test-agent"
    DEPARTMENT = "test"

    def __init__(self, output, audit_writer):
        self._output = output
        super().__init__(audit_writer=audit_writer)

    def get_system_prompt(self):
        return "test"

    def get_tools(self):
        return []

    async def execute_task(self, task):
        return self._output


@pytest.mark.asyncio
async def test_v1_high_risk_audit_failure_blocks_output():
    agent = _ConcreteV1Agent(
        AgentOutput(
            content="SHOULD NOT RETURN",
            confidence_score=0.8,
            risk_level=RiskLevel.HIGH,
            rationale="test",
        ),
        audit_writer=_FailingAuditWriter(),
    )

    with pytest.raises(GovernanceUnavailableError, match="audit unavailable"):
        await agent.run({"type": "dangerous"})


@pytest.mark.asyncio
async def test_v1_high_risk_records_override_and_blocks_output():
    writer = InMemoryAuditWriter(allow_test_mode=True)
    agent = _ConcreteV1Agent(
        AgentOutput(
            content="SHOULD NOT RETURN",
            confidence_score=0.8,
            risk_level=RiskLevel.HIGH,
            rationale="test",
        ),
        audit_writer=writer,
    )

    with patch("core.tools.handlers.handle_human_override", new=AsyncMock(return_value={"request_id": "ovr-1"})):
        with pytest.raises(GovernanceUnavailableError, match="override_request_id=ovr-1"):
            await agent.run({"type": "dangerous"})

    assert len(writer.entries) == 1
