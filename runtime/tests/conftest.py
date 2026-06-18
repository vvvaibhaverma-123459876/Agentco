"""
Runtime test environment setup.

Sets a minimal LLM configuration so that BaseAgentV2.__init__() can build an
OpenAI-compatible client object without a real API key.  Tests that exercise
actual LLM calls must patch client.chat.completions.create themselves.
"""
import os
import pytest
from runtime.base_agent.llm_client import clear_client_cache


@pytest.fixture(autouse=True)
def llm_test_env(monkeypatch):
    """
    Inject test-safe LLM env vars for every runtime test.

    Uses OpenAI provider with a placeholder key so the OpenAI SDK constructor
    does not raise "Missing credentials".  No real API calls are made by tests
    that do not patch the client — tests that call act() must mock client_for.
    """
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-placeholder-not-real")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("LLM_MODEL_DEFAULT", "gpt-4o-mini")
    # Clear cached clients so each test starts fresh
    clear_client_cache()
    yield
    clear_client_cache()
