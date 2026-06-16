"""
LLM client factory — points at Ollama's OpenAI-compatible endpoint by default.
Repoint to any provider by setting LLM_BASE_URL + LLM_API_KEY in the environment.
"""
import os
from openai import OpenAI


def make_client(
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenAI:
    return OpenAI(
        base_url=base_url or os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=api_key or os.environ.get("LLM_API_KEY", "ollama"),
    )
