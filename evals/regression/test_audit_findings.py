"""
Regression tests encoding the 2026-06-16 adversarial audit findings.

Each test reproduces a bug the audit found and asserts the fixed behaviour, so the
violation can never silently return. See evals/audit/audit_report_2026-06-16.md.
"""
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import EscalationGate
from runtime.base_agent.structured_output import get_validated_output


class _ConcreteAgent(BaseAgentV2):
    PROMPT_VERSION = "audit-regression-1.0"
    def run(self, task):  # pragma: no cover - not exercised
        pass


def _resolve_n(cal, agent_id, domain, n, outcome, probability=0.9):
    """Pre-register and resolve n predictions for an agent, returning the records."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    records = []
    for i in range(n):
        reg = PredictionRegistration(
            claim=f"{agent_id} claim {i}",
            probability=probability,
            confidence_basis={"method": "test"},
            producing_agent_id=agent_id,
            producing_prompt_version="1.0",
            resolution_criterion="External review",
            resolution_date=past,
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain=domain,
            claim_type="general",
        )
        pid = cal["ledger"].pre_register(reg)
        cal["resolution"].resolve(pid, outcome=outcome, ground_truth_source="external_auditor", evidence="e")
        records.append(cal["ledger"].get(pid))
    return records


# ---------------------------------------------------------------------------
# HIGH-1 — get_sample_count must not crash for an agent WITH a track record
# ---------------------------------------------------------------------------

class TestHigh1SampleCount:
    def test_get_sample_count_with_track_record(self):
        cal = create_calibration_engine()
        _resolve_n(cal, "agent-x", "sales", n=3, outcome=True)
        # Before the fix this raised AttributeError: 'TrustScore' has no attribute 'n_resolved'
        count = cal["trust"].get_sample_count("agent-x", "sales", "general", "short")
        assert count == 3

    def test_execute_action_does_not_crash_for_agent_with_history(self):
        cal = create_calibration_engine()
        _resolve_n(cal, "agent-y", "sales", n=6, outcome=True)
        agent = _ConcreteAgent("agent-y", calibration_engine=cal)
        action = AgentActionV2(
            action_type="emit", description="d", payload={}, risk_level="low",
            stated_confidence=0.7, domain="sales", claim_type="general", horizon_class="short",
        )
        result = agent.execute_action(action)   # must not raise
        assert result["n_samples"] if "n_samples" in result else True
        assert result["trusted_confidence"] <= result["stated_confidence"]


# ---------------------------------------------------------------------------
# HIGH-2 — malformed model output escalates cleanly instead of crashing
# ---------------------------------------------------------------------------

class TestHigh2EscalationRoute:
    SCHEMA = {"type": "object", "required": ["action"], "properties": {"action": {"type": "string"}}}

    def _client_returning(self, responses):
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=r))]) for r in responses
        ]
        return client

    def test_escalation_gate_has_route(self):
        gate = EscalationGate()
        out = gate.route(reason="structured_output_failure", detail="bad json", risk_level="medium")
        assert out["escalated"] is True
        assert any(p.claim_type == "structured_output_failure" for p in gate.list_pending())

    def test_malformed_output_escalates_cleanly(self):
        gate = EscalationGate()
        client = self._client_returning(["nope", "still bad", "{not json"])
        # Before the fix this raised AttributeError: 'EscalationGate' has no attribute 'route'
        result = get_validated_output(client, "qwen2.5:7b", [], self.SCHEMA, gate)
        assert result["escalated"] is True
        assert result["reason"] == "structured_output_failure"

    def test_agent_act_escalates_on_repeated_failure(self):
        cal = create_calibration_engine()
        agent = _ConcreteAgent("agent-z", calibration_engine=cal)
        agent._llm_client = self._client_returning(["bad", "bad", "bad"])
        agent._model = "qwen2.5:7b"
        result = agent.act([{"role": "user", "content": "go"}], schema=self.SCHEMA)
        assert result["escalated"] is True


# ---------------------------------------------------------------------------
# HIGH-3 — a real trust drop propagates to registered consumers
# ---------------------------------------------------------------------------

class TestHigh3DowngradePropagation:
    def test_downgrade_propagates_to_consumers(self):
        cal = create_calibration_engine()
        notified = []
        cal["trust"].register_downgrade_callback(
            lambda subject_id, mult: notified.append((subject_id, mult))
        )
        # High-confidence predictions resolving FALSE must drop the multiplier and notify.
        _resolve_n(cal, "agent-drop", "ops", n=1, outcome=False, probability=0.9)
        assert notified, "downgrade callback never fired (propagation was dead code)"
        assert notified[0][0] == "agent-drop"
        assert notified[0][1] < 1.0
