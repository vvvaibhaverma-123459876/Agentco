"""Minority report publication (Phase 4)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


@dataclass
class DissentRecord:
    """Dissenting opinion."""
    dissent_id: str
    claim_id: str
    reviewer_id: str
    rationale: str
    published: bool
    visibility: str  # 'public', 'institutional', 'private'
    timestamp: datetime


class MinorityReportManager:
    """Publish dissenting opinions."""

    def __init__(self):
        self.dissents: dict[str, DissentRecord] = {}

    def publish_dissent(self, claim_id: str, reviewer_id: str, rationale: str, visibility: str = "public") -> DissentRecord:
        """
        Publish dissenting opinion.

        Args:
            claim_id: Claim being reviewed
            reviewer_id: Dissenting reviewer
            rationale: Why they disagree
            visibility: public/institutional/private

        Returns:
            DissentRecord
        """
        dissent = DissentRecord(
            dissent_id=str(uuid.uuid4()),
            claim_id=claim_id,
            reviewer_id=reviewer_id,
            rationale=rationale,
            published=True,
            visibility=visibility,
            timestamp=datetime.now(timezone.utc),
        )

        self.dissents[dissent.dissent_id] = dissent

        logger.info(
            "DISSENT PUBLISHED: claim=%s reviewer=%s visibility=%s",
            claim_id, reviewer_id, visibility
        )

        return dissent

    def get_dissents_for_claim(self, claim_id: str) -> list[DissentRecord]:
        """Get all dissents for a claim."""
        return [d for d in self.dissents.values() if d.claim_id == claim_id and d.published]

    def count_dissents(self, claim_id: str) -> int:
        """Count dissents for claim."""
        return len(self.get_dissents_for_claim(claim_id))
