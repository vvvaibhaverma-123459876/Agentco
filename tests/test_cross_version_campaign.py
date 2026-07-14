import json
from pathlib import Path

from scripts import calculate_longitudinal_milestones, verify_cross_version_campaign, verify_migration_identity


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "fb27dc0529d3c5d11480503bfbcf6f2d156f5b04"
RAW = "651794a41513db1e40930f08c253ef261af7c1e7"
RECONCILED = "81cd17431f826d9d3cda06b9127758751e44b798"


def campaign_fixture(path: Path) -> Path:
    path.mkdir()
    (path / "runs").mkdir()
    manifest = {
        "benchmark_registry_hash": "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e",
        "evaluator_version": "longitudinal-evaluator-v1",
        "hidden_answer_isolation": {"subject_readable_expected_outputs": False},
        "subjects": {
            "version-a": {"sha": BASELINE},
            "version-b": {"sha": RAW},
            "version-c": {"sha": RECONCILED},
        },
        "comparisons": {
            "a_vs_b": {"paired_case_count": 120},
            "a_vs_c": {"paired_case_count": 120},
            "b_vs_c": {"paired_case_count": 120},
        },
    }
    (path / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))
    for subject, sha in {"version-a": BASELINE, "version-b": RAW, "version-c": RECONCILED}.items():
        cases = [
            {
                "case_id": f"case-{index}",
                "status": "failed" if subject == "version-b" and index == 0 else "passed",
                "output": {"confidence": 0.7, "budget_use": {"tokens": 0, "usd": 0.0}},
            }
            for index in range(120)
        ]
        run = {"subject": subject, "sha": sha, "run_ids": [f"{subject}-seed-{seed}" for seed in [101, 202, 303, 404, 505]], "case_results": cases}
        (path / "runs" / f"{subject}.json").write_text(json.dumps(run))
    return path


def test_migration_identity_ledger_accepts_contracts():
    ledger = verify_migration_identity.build_ledger()

    assert verify_migration_identity.validate(ledger) == []
    assert "129" in ledger["reused_sequence_contracts"]


def test_uncontracted_migration_sequence_collision_fails():
    ledger = verify_migration_identity.build_ledger()
    migration = dict(ledger["migrations"][0])
    migration["stable_migration_id"] = "999_duplicate.sql"
    migration["filename"] = "999_duplicate.sql"
    migration["sequence"] = 129
    ledger["migrations"].append(migration)

    assert any("REUSED_SEQUENCE_CONTRACT_MISMATCH:129" in error for error in verify_migration_identity.validate(ledger))


def test_cross_version_campaign_verifies_subject_shas(tmp_path):
    campaign_dir = campaign_fixture(tmp_path / "campaign")

    assert verify_cross_version_campaign.validate(campaign_dir, BASELINE, RAW, RECONCILED) == []


def test_raw_candidate_cannot_be_replaced_by_reconciled_candidate(tmp_path):
    campaign_dir = campaign_fixture(tmp_path / "campaign")

    errors = verify_cross_version_campaign.validate(campaign_dir, BASELINE, RECONCILED, RECONCILED)

    assert "SUBJECT_SHA_MISMATCH:version-b" in errors


def test_benchmark_hash_mismatch_fails(tmp_path):
    target = campaign_fixture(tmp_path / "campaign")
    manifest = json.loads((target / "CONTROL_MANIFEST.json").read_text())
    manifest["benchmark_registry_hash"] = "0" * 64
    (target / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))

    assert "BENCHMARK_HASH_MISMATCH" in verify_cross_version_campaign.validate(target, BASELINE, RAW, RECONCILED)


def test_hidden_answer_leakage_fails(tmp_path):
    target = campaign_fixture(tmp_path / "campaign")
    manifest = json.loads((target / "CONTROL_MANIFEST.json").read_text())
    manifest["hidden_answer_isolation"]["subject_readable_expected_outputs"] = True
    (target / "CONTROL_MANIFEST.json").write_text(json.dumps(manifest))

    assert "HIDDEN_ANSWERS_SUBJECT_READABLE" in verify_cross_version_campaign.validate(target, BASELINE, RAW, RECONCILED)


def test_omitted_failed_cases_fail(tmp_path):
    target = campaign_fixture(tmp_path / "campaign")
    run_path = target / "runs" / "version-b.json"
    data = json.loads(run_path.read_text())
    data["case_results"] = [item for item in data["case_results"] if item["status"] != "failed"]
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
