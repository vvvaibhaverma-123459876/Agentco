"""
Phase 1 DoD: V2 operating slice tests.

Verifies Config-Agent, CEO, CFO, COO V2 agents:
- Cannot self-modify (Config-Agent)
- Always block without human approval on critical actions
- Pre-register claims before critical decisions
- Use trusted_confidence via V2 runtime
"""
import pytest
from calibration import create_calibration_engine
from agents.people_ops.config_agent_v2 import ConfigAgentV2
from agents.executive.ceo_agent_v2 import CEOAgentV2
from agents.executive.cfo_agent_v2 import CFOAgentV2
from agents.executive.coo_agent_v2 import COOAgentV2


def _cal():
    return create_calibration_engine()


class TestConfigAgentV2:

    def test_cannot_modify_own_prompt(self):
        agent = ConfigAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "update_prompt",
            "target_agent_id": "config-agent",
            "new_prompt_version": "evil-v3",
        })
        assert result["status"] == "blocked"
        assert "cannot modify its own prompt" in result["reason"].lower()

    def test_prompt_update_requires_human_approval(self):
        agent = ConfigAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "update_prompt",
            "target_agent_id": "ceo-agent",
            "new_prompt_version": "2.1.0",
        })
        assert result["status"] == "awaiting_human_approval"
        assert "override_id" in result

    def test_prompt_update_pre_registers_claim(self):
        cal = _cal()
        agent = ConfigAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "update_prompt",
            "target_agent_id": "coo-agent",
            "new_prompt_version": "2.0.1",
        })
        # Claim should be registered even though action is blocked
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.domain == "engineering"
        assert record.claim_type == "config_change"

    def test_rollback_requires_human_approval(self):
        agent = ConfigAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "rollback",
            "target_agent_id": "cfo-agent",
            "target_version": "1.0.0",
        })
        assert result["status"] == "awaiting_human_approval"

    def test_proceed_after_human_approves_rollback(self):
        agent = ConfigAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "rollback",
            "target_agent_id": "cfo-agent",
            "target_version": "1.0.0",
        })
        override_id = result["override_id"]
        token = agent.approve_action(override_id, approver_id="governor-1")

        # Re-run with token
        from runtime.escalation.escalation_gate import HumanApprovalRequired
        from runtime.base_agent.base_agent_v2 import AgentActionV2
        action = AgentActionV2(
            action_type="rollback_prompt",
            description="Rollback cfo-agent to 1.0.0",
            payload={"target_agent_id": "cfo-agent", "target_version": "1.0.0", "sla_seconds": 60},
            risk_level="critical",
            stated_confidence=0.90,
            domain="engineering",
            claim_type="config_rollback",
        )
        exec_result = agent.execute_action(action, pre_approved_token=token)
        assert exec_result["outcome"] == "executed"


class TestCEOAgentV2:

    def test_strategic_pivot_blocked_requires_human(self):
        agent = CEOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "strategic_pivot",
            "description": "Expand into APAC market",
            "horizon_days": 90,
        })
        assert result["status"] == "awaiting_human_approval"
        assert "prediction_id" in result

    def test_strategic_pivot_pre_registers_claim(self):
        cal = _cal()
        agent = CEOAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "strategic_pivot",
            "description": "Expand into EU market",
            "horizon_days": 60,
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.domain == "strategy"
        assert record.probability == 0.65

    def test_large_budget_requires_approval(self):
        agent = CEOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "approve_budget",
            "amount": 600_000,
            "purpose": "New data center",
        })
        assert result["status"] == "awaiting_human_approval"


class TestCFOAgentV2:

    def test_spend_below_threshold_auto_approved(self):
        agent = CFOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "approve_spend",
            "amount": 5_000,
            "purpose": "Office supplies",
        })
        assert result["outcome"] == "executed"

    def test_spend_above_threshold_requires_human(self):
        agent = CFOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "approve_spend",
            "amount": 75_000,
            "purpose": "Cloud infrastructure upgrade",
        })
        assert result["status"] == "awaiting_human_approval"

    def test_runway_alert_fires_at_6_months(self):
        cal = _cal()
        agent = CFOAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "runway_check",
            "cash_balance": 300_000,
            "monthly_burn": 60_000,   # 5 months runway
        })
        assert result["status"] == "runway_alert"
        assert result["runway_months"] == pytest.approx(5.0, abs=0.1)
        # Should have pre-registered a fundraising claim
        pid = result.get("prediction_id")
        assert pid is not None

    def test_runway_ok_no_alert(self):
        agent = CFOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "runway_check",
            "cash_balance": 1_000_000,
            "monthly_burn": 60_000,   # 16+ months runway
        })
        assert result["status"] == "runway_ok"
        assert result["runway_months"] > 6


class TestCOOAgentV2:

    def test_structural_change_requires_ceo_and_human(self):
        agent = COOAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "structural_change",
            "description": "Merge Sales and Marketing departments",
        })
        assert result["status"] == "awaiting_ceo_and_human_approval"
        assert "prediction_id" in result

    def test_operational_target_pre_registers_claim(self):
        cal = _cal()
        agent = COOAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "operational_target",
            "metric": "customer_satisfaction_score",
            "target_value": 90,
            "horizon_days": 30,
            "probability": 0.75,
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.domain == "operations"
        assert record.probability == 0.75
