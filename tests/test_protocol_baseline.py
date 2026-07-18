from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_protocol_baseline_v1"


def test_protocol_cases_are_control_cases_not_capability_prompts():
    registry = json.loads((BENCH / "registry.json").read_text())
    cases = json.loads((BENCH / registry["case_manifest"]).read_text())
    assert len(cases) >= 24
    assert all("control_type" in case for case in cases)
    assert all("domain" not in case for case in cases)


def test_protocol_cases_have_evaluator_only_expectation_hashes():
    cases = json.loads((BENCH / "cases" / "cases.json").read_text())
    for case in cases:
        assert case["expectation_hash"]
        provider_visible = json.dumps(case["input"]).lower()
        assert "expected_status" not in provider_visible
        assert "expectation_hash" not in provider_visible


def test_protocol_campaign_never_emits_capability_decision():
    registry = json.loads((BENCH / "registry.json").read_text())
    assert registry["acceptance"] == "all_control_families_pass"
