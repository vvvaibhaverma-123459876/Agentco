"""Epistemic debt tracking (Phase 8)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
import uuid

logger = logging.getLogger(__name__)


class EpistemicDebtRegister:
    """Track unverified high-stakes beliefs."""

    def __init__(self):
        self.debts: dict[str, dict] = {}

    def acknowledge_unverified(self, claim_id: str, justification: str, review_schedule_days: int = 90) -> dict:
        """Register unverified claim as debt."""
        debt_id = str(uuid.uuid4())
        due_date = datetime.now(timezone.utc) + timedelta(days=review_schedule_days)

        self.debts[debt_id] = {
            "debt_id": debt_id,
            "claim_id": claim_id,
            "justification": justification,
            "due_date": due_date,
            "status": "outstanding",
        }

        return {
            "debt_id": debt_id,
            "due_date": due_date.isoformat(),
            "priority": "high" if review_schedule_days < 60 else "normal",
        }

    def debt_status(self, claim_id: str) -> dict:
        """Get debt status."""
        for debt in self.debts.values():
            if debt["claim_id"] == claim_id:
                now = datetime.now(timezone.utc)
                days_left = (debt["due_date"] - now).days
                return {
                    "outstanding": debt["status"] == "outstanding",
                    "days_until_review": max(0, days_left),
                    "priority": 1 if days_left < 7 else 2,
                }

        return {"outstanding": False, "days_until_review": 0, "priority": 0}

    def mark_resolved(self, debt_id: str) -> None:
        """Mark debt as resolved."""
        if debt_id in self.debts:
            self.debts[debt_id]["status"] = "resolved"
