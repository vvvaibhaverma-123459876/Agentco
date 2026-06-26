import pytest

from scripts.execute_durable_task import (
    PayloadValidationError,
    Task,
    UnsupportedFeatureError,
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


@pytest.mark.parametrize("task_type", ["review", "decision"])
def test_review_and_decision_are_unsupported_not_fake_success(task_type):
    task = Task(
        task_id="task-1",
        agent_id="reviewer-agent",
        task_type=task_type,
        payload={"options": ["approve"], "criteria": ["fast"]},
    )

    with pytest.raises(UnsupportedFeatureError, match="unsupported"):
        execute_task_logic(task)


def test_unknown_task_type_is_unsupported():
    task = Task(task_id="task-1", agent_id="agent", task_type="unknown", payload={})

    with pytest.raises(UnsupportedFeatureError, match="unsupported durable task_type"):
        execute_task_logic(task)


def test_record_observation_requires_observation():
    with pytest.raises(PayloadValidationError, match="observation"):
        validate_payload("record_observation", {})
