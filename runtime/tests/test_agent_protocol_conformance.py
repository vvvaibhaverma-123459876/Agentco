from __future__ import annotations

import asyncio
import importlib
import inspect
import re
from pathlib import Path

import pytest

from calibration import create_calibration_engine
from runtime.base_agent.agent_manifest import (
    ACTIVE_AGENT_PROFILES,
    PYTHON_ACTIVE_AGENT_PROFILES,
    TS_DURABLE_ACTIVE_AGENT_PROFILES,
)
from runtime.base_agent.audit_writer import InMemoryAuditWriter
from runtime.base_agent.base_agent_v2 import AgentActionV2, BaseAgentV2
from runtime.base_agent.spend_guardrail import SpendCapExceeded
from runtime.escalation.escalation_gate import HumanApprovalRequired

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_WRITE_PATTERNS = (
    re.compile(r"\bINSERT\s+INTO\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\s+prediction_ledger\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+prediction_ledger\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+prediction_ledger\b", re.IGNORECASE),
)


def _load_agent_class(implementation: str) -> type[BaseAgentV2]:
    module_name, class_name = implementation.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def _agent(profile):
    cls = _load_agent_class(profile.implementation)
    agent = cls(calibration_engine=create_calibration_engine())
    agent._audit_writer = InMemoryAuditWriter(allow_test_mode=True)
    return agent


def _allowed_action(profile, *, risk_level="low") -> AgentActionV2:
    return AgentActionV2(
        action_type=profile.allowed_actions[0],
        description=f"conformance action for {profile.agent_id}",
        payload={"evidence_id": f"evidence-{profile.agent_id}", "source": "phase9-conformance"},
        risk_level=risk_level,
        stated_confidence=0.95,
        domain="conformance",
        claim_type="protocol",
    )


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_active_agent_is_registered_with_governed_runtime(profile):
    agent = _agent(profile)
    assert isinstance(agent, BaseAgentV2)
    assert agent.agent_id == profile.agent_id
    assert agent.ALLOWED_ACTION_TYPES == set(profile.allowed_actions)


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_unauthorized_execution_is_rejected(profile):
    agent = _agent(profile)
    action = AgentActionV2(
        action_type="undeclared_phase9_action",
        description="must be rejected before evidence or audit",
        payload={},
        risk_level="low",
    )
    with pytest.raises(PermissionError, match="undeclared action"):
        agent.execute_action(action)
    assert agent.protocol_evidence == []
    assert agent.get_audit_log() == []


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_allowed_execution_records_evidence_success_and_audit(profile):
    agent = _agent(profile)
    result = agent.execute_action(_allowed_action(profile))

    assert result["outcome"] == "executed"
    assert result["attempt_id"]
    assert agent.protocol_evidence[-1]["attempt_id"] == result["attempt_id"]
    assert agent.protocol_successes[-1]["attempt_id"] == result["attempt_id"]

    audit_log = agent.get_audit_log()
    assert len(audit_log) == 1
    assert audit_log[0]["agent_id"] == profile.agent_id
    assert audit_log[0]["outcome"] == "executed"
    assert audit_log[0]["attempt_id"] == result["attempt_id"]


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_failure_is_finalized_and_audited(profile):
    agent = _agent(profile)
    with pytest.raises(HumanApprovalRequired):
        agent.execute_action(_allowed_action(profile, risk_level="critical"))

    assert agent.protocol_failures[-1]["outcome"] == "blocked"
    audit_log = agent.get_audit_log()
    assert len(audit_log) == 1
    assert audit_log[0]["outcome"] == "blocked"
    assert audit_log[0]["attempt_id"] == agent.protocol_failures[-1]["attempt_id"]


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_undeclared_tools_are_blocked(profile):
    agent = _agent(profile)
    with pytest.raises(PermissionError, match="has not declared tool"):
        asyncio.run(agent.execute_tool("undeclared_tool", {}))


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_spend_limits_are_enforced(profile):
    agent = _agent(profile)
    agent._spend._max_tokens = 0
    with pytest.raises(SpendCapExceeded):
        agent.execute_action(_allowed_action(profile))
    assert agent.protocol_failures[-1]["outcome"] == "spend_blocked"
    assert agent.get_audit_log() == []


@pytest.mark.parametrize("profile", PYTHON_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_active_agent_source_has_no_direct_protected_ledger_writes(profile):
    cls = _load_agent_class(profile.implementation)
    source_path = Path(inspect.getsourcefile(cls) or "")
    text = source_path.read_text()
    findings = []
    for pattern in PROTECTED_WRITE_PATTERNS:
        findings.extend(pattern.findall(text))
    assert findings == []


@pytest.mark.parametrize("profile", TS_DURABLE_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_ts_durable_active_agent_is_registry_limited_to_observation(profile):
    registry = (ROOT / "backend" / "src" / "agent-registry.ts").read_text()
    assert f"entry('{profile.agent_id}'" in registry
    assert f"entry('{profile.agent_id}'" in registry and "['record_observation']" in registry


@pytest.mark.parametrize("profile", TS_DURABLE_ACTIVE_AGENT_PROFILES, ids=lambda p: p.agent_id)
def test_ts_durable_active_agent_uses_canonical_audit_and_evidence(profile):
    durable = (ROOT / "backend" / "src" / "services" / "durable-execution.service.ts").read_text()
    civilization = (ROOT / "backend" / "src" / "services" / "civilization.service.ts").read_text()
    assert profile.agent_id in civilization
    assert "assertAgentCanRunTask" in durable
    assert "provenance.attestAction" in durable
    assert "auditLog.append" in durable
    assert "SET status='failed'" in durable
    assert not any(pattern.search(durable) for pattern in PROTECTED_WRITE_PATTERNS)


def test_every_active_agent_has_conformance_case():
    assert len(ACTIVE_AGENT_PROFILES) == 11
    assert len(PYTHON_ACTIVE_AGENT_PROFILES) == 9
    assert len(TS_DURABLE_ACTIVE_AGENT_PROFILES) == 2
    assert {profile.classification for profile in ACTIVE_AGENT_PROFILES} == {"active"}
