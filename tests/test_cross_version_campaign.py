import json
from pathlib import Path

from scripts import (
    calculate_longitudinal_milestones,
    verify_cross_version_campaign,
    verify_cross_version_harness_independence,
    verify_subject_request_consumption,
    verify_migration_identity,
    verify_subject_runtime_evidence,
)


BASELINE = "fb27dc0529d3c5d11480503bfbcf6f2d156f5b04"
RAW = "651794a41513db1e40930f08c253ef261af7c1e7"
RECONCILED = "81cd17431f826d9d3cda06b9127758751e44b798"


def real_campaign_fixture(path: Path) -> Path:
    path.mkdir()
    (path / "runs").mkdir()
    subjects = {
        "version-a": {"sha": BASELINE, "opaque_label": "subject-aaaa"},
        "version-b": {"sha": RAW, "opaque_label": "subject-bbbb"},
        "version-c": {"sha": RECONCILED, "opaque_label": "subject-cccc"},
    }
    manifest = {
        "control_manifest_version": "real-cross-version-campaign-v1",
        "methodology": "subject_process_invocation_no_synthetic_outputs",
        "planned_case_executions": 360,
        "benchmark_registry_hash": "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e",
        "evaluator_version": "longitudinal-evaluator-v1",
        "hidden_answer_isolation": {"subject_readable_expected_outputs": False},
        "blinding": {"mapping_hash": "abc", "sealed_mapping": {"subject-aaaa": {"public_label": "version-a"}}},
        "subjects": subjects,
        "comparisons": {
            "a_vs_b": {"paired_case_count": 120},
            "a_vs_c": {"paired_case_count": 120},
            "b_vs_c": {"paired_case_count": 120},
        },
    }
    (path / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))
    for public, meta in subjects.items():
        cases = [
            {
                "case_id": f"case-{index}",
                "status": "unsupported",
                "runtime_evidence_refs": [f"process://{meta['opaque_label']}/run-{index}/123"],
                "process": {
                    "pid": 123,
                    "wall_clock_ms": 1.0,
                    "cpu_time_ms": 1.0,
                    "peak_rss_kb": 1000,
                    "stdout_hash": "a" * 64,
                    "stderr_hash": "b" * 64,
                },
                "response": {"confidence": None},
            }
            for index in range(120)
        ]
        run = {"opaque_subject": meta["opaque_label"], "sha": meta["sha"], "run_ids": [f"{meta['opaque_label']}-seed-{seed}" for seed in [101, 202, 303, 404, 505]], "case_results": cases}
        (path / "runs" / f"{meta['opaque_label']}.json").write_text(json.dumps(run))
    return path


def subject_native_campaign_fixture(path: Path) -> Path:
    path.mkdir()
    (path / "runs").mkdir()
    subjects = {
        "version-a": {"sha": BASELINE, "opaque_label": "subject-aaaa"},
        "version-b": {"sha": RAW, "opaque_label": "subject-bbbb"},
        "version-c": {"sha": RECONCILED, "opaque_label": "subject-cccc"},
    }
    manifest = {
        "control_manifest_version": "subject-native-cross-version-campaign-v1",
        "methodology": "subject_native_existing_agentco_interfaces",
        "planned_case_executions": 360,
        "benchmark_registry_hash": "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e",
        "evaluator_version": "longitudinal-evaluator-v1",
        "hidden_answer_isolation": {"subject_readable_expected_outputs": False},
        "blinding": {"mapping_hash": "abc", "sealed_mapping": {"subject-aaaa": {"public_label": "version-a"}}},
        "subjects": subjects,
        "comparisons": {
            "a_vs_b": {"paired_case_count": 120},
            "a_vs_c": {"paired_case_count": 120},
            "b_vs_c": {"paired_case_count": 120},
        },
    }
    (path / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))
    for _public, meta in subjects.items():
        cases = []
        for index in range(120):
            completed = index < 10
            run_id = f"{meta['opaque_label']}-run-{index}"
            request_hash = "c" * 64
            status = "completed" if completed else "unsupported"
            cases.append(
                {
                    "case_id": f"case-{index}",
                    "domain": "calibration" if completed else "reasoning",
                    "status": status,
                    "support_status": "supported_common" if completed else "unsupported_incompatible_contract",
                    "request_hash": request_hash,
                    "response_hash": f"{index:064x}",
                    "runtime_evidence_refs": [f"process://{meta['opaque_label']}/{run_id}/123", f"request://{meta['opaque_label']}/{run_id}/{request_hash}"] if completed else [],
                    "request_consumption": {
                        "consumed": completed,
                        "evidence": [
                            {"type": "request_hash_echoed_as_prediction_id", "request_hash": request_hash},
                            {"type": "subject_runtime_function_executed", "executed_by": "scripts/execute_durable_task.py"},
                        ] if completed else [],
                    },
                    "measurements": [{"measurement_scope": "benchmark_task", "wall_clock_ms": 1.0}] if completed else [],
                    "process": {
                        "argv": ["python3.13", "-c", "from scripts.execute_durable_task import execute_task_logic"],
                        "pid": 123,
                        "wall_clock_ms": 1.0,
                        "cpu_time_ms": 1.0,
                        "peak_rss_kb": 1000,
                        "stdout_hash": "a" * 64,
                        "stderr_hash": "b" * 64,
                    } if completed else None,
                    "response": {"confidence": 0.5 if completed else None},
                }
            )
        run = {
            "opaque_subject": meta["opaque_label"],
            "sha": meta["sha"],
            "run_ids": [f"{meta['opaque_label']}-seed-{seed}" for seed in [101, 202, 303, 404, 505]],
            "case_results": cases,
        }
        (path / "runs" / f"{meta['opaque_label']}.json").write_text(json.dumps(run))
    return path


