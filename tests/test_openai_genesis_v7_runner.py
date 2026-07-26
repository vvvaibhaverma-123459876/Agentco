from __future__ import annotations

import io
import json
import urllib.error

import pytest

from agentco_capability.evidence import reproduce_payload_hash
import scripts.run_openai_genesis_v7_baseline as runner


def _auth(path, model: str = "gpt-authorized") -> None:
    path.write_text(
        json.dumps(
            {
                "provider": "OpenAI",
                "model": model,
                "endpoint": "https://api.openai.com/v1",
                "allowed_hostname": "api.openai.com",
                "maximum_cases": 24,
                "maximum_total_spend_usd": 3.0,
                "fallback_provider_allowed": False,
                "fallback_model_allowed": False,
            }
        )
    )


def _provider_data(content: str = '{"final_answer":"ok"}') -> dict:
    return {
        "id": "chatcmpl-secret-request-id",
        "model": "gpt-authorized",
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }


def test_genesis_v7_requires_source_bound_authorization(monkeypatch):
    monkeypatch.delenv(runner.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(SystemExit, match="authorization JSON"):
        runner.load_execution_config()


def test_genesis_v7_model_and_endpoint_come_from_authorization(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth, model="gpt-authorized")
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))

    config = runner.load_execution_config()

    assert config.model == "gpt-authorized"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.host == "api.openai.com"
    assert config.authorization_input_hash == runner.hash_file(auth)


def test_provider_visible_payload_declares_domain_required_fields():
    payload = runner.provider_visible_payload(
        {
            "case_id": "case-1",
            "domain": "planning",
            "request": {"prompt": "Plan this.", "structured_input": {"goal": "x"}},
        }
    )

    assert payload["output_contract"]["required_top_level_fields"] == [
        "goal",
        "assumptions",
        "constraints",
        "ordered_steps",
        "dependencies",
        "risks",
        "success_criteria",
        "fallbacks",
    ]


def test_chat_body_uses_authorized_model_and_explicit_json_contract(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth, model="gpt-authorized")
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    config = runner.load_execution_config()
    payload = runner.provider_visible_payload(
        {
            "case_id": "case-1",
            "domain": "reasoning",
            "request": {"prompt": "Answer.", "structured_input": {}},
        }
    )

    body = runner.build_chat_body(config, payload, runner.MAX_COMPLETION_TOKENS)

    assert body["model"] == "gpt-authorized"
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_completion_tokens"] >= 1000
    assert "final_answer" in body["messages"][1]["content"]
    assert "Do not include private chain-of-thought" in body["messages"][0]["content"]


def test_normalize_response_rejects_empty_provider_content():
    parsed, error = runner.normalize_response(_provider_data(""))

    assert parsed is None
    assert error == "structured_parse_failed:empty_provider_content"


def test_terminal_record_preserves_diagnosable_redacted_response(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth)
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    config = runner.load_execution_config()

    record = runner.terminal_record(
        config,
        {"case_id": "case-1", "domain": "reasoning", "split": "validation"},
        "INVALID_RESPONSE",
        "structured_parse_failed:JSONDecodeError",
        {"prompt": "answer"},
        0.01,
        0.002,
        0.25,
        10,
        0,
        4,
        _provider_data('{"partial":'),
        None,
        "2026-07-19T00:00:00+00:00",
    )

    assert record["provider_request_id_captured"] is True
    assert record["provider_request_id_hash"] == runner.sha256_text("chatcmpl-secret-request-id")
    assert record["redacted_provider_response"]["id"] == "[REDACTED_PROVIDER_REQUEST_ID]"
    assert record["finish_reason"] == "stop"
    assert record["parser_input_redacted"] == '{"partial":'
    assert record["parser_input_hash"] == runner.sha256_text('{"partial":')
    assert record["provider_response_hash"]
    assert record["audit_references"]
    assert record["semantic_hash"] == runner.recompute_case_semantic_hash(record)


