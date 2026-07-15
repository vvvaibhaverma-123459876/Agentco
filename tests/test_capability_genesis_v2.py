from __future__ import annotations

import json
from pathlib import Path

from agentco_capability.scoring import score_capability_task


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_genesis_v2"


def load_cases(split: str):
    return json.loads((BENCH / split / "cases.json").read_text())


def test_genesis_v2_cases_are_file_backed_and_counted():
    registry = json.loads((BENCH / "registry.json").read_text())

    assert len(load_cases("development")) >= 18
    assert len(load_cases("validation")) == registry["case_counts"]["validation"] == 12
    assert len(load_cases("hidden")) == registry["case_counts"]["hidden"] == 12


def test_validation_and_hidden_prompts_are_distinct():
    validation = {case["request"]["prompt"] for case in load_cases("validation")}
    hidden = {case["request"]["prompt"] for case in load_cases("hidden")}

    assert validation.isdisjoint(hidden)


def test_hidden_requests_do_not_expose_expected_outputs_or_rubrics():
    for case in load_cases("hidden"):
        request_text = json.dumps(case["request"]).lower()
        assert "expected_answer" not in request_text
        assert "rubric" not in request_text
        assert "expected_hash" not in request_text


def test_domain_labels_are_not_capability_coverage():
    response = {
        "status": "completed",
        "provider": "deterministic_protocol_reference",
        "answer": None,
        "structured_output": {"protocol_validated": True},
    }

    score = score_capability_task(response, {"expected_answer": "yes"})

    assert score["scorable"] is False
    assert score["score"] == 0.0
    assert "protocol reference" in score["reason"]


def test_completed_status_is_not_correctness():
    response = {
        "status": "completed",
        "provider": "openai_compatible",
        "answer": "wrong",
        "structured_output": {},
    }

    score = score_capability_task(response, {"expected_answer": "right"})

    assert score["correctness"] == 0.0
