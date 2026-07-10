"""
Phase 0 DoD: V2 BaseAgent contract tests.

Verifies:
- Agent pre-registers claims in ledger before acting
- Agent uses trusted_confidence(), NOT stated confidence
- Event envelope carries producer_prompt_version
- Escalation gate blocks on high-risk / low-confidence actions (no auto-approve)
- Audit log captures full context including trusted_confidence
"""
import pytest
import os
import uuid
from datetime import datetime, timedelta, timezone

from calibration import create_calibration_engine
from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.base_agent.audit_writer import (
    AuditUnavailableError,
    DurableAuditWriter,
    InMemoryAuditWriter,
)
from runtime.escalation.escalation_gate import HumanApprovalRequired


class ConcreteAgentV2(BaseAgentV2):
    PROMPT_VERSION = "2.0.0-test"

    def __init__(self, agent_id: str, calibration_engine=None):
        super().__init__(
            agent_id,
            calibration_engine=calibration_engine,
            allow_test_audit_writer=True,
        )

    def run(self, task: dict):
        pass


def _make_engine():
    return create_calibration_engine()


class TestBaseAgentV2Contract:

    def test_agent_pre_registers_claim_in_ledger(self):
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        pid = agent.pre_register_claim(
            claim="This action will produce a correct result",
            probability=0.75,
            resolution_criterion="Output reviewed by external auditor within 7 days",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=7),
            domain="product",
            claim_type="output_quality",
            ground_truth_source="external_auditor",
        )

        assert pid is not None
        record = cal["ledger"].get(pid)
        assert record.producing_agent_id == "test-agent"
        assert record.producing_prompt_version == "2.0.0-test"
        assert record.probability == 0.75

    def test_action_envelope_carries_prompt_version(self):
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="send_report",
            description="Send analysis report to stakeholders",
            payload={"report_id": "r-123"},
            risk_level="low",
            stated_confidence=0.80,
            domain="general",
        )
        result = agent.execute_action(action)
        envelope = result["envelope"]

        assert envelope["producer_prompt_version"] == "2.0.0-test"
        assert "confidence_score" in envelope
        assert "risk_level" in envelope
        assert "hmac_signature" in envelope

    def test_trusted_confidence_used_not_stated(self):
        """Without a track record, trusted_confidence must be < stated_confidence."""
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="analysis",
            description="Market analysis",
            payload={},
            risk_level="low",
            stated_confidence=0.90,
            domain="market_dynamics",
        )
        result = agent.execute_action(action)

        # No track record → trusted must be below stated (conservative discount applied)
        assert result["trusted_confidence"] < result["stated_confidence"]

    def test_high_risk_action_blocks_without_approval(self):
        """high-risk actions MUST block and raise HumanApprovalRequired."""
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="deploy_config",
            description="Deploy new configuration to production",
            payload={"config_version": "v2.1"},
            risk_level="high",
            stated_confidence=0.95,
            domain="engineering",
        )
        with pytest.raises(HumanApprovalRequired) as exc_info:
            agent.execute_action(action)

        err = exc_info.value
        assert err.override_id is not None
        assert err.risk_level == "high"

    def test_no_auto_approve_on_timeout(self):
        """Verifies no code path auto-approves a blocked action."""
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="critical_op",
            description="Critical operation",
            payload={},
            risk_level="critical",
            stated_confidence=0.99,
        )
        with pytest.raises(HumanApprovalRequired) as exc_info:
            agent.execute_action(action)

        override_id = exc_info.value.override_id
        pending = agent.get_pending_approvals()
        assert any(p.override_id == override_id for p in pending)
        assert not any(p.approved for p in pending)

    def test_action_proceeds_after_human_approval(self):
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="deploy_config",
            description="Deploy config",
            payload={},
            risk_level="high",
            stated_confidence=0.85,
        )
        try:
            agent.execute_action(action)
        except HumanApprovalRequired as exc:
            token = agent.approve_action(exc.override_id, approver_id="human-governor-1")

        result = agent.execute_action(action, pre_approved_token=token)
        assert result["outcome"] == "executed"

    def test_audit_log_captures_trusted_and_stated(self):
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="analysis",
            description="Risk analysis",
            payload={},
            risk_level="low",
            stated_confidence=0.88,
            domain="financial_forecast",
        )
        agent.execute_action(action)

        log = agent.get_audit_log()
        assert len(log) == 1
        entry = log[0]
        assert entry["agent_id"] == "test-agent"
        assert entry["prompt_version"] == "2.0.0-test"
        assert entry["stated_confidence"] == 0.88
        assert "trusted_confidence" in entry
        assert entry["outcome"] == "executed"

    def test_envelope_missing_confidence_score_would_fail_bus(self):
        """Validates envelope always includes confidence_score (bus rejects without it)."""
        cal = _make_engine()
        agent = ConcreteAgentV2("test-agent", calibration_engine=cal)

        action = AgentActionV2(
            action_type="notify",
            description="Send notification",
            payload={"msg": "hello"},
            risk_level="low",
            stated_confidence=0.8,
        )
        result = agent.execute_action(action)
        envelope = result["envelope"]

        # All required V2 envelope fields must be present
        for required_field in ["producer_prompt_version", "confidence_score", "risk_level", "hmac_signature"]:
            assert required_field in envelope, f"Missing required envelope field: {required_field}"


