from __future__ import annotations

import pytest

from agentco_capability.scoring import (
    score_capability_task,
    score_data_analysis,
    score_planning,
    score_software_engineering,
)


def test_empty_rubric_fails_closed():
    with pytest.raises(ValueError):
        score_capability_task({"status": "completed", "provider": "openai_compatible"}, {})


def test_generic_planning_template_fails():
    score = score_planning(
        {"provider": "openai_compatible", "structured_output": {"ordered_steps": ["analyze", "execute", "review"]}},
        {"required_steps": ["backup", "restore", "verify"], "generic_template_terms": ["analyze", "execute", "review"]},
    )
    assert score["score"] == 0.0


def test_incorrect_data_analysis_fails():
    score = score_data_analysis(
        {"provider": "openai_compatible", "structured_output": {"calculations": {"average": 8.0}}},
        {"expected_calculations": {"average": 7.0}},
    )
    assert score["score"] == 0.0


def test_comment_only_patch_fails():
    score = score_software_engineering(
        {"provider": "openai_compatible", "structured_output": {"patch": "# TODO", "changed_files": ["x.py"], "public_tests_passed": True, "hidden_tests_passed": True}},
        {},
    )
    assert score["score"] < 1.0


def test_protocol_reference_never_scores_capability():
    score = score_capability_task(
        {"status": "completed", "provider": "deterministic_protocol_reference", "task_type": "reasoning"},
        {"domain": "reasoning", "expected_final_answer": "yes"},
    )
    assert score["scorable"] is False
    assert score["score"] == 0.0
