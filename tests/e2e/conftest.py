"""
E2E test configuration.

Sets LLM environment for learning loop tests that need a real model.
Uses local ollama when available; skips gracefully when neither ollama nor an API key is set.
"""
import os

# Use local ollama for e2e tests unless an API key is explicitly configured
if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")):
    os.environ.setdefault("LLM_API_KEY", "ollama")
    os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
    os.environ.setdefault("LLM_MODEL_EXTRACTION", "llama3:latest")
