import json
from pathlib import Path

from scripts import aggregate_longitudinal_history, calculate_longitudinal_milestones, verify_longitudinal_evidence


ROOT = Path(__file__).resolve().parents[1]
HEAD = "db538c6a00d0e7e8464fbaa79801473270d8388a"


def load_results():
    return json.loads((ROOT / "docs/audit/current/INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json").read_text())


def base_context(**overrides):
    context = {
        "context_version": "longitudinal-workflow-context-v1",
        "event_name": "schedule",
        "expected_sha": HEAD,
        "actual_sha": HEAD,
        "branch": "audit/remediation-06a-longitudinal-remote-closure",
        "dirty_status": "clean",
        "campaign_series": "weekly-foundation-v1",
        "observation_kind": "scheduled",
        "observation_id": "weekly-foundation-v1-2026-W29-db538c6a00d0",
        "attempt_id": "weekly-foundation-v1-2026-W29-db538c6a00d0-attempt-1",
        "github_run_id": "293",
        "github_run_attempt": "1",
        "repository": "vvvaibhaverma-123459876/Agentco",
        "workflow_name": "Longitudinal Evidence",
        "created_at": "2026-07-14T11:00:00Z",
        "registry_hash": "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e",
        "lockfile_hash": "hash",
        "python_version": "3.13.9",
        "os": "linux",
        "architecture": "x64",
    }
    context.update(overrides)
    return context


def attempt(**overrides):
    item = {
        "attempt_id": "weekly-foundation-v1-2026-W29-db538c6a00d0-attempt-1",
        "observation_id": "weekly-foundation-v1-2026-W29-db538c6a00d0",
        "observation_kind": "scheduled",
        "campaign_series": "weekly-foundation-v1",
        "status": "success",
        "event_name": "schedule",
        "commit_sha": HEAD,
        "iso_week": "2026-W29",
        "started_at": "2026-07-14T11:00:00Z",
        "completed_at": "2026-07-14T11:01:00Z",
        "benchmark_versions": {"reasoning-v1": "1.0.0"},
        "evaluator_versions": ["longitudinal-evaluator-v1"],
        "provider_classification": "deterministic_fixture",
        "advances_calendar_milestone": False,
    }
    item.update(overrides)
    return item


def test_pull_request_merge_sha_is_rejected():
    context = base_context(event_name="pull_request", expected_sha=HEAD, actual_sha="0" * 40, observation_kind="pull_request_protocol", observation_id="protocol-pr-db538c6a00d0-293")

    assert "EXPECTED_SHA_MISMATCH" in verify_longitudinal_evidence.validate_context(context)


def test_campaign_manifest_for_another_commit_is_rejected(tmp_path):
    data = load_results()
    data["runs"][0]["manifest"]["commit_sha"] = "0" * 40
    path = tmp_path / "CAMPAIGN_RESULTS.json"
    path.write_text(json.dumps(data))

    errors = verify_longitudinal_evidence.validate_campaign(path, HEAD)

    assert any("MANIFEST_COMMIT_MISMATCH" in error for error in errors)


def test_fixed_campaign_id_reused_for_schedule_is_rejected():
    context = base_context(observation_id="initial-foundation-v1")

    errors = verify_longitudinal_evidence.validate_context(context)

    assert "INVALID_OBSERVATION_ID" in errors
    assert "FIXED_CAMPAIGN_ID_REUSED_FOR_SCHEDULE" in errors


def test_two_scheduled_successes_same_iso_week_fail():
    history = {"attempts": [attempt(), attempt(attempt_id="weekly-foundation-v1-2026-W29-db538c6a00d0-attempt-2")], "failed_attempts": [], "current_aggregate_hash": ""}

    errors = aggregate_longitudinal_history.validate_history(history)

    assert any("duplicate successful scheduled observation" in error for error in errors)


def test_failed_attempt_omission_is_rejected():
    history = {"attempts": [attempt(status="success")], "failed_attempts": ["missing-failed-attempt"], "current_aggregate_hash": ""}

    assert "PRIOR_FAILED_ATTEMPT_DISAPPEARED" in aggregate_longitudinal_history.validate_history(history)


def test_manual_run_does_not_advance_four_week_milestone():
    history = {"attempts": [attempt(observation_kind="manual", iso_week="2026-W29", status="success")], "benchmark_versions": {"reasoning-v1": "1.0.0"}, "evaluator_versions": ["longitudinal-evaluator-v1"]}

    result = calculate_longitudinal_milestones.result(history)

    assert result["manual_success_count"] == 1
    assert result["four_week"] is False


def test_two_same_day_runs_do_not_count_as_two_weeks():
    history = {"attempts": [attempt(), attempt(attempt_id="weekly-foundation-v1-2026-W29-db538c6a00d0-attempt-2", status="failed")], "benchmark_versions": {"reasoning-v1": "1.0.0"}, "evaluator_versions": ["longitudinal-evaluator-v1"]}

    result = calculate_longitudinal_milestones.result(history)

    assert result["scheduled_week_count"] == 1
    assert result["four_week"] is False


def test_iso_year_boundary_weeks_are_distinct_but_time_blocked_without_cross_version():
    history = {
        "attempts": [
            attempt(iso_week="2026-W53", completed_at="2026-12-31T00:00:00Z"),
            attempt(attempt_id="weekly-foundation-v1-2027-W01-db538c6a00d0-attempt-1", observation_id="weekly-foundation-v1-2027-W01-db538c6a00d0", iso_week="2027-W01", completed_at="2027-01-04T00:00:00Z"),
        ],
        "benchmark_versions": {"reasoning-v1": "1.0.0"},
        "evaluator_versions": ["longitudinal-evaluator-v1"],
    }

    result = calculate_longitudinal_milestones.result(history)

    assert result["scheduled_weeks"] == ["2026-W53", "2027-W01"]
    assert result["four_week"] is False


