import pytest

from scripts import execute_durable_task as executor
from scripts.execute_durable_task import (
    PayloadValidationError,
    Task,
    execute_task_logic,
    validate_payload,
)


def test_llm_call_payload_requires_prompt():
    with pytest.raises(PayloadValidationError, match="prompt"):
        validate_payload("llm_call", {})


def test_calibration_payload_scores_real_binary_outcome():
    task = Task(
        task_id="task-1",
        agent_id="calibration-reasoner",
        task_type="calibration",
        payload={"prediction_id": "pred-1", "confidence": 0.8, "outcome": 1},
    )

    result = execute_task_logic(task)

    assert result["kind"] == "calibration_score"
    assert result["brier_score"] == pytest.approx(0.04)


def test_review_requires_real_llm_not_fake_summary(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    task = Task(
        task_id="task-1",
        agent_id="reviewer-agent",
        task_type="review",
        payload={"subject": "Change set", "criteria": ["security"]},
    )

    with pytest.raises(RuntimeError, match="requires LLM_API_KEY"):
        execute_task_logic(task)


def test_decision_does_not_choose_first_option_without_llm(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    task = Task(
        task_id="task-1",
        agent_id="reviewer-agent",
        task_type="decision",
        payload={"options": ["approve", "reject"], "criteria": ["security"]},
    )

    with pytest.raises(RuntimeError, match="requires LLM_API_KEY"):
        execute_task_logic(task)


def test_decision_rejects_llm_option_not_in_payload(monkeypatch):
    def fake_call(messages, timeout_seconds):
        return {
            "selected_option": "ship_anyway",
            "rationale": "bad output",
            "confidence": 0.9,
            "evidence_ids_used": [],
        }, 1, "fake-test-model"

    monkeypatch.setattr(executor, "call_openai_json", fake_call)
    task = Task(
        task_id="task-1",
        agent_id="reviewer-agent",
        task_type="decision",
        payload={"options": ["approve", "reject"], "criteria": ["security"]},
    )

    with pytest.raises(RuntimeError, match="option not present"):
        execute_task_logic(task)


def test_unknown_task_type_is_unsupported():
    task = Task(task_id="task-1", agent_id="agent", task_type="unknown", payload={})

    with pytest.raises(RuntimeError, match="unsupported durable task_type"):
        execute_task_logic(task)


def test_record_observation_requires_observation():
    with pytest.raises(PayloadValidationError, match="observation"):
        validate_payload("record_observation", {})
