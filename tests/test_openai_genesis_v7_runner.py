from __future__ import annotations

import json

import pytest

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
