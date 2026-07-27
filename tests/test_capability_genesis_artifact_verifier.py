from __future__ import annotations

import json

from agentco_capability.evidence import payload_manifest
from scripts.verify_capability_genesis_artifact import (
    _aggregate_semantic_hash,
    _case_semantic_hash,
    verify_genesis_v7_evidence,
    verify_roots,
)


def _manifest(**overrides):
    manifest = {
        "artifact_type": "real_provider_genesis_v7_aggregate",
        "campaign_id": "governed-capability-genesis-v7-test",
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "planned_cases": 24,
        "executed_cases": 1,
        "completed_cases": 0,
        "failed_cases": 0,
        "timed_out_cases": 0,
        "denied_cases": 0,
        "evidence_unavailable_cases": 0,
        "evaluator_unavailable_cases": 0,
        "invalid_response_cases": 1,
        "infrastructure_failure_cases": 0,
        "aggregate_correctness": None,
        "supported_domains": [],
    }
    manifest.update(overrides)
    if "semantic_hash" not in overrides:
        manifest["semantic_hash"] = _aggregate_semantic_hash(manifest)
    return manifest


def _case(**overrides):
    record = {
        "artifact_type": "genesis_v7_case_evidence",
        "campaign_id": "governed-capability-genesis-v7-test",
        "case_id": "case-1",
        "terminal_status": "INVALID_RESPONSE",
        "provider_request_id_captured": True,
        "provider_response_hash": "a" * 64,
        "provider_request_id_hash": "b" * 64,
        "finish_reason": "stop",
        "parser_input_hash": "c" * 64,
        "parser_input_redacted": '{"not":"schema-valid"}',
        "redacted_provider_response": {
            "id": "[REDACTED_PROVIDER_REQUEST_ID]",
            "choices": [{"message": {"content": '{"not":"schema-valid"}'}, "finish_reason": "stop"}],
        },
        "cost": {"reserved_usd": 0.1, "consumed_usd": 0.01, "released_usd": 0.09, "unreleased_amount": 0},
        "audit_references": [{"type": "local_case_record", "id": "case-1"}],
    }
    record.update(overrides)
    if "semantic_hash" not in overrides:
        record["semantic_hash"] = _case_semantic_hash(record)
    return record


def _clean_clone_report(**overrides):
    report = {
        "verification_result": "passed",
        "decision_recomputable_without_provider_credentials": True,
        "aggregate_hash_matches": True,
        "terminal_totals_reconcile": True,
    }
    report.update(overrides)
    return report


def _write_manifest_with_payload(campaign, manifest):
    payload, aggregate = payload_manifest(
        campaign,
        [],
        campaign_execution_sha="test-sha",
        workflow_head_sha="test-sha",
        campaign_id=manifest["campaign_id"],
        hash_fields={},
    )
    manifest["internal_payload_manifest_hash"] = aggregate
    manifest["semantic_hash"] = _aggregate_semantic_hash(manifest)
    (campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(manifest))
    (campaign / "INTERNAL_PAYLOAD_MANIFEST.json").write_text(json.dumps(payload))


def _frozen_case_manifest(path, cases):
    path.write_text(
        json.dumps(
            {
                "case_count": len(cases),
                "cases": cases,
                "validation_errors": [],
            }
        )
    )


def _expected_frozen_cases():
    cases = []
    for split in ("validation", "hidden"):
        for index in range(12):
            cases.append({"case_id": f"{split}-case-{index}", "split": split, "domain": "reasoning"})
    return cases