def test_openai_http_error_preserves_request_id_and_redacted_body(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth)
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    config = runner.load_execution_config()

    class FakeHeaders(dict):
        def get(self, key, default=None):  # noqa: ANN001
            return super().get(key.lower(), default)

    class FakeOpener:
        def open(self, request, timeout):  # noqa: ANN001, ARG002
            raise urllib.error.HTTPError(
                request.full_url,
                400,
                "bad request",
                FakeHeaders({"x-request-id": "req-http-error-1"}),
                io.BytesIO(b'{"error":{"message":"bad sk-test-secret request"}}'),
            )

    monkeypatch.setattr(runner.urllib.request, "build_opener", lambda *args: FakeOpener())

    with pytest.raises(runner.ProviderHTTPError) as exc_info:
        runner.openai_chat(config, {"prompt": "answer"}, max_completion_tokens=32, timeout=1)

    provider_data = exc_info.value.provider_data()

    assert exc_info.value.status_code == 400
    assert exc_info.value.request_id == "req-http-error-1"
    assert provider_data["_request_id_hint"] == "req-http-error-1"
    assert provider_data["_provider_http_status"] == 400
    assert "sk-test-secret" not in provider_data["_raw_body_redacted"]


def test_terminal_record_preserves_diagnosable_http_error_response(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth)
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    config = runner.load_execution_config()
    error = runner.ProviderHTTPError(
        400,
        b'{"error":{"message":"bad sk-test-secret request"}}',
        "req-http-error-1",
    )

    record = runner.terminal_record(
        config,
        {"case_id": "case-1", "domain": "reasoning", "split": "validation"},
        "FAILED",
        "http_400",
        {"prompt": "answer"},
        0.01,
        0.002,
        0.25,
        10,
        0,
        4,
        error.provider_data(),
        None,
        "2026-07-19T00:00:00+00:00",
    )

    assert record["provider_request_id_captured"] is True
    assert record["provider_request_id_hash"] == runner.sha256_text("req-http-error-1")
    assert record["finish_reason"] == "provider_error"
    assert record["parser_input_redacted"] is not None
    assert "sk-test-secret" not in record["parser_input_redacted"]
    assert record["parser_input_hash"] == runner.sha256_text(record["parser_input_redacted"])
    assert record["redacted_provider_response"]["_request_id_hint"] == "[REDACTED_PROVIDER_REQUEST_ID]"
    assert record["redacted_provider_response"]["_request_id_hint_hash"] == runner.sha256_text("req-http-error-1")
    assert "sk-test-secret" not in json.dumps(record["redacted_provider_response"])
    assert runner.case_requires_diagnosable_provider_evidence(record) is True
    assert runner.has_diagnosable_provider_evidence(record) is True


def test_clean_clone_recomputation_rejects_hash_only_provider_evidence():
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "executed_cases": 1,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
    }
    aggregate["semantic_hash"] = runner.sha256_text(runner.canonical(aggregate))
    record = {
        "campaign_id": runner.CAMPAIGN_ID,
        "case_id": "case-1",
        "domain": "reasoning",
        "terminal_status": "INVALID_RESPONSE",
        "failure_category": "structured_parse_failed:JSONDecodeError",
        "requested_model": "gpt-authorized",
        "returned_model_identity": "gpt-authorized",
        "redacted_request_hash": "a" * 64,
        "provider_response_hash": "b" * 64,
        "finish_reason": None,
        "parser_input_hash": None,
        "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_reasoning_tokens": 1},
        "cost": {"reserved_usd": 0.1, "consumed_usd": 0.01, "released_usd": 0.09, "unreleased_amount": 0},
        "evaluator_result": None,
    }
    record["semantic_hash"] = runner.recompute_case_semantic_hash(record)

    report = runner.clean_clone_verification_report(aggregate, [record])

    assert report["verification_result"] == "failed"
    assert report["diagnosable_provider_attempts"] is False


