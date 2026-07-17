from __future__ import annotations

import json

import pytest

from agentco_capability.scoring import score_capability_task, score_claim_grounding
from scripts.run_governed_capability_genesis import contains_forbidden_provider_data, preflight_provider


def test_expected_answers_reaching_provider_are_detected():
    assert contains_forbidden_provider_data({"structured_input": {"expected_answer": "secret"}})


def test_rubrics_reaching_provider_are_detected():
    assert contains_forbidden_provider_data({"request": {"rubric": {"answer": "x"}}})


def test_completed_status_alone_cannot_pass_capability():
    with pytest.raises(ValueError):
        score_capability_task({"status": "completed", "provider": "openai_compatible", "answer": "non-empty"}, {})


def test_non_empty_evidence_does_not_ground_claim():
    score = score_claim_grounding(
        {"provider": "openai_compatible", "structured_output": {"claims": [{"supported": False, "evidence_refs": ["e1"]}]}},
        {"supported": True},
    )
    assert score["score"] < 1.0


def test_unavailable_provider_is_not_capability_unsupported(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    result = preflight_provider("openai_compatible")
    assert result["provider_preflight"] == "unavailable"
    assert result["execution_attempted"] is False


def test_protocol_reference_cannot_be_real_provider():
    result = preflight_provider("deterministic_protocol_reference")
    assert result["provider_preflight"] == "invalid_provider_for_real_capability"
    assert result["execution_attempted"] is False
