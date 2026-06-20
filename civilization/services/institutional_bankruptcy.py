"""Institutional bankruptcy when trust collapses (Phase 4)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BankruptcyAssessment:
    """Institutional bankruptcy assessment."""
    bankruptcy_score: float  # 0-1, > 0.7 triggers bankruptcy
    wrong_determinations: int
    approval_speed_avg_seconds: float
    rubber_stamp_rate: float  # % of approvals < 5 min
    status: str  # 'healthy', 'at_risk', 'bankrupt'


class InstitutionalBankruptcyEngine:
    """Assess and trigger institutional bankruptcy."""

    def bankruptcy_score(self, institution_id: str, determinations: list[dict]) -> BankruptcyAssessment:
        """
        Compute bankruptcy score.

        Args:
            institution_id: Institution ID
            determinations: list of {correct, approval_time_seconds}

        Returns:
            BankruptcyAssessment
        """
        if not determinations:
            return BankruptcyAssessment(
                bankruptcy_score=0.0,
                wrong_determinations=0,
                approval_speed_avg_seconds=0.0,
                rubber_stamp_rate=0.0,
                status="healthy",
            )

        wrong = sum(1 for d in determinations if not d.get("correct", True))
        wrong_rate = wrong / len(determinations)

        times = [d.get("approval_time_seconds", 300) for d in determinations]
        avg_time = sum(times) / len(times)

        rubber_stamps = sum(1 for t in times if t < 300)  # 5 min
        rubber_stamp_rate = rubber_stamps / len(times)

        # Score: 0.4 * wrong_rate + 0.3 * (fast_approvals) + 0.3 * (rubber_stamp_rate)
        bankruptcy = 0.4 * wrong_rate + 0.3 * min(1.0, avg_time / 60) + 0.3 * rubber_stamp_rate

        if bankruptcy > 0.7:
            status = "bankrupt"
        elif bankruptcy > 0.5:
            status = "at_risk"
        else:
            status = "healthy"

        return BankruptcyAssessment(
            bankruptcy_score=min(1.0, bankruptcy),
            wrong_determinations=wrong,
            approval_speed_avg_seconds=avg_time,
            rubber_stamp_rate=rubber_stamp_rate,
            status=status,
        )

    def trigger_bankruptcy(self, institution_id: str) -> dict:
        """Trigger institutional bankruptcy."""
        return {
            "institution_id": institution_id,
            "status": "bankrupt",
            "action": "QUARANTINE_AND_REBUILD",
            "message": "Institution quarantined. All determinations under review.",
        }
