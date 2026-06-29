#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "system_run" / "latest" / "openai_connectivity.json"


def load_env() -> None:
    for name in (".codex.env", "codex.env"):
        path = ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = (os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL_DEFAULT") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if not api_key:
        result = {"success": False, "status": "missing_key", "model": model, "latency_ms": None}
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, sort_keys=True))
        return 1
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Return JSON with status, claim, confidence. Claim: This is an Agentco OpenAI connectivity test.",
                }
            ],
            "temperature": 0,
            "max_tokens": 80,
            "response_format": {"type": "json_object"},
        }
    ).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
        latency_ms = int((time.time() - started) * 1000)
        content = payload["choices"][0]["message"]["content"]
        result = {
            "success": True,
            "status": "ok",
            "model": model,
            "latency_ms": latency_ms,
            "response": json.loads(content),
            "usage": payload.get("usage", {}),
        }
        code = 0
    except Exception as exc:
        result = {"success": False, "status": "error", "model": model, "latency_ms": int((time.time() - started) * 1000), "error": str(exc)}
        code = 1
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("success", "status", "model", "latency_ms")}, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
