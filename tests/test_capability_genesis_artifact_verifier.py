from __future__ import annotations

import json

from scripts.verify_capability_genesis_artifact import verify_genesis_v7_evidence


def _manifest(**overrides):
    manifest = {
        "artifact_type": "real_provider_genesis_v7_aggregate",
        "campaign_id": "governed-capability-genesis-v7-test",
        "decision": "HOLD_FOR_MORE_EVIDENCE",
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
        "audit_references": [{"type": "local_case_record", "id": "case-1"}],
    }
    record.update(overrides)
    return record


def test_genesis_v7_verifier_rejects_hash_only_provider_evidence(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
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


def test_genesis_v7_verifier_accepts_diagnosable_invalid_response(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest()
    manifest_path.write_text(json.dumps(manifest))
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case()))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert findings == []


def test_genesis_v7_verifier_rejects_identical_hash_only_response_pattern(tmp_path):
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    manifest_path = campaign / "GENESIS_V7_CAMPAIGN_MANIFEST.json"
    manifest = _manifest(executed_cases=2, invalid_response_cases=2)
    manifest_path.write_text(json.dumps(manifest))
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
    (campaign / "CASE_case-1.json").write_text(json.dumps(_case(terminal_status="COMPLETED")))

    findings = verify_genesis_v7_evidence(manifest_path, manifest)

    assert any(item.startswith("GENESIS_V7_DECISION_WITHOUT_SCORABLE_COMPLETIONS") for item in findings)
    assert any(item.startswith("GENESIS_V7_SUPPORTED_DOMAINS_WITHOUT_CORRECTNESS") for item in findings)