def test_backdated_observation_before_activation_is_rejected():
    history = {"workflow_activation_date": "2026-07-14T00:00:00Z", "attempts": [attempt(completed_at="2026-07-01T00:00:00Z")], "failed_attempts": [], "current_aggregate_hash": ""}

    assert "HISTORICAL_OBSERVATION_BEFORE_WORKFLOW_ACTIVATION" in aggregate_longitudinal_history.validate_history(history)


def test_modified_aggregate_hash_is_rejected():
    history = aggregate_longitudinal_history.append_attempt({}, attempt())
    history["campaign_series"] = "tampered"

    assert "AGGREGATE_CHAIN_HASH_MISMATCH" in aggregate_longitudinal_history.validate_history(history)


def test_broken_aggregate_chain_is_rejected():
    history = aggregate_longitudinal_history.append_attempt({}, attempt())
    history["current_aggregate_hash"] = "bad"

    assert "AGGREGATE_CHAIN_HASH_MISMATCH" in aggregate_longitudinal_history.validate_history(history)


def test_benchmark_hash_change_is_rejected(tmp_path):
    data = load_results()
    data["registry_hash"] = "bad"
    path = tmp_path / "CAMPAIGN_RESULTS.json"
    path.write_text(json.dumps(data))

    assert "BENCHMARK_REGISTRY_HASH_MISMATCH" in verify_longitudinal_evidence.validate_campaign(path, data["runs"][0]["manifest"]["commit_sha"])


def test_evaluator_version_difference_is_rejected(tmp_path):
    data = load_results()
    data["evaluator_versions"] = ["other"]
    path = tmp_path / "CAMPAIGN_RESULTS.json"
    path.write_text(json.dumps(data))

    assert "EVALUATOR_VERSION_MISMATCH" in verify_longitudinal_evidence.validate_campaign(path, data["runs"][0]["manifest"]["commit_sha"])


def test_required_artifact_missing_is_rejected(tmp_path):
    errors = verify_longitudinal_evidence.verify_chain(tmp_path / "missing", "run")

    assert "run:MISSING_EVIDENCE_ARTIFACT" in errors


def test_failure_manifest_records_failed_attempt(tmp_path):
    context_path = tmp_path / "context.json"
    output_path = tmp_path / "failure.json"
    context_path.write_text(json.dumps(base_context()))

    class Args:
        context = context_path
        expected_sha = HEAD
        event_name = "schedule"
        github_run_id = "293"
        github_run_attempt = "1"
        campaign_series = "weekly-foundation-v1"
        failure_stage = "benchmark-governance"
        exit_code = 2
        output = output_path

    assert verify_longitudinal_evidence.emit_failure_manifest(Args()) == 0
    manifest = json.loads(output_path.read_text())

    assert manifest["attempt_id"] == "weekly-foundation-v1-2026-W29-db538c6a00d0-attempt-1"
    assert manifest["failure_stage"] == "benchmark-governance"
    assert manifest["exit_code"] == 2
    assert manifest["artifact_hash"]


def test_artifact_repository_or_workflow_mismatch_is_rejected():
    errors = verify_longitudinal_evidence.validate_context(base_context(repository="elsewhere/repo", workflow_name="Other"))

    assert "ARTIFACT_REPOSITORY_MISMATCH" in errors
    assert "ARTIFACT_WORKFLOW_MISMATCH" in errors


def test_dirty_working_tree_context_is_rejected():
    assert "WORKING_TREE_DIRTY" in verify_longitudinal_evidence.validate_context(base_context(dirty_status="dirty"))


def test_hosted_evidence_claimed_by_fixture_is_rejected(tmp_path):
    data = load_results()
    data["runs"][0]["manifest"]["provider_classification"] = "hosted_staging"
    path = tmp_path / "CAMPAIGN_RESULTS.json"
    path.write_text(json.dumps(data))

    errors = verify_longitudinal_evidence.validate_campaign(path, data["runs"][0]["manifest"]["commit_sha"])

    assert any("HOSTED_OR_PRODUCTION_CLAIM_WITHOUT_PROOF" in error for error in errors)


def test_production_evidence_claimed_by_github_runner_is_rejected(tmp_path):
    data = load_results()
    data["runs"][0]["manifest"]["provider_classification"] = "production"
    path = tmp_path / "CAMPAIGN_RESULTS.json"
    path.write_text(json.dumps(data))

    errors = verify_longitudinal_evidence.validate_campaign(path, data["runs"][0]["manifest"]["commit_sha"])

    assert any("HOSTED_OR_PRODUCTION_CLAIM_WITHOUT_PROOF" in error for error in errors)


def test_unmerged_pr_workflow_cannot_claim_schedule_activation():
    context = base_context(event_name="pull_request", observation_kind="scheduled")

    assert "UNMERGED_WORKFLOW_CLAIMS_ACTIVE_CAMPAIGN" in verify_longitudinal_evidence.validate_context(context)


def test_historical_observation_before_workflow_activation_is_rejected():
    history = {
        "workflow_activation_date": "2026-07-14T00:00:00Z",
        "attempts": [attempt(completed_at="2026-01-01T00:00:00Z")],
        "failed_attempts": [],
        "current_aggregate_hash": "",
    }

    assert "HISTORICAL_OBSERVATION_BEFORE_WORKFLOW_ACTIVATION" in aggregate_longitudinal_history.validate_history(history)
