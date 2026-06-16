"""
Tests for the local-model setup addendum.

These tests are LLM-independent — they verify the wiring and validation logic
without making real HTTP calls to Ollama.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from runtime.base_agent.model_tiers import model_for, MODEL_TIERS, AGENT_TIER
from runtime.base_agent.structured_output import get_validated_output, _extract_json


# ---------------------------------------------------------------------------
# model_tiers
# ---------------------------------------------------------------------------

class TestModelTiers:
    def test_known_agent_returns_correct_model(self):
        assert model_for("ceo-agent") == MODEL_TIERS["frontier"]
        assert model_for("coder-agent") == MODEL_TIERS["coder"]
        assert model_for("support-agent") == MODEL_TIERS["monitor"]

    def test_unknown_agent_defaults_to_standard(self):
        assert model_for("some-new-agent") == MODEL_TIERS["standard"]

    def test_all_tier_values_are_non_empty_strings(self):
        for tier, model in MODEL_TIERS.items():
            assert isinstance(model, str) and model, f"Empty model for tier {tier}"


# ---------------------------------------------------------------------------
# _extract_json helper
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json(self):
        assert _extract_json('{"a": 1}') == '{"a": 1}'

    def test_strips_code_fence(self):
        raw = '```json\n{"a": 1}\n```'
        assert json.loads(_extract_json(raw)) == {"a": 1}

    def test_strips_prose_around_json(self):
        raw = 'Here is the output: {"a": 1} Done.'
        assert json.loads(_extract_json(raw)) == {"a": 1}


# ---------------------------------------------------------------------------
# get_validated_output — mocked LLM client
# ---------------------------------------------------------------------------

def _make_mock_client(responses: list[str]):
    """Build a mock OpenAI client that returns responses in order."""
    client = MagicMock()
    choices = [MagicMock(message=MagicMock(content=r)) for r in responses]
    client.chat.completions.create.side_effect = [
        MagicMock(choices=[c]) for c in choices
    ]
    return client


SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "number"},
        "action": {"type": "string"},
    },
    "required": ["confidence", "action"],
}


class TestGetValidatedOutput:
    def test_valid_on_first_attempt(self):
        payload = '{"confidence": 0.8, "action": "proceed"}'
        client = _make_mock_client([payload])
        escalation = MagicMock()

        result = get_validated_output(client, "qwen2.5:7b", [], SCHEMA, escalation)

        assert result == {"confidence": 0.8, "action": "proceed"}
        escalation.route.assert_not_called()

    def test_retries_on_invalid_json_then_succeeds(self):
        good = '{"confidence": 0.5, "action": "wait"}'
        client = _make_mock_client(["not json at all", good])
        escalation = MagicMock()

        result = get_validated_output(client, "qwen2.5:7b", [], SCHEMA, escalation)

        assert result["action"] == "wait"
        assert client.chat.completions.create.call_count == 2

    def test_escalates_after_max_retries(self):
        client = _make_mock_client(["bad", "bad", "bad"])
        escalation = MagicMock()
        escalation.route.return_value = {"escalated": True}

        result = get_validated_output(client, "qwen2.5:7b", [], SCHEMA, escalation)

        call_kwargs = escalation.route.call_args.kwargs
        assert call_kwargs["reason"] == "structured_output_failure"
        assert call_kwargs["risk_level"] == "medium"
        assert isinstance(call_kwargs["detail"], str)

    def test_strips_code_fence_before_validation(self):
        payload = '```json\n{"confidence": 0.9, "action": "go"}\n```'
        client = _make_mock_client([payload])
        escalation = MagicMock()

        result = get_validated_output(client, "qwen2.5:7b", [], SCHEMA, escalation)
        assert result["confidence"] == 0.9


# ---------------------------------------------------------------------------
# BaseAgentV2 — client + model wired in
# ---------------------------------------------------------------------------

class TestBaseAgentV2LocalModel:
    def test_agent_has_model_and_client(self):
        from runtime.base_agent.base_agent_v2 import BaseAgentV2

        class ConcreteAgent(BaseAgentV2):
            PROMPT_VERSION = "test-1.0"
            def run(self, task): pass

        with patch("runtime.base_agent.base_agent_v2.make_client") as mc:
            mc.return_value = MagicMock()
            agent = ConcreteAgent("ceo-agent")

        assert agent._model == MODEL_TIERS["frontier"]
        assert agent._llm_client is not None

    def test_act_calls_get_validated_output(self):
        from runtime.base_agent.base_agent_v2 import BaseAgentV2

        class ConcreteAgent(BaseAgentV2):
            PROMPT_VERSION = "test-1.0"
            def run(self, task): pass

        with patch("runtime.base_agent.base_agent_v2.make_client") as mc:
            mc.return_value = MagicMock()
            agent = ConcreteAgent("support-agent")

        with patch("runtime.base_agent.base_agent_v2.get_validated_output") as mock_gvo:
            mock_gvo.return_value = {"confidence": 0.7, "action": "done"}
            result = agent.act([{"role": "user", "content": "go"}], schema=SCHEMA)

        mock_gvo.assert_called_once()
        assert result == {"confidence": 0.7, "action": "done"}
