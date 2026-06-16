"""
Escalation Gate — blocks execution on human approval.

INVARIANT: No auto-approve on timeout. If a human has not approved,
           the action does not proceed. The gate raises HumanApprovalRequired
           and the agent must halt.

Mirrors the V1 override-queue but with V2 trusted_confidence context attached.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HumanApprovalRequired(Exception):
    """Raised when an action requires human approval that has not yet been granted."""
    def __init__(self, override_id: str, risk_level: str, action_summary: str):
        self.override_id = override_id
        self.risk_level = risk_level
        self.action_summary = action_summary
        super().__init__(
            f"Human approval required (override_id={override_id}, risk={risk_level}): {action_summary}"
        )


@dataclass
class PendingApproval:
    override_id: str
    agent_id: str
    action_summary: str
    risk_level: str
    trusted_confidence: float
    stated_confidence: float
    domain: str
    claim_type: str
    payload: dict
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved: bool = False
    rejected: bool = False
    approval_token: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class EscalationGate:
    """
    Gate that blocks execution when trusted_confidence is below threshold
    or risk_level requires human oversight.

    INVARIANT: approved=False means the action DOES NOT run. Period.
               No timeout auto-approval. No fallback execution.
    """

    # Actions with risk_level >= these thresholds require human approval
    REQUIRE_APPROVAL_RISK_LEVELS = {"high", "critical"}

    # If trusted_confidence falls below this, require human approval regardless of risk_level
    CONFIDENCE_APPROVAL_THRESHOLD = 0.50

    def __init__(self):
        self._pending: dict[str, PendingApproval] = {}

    def check_and_gate(
        self,
        agent_id: str,
        action_summary: str,
        risk_level: str,
        trusted_confidence: float,
        stated_confidence: float,
        domain: str,
        claim_type: str,
        payload: dict,
        pre_approved_token: Optional[str] = None,
    ) -> str:
        """
        Check if this action can proceed. Returns override_id.
        Raises HumanApprovalRequired if human must approve first.
        If pre_approved_token is provided and valid, proceeds without blocking.
        """
        needs_approval = (
            risk_level in self.REQUIRE_APPROVAL_RISK_LEVELS
            or trusted_confidence < self.CONFIDENCE_APPROVAL_THRESHOLD
        )

        if not needs_approval:
            return "auto-approved"

        # Check if a valid pre-approved token was provided
        if pre_approved_token:
            for pending in self._pending.values():
                if pending.approval_token == pre_approved_token and pending.approved:
                    logger.info(
                        "ESCALATION GATE: pre-approved token accepted for agent=%s action=%s",
                        agent_id, action_summary[:60]
                    )
                    return pending.override_id

        # No valid approval — create pending request and block
        override_id = str(uuid.uuid4())
        pending = PendingApproval(
            override_id=override_id,
            agent_id=agent_id,
            action_summary=action_summary,
            risk_level=risk_level,
            trusted_confidence=trusted_confidence,
            stated_confidence=stated_confidence,
            domain=domain,
            claim_type=claim_type,
            payload=payload,
        )
        self._pending[override_id] = pending
        logger.warning(
            "ESCALATION GATE BLOCKED: override_id=%s agent=%s risk=%s trusted_conf=%.3f",
            override_id, agent_id, risk_level, trusted_confidence
        )
        raise HumanApprovalRequired(override_id, risk_level, action_summary)

    def approve(self, override_id: str, approver_id: str) -> str:
        """Human approves a pending action. Returns approval token."""
        pending = self._pending.get(override_id)
        if not pending:
            raise ValueError(f"Override {override_id!r} not found")
        if pending.rejected:
            raise ValueError(f"Override {override_id!r} was already rejected")
        token = str(uuid.uuid4())
        pending.approved = True
        pending.approval_token = token
        pending.resolved_at = datetime.now(timezone.utc)
        pending.resolved_by = approver_id
        logger.info("ESCALATION GATE APPROVED: override_id=%s by=%s", override_id, approver_id)
        return token

    def reject(self, override_id: str, rejector_id: str) -> None:
        """Human rejects a pending action. Action must not proceed."""
        pending = self._pending.get(override_id)
        if not pending:
            raise ValueError(f"Override {override_id!r} not found")
        pending.rejected = True
        pending.resolved_at = datetime.now(timezone.utc)
        pending.resolved_by = rejector_id
        logger.warning("ESCALATION GATE REJECTED: override_id=%s by=%s", override_id, rejector_id)

    def list_pending(self) -> list[PendingApproval]:
        return [p for p in self._pending.values() if not p.approved and not p.rejected]
