#!/usr/bin/env python3
"""Minimal sanitized OpenAI-compatible connectivity check for AgentCo."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
OUT = REPORT_DIR / "openai_connectivity.json"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def main() -> int:
    load_env_file(ROOT / "codex.env")
    load_env_file(ROOT / ".codex.env")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL_DEFAULT") or "gpt-4o-mini"
    base_url = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    result = {
        "success": False,
        "provider_path": "openai_compatible_chat_completions",
        "model": model,
        "base_url_present": bool(base_url),
        "api_key_present": bool(key),
        "latency_ms": None,
        "response": None,
        "error": None,
    }
    if not key:
        result["error"] = "missing OPENAI_API_KEY/LLM_API_KEY"
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only compact JSON with status, claim, and confidence."},
            {"role": "user", "content": 'Return JSON for this claim: "This is an AgentCo OpenAI connectivity test."'},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 80,
    }
    request = urllib.request.Request(
        api_url(base_url),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {"raw_excerpt": content[:160]}
        result.update(
            {
                "success": True,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "response": parsed,
                "usage": body.get("usage"),
            }
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError) as exc:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        if isinstance(exc, urllib.error.HTTPError):
            result["error"] = f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}"
        else:
            result["error"] = str(exc)

    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
