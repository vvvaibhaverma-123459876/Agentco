"""
Surprise Register — detects when reality diverges from what the system believed.

A surprise is when a high-confidence prediction resolves FALSE or
a low-confidence prediction resolves TRUE with high surprise score.
Surprises trigger Trust Controller downgrade propagation.

The Surprise Register maximises SURPRISE DETECTION, not coverage of unknown unknowns.
We do not claim to simulate black swans we cannot conceive. We detect when reality
contradicts what we thought we knew.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionRecord

logger = logging.getLogger(__name__)


@dataclass
class SurpriseEvent:
    surprise_id: str
    prediction_id: str
    producing_agent_id: str
    stated_probability: float
    actual_outcome: bool
    surprise_score: float          # 0–1; higher = more surprising
    domain: str
    claim_type: str
    horizon_class: str
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    investigated: bool = False
    investigation_notes: str = ""


class SurpriseRegister:
    """
    Detects and catalogues surprises. Does NOT attempt to explain tail events
    it could not have anticipated — it records what happened and triggers review.
    """

    HIGH_CONFIDENCE_THRESHOLD = 0.80   # prediction with p >= this resolving FALSE = surprise
    LOW_CONFIDENCE_THRESHOLD = 0.20    # prediction with p <= this resolving TRUE = surprise
    SURPRISE_SCORE_WEIGHT = 2.0        # how harshly to penalise high-confidence misses

    def __init__(self):
        self._events: list[SurpriseEvent] = []

    def check(self, record: "PredictionRecord", outcome: bool) -> bool:
        """
        Returns True if this resolution is a surprise.
        Called by Resolution Service before registering the event.
        """
        p = record.probability
        is_surprise = False

        if outcome is False and p >= self.HIGH_CONFIDENCE_THRESHOLD:
            is_surprise = True
            logger.warning(
                "SURPRISE: high-confidence prediction resolved FALSE — agent=%s p=%.3f domain=%s",
                record.producing_agent_id, p, record.domain
            )
        elif outcome is True and p <= self.LOW_CONFIDENCE_THRESHOLD:
            is_surprise = True
            logger.info(
                "SURPRISE: low-confidence prediction resolved TRUE — agent=%s p=%.3f domain=%s",
                record.producing_agent_id, p, record.domain
            )

        return is_surprise

    def register_surprise(self, record: "PredictionRecord", outcome: bool) -> SurpriseEvent:
        """Register a confirmed surprise for investigation and Trust Controller notification."""
        import uuid
        p = record.probability

        # Surprise score: 0–1, higher = more surprising
        if outcome is False:
            score = p ** self.SURPRISE_SCORE_WEIGHT  # high p that missed = very surprising
        else:
            score = (1.0 - p) ** self.SURPRISE_SCORE_WEIGHT  # low p that hit = surprising

        event = SurpriseEvent(
            surprise_id=str(uuid.uuid4()),
            prediction_id=record.prediction_id,
            producing_agent_id=record.producing_agent_id,
            stated_probability=p,
            actual_outcome=outcome,
            surprise_score=round(score, 4),
            domain=record.domain,
            claim_type=record.claim_type,
            horizon_class=record.horizon_class,
        )
        self._events.append(event)
        logger.warning(
            "SURPRISE REGISTERED: id=%s agent=%s score=%.4f domain=%s — scheduled for investigation",
            event.surprise_id, event.producing_agent_id, event.surprise_score, event.domain
        )
        return event

    def list_uninvestigated(self) -> list[SurpriseEvent]:
        return [e for e in self._events if not e.investigated]

    def list_all(self, domain: Optional[str] = None) -> list[SurpriseEvent]:
        if domain:
            return [e for e in self._events if e.domain == domain]
        return list(self._events)

    def mark_investigated(self, surprise_id: str, notes: str) -> None:
        for e in self._events:
            if e.surprise_id == surprise_id:
                e.investigated = True
                e.investigation_notes = notes
                logger.info("SURPRISE INVESTIGATED: id=%s", surprise_id)
                return
        raise ValueError(f"Surprise {surprise_id!r} not found")