class _FailingAuditWriter:
    def write(self, entry):
        raise AuditUnavailableError("audit sink unavailable")


class TestBaseAgentV2DurableAudit:
    def _live_decision_log(self):
        dsn = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not dsn:
            pytest.skip("live-service: no AGENTCO_TEST_DATABASE_URL or DATABASE_URL configured")
        psycopg2 = pytest.importorskip("psycopg2", reason="live-service: psycopg2 unavailable")
        try:
            conn = psycopg2.connect(dsn, connect_timeout=2)
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM decision_log LIMIT 1")
            return dsn, psycopg2
        except Exception as exc:
            pytest.skip(f"live-service: decision_log unavailable: {exc}")

    def test_high_risk_action_with_failing_audit_writer_is_blocked(self):
        cal = _make_engine()
        agent = ConcreteAgentV2("audit-fail-agent", calibration_engine=cal)
        action = AgentActionV2(
            action_type="deploy_config",
            description="Deploy approved config",
            payload={},
            risk_level="high",
            stated_confidence=0.9,
        )
        try:
            agent.execute_action(action)
        except HumanApprovalRequired as exc:
            token = agent.approve_action(exc.override_id, approver_id="human-governor-1")

        agent._audit_writer = _FailingAuditWriter()
        with pytest.raises(AuditUnavailableError, match="audit sink unavailable"):
            agent.execute_action(action, pre_approved_token=token)

    def test_in_memory_audit_writer_requires_explicit_test_flag(self):
        with pytest.raises(AuditUnavailableError):
            InMemoryAuditWriter()
        writer = InMemoryAuditWriter(allow_test_mode=True)
        assert writer.write({"trace_id": "t-1"})["backend"] == "memory"

    def test_durable_audit_writer_round_trip_live_postgres(self):
        dsn, _ = self._live_decision_log()

        agent = ConcreteAgentV2(
            "durable-audit-agent",
            calibration_engine=_make_engine(),
        )
        agent._audit_writer = DurableAuditWriter(dsn)
        action = AgentActionV2(
            action_type="analysis",
            description="Durable audit round-trip",
            payload={},
            risk_level="low",
            stated_confidence=0.8,
        )

        result = agent.execute_action(action)

        assert result["outcome"] == "executed"
        assert agent.audit_failure_count == 0

    def test_lost_ack_retry_uses_same_attempt_id_and_action_proceeds_live_postgres(self):
        dsn, psycopg2 = self._live_decision_log()
        agent = ConcreteAgentV2(
            f"lost-ack-agent-{uuid.uuid4().hex[:8]}",
            calibration_engine=_make_engine(),
        )
        action = AgentActionV2(
            action_type="deploy_config",
            description="Approved high-risk action with lost audit ACK",
            payload={},
            risk_level="high",
            stated_confidence=0.9,
        )
        try:
            agent.execute_action(action)
        except HumanApprovalRequired as exc:
            token = agent.approve_action(exc.override_id, approver_id="human-governor-1")

        writer = DurableAuditWriter(dsn, max_retries=2, retry_backoff_seconds=0)
        original_write_once = writer._write_once
        calls = {"count": 0}

        def lost_ack_once(data, *, attempt_id, psycopg2):
            calls["count"] += 1
            ack = original_write_once(data, attempt_id=attempt_id, psycopg2=psycopg2)
            if calls["count"] == 1:
                raise AuditUnavailableError("simulated lost ack after commit")
            return ack

        writer._write_once = lost_ack_once
        agent._audit_writer = writer

        result = agent.execute_action(action, pre_approved_token=token)

        assert result["outcome"] == "executed"
        assert agent.audit_failure_count == 0
        assert calls["count"] == 2
        with psycopg2.connect(dsn, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT attempt_id, COUNT(*)::int
                      FROM decision_log
                     WHERE agent_id = %s
                       AND input_summary = %s
                     GROUP BY attempt_id
                    """,
                    (agent.agent_id, action.description),
                )
                rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] is not None
        assert rows[0][1] == 1

    def test_genuine_audit_write_failure_exhausts_retries_and_writes_zero_rows_live_postgres(self):
        dsn, psycopg2 = self._live_decision_log()
        attempt_id = str(uuid.uuid4())
        writer = DurableAuditWriter(dsn, max_retries=2, retry_backoff_seconds=0)

        def fail_before_insert(data, *, attempt_id, psycopg2):
            raise AuditUnavailableError("simulated write failure before insert")

        writer._write_once = fail_before_insert

        with pytest.raises(AuditUnavailableError, match="simulated write failure before insert"):
            writer.write({
                "attempt_id": attempt_id,
                "agent_id": "write-failure-agent",
                "action_type": "decision",
                "description": "this write never reaches postgres",
                "trusted_confidence": 0.6,
                "risk_level": "high",
                "outcome": "blocked",
                "trace_id": str(uuid.uuid4()),
            })

        with psycopg2.connect(dsn, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*)::int FROM decision_log WHERE attempt_id = %s", (attempt_id,))
                count = cur.fetchone()[0]
        assert count == 0