def test_migration_identity_ledger_accepts_contracts():
    ledger = verify_migration_identity.build_ledger()

    assert verify_migration_identity.validate(ledger) == []
    for sequence in ("51", "58", "59", "129"):
        assert sequence in ledger["reused_sequence_contracts"]


def test_uncontracted_migration_sequence_collision_fails():
    ledger = verify_migration_identity.build_ledger()
    migration = dict(ledger["migrations"][0])
    migration["stable_migration_id"] = "999_duplicate.sql"
    migration["filename"] = "999_duplicate.sql"
    migration["sequence"] = 129
    ledger["migrations"].append(migration)

    assert any("REUSED_SEQUENCE_CONTRACT_MISMATCH:129" in error for error in verify_migration_identity.validate(ledger))


def test_real_campaign_verifies_subject_shas_and_runtime_evidence(tmp_path):
    campaign_dir = real_campaign_fixture(tmp_path / "campaign")

    assert verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED) == []
    assert verify_subject_runtime_evidence.validate(campaign_dir) == []


def test_subject_native_campaign_requires_request_consumption(tmp_path):
    campaign_dir = subject_native_campaign_fixture(tmp_path / "campaign")

    assert verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED) == []
    assert verify_subject_runtime_evidence.validate(campaign_dir) == []
    assert verify_subject_request_consumption.validate(campaign_dir) == []


def test_completed_subject_native_case_without_consumption_fails(tmp_path):
    campaign_dir = subject_native_campaign_fixture(tmp_path / "campaign")
    run_path = campaign_dir / "runs" / "subject-aaaa.json"
    run = json.loads(run_path.read_text())
    run["case_results"][0]["request_consumption"] = {"consumed": False, "evidence": []}
    run_path.write_text(json.dumps(run))

    assert any(error.startswith("REQUEST_NOT_CONSUMED:version-a") for error in verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED))
    assert any(error.startswith("REQUEST_NOT_CONSUMED:version-a") for error in verify_subject_request_consumption.validate(campaign_dir))


def test_help_command_cannot_be_counted_as_capability_task(tmp_path):
    campaign_dir = subject_native_campaign_fixture(tmp_path / "campaign")
    run_path = campaign_dir / "runs" / "subject-aaaa.json"
    run = json.loads(run_path.read_text())
    run["case_results"][0]["process"]["argv"] = ["python3.13", "scripts/verify_mission_progress.py", "--help"]
    run_path.write_text(json.dumps(run))

    errors = verify_subject_request_consumption.validate(campaign_dir)

    assert any(error.startswith("HEALTH_OR_HELP_COMMAND_COUNTED_AS_TASK:version-a") for error in errors)
    assert any(error.startswith("MISSION_PROGRESS_HELP_COUNTED_AS_TASK:version-a") for error in errors)


def test_supported_common_case_cannot_disappear_as_unsupported(tmp_path):
    campaign_dir = subject_native_campaign_fixture(tmp_path / "campaign")
    run_path = campaign_dir / "runs" / "subject-aaaa.json"
    run = json.loads(run_path.read_text())
    run["case_results"][0]["status"] = "unsupported"
    run_path.write_text(json.dumps(run))

    assert any(error.startswith("COMMON_CORE_UNSUPPORTED:version-a") for error in verify_subject_request_consumption.validate(campaign_dir))


def test_health_measurement_cannot_supply_capability_measurement(tmp_path):
    campaign_dir = subject_native_campaign_fixture(tmp_path / "campaign")
    run_path = campaign_dir / "runs" / "subject-aaaa.json"
    run = json.loads(run_path.read_text())
    run["case_results"][0]["measurements"] = [{"measurement_scope": "health", "wall_clock_ms": 1.0}]
    run_path.write_text(json.dumps(run))

    assert any(error.startswith("MISSING_BENCHMARK_TASK_MEASUREMENT:version-a") for error in verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED))
    assert any(error.startswith("MISSING_BENCHMARK_TASK_MEASUREMENT:version-a") for error in verify_subject_request_consumption.validate(campaign_dir))


