"""Tests for CEO-Agent strategic reasoning and escalation logic."""
import pytest
from unittest.mock import AsyncMock
from core.types import RiskLevel
from runtime.base_agent.model_tiers import model_for


@pytest.mark.asyncio
async def test_strategic_pivot_requires_human_approval():
    from executive.ceo_agent import CEOAgent
    agent = CEOAgent.__new__(CEOAgent)
    agent.AGENT_ID = "ceo-agent"
    agent.model = model_for(agent.AGENT_ID)
    agent.session_id = "test"
    agent.client = None
    agent.llm_call = AsyncMock(return_value="Strategic analysis...")
    agent.publish_event = AsyncMock()

    result = await agent._process_strategic_signal({
        "signal": {"type": "market_shift"},
        "requires_pivot": True,
    })

    assert result.requires_human_approval is True
    assert result.risk_level == RiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_routine_goal_setting_autonomous():
    from executive.ceo_agent import CEOAgent
    agent = CEOAgent.__new__(CEOAgent)
    agent.AGENT_ID = "ceo-agent"
    agent.model = model_for(agent.AGENT_ID)
    agent.session_id = "test"
    agent.client = None
    agent.llm_call = AsyncMock(return_value="Q3 goals: ...")
    agent.get_tools = lambda: []

    result = await agent._quarterly_goal_setting({"okr_inputs": {"product": "ship v2"}})

    assert result.requires_human_approval is False
    assert result.confidence_score >= 0.7