def test_clean_clone_recomputation_rejects_failed_provider_attempt_without_diagnostics():
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "executed_cases": 1,
        "completed_cases": 0,
        "failed_cases": 1,
        "timed_out_cases": 0,
        "denied_cases": 0,
        "evidence_unavailable_cases": 0,
        "evaluator_unavailable_cases": 0,
        "invalid_response_cases": 0,
        "infrastructure_failure_cases": 0,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "generated_at": "volatile",
    }
    aggregate["semantic_hash"] = runner.sha256_text(
        runner.canonical({k: v for k, v in aggregate.items() if k not in {"generated_at", "semantic_hash"}})
    )
    record = {
        "campaign_id": runner.CAMPAIGN_ID,
        "case_id": "case-1",
        "domain": "reasoning",
        "terminal_status": "FAILED",
        "failure_category": "provider_malformed_response",
        "requested_model": "gpt-authorized",
        "returned_model_identity": "gpt-authorized",
        "redacted_request_hash": "a" * 64,
        "provider_response_hash": "b" * 64,
        "provider_request_id_captured": True,
        "provider_request_id_hash": None,
        "finish_reason": None,
        "parser_input_hash": None,
        "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_reasoning_tokens": 1},
        "cost": {"reserved_usd": 0.1, "consumed_usd": 0.01, "released_usd": 0.09, "unreleased_amount": 0},
        "evaluator_result": None,
    }
    record["semantic_hash"] = runner.recompute_case_semantic_hash(record)

    report = runner.clean_clone_verification_report(aggregate, [record])

    assert report["verification_result"] == "failed"
    assert report["diagnosable_provider_attempts"] is False


def test_clean_clone_recomputation_allows_failed_before_provider_attempt():
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "executed_cases": 1,
        "completed_cases": 0,
        "failed_cases": 1,
        "timed_out_cases": 0,
        "denied_cases": 0,
        "evidence_unavailable_cases": 0,
        "evaluator_unavailable_cases": 0,
        "invalid_response_cases": 0,
        "infrastructure_failure_cases": 0,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "generated_at": "volatile",
    }
    aggregate["semantic_hash"] = runner.sha256_text(
        runner.canonical({k: v for k, v in aggregate.items() if k not in {"generated_at", "semantic_hash"}})
    )
    record = {
        "campaign_id": runner.CAMPAIGN_ID,
        "case_id": "case-1",
        "domain": "reasoning",
        "terminal_status": "FAILED",
        "failure_category": "schema_validation_failed_before_provider_call",
        "requested_model": "gpt-authorized",
        "returned_model_identity": None,
        "redacted_request_hash": "a" * 64,
        "provider_response_hash": None,
        "provider_request_id_captured": False,
        "provider_request_id_hash": None,
        "finish_reason": None,
        "parser_input_hash": None,
        "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_reasoning_tokens": 0},
        "cost": {"reserved_usd": 0.1, "consumed_usd": 0, "released_usd": 0.1, "unreleased_amount": 0},
        "evaluator_result": None,
    }
    record["semantic_hash"] = runner.recompute_case_semantic_hash(record)

    report = runner.clean_clone_verification_report(aggregate, [record])

    assert report["verification_result"] == "passed"
    assert report["diagnosable_provider_attempts"] is True


def test_clean_clone_recomputation_passes_with_diagnosable_provider_evidence(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth)
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    config = runner.load_execution_config()
    record = runner.terminal_record(
        config,
        {"case_id": "case-1", "domain": "reasoning", "split": "validation"},
        "INVALID_RESPONSE",
        "structured_parse_failed:JSONDecodeError",
        {"prompt": "answer"},
        0.01,
        0.002,
        0.25,
        10,
        0,
        4,
        _provider_data('{"partial":'),
        None,
        "2026-07-19T00:00:00+00:00",
    )
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "executed_cases": 1,
        "completed_cases": 0,
        "failed_cases": 0,
        "timed_out_cases": 0,
        "denied_cases": 0,
        "evidence_unavailable_cases": 0,
        "evaluator_unavailable_cases": 0,
        "invalid_response_cases": 1,
        "infrastructure_failure_cases": 0,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "generated_at": "volatile",
    }
    aggregate["semantic_hash"] = runner.sha256_text(
        runner.canonical({k: v for k, v in aggregate.items() if k not in {"generated_at", "semantic_hash"}})
    )

    report = runner.clean_clone_verification_report(aggregate, [record])

    assert report["verification_result"] == "passed"
    assert report["case_hashes_match"] is True
    assert report["decision_recomputable_without_provider_credentials"] is True


