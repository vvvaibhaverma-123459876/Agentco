"""Minimal Agentco governed API Python SDK stub."""
from __future__ import annotations

import json
from urllib import request


class AgentcoClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _post(self, path: str, payload: dict, idempotency_key: str | None = None) -> dict:
        headers = {"Content-Type": "application/json", "x-agentco-api-key": self.api_key}
        if idempotency_key:
            headers["idempotency-key"] = idempotency_key
        req = request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def create_institution(self, name: str, idempotency_key: str | None = None) -> dict:
        return self._post("/institutions", {"name": name}, idempotency_key)

    def register_claim(self, claim: str, probability: float, idempotency_key: str | None = None) -> dict:
        return self._post("/claims/register", {"claim": claim, "probability": probability}, idempotency_key)
