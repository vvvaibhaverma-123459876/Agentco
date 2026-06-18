"""
Per-run LLM spend guardrail.

Tracks token usage and call rate for a single agent instance.  When the cap
is exceeded, raises SpendCapExceeded and (if an escalation gate is wired)
routes a 'spend_cap_exceeded' escalation — halting further LLM calls rather
than letting an autonomous loop run up unbounded cost.

Configuration (environment variables):
  LLM_MAX_TOKENS_PER_RUN   — hard token cap per agent instantiation (default 100_000)
  LLM_RATE_LIMIT_RPM       — max LLM calls per minute per agent (default 60)

Both caps are per-instance (not global across agents in a process).  For a
global process-level cap, a shared SpendGuardrail instance can be passed to
multiple agents.

Under-claim note: token tracking requires the LLM response to include a
`usage.total_tokens` field.  OpenAI and Anthropic (via adapter) both expose
this.  For providers that omit it, usage is estimated as 0 per call, so the
token cap has no effect — only the rate-limit cap applies.  Set
LLM_RATE_LIMIT_RPM to a safe value for those providers.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

_DEFAULT_MAX_TOKENS: int = int(os.environ.get("LLM_MAX_TOKENS_PER_RUN", "100000"))
_DEFAULT_RPM: int = int(os.environ.get("LLM_RATE_LIMIT_RPM", "60"))


class SpendCapExceeded(RuntimeError):
    """Raised when a per-run token or rate-limit cap is exceeded."""


class SpendGuardrail:
    """
    Tracks token usage and call rate for one agent run.

    Usage in structured_output.py:
        guardrail.check_before_call()           # raises if over limit
        ... make the call ...
        guardrail.record_usage(response.usage.total_tokens)  # accumulate
    """

    def __init__(
        self,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        max_calls_per_minute: int = _DEFAULT_RPM,
        agent_id: str = "unknown",
        escalation: Optional[Any] = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._rpm_cap = max_calls_per_minute
        self._agent_id = agent_id
        self._escalation = escalation

        self._tokens_used: int = 0
        self._calls_this_window: int = 0
        self._window_start: float = time.monotonic()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def calls_this_minute(self) -> int:
        self._refresh_window()
        return self._calls_this_window

    def check_before_call(self) -> None:
        """
        Assert that the current call is allowed.  Raises SpendCapExceeded if:
          - cumulative token usage already meets or exceeds max_tokens, OR
          - call rate this minute meets or exceeds max_calls_per_minute.
        Also escalates via EscalationGate if one is wired.
        """
        if self._tokens_used >= self._max_tokens:
            self._escalate_and_raise(
                f"agent '{self._agent_id}' has used {self._tokens_used} tokens "
                f"(cap={self._max_tokens}). Halting further LLM calls.",
                reason="spend_cap_exceeded",
            )

        self._refresh_window()
        if self._calls_this_window >= self._rpm_cap:
            self._escalate_and_raise(
                f"agent '{self._agent_id}' rate limit: {self._calls_this_window} calls "
                f"in the last minute (cap={self._rpm_cap}).",
                reason="rate_limit_exceeded",
            )

        self._calls_this_window += 1

    def record_usage(self, total_tokens: int) -> None:
        """Accumulate token usage from one LLM call response."""
        self._tokens_used += max(0, total_tokens)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_window(self) -> None:
        elapsed = time.monotonic() - self._window_start
        if elapsed >= 60.0:
            self._calls_this_window = 0
            self._window_start = time.monotonic()

    def _escalate_and_raise(self, detail: str, reason: str) -> None:
        if self._escalation is not None:
            try:
                self._escalation.route(
                    reason=reason,
                    detail=detail,
                    risk_level="critical",
                )
            except Exception:
                pass  # escalation must not suppress the primary cap error
        raise SpendCapExceeded(detail)
