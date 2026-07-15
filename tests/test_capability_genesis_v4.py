from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_genesis_v4"


def test_genesis_v4_registry_and_hidden_validation_splits():
    registry = json.loads((BENCH / "registry.json").read_text())
    assert registry["benchmark_id"] == "capability-genesis-v4"
    validation = json.loads((BENCH / registry["case_manifest_files"]["validation"]).read_text())
    hidden = json.loads((BENCH / registry["case_manifest_files"]["hidden"]).read_text())
    assert len(validation) == 12
    assert len(hidden) == 12
    assert {case["request"]["prompt"] for case in validation}.isdisjoint({case["request"]["prompt"] for case in hidden})


def test_genesis_v4_software_and_data_rubrics_are_evaluator_owned():
    registry = json.loads((BENCH / "registry.json").read_text())
    rubrics = json.loads((BENCH / registry["rubric_manifest"]).read_text())
    assert any(r.get("domain") == "software_engineering" and r.get("evaluator_test_evidence") for r in rubrics.values())
    assert any(r.get("domain") == "data_analysis" and r.get("evaluator_verification") for r in rubrics.values())
