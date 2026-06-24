"""
Autonomy Orchestrator HTTP Client
==================================

Communicates with the TypeScript autonomy orchestrator service
to execute goals and process results.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import http.client
from urllib.parse import urlparse

from agents.db import get_db, query_autonomy_evidence

logger = logging.getLogger(__name__)


class OrchestratorClient:
    """HTTP client for autonomy orchestrator."""

    def __init__(self, base_url: str = "http://localhost:3000"):
        """Initialize orchestrator client.

        Args:
            base_url: Base URL of autonomy orchestrator (default: localhost:3000)
        """
        self.base_url = base_url.rstrip("/")
        self.db = get_db()

    async def execute_autonomy_loop(
        self, goal_id: str, objective: str, timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """Execute an autonomy loop for a specific goal.

        Args:
            goal_id: The autonomy_goals.id to execute
            objective: Human-readable goal description
            timeout_seconds: Max time to run (default: 60)

        Returns:
            Results dict with claims, evidence, actions, etc.
        """
        try:
            logger.info(f"Executing autonomy loop for goal {goal_id}: {objective}")

            # Build request payload
            payload = {
                "goalId": goal_id,
                "objective": objective,
                "maxDurationSeconds": timeout_seconds,
            }

            # Call orchestrator
            response = await self._http_post(
                "/api/autonomy/action-loop",
                payload,
                timeout=timeout_seconds + 10,  # HTTP timeout > loop timeout
            )

            if response["status"] == "error":
                logger.error(f"Orchestrator error: {response.get('message')}")
                return {
                    "status": "failed",
                    "goal_id": goal_id,
                    "error": response.get("message"),
                    "claims": [],
                    "evidence": [],
                }

            # Process results
            result = self._process_orchestrator_result(goal_id, response)
            logger.info(
                f"Loop completed: {result['claims_extracted']} claims, "
                f"{result['evidence_collected']} evidence"
            )

            return result

        except Exception as e:
            logger.error(f"Orchestrator execution failed: {e}")
            return {
                "status": "failed",
                "goal_id": goal_id,
                "error": str(e),
                "claims": [],
                "evidence": [],
            }

    def _process_orchestrator_result(
        self, goal_id: str, response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process orchestrator response and extract artifacts.

        Args:
            goal_id: The goal that was executed
            response: Response from orchestrator

        Returns:
            Processed results with counts and IDs
        """
        result = {
            "status": "success",
            "goal_id": goal_id,
            "claims_extracted": 0,
            "evidence_collected": 0,
            "actions_executed": response.get("actionsExecuted", 0),
            "loop_reason": response.get("reason", ""),
            "claim_ids": [],
            "evidence_ids": [],
        }

        # Extract artifacts from response
        if "artifacts" in response:
            artifacts = response["artifacts"]

            # Count evidence and claims
            evidence_ids = [a for a in artifacts if a.startswith("evidence_")]
            claim_ids = [a for a in artifacts if a.startswith("claim_")]

            result["evidence_collected"] = len(evidence_ids)
            result["claims_extracted"] = len(claim_ids)
            result["evidence_ids"] = evidence_ids
            result["claim_ids"] = claim_ids

        return result

    async def _http_post(
        self, endpoint: str, payload: Dict[str, Any], timeout: int = 30
    ) -> Dict[str, Any]:
        """Make HTTP POST request to orchestrator.

        Args:
            endpoint: API endpoint (e.g., "/api/autonomy/action-loop")
            payload: Request body
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response
        """
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        try:
            # Use http.client for simplicity (no external dependencies)
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(host, port, timeout=timeout)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            body = json.dumps(payload)
            conn.request("POST", endpoint, body, headers)

            response = conn.getresponse()
            response_body = response.read().decode("utf-8")

            if response.status != 200:
                logger.warning(
                    f"Orchestrator returned {response.status}: {response_body[:200]}"
                )
                return {
                    "status": "error",
                    "message": f"HTTP {response.status}",
                }

            return json.loads(response_body)

        except Exception as e:
            logger.error(f"HTTP POST failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
        finally:
            if "conn" in locals():
                conn.close()


async def execute_goal_via_orchestrator(
    goal_id: str, objective: str, timeout_seconds: int = 60
) -> Dict[str, Any]:
    """Convenience function to execute goal via orchestrator.

    Args:
        goal_id: The goal to execute
        objective: Goal description
        timeout_seconds: Timeout for execution

    Returns:
        Results dict with artifacts and metrics
    """
    client = OrchestratorClient()
    return await client.execute_autonomy_loop(goal_id, objective, timeout_seconds)