def test_synthetic_manifest_is_rejected(tmp_path):
    campaign_dir = real_campaign_fixture(tmp_path / "campaign")
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["control_manifest_version"] = "cross-version-campaign-v1"
    manifest["methodology"] = "deterministic_output"
    manifest_path.write_text(json.dumps(manifest))

    errors = verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED)

    assert "SYNTHETIC_OR_UNKNOWN_CAMPAIGN_MANIFEST" in errors
    assert "METHODOLOGY_NOT_REAL_SUBJECT_INVOCATION" in errors


def test_runtime_evidence_is_required(tmp_path):
    campaign_dir = real_campaign_fixture(tmp_path / "campaign")
    run_path = campaign_dir / "runs" / "subject-bbbb.json"
    run = json.loads(run_path.read_text())
    run["case_results"][0]["runtime_evidence_refs"] = ["subject://version-b/fake"]
    run_path.write_text(json.dumps(run))

    assert any(error.startswith("UNRESOLVED_RUNTIME_EVIDENCE:version-b") for error in verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED))
    assert any(error.startswith("UNRESOLVABLE_REF:version-b") for error in verify_subject_runtime_evidence.validate(campaign_dir))


def test_harness_independence_rejects_subject_specific_logic(tmp_path):
    target = tmp_path / "bad_runner.py"
    target.write_text(
        "def deterministic_output(subject):\n"
        "    if subject == 'version-a':\n"
        "        return 'pass'\n"
        "    return 'fail'\n"
    )

    errors = verify_cross_version_harness_independence.validate(target)

    assert "FORBIDDEN_FUNCTION:deterministic_output" in errors
    assert any(error.startswith("SUBJECT_LABEL_BRANCH") for error in errors)


def test_current_harness_has_no_subject_specific_output_logic():
    assert verify_cross_version_harness_independence.validate() == []


def test_raw_candidate_cannot_be_replaced_by_reconciled_candidate(tmp_path):
    campaign_dir = real_campaign_fixture(tmp_path / "campaign")

    errors = verify_cross_version_campaign.validate(campaign_dir, BASELINE, RECONCILED, RECONCILED)

    assert "SUBJECT_SHA_MISMATCH:version-b" in errors


def test_benchmark_hash_mismatch_fails(tmp_path):
    target = real_campaign_fixture(tmp_path / "campaign")
    manifest = json.loads((target / "CONTROL_MANIFEST.json").read_text())
    manifest["benchmark_registry_hash"] = "0" * 64
    (target / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))

    assert "BENCHMARK_HASH_MISMATCH" in verify_cross_version_campaign.validate(target, BASELINE, RAW, RECONCILED)


def test_hidden_answer_leakage_fails(tmp_path):
    target = real_campaign_fixture(tmp_path / "campaign")
    manifest = json.loads((target / "CONTROL_MANIFEST.json").read_text())
    manifest["hidden_answer_isolation"]["subject_readable_expected_outputs"] = True
    (target / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))

    assert "HIDDEN_ANSWERS_SUBJECT_READABLE" in verify_cross_version_campaign.validate(target, BASELINE, RAW, RECONCILED)


def test_omitted_cases_fail(tmp_path):
    target = real_campaign_fixture(tmp_path / "campaign")
    run_path = target / "runs" / "subject-bbbb.json"
    data = json.loads(run_path.read_text())
    data["case_results"] = data["case_results"][:-1]
    run_path.write_text(json.dumps(data))

    assert any(error.startswith("CASE_COUNT_MISMATCH:version-b") for error in verify_cross_version_campaign.validate(target, BASELINE, RAW, RECONCILED))


def test_manual_observation_does_not_advance_four_week_milestone():
    history = {
        "attempts": [
            {"observation_kind": "manual", "status": "success", "iso_week": "2026-W29", "commit_sha": RECONCILED},
            {"observation_kind": "manual", "status": "success", "iso_week": "2026-W30", "commit_sha": RECONCILED},
            {"observation_kind": "manual", "status": "success", "iso_week": "2026-W31", "commit_sha": RECONCILED},
            {"observation_kind": "manual", "status": "success", "iso_week": "2026-W32", "commit_sha": RECONCILED},
        ],
        "benchmark_versions": {"reasoning-v1": "1.0.0"},
        "evaluator_versions": ["longitudinal-evaluator-v1"],
    }

    result = calculate_longitudinal_milestones.result(history)

    assert result["manual_success_count"] == 4
    assert result["scheduled_week_count"] == 0
    assert result["four_week"] is False
