from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agentco_capability import real_provider_readiness as readiness


def _valid_config() -> dict:
    return {
        "provider_name": "openai_compatible",
        "model_identifier": "gpt-test",
        "api_base_url": "https://api.example.test/v1",
        "credential_reference": "env:OPENAI_API_KEY",
        "provider_host_allowlist": ["api.example.test"],
        "request_timeout_seconds": 30,
        "retry_limit": 2,
        "concurrency_limit": 1,
        "token_budget": 24000,
        "monetary_budget_usd": 10.0,
        "campaign_execution_budget": {"max_calls": 24, "max_retries_total": 48},
        "dns_resolution_policy": {
            "resolve_before_connect": True,
            "reject_forbidden_ranges": True,
            "fail_on_ambiguous_resolution": True,
        },
        "redirect_policy": {"enabled": False, "max_redirects": 0},
        "model_identity_verification_mode": "strict_response_match_or_hold",
        "region_or_deployment": None,
    }


def _authorization(config: dict) -> dict:
    source = readiness.current_source_identity()
    return {
        "campaign_id": readiness.GENESIS_IDENTITY,
        "source_commit": source["commit"],
        "source_tree": source["tree"],
        "protocol_version": readiness.PROTOCOL_IDENTITY,
        "genesis_version": readiness.GENESIS_IDENTITY,
        "provider": config["provider_name"],
        "model": config["model_identifier"],
        "endpoint": config["api_base_url"],
        "approved_domains": ["reasoning", "planning"],
        "planned_case_count": 24,
        "maximum_calls": 24,
        "maximum_tokens": 24000,
        "maximum_cost_usd": 10.0,
        "timeout_seconds": 30,
        "retry_policy": {"max_retries_per_case": 2, "max_retries_total": 48},
        "concurrency": 1,
        "authorized_operator": "operator@example.test",
        "authorization_timestamp": datetime.now(timezone.utc).isoformat(),
        "authorization_expiry": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "approved_evidence_destination": "artifacts/capability-runtime/governed-capability-genesis-v5",
        "non_claims": ["no hosted evidence", "no production evidence"],
        "limitations": ["provider identity must be verified"],
        "signature_required": False,
    }


def test_missing_provider_configuration_produces_governed_hold(monkeypatch):
    for name in ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"]:
        monkeypatch.delenv(name, raising=False)
    result = readiness.real_provider_hold_result()
    assert result["decision"] == "HOLD_FOR_MORE_EVIDENCE"
    assert result["execution_attempted"] is False
    assert result["evidence_unavailable_cases"] == 24
    assert result["supported_domains"] == []
    assert result["aggregate_correctness"] is None


def test_invalid_provider_configuration_fails_closed():
    config = _valid_config()
    config["api_base_url"] = "http://api.example.test/v1"
    result = readiness.validate_provider_config(config, resolve_dns=False)
    assert result["status"] == "invalid"
    assert "invalid_provider_endpoint" in result["failure_codes"]


def test_credentials_are_references_not_secret_values():
    config = _valid_config()
    config["credential_reference"] = "env:OPENAI_API_KEY"
    result = readiness.validate_provider_config(config, resolve_dns=False)
    assert result["secret_values_recorded"] is False
    assert "OPENAI_API_KEY" not in result["configuration_hash"]


def test_authorization_is_mandatory_and_commit_model_endpoint_bound():
    config = _valid_config()
    valid = _authorization(config)
    assert readiness.validate_authorization(valid, config)["status"] == "valid"
    bad_commit = dict(valid, source_commit="0" * 40)
    assert "source_commit_mismatch" in readiness.validate_authorization(bad_commit, config)["failure_codes"]
    bad_model = dict(valid, model="other")
    assert "model_mismatch" in readiness.validate_authorization(bad_model, config)["failure_codes"]
    bad_endpoint = dict(valid, endpoint="https://other.example.test/v1")
    assert "endpoint_mismatch" in readiness.validate_authorization(bad_endpoint, config)["failure_codes"]


def test_expired_authorization_fails():
    config = _valid_config()
    auth = _authorization(config)
    auth["authorization_expiry"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert "authorization_expired" in readiness.validate_authorization(auth, config)["failure_codes"]


def test_forbidden_resolved_ip_is_blocked(monkeypatch):
    monkeypatch.setattr(readiness.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))])
    result = readiness.validate_provider_config(_valid_config(), resolve_dns=True)
    assert "forbidden_resolved_address" in result["failure_codes"]


def test_redirect_policy_remains_blocked():
    config = _valid_config()
    config["redirect_policy"] = {"enabled": True, "max_redirects": 1}
    result = readiness.validate_provider_config(config, resolve_dns=False)
    assert "redirects_not_permitted" in result["failure_codes"]


def test_budget_reservation_reconciles_and_timeout_settles():
    assert readiness.budget_settlement_valid({"reserved_amount": 10, "consumed_amount": 4, "released_amount": 6, "unreleased_amount": 0})
    assert not readiness.budget_settlement_valid({"reserved_amount": 10, "consumed_amount": 4, "released_amount": 5, "unreleased_amount": 1})


def test_retries_are_bounded_and_non_retryable_not_reset():
    config = _valid_config()
    config["retry_limit"] = 3
    config["campaign_execution_budget"]["max_retries_total"] = 2
    result = readiness.validate_provider_config(config, resolve_dns=False)
    assert "conflicting_retry_budget" in result["failure_codes"]


def test_duplicate_attempts_do_not_count_as_real_execution_in_dry_run():
    result = readiness.dry_run_result(_valid_config())
    assert result["capability_effect"] == "none"
    assert result["real_provider_execution"] is False
    assert result["simulated_reservations"] == 24


def test_evaluator_results_are_separated_from_provider_outputs():
    evidence = readiness.execution_evidence_example()
    assert "evaluator_result" in evidence
    assert "redacted_response" in evidence
    assert evidence["terminal_status"] == "evidence_unavailable"


def test_mock_responses_cannot_count_as_real_capability():
    dry = readiness.dry_run_result(_valid_config())
    assert dry["mock_or_deterministic_outputs_count_as_capability"] is False


def test_evidence_unavailable_is_not_scored_as_failure():
    hold = readiness.real_provider_hold_result(_valid_config())
    assert hold["failed_cases"] == 0
    assert hold["evidence_unavailable_cases"] == 24


def test_unsupported_domains_are_not_claimed_without_thresholds():
    hold = readiness.real_provider_hold_result(_valid_config())
    assert hold["supported_domains"] == []


def test_semantic_hashes_are_deterministic():
    value = {"b": [2, 1], "a": {"x": True}}
    assert readiness.stable_hash(value) == readiness.stable_hash({"a": {"x": True}, "b": [2, 1]})


def test_source_tree_mismatch_invalidates_campaign_authorization():
    config = _valid_config()
    auth = _authorization(config)
    auth["source_tree"] = "1" * 40
    assert "source_tree_mismatch" in readiness.validate_authorization(auth, config)["failure_codes"]


def test_corrupt_persisted_evidence_schema_rejected():
    evidence = readiness.execution_evidence_example()
    evidence.pop("semantic_hash")
    with pytest.raises(readiness.ReadinessError):
        readiness.schema_validate(readiness.EXECUTION_EVIDENCE_SCHEMA, evidence)


def test_real_execution_cannot_start_without_explicit_authorization():
    config = _valid_config()
    hold = readiness.real_provider_hold_result(config)
    assert hold["execution_attempted"] is False
    assert hold["decision"] == "HOLD_FOR_MORE_EVIDENCE"
