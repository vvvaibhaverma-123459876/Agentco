"""Phase 6.5 proof tests for LIVE V1 specialist severity reachability.

These tests document current intended-safe-but-non-blocking behavior. When the
LIVE specialists migrate to BaseAgentV2 in Phase 7, update these assertions to
the new V2 escalation path instead of deleting the coverage.
"""

from __future__ import annotations

from agents.autonomy.quality_auditor import QualityAuditorAgent
from agents.core.base_agent import BaseAgent


def test_quality_auditor_standard_execute_path_does_not_touch_v1_governance(monkeypatch):
    """The live /execute path should complete without calling BaseAgent.run()."""

    def fail_if_run_is_used(*_args, **_kwargs):
        raise AssertionError("LIVE specialist /execute path unexpectedly called BaseAgent.run()")

    async def fail_if_approval_is_requested(*_args, **_kwargs):
        raise AssertionError("LIVE specialist /execute path unexpectedly requested V1 approval")

    monkeypatch.setattr(BaseAgent, "run", fail_if_run_is_used)
    monkeypatch.setattr(BaseAgent, "_request_human_approval", fail_if_approval_is_requested)

    agent = QualityAuditorAgent(
        "phase65-quality-auditor",
        "quality_auditor",
        {"tokens": 1000, "iterations": 10, "seconds": 60},
    )

    response = agent.app.test_client().post(
        "/execute",
        json={
            "actionId": "phase65-action",
            "actionType": "EXTRACT_EVIDENCE",
            "objective": "audit evidence quality",
            "args": {"sourceId": "phase65-source"},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "completed"
    assert payload["observations"]["status"] == "quality_metrics_extracted"
