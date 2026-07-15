from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from agentco_capability.runtime import execute_capability_request


class ProviderHandler(BaseHTTPRequestHandler):
    seen: list[dict] = []
    failures_before_success: int = 0

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode())
        ProviderHandler.seen.append({"path": self.path, "payload": payload, "authorization": self.headers.get("authorization")})
        if ProviderHandler.failures_before_success > 0:
            ProviderHandler.failures_before_success -= 1
            self.send_response(429)
            self.end_headers()
            return
        if self.path.endswith("/chat/completions"):
            body = {
                "id": "openai-local-response",
                "model": "local-openai-model",
                "choices": [{"message": {"content": "provider answer"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            }
        elif self.path.endswith("/v1/messages"):
            body = {
                "id": "anthropic-local-response",
                "model": "local-anthropic-model",
                "content": [{"type": "text", "text": "anthropic answer"}],
                "usage": {"input_tokens": 3, "output_tokens": 2},
                "stop_reason": "end_turn",
            }
        else:
            body = {"id": "generic-local-response", "answer": {"text": "generic answer"}, "usage": {"requests": 1}}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


def start_server():
    ProviderHandler.seen = []
    ProviderHandler.failures_before_success = 0
    server = HTTPServer(("127.0.0.1", 0), ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


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


def test_openai_compatible_adapter_uses_configured_endpoint(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    server = start_server()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", base_url)
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("openai_compatible"))
    server.shutdown()

    assert response["status"] == "completed"
    assert response["answer"] == "provider answer"
    assert response["provider_usage"]["total_tokens"] == 5
    assert response["structured_output"]["finish_reason"] == "stop"
    assert response["request_metadata"]["headers"]["Authorization"] == "[REDACTED]"
    assert "structured_input" in ProviderHandler.seen[-1]["payload"]["messages"][1]["content"]


def test_anthropic_compatible_adapter_uses_messages_contract(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    server = start_server()
    base_url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "local-anthropic-model")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", base_url)
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("anthropic_compatible"))
    server.shutdown()

    assert response["status"] == "completed"
    assert response["answer"] == "anthropic answer"
    assert response["provider_usage"]["output_tokens"] == 2
    assert ProviderHandler.seen[-1]["path"] == "/v1/messages"


def test_generic_http_adapter_extracts_configured_answer(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path))
    server = start_server()
    url = f"http://127.0.0.1:{server.server_port}/execute"
    monkeypatch.setenv("AGENTCO_GENERIC_PROVIDER_URL", url)
    monkeypatch.setenv("AGENTCO_GENERIC_PROVIDER_TOKEN", "secret-generic")
    monkeypatch.setenv("AGENTCO_GENERIC_ANSWER_FIELD", "answer.text")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")

    response = execute_capability_request(base_request("generic_http"))
    server.shutdown()

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
    server = start_server()
    ProviderHandler.failures_before_success = 1
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
    monkeypatch.setenv("OPENAI_MODEL", "local-openai-model")
    monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "127.0.0.1")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "2")

    response = execute_capability_request(base_request("openai_compatible"))
    server.shutdown()

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
