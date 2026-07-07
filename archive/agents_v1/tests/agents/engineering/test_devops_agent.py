"""Tests for DevOps-Agent auto-rollback logic and hard constraints."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from core.types import RiskLevel
from runtime.base_agent.model_tiers import model_for


@pytest.mark.asyncio
async def test_deploy_without_reviewer_approval_blocked():
    from engineering.devops_agent import DevOpsAgent
    agent = DevOpsAgent.__new__(DevOpsAgent)
    agent.AGENT_ID = "devops-agent"
    agent.model = model_for(agent.AGENT_ID)
    agent.session_id = "test"

    result = await agent._deploy({"reviewer_approved": False})
    assert result.risk_level == RiskLevel.CRITICAL
    assert "blocked" in str(result.content).lower() or result.confidence_score == 0.99


@pytest.mark.asyncio
async def test_rollback_triggered_by_error_rate():
    from engineering.devops_agent import DevOpsAgent
    agent = DevOpsAgent.__new__(DevOpsAgent)
    agent.AGENT_ID = "devops-agent"
    agent.model = model_for(agent.AGENT_ID)
    agent.session_id = "test"
    agent.client = None

    # Patch publish_event to avoid real Kafka call
    agent.publish_event = AsyncMock()

    result = await agent._check_rollback_trigger({
        "error_rate": 0.10,  # above 5% threshold
        "latency_multiplier": 1.0,
        "memory_pct": 0.5,
        "deployment_id": "dep-001",
        "previous_stable_version": "v1.2.0",
    })

    assert result.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)
    agent.publish_event.assert_called_once()


@pytest.mark.asyncio
async def test_no_rollback_when_metrics_healthy():
    from engineering.devops_agent import DevOpsAgent
    agent = DevOpsAgent.__new__(DevOpsAgent)
    agent.AGENT_ID = "devops-agent"
    agent.model = model_for(agent.AGENT_ID)
    agent.session_id = "test"
    agent.publish_event = AsyncMock()

    result = await agent._check_rollback_trigger({
        "error_rate": 0.01,
        "latency_multiplier": 1.1,
        "memory_pct": 0.60,
    })

    assert result.risk_level == RiskLevel.LOW
    agent.publish_event.assert_not_called()
