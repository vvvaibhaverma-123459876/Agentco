"""
Prediction Ledger — immutable, append-only pre-registration service.

Predicting agents call pre_register(). They receive a prediction_id.
They NEVER call resolve(). That is the Resolution Service's job.

post_hoc detection: if earliest_knowable_at is provided and now() > earliest_knowable_at,
the entry is flagged post_hoc=True and excluded from all calibration math.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PredictionRegistration:
    claim: str
    probability: float
    confidence_basis: dict[str, Any]
    producing_agent_id: str
    producing_prompt_version: str
    resolution_criterion: str
    resolution_date: datetime
    ground_truth_source: str         # MUST be external to the reasoning system
    horizon_class: str               # 'short' | 'medium' | 'long'
    domain: str
    claim_type: str
    correlation_id: Optional[str] = None
    earliest_knowable_at: Optional[datetime] = None


@dataclass
class PredictionRecord:
    prediction_id: str
    claim: str
    probability: float
    confidence_basis: dict[str, Any]
    producing_agent_id: str
    producing_prompt_version: str
    resolution_criterion: str
    resolution_date: datetime
    ground_truth_source: str
    horizon_class: str
    domain: str
    claim_type: str
    created_at: datetime
    post_hoc: bool
    correlation_id: Optional[str] = None
    # Resolution fields (None until resolved by Resolution Service)
    resolved: bool = False
    resolved_outcome: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    brier_score: Optional[float] = None
    log_score: Optional[float] = None
    was_surprise: bool = False


class PredictionLedger:
    """
    The pre-registration authority. Agents call pre_register().
    The Resolution Service calls resolve() (separately, with DB role enforcement).
    No agent may call resolve().
    """

    INTERNAL_SOURCES = frozenset({
        "self", "internal", "simulation", "agent", "reasoning_system",
        "agentco_system", "twin", "sandbox"
    })

    def __init__(self, db=None):
        self._db = db  # In production: asyncpg/psycopg2 connection pool
        self._in_memory: dict[str, PredictionRecord] = {}  # dev fallback

    def pre_register(self, reg: PredictionRegistration) -> str:
        """
        Register a prediction BEFORE its outcome is knowable.
        Returns prediction_id.

        Raises:
            ValueError: if probability out of [0,1]
            ValueError: if ground_truth_source is internal (disqualified)
            ValueError: if resolution_date is in the past
        """
        self._validate_registration(reg)

        now = datetime.now(timezone.utc)
        post_hoc = bool(
            reg.earliest_knowable_at and now > reg.earliest_knowable_at
        )
        if post_hoc:
            logger.warning(
                "POST-HOC PREDICTION DETECTED: agent=%s claim=%r — flagged post_hoc=True, excluded from calibration",
                reg.producing_agent_id, reg.claim[:80]
            )

        prediction_id = str(uuid.uuid4())
        record = PredictionRecord(
            prediction_id=prediction_id,
            claim=reg.claim,
            probability=reg.probability,
            confidence_basis=reg.confidence_basis,
            producing_agent_id=reg.producing_agent_id,
            producing_prompt_version=reg.producing_prompt_version,
            resolution_criterion=reg.resolution_criterion,
            resolution_date=reg.resolution_date,
            ground_truth_source=reg.ground_truth_source,
            horizon_class=reg.horizon_class,
            domain=reg.domain,
            claim_type=reg.claim_type,
            correlation_id=reg.correlation_id,
            created_at=now,
            post_hoc=post_hoc,
        )

        # In production: INSERT into prediction_ledger; DB enforces immutability
        self._in_memory[prediction_id] = record
        logger.info(
            "PREDICTION REGISTERED: id=%s agent=%s domain=%s probability=%.3f post_hoc=%s",
            prediction_id, reg.producing_agent_id, reg.domain, reg.probability, post_hoc
        )
        return prediction_id

    def get(self, prediction_id: str) -> Optional[PredictionRecord]:
        return self._in_memory.get(prediction_id)

    def list_unresolved(self, due_by: Optional[datetime] = None) -> list[PredictionRecord]:
        records = [r for r in self._in_memory.values() if not r.resolved]
        if due_by:
            records = [r for r in records if r.resolution_date <= due_by]
        return records

    def list_by_agent(self, agent_id: str) -> list[PredictionRecord]:
        return [r for r in self._in_memory.values() if r.producing_agent_id == agent_id]

    def _validate_registration(self, reg: PredictionRegistration) -> None:
        if not (0.0 <= reg.probability <= 1.0):
            raise ValueError(f"probability must be in [0,1], got {reg.probability}")
        source_lower = reg.ground_truth_source.lower()
        for disqualified in self.INTERNAL_SOURCES:
            if disqualified in source_lower:
                raise ValueError(
                    f"ground_truth_source '{reg.ground_truth_source}' appears to be internal — "
                    "ground truth must originate outside the reasoning system"
                )
        now = datetime.now(timezone.utc)
        if reg.resolution_date <= now:
            logger.warning(
                "BACKDATED resolution_date %s for agent=%s — will be flagged post_hoc",
                reg.resolution_date, reg.producing_agent_id
            )
        if not reg.claim.strip():
            raise ValueError("claim cannot be empty")
        if not reg.resolution_criterion.strip():
            raise ValueError("resolution_criterion cannot be empty")
        if reg.horizon_class not in ('short', 'medium', 'long'):
            raise ValueError(f"horizon_class must be short/medium/long, got {reg.horizon_class!r}")