def test_genesis_v7_verifier_rejects_hash_only_provider_evidence(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(
        json.dumps(
            _case(
                redacted_provider_response=None,
                provider_request_id_hash=None,
                finish_reason=None,
                parser_input_hash=None,
                parser_input_redacted=None,
                audit_references=[],
            )
        )
    )

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_PROVIDER_EVIDENCE_NOT_DIAGNOSABLE") for item in findings)


def test_genesis_v7_verifier_rejects_provider_response_status_without_evidence(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(
        completed_cases=1,
        invalid_response_cases=0,
        aggregate_correctness=0.75,
    )
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(
        json.dumps(
            _case(
                terminal_status="COMPLETED",
                provider_request_id_captured=False,
                provider_response_hash=None,
                returned_model_identity=None,
                redacted_provider_response=None,
                provider_request_id_hash=None,
                finish_reason=None,
                parser_input_hash=None,
                parser_input_redacted=None,
                audit_references=[],
            )
        )
    )

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_PROVIDER_EVIDENCE_NOT_DIAGNOSABLE") for item in findings)


def test_genesis_v7_verifier_accepts_diagnosable_invalid_response(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=24, invalid_response_cases=24)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    for index in range(24):
        (campaign / f"CASE_case-{index}.json").write_text(
            json.dumps(_case(case_id=f"case-{index}", provider_response_hash=f"{index:064x}"))
        )

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert findings == []


def test_genesis_v7_verifier_rejects_missing_clean_clone_report(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case()))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_CLEAN_CLONE_REPORT_MISSING") for item in findings)


def test_genesis_v7_verifier_rejects_placeholder_clean_clone_report(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(
        baseline_execution_attempted=False,
        executed_cases=0,
        evidence_unavailable_cases=24,
        invalid_response_cases=0,
    )
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(
        json.dumps({"status": "not_run_after_canary_failed", "verification_result": None})
    )

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_CLEAN_CLONE_REPORT_PLACEHOLDER") for item in findings)
    assert any(item.startswith("GENESIS_V7_CLEAN_CLONE_REPORT_NOT_PASSED") for item in findings)


def test_genesis_v7_verifier_rejects_case_population_not_in_frozen_manifest(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    frozen_manifest = tmp_path / "frozen_case_manifest.json"
    _frozen_case_manifest(frozen_manifest, _expected_frozen_cases())
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=24, invalid_response_cases=24)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    for index in range(23):
        case_id = f"validation-case-{index}" if index < 12 else f"hidden-case-{index - 12}"
        (campaign / f"CASE_{case_id}.json").write_text(
            json.dumps(_case(case_id=case_id, split="validation" if index < 12 else "hidden", domain="reasoning", provider_response_hash=f"{index:064x}"))
        )
    (campaign / "CASE_extra-case.json").write_text(
        json.dumps(_case(case_id="extra-case", split="hidden", domain="reasoning", provider_response_hash=f"{23:064x}"))
    )

    findings = verify_genesis_v7_evidence(manifest_path, manifest, frozen_case_manifest_path=frozen_manifest)

    assert any(item.startswith("GENESIS_V7_FROZEN_CASE_MISSING") and item.endswith(":hidden-case-11") for item in findings)
    assert any(item.startswith("GENESIS_V7_UNREGISTERED_CASE_RECORD") and item.endswith(":extra-case") for item in findings)


def test_genesis_v7_verifier_rejects_split_and_domain_drift_from_frozen_manifest(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    frozen_manifest = tmp_path / "frozen_case_manifest.json"
    cases = _expected_frozen_cases()
    _frozen_case_manifest(frozen_manifest, cases)
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=24, invalid_response_cases=24)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    for index, frozen_case in enumerate(cases):
        overrides = {}
        if frozen_case["case_id"] == "validation-case-0":
            overrides = {"split": "hidden", "domain": "planning"}
        (campaign / f"CASE_{frozen_case['case_id']}.json").write_text(
            json.dumps(
                _case(
                    case_id=frozen_case["case_id"],
                    split=overrides.get("split", frozen_case["split"]),
                    domain=overrides.get("domain", frozen_case["domain"]),
                    provider_response_hash=f"{index:064x}",
                )
            )
        )

    findings = verify_genesis_v7_evidence(manifest_path, manifest, frozen_case_manifest_path=frozen_manifest)

    assert any(item.startswith("GENESIS_V7_CASE_SPLIT_MISMATCH") for item in findings)
    assert any(item.startswith("GENESIS_V7_CASE_DOMAIN_MISMATCH") for item in findings)


def test_genesis_v7_verifier_rejects_identical_hash_only_response_pattern(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=2, invalid_response_cases=2)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    for case_id in ("case-1", "case-2"):
        (campaign / f"CASE_{case_id}.json").write_text(
            json.dumps(
                _case(
                    case_id=case_id,
                    redacted_provider_response=None,
                    provider_request_id_hash=None,
                    finish_reason=None,
                    parser_input_hash=None,
                    parser_input_redacted=None,
                    audit_references=[],
                )
            )
        )

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_IDENTICAL_PROVIDER_RESPONSE_HASHES") for item in findings)


def test_genesis_v7_verifier_rejects_capability_decision_without_scores(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(
        decision="REAL_CAPABILITY_BASELINE_ACCEPTED",
        executed_cases=1,
        invalid_response_cases=0,
        completed_cases=1,
        aggregate_correctness=None,
        supported_domains=["reasoning"],
    )
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(terminal_status="COMPLETED")))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_DECISION_WITHOUT_SCORABLE_COMPLETIONS") for item in findings)
    assert any(item.startswith("GENESIS_V7_SUPPORTED_DOMAINS_WITHOUT_CORRECTNESS") for item in findings)
    assert any(item.startswith("GENESIS_V7_DECISION_MISMATCH") for item in findings)


def test_genesis_v7_verifier_rejects_case_semantic_hash_tampering(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(semantic_hash="f" * 64)))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_CASE_SEMANTIC_HASH_MISMATCH") for item in findings)


def test_genesis_v7_verifier_rejects_case_id_filename_mismatch(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_expected-id.json").write_text(json.dumps(_case(case_id="different-id")))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_CASE_ID_FILENAME_MISMATCH") for item in findings)


def test_genesis_v7_verifier_rejects_duplicate_case_ids(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=2, invalid_response_cases=2)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(case_id="duplicate")))
    (campaign / "CASE_case-2.json").write_text(json.dumps(_case(case_id="duplicate", provider_response_hash="d" * 64)))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_DUPLICATE_CASE_ID") for item in findings)


def test_genesis_v7_verifier_rejects_case_campaign_mismatch(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(campaign_id="other-campaign")))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_CASE_CAMPAIGN_ID_MISMATCH") for item in findings)


