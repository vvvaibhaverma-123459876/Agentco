from __future__ import annotations

import json
import urllib.error
import urllib.request

import agentco_capability.providers as providers
from agentco_capability.runtime import execute_capability_request


class FakeTransport:
    def __init__(self, failures_before_success: int = 0):
        self.seen: list[dict] = []
        self.failures_before_success = failures_before_success

    def __call__(self, url, payload, headers, timeout, max_bytes):
        self.seen.append({"url": url, "payload": payload, "headers": headers, "timeout": timeout, "max_bytes": max_bytes})
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise providers.ProviderResponseError("retryable_http_429")
        if url.endswith("/chat/completions"):
            return {
                "id": "openai-local-response",
                "model": "local-openai-model",
                "choices": [{"message": {"content": "provider answer"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                "_agentco_latency_ms": 1.0,
            }
        if url.endswith("/v1/messages"):
            return {
                "id": "anthropic-local-response",
                "model": "local-anthropic-model",
                "content": [{"type": "text", "text": "anthropic answer"}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
                "stop_reason": "end_turn",
                "_agentco_latency_ms": 1.0,
            }
        return {"id": "generic-local-response", "answer": {"text": "generic answer"}, "usage": {"requests": 1}, "_agentco_latency_ms": 1.0}


def base_request(provider: str):
    return {
        "protocol_version": "agentco-capability-v1",
        "request_id": f"req-{provider}",
        "attempt_id": f"attempt-{provider}",
        "actor": {"id": "tester"},
        "tenant": "test",
        "task_type": "reasoning",
        "prompt": "Return a provider answer.",
        "structured_input": {},
        "context": {"operation_classification": "capability_task"},
        "memory_policy": {},
        "tool_allowlist": [],
        "provider_policy": {"provider": provider},
        "budget": {"max_wall_ms": 5000, "max_provider_calls": 1, "max_tokens": 32},
        "deadline": None,
        "idempotency_key": f"idem-{provider}",
        "authorization_context": {"permissions": ["capability:execute", "provider:live"]},
        "trace_context": {"trace_id": f"trace-{provider}"},
    }


def allow_local_provider(monkeypatch):
    monkeypatch.setenv("AGENTCO_PROVIDER_ALLOW_LOCAL_HTTP", "1")


def test_openai_compatible_adapter_uses_configured_endpoint(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    fake = FakeTransport()
    monkeypatch.setattr(providers, "_post_json_once", fake)
    base_url = "http://127.0.0.1:12345/v1"
    allow_local_provider(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", base_url)
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "completed"
    assert response["answer"] == "provider answer"
    assert response["provider_usage"]["total_tokens"] == 5
    assert response["structured_output"]["finish_reason"] == "stop"
    assert response["request_metadata"]["headers"]["Authorization"] == "[REDACTED]"
    assert "structured_input" in fake.seen[-1]["payload"]["messages"][1]["content"]


def test_anthropic_compatible_adapter_uses_messages_contract(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    fake = FakeTransport()
    monkeypatch.setattr(providers, "_post_json_once", fake)
    base_url = "http://127.0.0.1:12345"
    allow_local_provider(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "local-anthropic-model")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", base_url)
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("anthropic_compatible"))

    assert response["status"] == "completed"
    assert response["answer"] == "anthropic answer"
    assert response["provider_usage"]["output_tokens"] == 2
    assert fake.seen[-1]["url"].endswith("/v1/messages")


def test_generic_http_adapter_extracts_configured_answer(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    fake = FakeTransport()
    monkeypatch.setattr(providers, "_post_json_once", fake)
    url = "http://127.0.0.1:12345/execute"
    allow_local_provider(monkeypatch)
    monkeypatch.setenv("AGENTCO_GENERIC_PROVIDER_URL", url)
    monkeypatch.setenv("AGENTCO_GENERIC_PROVIDER_TOKEN", "secret-generic")
    monkeypatch.setenv("AGENTCO_GENERIC_ANSWER_FIELD", "answer.text")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("generic_http"))

    assert response["status"] == "completed"
    assert response["answer"] == "generic answer"
    assert response["request_metadata"]["headers"]["Authorization"] == "[REDACTED]"


def test_live_provider_does_not_silently_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "unsupported"
    assert response["provider"] == "openai_compatible"
    assert "OPENAI_API_KEY" in response["failure"]["message"]


def test_openai_adapter_retries_429_then_succeeds(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    fake = FakeTransport(failures_before_success=1)
    monkeypatch.setattr(providers, "_post_json_once", fake)
    allow_local_provider(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:12345/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "2")

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "completed"
    assert response["latency"]["retry_count"] == 1


def test_non_allowlisted_host_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "api.openai.com")

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "unsupported"
    assert "not allowlisted" in response["failure"]["message"]


def test_loopback_requires_explicit_local_development_opt_in(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:12345/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")
    monkeypatch.delenv("AGENTCO_PROVIDER_ALLOW_LOCAL_HTTP", raising=False)

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "unsupported"
    assert "HTTPS outside explicit local development" in response["failure"]["message"]


def test_allowlisted_hostname_resolving_to_private_address_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "api.example.test")
    monkeypatch.setattr(providers, "_resolve_provider_addresses", lambda host, port: ["10.0.0.5"])

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "unsupported"
    assert "forbidden address" in response["failure"]["message"]


def test_forbidden_ipv6_and_unspecified_addresses_fail_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "api.example.test")

    for index, address in enumerate(["::1", "fc00::1", "fe80::1", "::", "ff02::1"]):
        monkeypatch.setattr(providers, "_resolve_provider_addresses", lambda host, port, addr=address: [addr])
        request = base_request("openai_compatible")
        request["request_id"] = f"req-openai-ipv6-{index}"
        request["attempt_id"] = f"attempt-openai-ipv6-{index}"
        request["idempotency_key"] = f"idem-openai-ipv6-{index}"

        response = execute_capability_request(request)

        assert response["status"] == "unsupported"
        assert "forbidden address" in response["failure"]["message"]


def test_alternative_ip_representations_fail_closed_after_resolution(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")

    for index, host in enumerate(["2130706433", "0x7f000001", "017700000001"]):
        monkeypatch.setenv("OPENAI_BASE_URL", f"https://{host}/v1")
        monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", host)
        monkeypatch.setattr(providers, "_resolve_provider_addresses", lambda resolved_host, port: ["127.0.0.1"])
        request = base_request("openai_compatible")
        request["request_id"] = f"req-openai-alt-ip-{index}"
        request["attempt_id"] = f"attempt-openai-alt-ip-{index}"
        request["idempotency_key"] = f"idem-openai-alt-ip-{index}"

        response = execute_capability_request(request)

        assert response["status"] == "unsupported"
        assert "forbidden address" in response["failure"]["message"]


def test_dns_rebinding_between_validation_and_attempt_fails_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "api.example.test")
    calls = {"count": 0}

    def resolving_addresses(host, port):
        calls["count"] += 1
        return ["93.184.216.34"] if calls["count"] == 1 else ["127.0.0.1"]

    monkeypatch.setattr(providers, "_resolve_provider_addresses", resolving_addresses)

    response = execute_capability_request(base_request("openai_compatible"))

    assert response["status"] == "unsupported"
    assert "forbidden address" in response["failure"]["message"]
    assert calls["count"] >= 2


def test_malformed_url_userinfo_and_non_https_fail_closed(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "api.example.test")

    for index, (url, expected) in enumerate([
        ("https://user:pass@api.example.test/v1", "user-info"),
        ("ftp://api.example.test/v1", "scheme"),
        ("http://api.example.test/v1", "HTTPS outside explicit local development"),
    ]):
        monkeypatch.setenv("OPENAI_BASE_URL", url)
        request = base_request("openai_compatible")
        request["request_id"] = f"req-openai-url-{index}"
        request["attempt_id"] = f"attempt-openai-url-{index}"
        request["idempotency_key"] = f"idem-openai-url-{index}"
        response = execute_capability_request(request)
        assert response["status"] == "unsupported"
        assert expected in response["failure"]["message"]


def test_provider_redirects_are_blocked_without_forwarding_credentials(monkeypatch):
    class RedirectingOpener:
        def __init__(self, location):
            self.location = location
            self.seen_headers = None
            self.calls = 0

        def open(self, request, timeout):
            self.calls += 1
            self.seen_headers = dict(request.header_items())
            raise urllib.error.HTTPError(
                request.full_url,
                302,
                "provider redirect blocked",
                {"Location": self.location},
                None,
            )

    for location in [
        "http://127.0.0.1/private",
        "https://10.0.0.5/private",
        "https://not-allowlisted.example/private",
    ]:
        opener = RedirectingOpener(location)
        monkeypatch.setattr(urllib.request, "build_opener", lambda *handlers, op=opener: op)

        try:
            providers._post_json_once(
                "https://api.example.test/v1",
                {"request": "payload"},
                {"Authorization": "Bearer secret-canary"},
                timeout=1,
                max_bytes=1024,
            )
        except providers.ProviderResponseError as exc:
            assert "non_retryable_http_302" in str(exc)
        else:
            raise AssertionError("redirect was not blocked")
        assert opener.calls == 1
        assert opener.seen_headers["Authorization"] == "Bearer secret-canary"