def test_clean_clone_recomputation_rejects_terminal_count_mismatch(monkeypatch, tmp_path):
    auth = tmp_path / "authorization.json"
    _auth(auth)
    monkeypatch.setenv(runner.AUTHORIZATION_ENV, str(auth))
    config = runner.load_execution_config()
    record = runner.terminal_record(
        config,
        {"case_id": "case-1", "domain": "reasoning", "split": "validation"},
        "INVALID_RESPONSE",
        "structured_parse_failed:JSONDecodeError",
        {"prompt": "answer"},
        0.01,
        0.002,
        0.25,
        10,
        0,
        4,
        _provider_data('{"partial":'),
        None,
        "2026-07-19T00:00:00+00:00",
    )
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "executed_cases": 1,
        "completed_cases": 1,
        "invalid_response_cases": 0,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "generated_at": "volatile",
    }
    aggregate["semantic_hash"] = runner.sha256_text(
        runner.canonical({k: v for k, v in aggregate.items() if k not in {"generated_at", "semantic_hash"}})
    )

    report = runner.clean_clone_verification_report(aggregate, [record])

    assert report["verification_result"] == "failed"
    assert report["terminal_totals_reconcile"] is False
    assert report["terminal_count_recomputation"]["completed_cases"] == {"expected": 1, "actual": 0}
    assert report["terminal_count_recomputation"]["invalid_response_cases"] == {"expected": 0, "actual": 1}


def test_write_reports_adds_reproducible_internal_payload_manifest(monkeypatch, tmp_path):
    evidence_dir = tmp_path / "evidence"
    artifact_dir = tmp_path / "artifact"
    monkeypatch.setattr(runner, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(runner, "ARTIFACT_DIR", artifact_dir)
    record = {
        "campaign_id": runner.CAMPAIGN_ID,
        "case_id": "case-1",
        "domain": "reasoning",
        "terminal_status": "EVIDENCE_UNAVAILABLE",
        "failure_category": "budget_guard_refused_start",
        "semantic_hash": "a" * 64,
        "latency_ms": 0,
        "cost": {"reserved_usd": 0.1, "consumed_usd": 0, "released_usd": 0.1, "unreleased_amount": 0},
    }
    aggregate = {
        "campaign_id": runner.CAMPAIGN_ID,
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "provider": "OpenAI",
        "requested_model": "gpt-authorized",
        "authorization_hash": "b" * 64,
        "case_manifest_hash": "c" * 64,
        "evaluator_protocol_hash": "d" * 64,
        "threshold_specification_hash": "e" * 64,
        "executed_cases": 1,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "total_input_tokens": 0,
        "total_cached_input_tokens": 0,
        "total_output_reasoning_tokens": 0,
        "total_campaign_cost_usd": 0,
        "remaining_authorized_campaign_budget_usd": 3,
        "retry_count": 0,
        "generated_at": "volatile",
    }

    runner.write_reports(aggregate, [record], {"reasoning": {"planned_cases": 1}})

    payload = json.loads((evidence_dir / "INTERNAL_PAYLOAD_MANIFEST.json").read_text())
    manifest = json.loads((evidence_dir / "GENESIS_V7_CAMPAIGN_MANIFEST.json").read_text())

    assert reproduce_payload_hash(payload, evidence_dir) == payload["aggregate_payload_hash"]
    assert manifest["internal_payload_manifest_hash"] == payload["aggregate_payload_hash"]
    assert (artifact_dir / "INTERNAL_PAYLOAD_MANIFEST.json").exists()
    assert (artifact_dir / "GENESIS_V7_CAMPAIGN_MANIFEST.json").exists()
    assert "internal_payload_manifest_hash" not in json.loads((evidence_dir / "AGGREGATE_REPORT.json").read_text())
