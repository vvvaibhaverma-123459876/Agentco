"""
Principle Library — stores cross-domain insights discovered by Synthesis-Agent.

Every principle enters as "provisional". Promotion to "reality_validated"
requires the same path as any belief: pre-registered predictions, external
ground truth, Resolution Service scoring.

The library enforces: NO principle may be tagged reality_validated
unless it has an associated belief_id that the Firewall has promoted.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Principle:
    principle_id: str
    title: str
    description: str
    source_domains: list[str]          # which domains this principle spans
    evidence_prediction_ids: list[str] # ledger predictions that support this
    validation_status: str             # "provisional" | "reality_validated"
    belief_id: Optional[str]           # firewall belief_id (required for reality_validated)
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    promoted_at: Optional[datetime] = None
    cited_by: list[str] = field(default_factory=list)


class PrincipleLibrary:
    """
    Append-only store of cross-domain principles.
    Principles start provisional. Promotion requires an externally-verified belief.
    """

    def __init__(self, firewall=None):
        self._principles: dict[str, Principle] = {}
        self._firewall = firewall

    def add_principle(
        self,
        title: str,
        description: str,
        source_domains: list[str],
        confidence: float = 0.5,
        evidence_prediction_ids: Optional[list[str]] = None,
    ) -> Principle:
        """Add a new provisional principle. Always starts as provisional."""
        p = Principle(
            principle_id=str(uuid.uuid4()),
            title=title,
            description=description,
            source_domains=source_domains,
            evidence_prediction_ids=evidence_prediction_ids or [],
            validation_status="provisional",
            belief_id=None,
            confidence=confidence,
        )
        self._principles[p.principle_id] = p
        logger.info(
            "PRINCIPLE LIBRARY: added provisional principle %s '%s' domains=%s",
            p.principle_id, title[:50], source_domains
        )
        return p

    def promote_principle(self, principle_id: str, belief_id: str) -> bool:
        """
        Promote a principle to reality_validated IF the associated belief
        has been promoted by the Firewall. Refuses if firewall says otherwise.
        """
        p = self._principles.get(principle_id)
        if not p:
            raise ValueError(f"Principle {principle_id!r} not found")

        if self._firewall:
            belief = self._firewall._beliefs.get(belief_id)
            if not belief or belief.validation_status != "reality_validated":
                logger.warning(
                    "PRINCIPLE LIBRARY: promotion refused for %s — belief %s is not reality_validated (status=%s)",
                    principle_id, belief_id, belief.validation_status if belief else "not_found"
                )
                return False

        p.validation_status = "reality_validated"
        p.belief_id = belief_id
        p.promoted_at = datetime.now(timezone.utc)
        logger.info(
            "PRINCIPLE LIBRARY: promoted principle %s '%s' to reality_validated via belief %s",
            principle_id, p.title[:50], belief_id
        )
        return True

    def get(self, principle_id: str) -> Optional[Principle]:
        return self._principles.get(principle_id)

    def list_by_status(self, status: str) -> list[Principle]:
        return [p for p in self._principles.values() if p.validation_status == status]

    def list_by_domain(self, domain: str) -> list[Principle]:
        return [p for p in self._principles.values() if domain in p.source_domains]