def test_genesis_v7_verifier_rejects_unknown_terminal_status(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(terminal_status="Completed")))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_UNKNOWN_TERMINAL_STATUS") for item in findings)
    assert any(item.startswith("GENESIS_V7_TERMINAL_BUCKET_TOTAL_MISMATCH") for item in findings)


def test_genesis_v7_verifier_requires_baseline_count_fields(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    del manifest["planned_cases"]
    manifest["semantic_hash"] = _aggregate_semantic_hash(manifest)
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case()))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_REQUIRED_COUNT_FIELD_MISSING") and item.endswith(":planned_cases") for item in findings)


def test_genesis_v7_verifier_accepts_prebaseline_hold_without_case_records(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(
        baseline_execution_attempted=False,
        executed_cases=0,
        evidence_unavailable_cases=24,
        invalid_response_cases=0,
    )
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert findings == []


def test_artifact_verifier_scans_multiple_evidence_roots(tmp_path):
    artifact_root = tmp_path / "artifacts" / "capability-runtime"
    docs_root = tmp_path / "docs" / "capability"
    good_campaign = artifact_root / "good"
    bad_campaign = docs_root / "bad"
    good_campaign.mkdir(parents=True)
    bad_campaign.mkdir(parents=True)
    manifest = _manifest()
    (good_campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(manifest))
    (good_campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (good_campaign / "CASE_case-1.json").write_text(json.dumps(_case()))
    (bad_campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(manifest))
    (bad_campaign / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (bad_campaign / "CASE_case-1.json").write_text(
        json.dumps(
            _case(
                redacted_provider_response=None,
                provider_request_id_hash=None,
                finish_reason=None,
                parser_input_hash=None,
                parser_input_redacted=None,
                audit_references=[],
            )
        )
    )

    findings = verify_roots([artifact_root, docs_root])

    assert any(str(bad_campaign) in item and item.startswith("GENESIS_V7_PROVIDER_EVIDENCE_NOT_DIAGNOSABLE") for item in findings)


def test_artifact_verifier_reports_malformed_manifest_json(tmp_path):
    root = tmp_path / "artifacts"
    campaign = root / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text("{not-json")

    findings = verify_roots([root])

    assert any(item.startswith("CAPABILITY_MANIFEST_JSON_INVALID") for item in findings)


def test_artifact_verifier_reports_payload_manifest_json_error(tmp_path):
    root = tmp_path / "artifacts"
    campaign = root / "campaign"
    campaign.mkdir(parents=True)
    manifest = _manifest(baseline_execution_attempted=False, executed_cases=0, evidence_unavailable_cases=24, invalid_response_cases=0)
    (campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(manifest))
    (campaign / "INTERNAL_PAYLOAD_MANIFEST.json").write_text("{not-json")

    findings = verify_roots([root])

    assert any(item.startswith("PAYLOAD_MANIFEST_JSON_INVALID") for item in findings)


def test_artifact_verifier_can_pin_selected_campaign_and_ignore_stale_artifacts(tmp_path):
    root = tmp_path / "artifacts"
    selected = root / "selected"
    stale = root / "stale"
    selected.mkdir(parents=True)
    stale.mkdir(parents=True)

    selected_manifest = _manifest(
        campaign_id="governed-capability-genesis-v7-selected",
        baseline_execution_attempted=False,
        executed_cases=0,
        evidence_unavailable_cases=24,
        invalid_response_cases=0,
    )
    _write_manifest_with_payload(selected, selected_manifest)
    (selected / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))

    stale_manifest = _manifest(campaign_id="governed-capability-genesis-v7-stale")
    (stale / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(stale_manifest))
    (stale / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (stale / "CASE_case-1.json").write_text(
        json.dumps(
            _case(
                campaign_id="governed-capability-genesis-v7-stale",
                redacted_provider_response=None,
                provider_request_id_hash=None,
                finish_reason=None,
                parser_input_hash=None,
                parser_input_redacted=None,
                audit_references=[],
            )
        )
    )

    findings = verify_roots(
        [root],
        frozen_case_manifest_path=None,
        campaign_id="governed-capability-genesis-v7-selected",
    )

    assert findings == []


def test_artifact_verifier_rejects_missing_selected_campaign_even_when_stale_artifacts_exist(tmp_path):
    root = tmp_path / "artifacts"
    stale = root / "stale"
    stale.mkdir(parents=True)
    stale_manifest = _manifest(campaign_id="governed-capability-genesis-v7-stale")
    (stale / "GENESIS_V7_CAMPAIGN_MANIFEST.json").write_text(json.dumps(stale_manifest))
    (stale / "CLEAN_CLONE_VERIFICATION_REPORT.json").write_text(json.dumps(_clean_clone_report()))
    (stale / "CASE_case-1.json").write_text(json.dumps(_case(campaign_id="governed-capability-genesis-v7-stale")))

    findings = verify_roots(
        [root],
        frozen_case_manifest_path=None,
        campaign_id="governed-capability-genesis-v7-selected",
    )

    assert findings == ["SELECTED_CAMPAIGN_MANIFEST_MISSING:governed-capability-genesis-v7-selected"]
