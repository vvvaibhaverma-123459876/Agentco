import json
import subprocess
from pathlib import Path

import pytest

from scripts import longitudinal_foundation


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text())


def test_benchmark_governance_accepts_current_registry():
    registry = load_json("benchmarks/registry.json")

    assert longitudinal_foundation.validate_registry(registry) == []


def test_hidden_answers_are_not_candidate_readable():
    registry = load_json("benchmarks/registry.json")
    hidden_cases = [case for suite in registry["suites"] for case in suite["cases"] if case["split"] == "hidden"]

    assert hidden_cases
    assert all("expected_output" not in case for case in hidden_cases)
    assert all(case["expected_output_hash"] for case in hidden_cases)


def test_benchmark_governance_rejects_hidden_answer_leakage():
    registry = load_json("benchmarks/registry.json")
    leaked = json.loads(json.dumps(registry))
    for suite in leaked["suites"]:
        for case in suite["cases"]:
            if case["split"] == "hidden":
                case["expected_output"] = {"label": "pass"}
                break
        break

    errors = longitudinal_foundation.validate_registry(leaked)

    assert any("hidden expected output is candidate-readable" in error for error in errors)


def test_benchmark_governance_rejects_tampered_case_hash():
    registry = load_json("benchmarks/registry.json")
    tampered = json.loads(json.dumps(registry))
    tampered["suites"][0]["cases"][0]["prompt"] = "changed after freeze"

    errors = longitudinal_foundation.validate_registry(tampered)

    assert any("input hash mismatch" in error for error in errors)
    assert any("case manifest hash mismatch" in error for error in errors)


def test_run_manifest_uses_unambiguous_provider_classification():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")

    for run in results["runs"]:
        manifest = run["manifest"]
        assert manifest["provider_classification"] == "deterministic_fixture"
        assert manifest["run_id"] == run["run_id"]
        assert manifest["benchmark_registry_hash"] == results["registry_hash"]
        assert manifest["seed"] in results["seeds"]
        assert manifest["budgets"]["max_tool_calls"] == 0


def test_campaign_completeness_and_failed_runs_are_retained():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")

    assert results["campaign_completeness"] == {"required_runs": 5, "completed_runs": 5, "missing_runs": 0}
    assert results["failure_count"] > 0
    assert all("failures" in run for run in results["runs"])


def test_independent_recomputation_detects_duplicate_run_id():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")
    forged = json.loads(json.dumps(results))
    forged["runs"][1]["run_id"] = forged["runs"][0]["run_id"]

    errors = longitudinal_foundation.recompute_campaign(forged)

    assert any("duplicate run id" in error for error in errors)


def test_statistical_comparison_reports_safety_blocking_fields():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")
    comparison = results["controlled_improvement"]["comparison"]

    for key in [
        "sample_count",
        "paired_cases",
        "mean_difference",
        "median_difference",
        "effect_size",
        "confidence_interval_95",
        "regression_count",
        "improvement_count",
        "failure_rate_difference",
        "calibration_difference",
    ]:
        assert key in comparison
    assert comparison["paired_cases"] == 48
    assert comparison["calibration_difference"] < 0
    assert comparison["promotion_allowed"] is False


def test_calibration_report_contains_required_metrics():
    report = load_json("docs/audit/current/LONGITUDINAL_CALIBRATION_REPORT.json")

    for key in [
        "brier_score",
        "log_loss",
        "expected_calibration_error",
        "maximum_calibration_error",
        "reliability_bins",
        "abstention_coverage",
        "selective_risk",
        "overconfidence_rate",
        "underconfidence_rate",
    ]:
        assert key in report


def test_memory_and_governance_metrics_are_reported_separately():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")
    vector = results["capability_vector"]

    assert "memory_usefulness" in vector
    assert "authorization_compliance" in vector
    assert "budget_compliance" in vector
    assert vector["authorization_compliance"] == 1.0
    assert vector["budget_compliance"] == 1.0


def test_candidate_cannot_self_approve():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")
    approval = results["controlled_improvement"]["approval"]

    assert approval["self_approval"] is False
    assert approval["approver_identity"] != approval["proposer_identity"]


def test_unsafe_improvement_is_rejected():
    results = load_json("docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json")

    rejected = results["rejected_improvement"]
    assert rejected["decision"] == "rejected"
    assert "budget" in rejected["reason"]


def test_cross_domain_transfer_does_not_overclaim():
    transfer = load_json("docs/audit/current/CROSS_DOMAIN_TRANSFER_MATRIX.json")

    assert transfer["domains"]["evidence_evaluation"] == "positive_transfer"
    assert all(value in {"positive_transfer", "neutral", "negative_transfer", "insufficient_evidence", "not_applicable"} for value in transfer["domains"].values())
    assert any(value == "neutral" for value in transfer["domains"].values())


def test_calendar_milestones_remain_time_blocked():
    milestone = load_json("docs/audit/current/LONGITUDINAL_MILESTONE_POLICY.json")

    assert milestone["eligible"] == ["foundation"]
    assert "four_week" in milestone["time_blocked"]
    assert "twelve_week" in milestone["time_blocked"]
    assert "hosted" in milestone["time_blocked"]


def test_structural_score_is_not_longitudinal_evidence():
    matrix = load_json("docs/audit/current/CLAIM_EVIDENCE_MATRIX.json")
    claim = next(item for item in matrix["claims"] if item["claim"] == "Longitudinal mission evidence foundation exists")

    assert claim["evidence_level"] == "repeated_same_version"
    assert claim["hosted"] is False
    assert claim["production"] is False
    assert claim["calendar_duration"] == "same_day"


def test_benchmark_governance_cli_fails_on_negative_fixture(tmp_path):
    registry = load_json("benchmarks/registry.json")
    registry["suites"][0]["license_or_provenance"] = ""
    fixture = tmp_path / "registry.json"
    fixture.write_text(json.dumps(registry))

    result = subprocess.run(
        ["python3.13", "scripts/verify_benchmark_governance.py", "--registry", str(fixture), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "missing provenance" in result.stdout


def test_longitudinal_foundation_check_passes():
    result = subprocess.run(
        ["python3.13", "scripts/longitudinal_foundation.py", "check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "initial-foundation-v1" in result.stdout


@pytest.mark.parametrize(
    "required_doc",
    [
        "docs/audit/current/MISSION_CLAIM_DECOMPOSITION.json",
        "docs/audit/current/LONGITUDINAL_EVIDENCE_TIERS.md",
        "docs/audit/current/BENCHMARK_GOVERNANCE_POLICY.json",
        "docs/audit/current/LONGITUDINAL_RUN_PROTOCOL.md",
        "docs/audit/current/CAPABILITY_VECTOR_SPECIFICATION.json",
        "docs/audit/current/LONGITUDINAL_COMPARISON_POLICY.md",
        "docs/audit/current/LONGITUDINAL_MISSION_FINDINGS.json",
    ],
)
def test_required_longitudinal_docs_exist(required_doc):
    assert (ROOT / required_doc).exists()
