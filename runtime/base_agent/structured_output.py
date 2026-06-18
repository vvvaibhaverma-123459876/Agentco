"""
Validate-and-retry layer for structured LLM output.

Provider-agnostic: works with any client that exposes
  client.chat.completions.create(model, messages, temperature)
and returns response.choices[0].message.content.

Escalates on repeated structured-output failure; never emits malformed output
to the event bus.

If a SpendGuardrail is passed, it is checked BEFORE each attempt and updated
AFTER (with token usage from response.usage.total_tokens when available).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def get_validated_output(
    client: Any,
    model: str,
    messages: list[dict],
    schema: dict,
    escalation: Any,
    guardrail: Optional[Any] = None,
) -> dict:
    """
    Call the model; validate against schema; retry with corrective feedback;
    escalate on repeated failure. Never returns malformed structured output.

    guardrail — optional SpendGuardrail; checked before each call and updated
                after with token usage.  Raises SpendCapExceeded if over limit.
    """
    last_error: Exception | None = None
    current_messages = list(messages)

    for attempt in range(MAX_RETRIES):
        if guardrail is not None:
            guardrail.check_before_call()  # raises SpendCapExceeded if over limit

        resp = client.chat.completions.create(
            model=model,
            messages=current_messages,
            temperature=0.2,
        )

        if guardrail is not None:
            usage = getattr(resp, "usage", None)
            if usage is not None:
                total = getattr(usage, "total_tokens", 0) or 0
                if isinstance(total, int):
                    guardrail.record_usage(total)

        raw = resp.choices[0].message.content or ""
        try:
            parsed = json.loads(_extract_json(raw))
            validate(instance=parsed, schema=schema)
            return parsed
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Structured output invalid (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES, exc,
            )
            current_messages = current_messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"That output was invalid: {exc}. "
                        "Return ONLY valid JSON matching the schema. No prose, no code fences."
                    ),
                },
            ]

    logger.error("Structured output failed after %d attempts; escalating.", MAX_RETRIES)
    return escalation.route(
        reason="structured_output_failure",
        detail=str(last_error),
        risk_level="medium",
    )


def _extract_json(raw: str) -> str:
    """Strip markdown code fences and leading/trailing prose from model output."""
    s = raw.strip()
    if "```" in s:
        s = s.split("```")[1]
        if s.startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    return s[start : end + 1] if start != -1 and end != -1 else s
