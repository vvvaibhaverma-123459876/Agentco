"""
Thin adapter that exposes the OpenAI chat.completions.create() interface over
Anthropic's native Python SDK.

Used when LLM_PROVIDER=anthropic (or LLM_PROVIDER_<TIER>=anthropic).

Anthropic's API differs from the OpenAI shape:
  - System messages are a separate top-level field (not a list item)
  - Response uses .content[0].text instead of .choices[0].message.content
  - Model names: claude-sonnet-4-6, claude-haiku-4-5-20251001, etc.
  - Usage: response.usage.input_tokens + output_tokens

This adapter translates both directions so no agent code needs to change.

Requires: pip install anthropic>=0.40.0
"""
from __future__ import annotations

from typing import Any


def build(api_key: str) -> "_AnthropicAdapter":
    """Build an Anthropic adapter.  Raises ConfigurationError if package is absent."""
    try:
        import anthropic as _anthropic_sdk
    except ImportError as exc:
        from runtime.base_agent.provider_config import ConfigurationError
        raise ConfigurationError(
            "LLM_PROVIDER=anthropic requires 'pip install anthropic>=0.40.0'. "
            f"Original error: {exc}"
        ) from exc
    return _AnthropicAdapter(_anthropic_sdk.Anthropic(api_key=api_key))


class _AnthropicAdapter:
    """
    Drop-in replacement for an OpenAI client.
    Only implements: client.chat.completions.create(**kwargs) -> response
    where response.choices[0].message.content is a string.
    """

    def __init__(self, client: Any) -> None:
        self._client = client
        self.chat = self  # client.chat.completions.create(...)
        self.completions = self

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **_kwargs: Any,
    ) -> "_AnthropicResponse":
        # Extract system message (Anthropic wants it top-level)
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        conversation = [m for m in messages if m["role"] != "system"]
        system_text = "\n\n".join(system_parts) if system_parts else None

        create_kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=conversation,
            temperature=temperature,
        )
        if system_text:
            create_kwargs["system"] = system_text

        resp = self._client.messages.create(**create_kwargs)
        return _AnthropicResponse(resp)


class _AnthropicUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.total_tokens = input_tokens + output_tokens
        self.prompt_tokens = input_tokens
        self.completion_tokens = output_tokens


class _AnthropicMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _AnthropicChoice:
    def __init__(self, content: str) -> None:
        self.message = _AnthropicMessage(content)


class _AnthropicResponse:
    """Wraps an anthropic.types.Message to look like an openai ChatCompletion."""

    def __init__(self, raw: Any) -> None:
        text = raw.content[0].text if raw.content else ""
        self.choices = [_AnthropicChoice(text)]
        self.usage = _AnthropicUsage(
            input_tokens=getattr(raw.usage, "input_tokens", 0),
            output_tokens=getattr(raw.usage, "output_tokens", 0),
        )
