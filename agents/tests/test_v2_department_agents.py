"""
Phase 2 DoD: V2 department agents contract tests.

Verifies hardcoded invariants across Engineering, Product, and Legal V2 agents.
"""
import pytest
from calibration import create_calibration_engine
from agents.engineering.coder_agent_v2 import CoderAgentV2
from agents.engineering.reviewer_agent_v2 import ReviewerAgentV2
from agents.engineering.devops_agent_v2 import DevOpsAgentV2
from agents.product.pm_agent_v2 import PMAgentV2
from agents.legal.privacy_agent_v2 import PrivacyAgentV2


def _cal():
    return create_calibration_engine()


class TestCoderAgentV2:

    def test_can_merge_is_false(self):
        assert CoderAgentV2.CAN_MERGE is False

    def test_merge_attempt_returns_blocked(self):
        agent = CoderAgentV2(calibration_engine=_cal())
        result = agent.run({"action_type": "merge", "pr_id": "pr-123"})
        assert result["status"] == "blocked"
        assert "CAN_MERGE=False" in result["reason"]

    def test_write_code_pre_registers_claim(self):
        cal = _cal()
        agent = CoderAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "write_code",
            "ticket_id": "TICKET-42",
            "description": "Add pagination to API endpoint",
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.domain == "engineering"
        assert record.claim_type == "code_quality"
        assert record.producing_agent_id == "coder-agent"

    def test_scope_change_requires_pm_and_human(self):
        agent = CoderAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "scope_change",
            "description": "Add real-time streaming to the feature",
        })
        assert result["status"] == "awaiting_pm_and_human_approval"
        assert "override_id" in result

    def test_security_alert_always_blocks(self):
        agent = CoderAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "security_alert",
            "severity": "critical",
            "description": "SQL injection vulnerability in user input handler",
        })
        assert result["status"] == "awaiting_human_review"
        assert "override_id" in result


class TestReviewerAgentV2:

    def test_is_sole_merge_authority(self):
        assert ReviewerAgentV2.IS_SOLE_MERGE_AUTHORITY is True

    def test_merge_with_critical_vulns_blocked(self):
        agent = ReviewerAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "merge",
            "pr_id": "pr-456",
            "has_critical_vulns": True,
        })
        assert result["status"] == "merge_blocked"
        assert "zero tolerance" in result["reason"].lower()

    def test_review_below_coverage_rejected(self):
        agent = ReviewerAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "review",
            "pr_id": "pr-789",
            "test_coverage": 0.80,  # below 95% threshold
        })
        assert result["status"] == "review_rejected"

    def test_review_pre_registers_safety_claim(self):
        cal = _cal()
        agent = ReviewerAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "review",
            "pr_id": "pr-101",
            "test_coverage": 0.97,
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.claim_type == "code_review"

    def test_merge_requires_human_approval(self):
        agent = ReviewerAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "merge",
            "pr_id": "pr-202",
            "has_critical_vulns": False,
        })
        assert result["status"] == "awaiting_human_approval"


class TestDevOpsAgentV2:

    def test_rollback_thresholds_are_hardcoded(self):
        assert DevOpsAgentV2.AUTO_ROLLBACK_ERROR_RATE == 0.05
        assert DevOpsAgentV2.AUTO_ROLLBACK_LATENCY_MULTIPLIER == 3.0
        assert DevOpsAgentV2.AUTO_ROLLBACK_MEMORY_PCT == 0.90

    def test_threshold_check_triggers_on_high_error_rate(self):
        agent = DevOpsAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "check_thresholds",
            "error_rate": 0.08,
            "latency_multiplier": 1.2,
            "memory_pct": 0.60,
        })
        assert result["should_rollback"] is True
        assert any("error_rate" in t for t in result["triggers"])

    def test_threshold_check_no_trigger_when_normal(self):
        agent = DevOpsAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "check_thresholds",
            "error_rate": 0.01,
            "latency_multiplier": 1.5,
            "memory_pct": 0.70,
        })
        assert result["should_rollback"] is False

    def test_deploy_pre_registers_success_claim(self):
        cal = _cal()
        agent = DevOpsAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "deploy",
            "version": "v2.1.0",
            "environment": "production",
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.claim_type == "deployment"
        assert record.domain == "engineering"

    def test_novel_incident_hard_pause(self):
        agent = DevOpsAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "novel_incident",
            "description": "Unknown cascading failure pattern across 3 services",
        })
        assert result["status"] == "hard_pause_awaiting_human"
        assert "No auto-resolution" in result["message"]

    def test_rollback_failure_escalates_to_human(self):
        agent = DevOpsAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "auto_rollback",
            "trigger": "error_rate",
            "version": "v2.0.9",
            "rollback_failed": True,
        })
        assert result["status"] == "human_escalation_required"
        assert result["rollback_failed"] is True


class TestPMAgentV2:

    def test_feature_prioritization_pre_registers_claim(self):
        cal = _cal()
        agent = PMAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "feature_prioritization",
            "feature": "dark-mode",
            "horizon_days": 21,
            "probability": 0.80,
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.claim_type == "feature_delivery"
        assert record.probability == 0.80

    def test_scope_approval_requires_human(self):
        agent = PMAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "scope_approval",
            "requesting_agent": "coder-agent",
            "description": "Add streaming API to the search feature",
        })
        assert result["status"] == "awaiting_human_approval"


class TestPrivacyAgentV2:

    def test_autonomous_remediation_is_false(self):
        assert PrivacyAgentV2.AUTONOMOUS_REMEDIATION is False

    def test_breach_response_always_blocks(self):
        agent = PrivacyAgentV2(calibration_engine=_cal())
        result = agent.run({
            "action_type": "breach_response",
            "breach_type": "unauthorized_data_export",
            "affected_records": 15000,
        })
        assert result["status"] == "breach_escalated_awaiting_human"
        assert result["autonomous_remediation"] is False
        assert result["affected_records"] == 15000

    def test_breach_response_cannot_auto_remediate(self):
        """Even if somehow AUTONOMOUS_REMEDIATION were True, a RuntimeError would fire."""
        agent = PrivacyAgentV2(calibration_engine=_cal())
        # Confirm the class attribute is immutably False
        assert agent.AUTONOMOUS_REMEDIATION is False

    def test_compliance_check_pre_registers_claim(self):
        cal = _cal()
        agent = PrivacyAgentV2(calibration_engine=cal)
        result = agent.run({
            "action_type": "compliance_check",
            "regulation": "GDPR",
            "scope": "EU user data processing",
            "probability": 0.88,
        })
        pid = result.get("prediction_id")
        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.domain == "legal"
        assert record.producing_agent_id == "privacy-agent"
