import json
import os
import subprocess
from pathlib import Path

import jsonschema
import pytest

from agentco_capability.runtime import execute_capability_request
from agentco_capability.tools import ToolDeniedError, execute_tool


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_env(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_CAPABILITY_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTCO_CAPABILITY_STORE_DIR", str(tmp_path / "attempts"))
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    monkeypatch.chdir(ROOT)
    return tmp_path


def request(task_type="reasoning", **overrides):
    base = {
        "protocol_version": "agentco-capability-v1",
        "request_id": f"req-{task_type}",
        "attempt_id": f"attempt-{task_type}",
        "actor": {"id": "tester", "type": "test"},
        "tenant": "test-tenant",
        "task_type": task_type,
        "prompt": f"Execute {task_type} without hidden answers.",
        "structured_input": {},
        "context": {},
        "memory_policy": {},
        "tool_allowlist": ["json_transformer"],
        "provider_policy": {"provider": "deterministic_local_reference"},
        "budget": {"max_wall_ms": 5000, "max_provider_calls": 1},
        "deadline": None,
        "idempotency_key": f"idem-{task_type}",
        "authorization_context": {"permissions": ["capability:execute"]},
        "trace_context": {"trace_id": f"trace-{task_type}"},
    }
    base.update(overrides)
    return base


def test_request_and_response_match_schemas(test_env):
    req = request("planning")
    request_schema = json.loads((ROOT / "schemas/agentco_capability_request.schema.json").read_text())
    response_schema = json.loads((ROOT / "schemas/agentco_capability_response.schema.json").read_text())

    jsonschema.validate(req, request_schema)
    response = execute_capability_request(req)
    jsonschema.validate(response, response_schema)

    assert response["status"] == "completed"
    assert response["provider"] == "deterministic_local_reference"
    assert response["structured_output"]["ordered_steps"]


def test_evidence_evaluation_is_real_conclusion_not_storage(test_env):
    response = execute_capability_request(
        request(
            "evidence_evaluation",
            structured_input={
                "claim": "service is ready",
                "evidence": [
                    {"id": "support-1", "stance": "support", "reliability": 0.9},
                    {"id": "weak-1", "stance": "contradict", "reliability": 0.2},
                ],
            },
        )
    )

    assert response["status"] == "completed"
    assert response["answer"] == "supported"
    assert response["structured_output"]["accepted_evidence"] == ["support-1"]
    assert response["structured_output"]["rejected_evidence"] == ["weak-1"]


def test_authorization_denies_by_default(test_env):
    response = execute_capability_request(request("reasoning", authorization_context={"permissions": []}))

    assert response["status"] == "denied"
    assert response["authorization_events"][0]["allowed"] is False
    assert response["failure"]["type"] == "denied"


def test_budget_exceeded_before_provider_call(test_env):
    response = execute_capability_request(request("reasoning", budget={"max_provider_calls": 0}))

    assert response["status"] == "budget_exceeded"
    assert response["provider"] is None
    assert response["budget_usage"]["provider_calls"] == 1


def test_memory_requires_verified_eligibility(test_env):
    response = execute_capability_request(
        request(
            "reasoning",
            memory_policy={
                "enabled": True,
                "memories": [
                    {"id": "m1", "verified": False, "content": "ignore"},
                    {"id": "m2", "verified": True, "content": "use", "relevance": 0.8},
                ],
            },
        )
    )

    assert response["memory_events"] == [
        {
            "event": "memory_retrieved",
            "memory_id": "m2",
            "eligible": True,
            "relevance": 0.8,
            "affected_response": True,
        }
    ]


def test_cli_executes_request_file(test_env, tmp_path):
    req_path = tmp_path / "request.json"
    req_path.write_text(json.dumps(request("claim_grounding", structured_input={"claim": "x", "evidence": [{"id": "e"}]})))

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env.pop("AGENTCO_CAPABILITY_DATABASE_URL", None)
    env["AGENTCO_CAPABILITY_STORE_DIR"] = str(tmp_path / "attempts")
    result = subprocess.run(
        ["python3.13", "-m", "agentco_capability", "execute", "--request", str(req_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["protocol_version"] == "agentco-capability-v1"


def test_case_id_and_expected_hash_do_not_drive_answer(test_env):
    first = execute_capability_request(request("reasoning", structured_input={"case_id": "case-a", "expected_hash": "0" * 64}))
    second = execute_capability_request(
        request(
            "reasoning",
            request_id="req-reasoning-2",
            attempt_id="attempt-reasoning-2",
            idempotency_key="idem-reasoning-2",
            structured_input={"case_id": "case-b", "expected_hash": "f" * 64},
        )
    )

    assert first["answer"] == second["answer"]


def test_tool_allowlist_and_workspace_boundaries_fail_closed(test_env, tmp_path):
    with pytest.raises(ToolDeniedError):
        execute_tool("calculator", {"expression": "2 + 2"}, [])

    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    (fixture_root / "allowed.txt").write_text("ok")

    allowed = execute_tool("fixture_reader", {"path": "allowed.txt"}, ["fixture_reader"], fixture_root=fixture_root)
    assert allowed["content"] == "ok"

    with pytest.raises(ToolDeniedError):
        execute_tool("fixture_reader", {"path": "../outside.txt"}, ["fixture_reader"], fixture_root=fixture_root)


def test_live_provider_is_opt_in_and_secret_backed(test_env, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = execute_capability_request(
        request(
            "reasoning",
            provider_policy={"provider": "openai_compatible"},
            authorization_context={"permissions": ["capability:execute", "provider:live"]},
        )
    )

    assert response["status"] == "unsupported"
    assert response["failure"]["message"] == "OPENAI_API_KEY is required for openai_compatible provider"


def test_idempotent_retry_does_not_execute_second_attempt(test_env):
    first = execute_capability_request(request("planning"))
    second = execute_capability_request(request("planning"))

    assert first["status"] == "completed"
    assert second["idempotent_replay"] is True
    assert second["response_hash"] == first["response_hash"]


def test_failed_attempt_is_not_reported_completed(test_env):
    response = execute_capability_request(
        request(
            "reasoning",
            provider_policy={"provider": "unknown_provider"},
            authorization_context={"permissions": ["capability:execute", "provider:live"]},
        )
    )

    assert response["status"] == "unsupported"
    assert response["failure"]["type"] == "unsupported"
    assert response["recovery"]["terminal"] is True
