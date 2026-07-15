from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_genesis_v3"


def load_cases(split: str):
    return json.loads((BENCH / split / "cases.json").read_text())


def test_genesis_v3_case_counts_and_rubric_references():
    registry = json.loads((BENCH / "registry.json").read_text())
    assert len(load_cases("development")) >= 18
    assert len(load_cases("validation")) == registry["case_counts"]["validation"] == 12
    assert len(load_cases("hidden")) == registry["case_counts"]["hidden"] == 12
    rubrics = json.loads((BENCH / registry["rubric_manifest"]).read_text())
    for case in load_cases("validation") + load_cases("hidden"):
        assert case["rubric_id"] in rubrics
        assert case["rubric_hash"]
        assert case["scorer_id"].endswith("-v1")


def test_validation_and_hidden_cases_are_distinct():
    validation = {case["request"]["prompt"] for case in load_cases("validation")}
    hidden = {case["request"]["prompt"] for case in load_cases("hidden")}
    assert validation.isdisjoint(hidden)


def test_provider_visible_requests_do_not_contain_evaluator_data():
    for case in load_cases("validation") + load_cases("hidden"):
        text = json.dumps(case["request"]).lower()
        assert "expected" not in text
        assert "rubric" not in text
        assert "hidden_tests" not in text
        assert "reference_solution" not in text


def test_thresholds_require_real_capability_domains():
    registry = json.loads((BENCH / "registry.json").read_text())
    assert registry["minimum_acceptance"]["capability_task_domains"] >= 4
    assert registry["minimum_acceptance"]["validation_hidden_executed_scorable_cases"] >= 18
