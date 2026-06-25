#!/usr/bin/env python3
"""Minimal bounded specialist HTTP runtime used by TeamActivationService.

The Node service starts this module with ``python3 -m agents.autonomy.<role>``.
It exposes:
  - GET /status
  - POST /execute

The runtime verifies the HMAC signature sent by TeamActivationService, enforces
iteration/time budgets, and returns structured ActionResult-shaped JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class SpecialistState:
    def __init__(self, specialist_id: str, role: str, budget: dict[str, Any]) -> None:
        self.specialist_id = specialist_id
        self.role = role
        self.budget = budget
        self.started_at = time.time()
        self.iterations_used = 0
        self.tokens_used = 0

    def budget_error(self) -> str | None:
        seconds_budget = float(self.budget.get("seconds", 60))
        iterations_budget = int(self.budget.get("iterations", 1))
        tokens_budget = int(self.budget.get("tokens", 1))
        if time.time() - self.started_at > seconds_budget:
            return "time budget exceeded"
        if self.iterations_used >= iterations_budget:
            return "iteration budget exceeded"
        if self.tokens_used > tokens_budget:
            return "token budget exceeded"
        return None


class SpecialistHandler(BaseHTTPRequestHandler):
    state: SpecialistState
    shared_secret: str

    def do_GET(self) -> None:
        if self.path != "/status":
            self.send_json(404, {"error": "not found"})
            return
        self.send_json(200, {
            "status": "ready",
            "specialist_id": self.state.specialist_id,
            "role": self.state.role,
            "iterations_used": self.state.iterations_used,
            "tokens_used": self.state.tokens_used,
        })

    def do_POST(self) -> None:
        if self.path != "/execute":
            self.send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if not self.valid_signature(body):
            self.send_json(401, {"error": "invalid signature"})
            return

        budget_error = self.state.budget_error()
        if budget_error:
            self.send_json(429, {"error": budget_error})
            return

        try:
            action = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid json"})
            return

        self.state.iterations_used += 1
        self.state.tokens_used += max(1, len(body) // 4)
        action_type = str(action.get("actionType", "unknown"))
        action_id = str(action.get("actionId", ""))

        self.send_json(200, {
            "actionId": action_id,
            "status": "completed",
            "tokens_used": max(1, len(body) // 4),
            "artifacts": [],
            "observations": {
                "specialist_id": self.state.specialist_id,
                "role": self.state.role,
                "accepted_action_type": action_type,
                "objective": str(action.get("objective", "")),
                "status": "bounded_action_completed",
            },
        })

    def valid_signature(self, body: bytes) -> bool:
        signature = self.headers.get("X-Signature", "")
        timestamp = self.headers.get("X-Timestamp", "")
        if not signature or not timestamp:
            return False
        message = body.decode("utf-8") + ":" + timestamp
        expected = hmac.new(
            self.shared_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.state.specialist_id}] {fmt % args}", flush=True)


def run(role_name: str | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--specialist-id", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--role", default=role_name or "specialist")
    parser.add_argument("--budget", default="{}")
    args = parser.parse_args()

    budget = json.loads(args.budget)
    SpecialistHandler.state = SpecialistState(args.specialist_id, args.role, budget)
    SpecialistHandler.shared_secret = os.environ.get("SPECIALIST_SHARED_SECRET", "default-insecure-secret")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), SpecialistHandler)
    print(f"{args.role} specialist ready on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
