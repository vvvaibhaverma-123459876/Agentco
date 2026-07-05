"""
Resolution Service — scores predictions at/after their resolution_date.

Rules:
- Resolving agents cannot resolve their own predictions (no grading own homework).
- Ground truth must come from external sources.
- Outcome is written ONCE. The DB trigger enforces this at the data layer.
- Resolution triggers Trust Controller update + Surprise Register check.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRecord
    from calibration.scoring.scoring_module import ScoringModule
    from calibration.surprise.surprise_register import SurpriseRegister
    from calibration.trust.trust_controller import TrustController

logger = logging.getLogger(__name__)

INTERNAL_SOURCES = frozenset({"self", "internal", "simulation", "agentco_system", "twin", "sandbox"})


class ResolutionService:
    """
    The ONLY entity authorised to resolve predictions in the ledger.
    Never called by predicting agents.
    """

    def __init__(
        self,
        ledger: "PredictionLedger",
        scoring: "ScoringModule",
        surprise_register: "SurpriseRegister",
        trust_controller: "TrustController",
    ):
        self.ledger = ledger
        self.scoring = scoring
        self.surprise_register = surprise_register
        self.trust_controller = trust_controller

    def resolve(
        self,
        prediction_id: str,
        outcome: bool,
        ground_truth_source: str,
        evidence: dict,
    ) -> "PredictionRecord":
        """
        Resolve a prediction. Only callable by this service, not by agents.

        Args:
            prediction_id: which prediction
            outcome: the actual true/false outcome
            ground_truth_source: MUST be external
            evidence: supporting evidence dict (logged to audit)

        Returns:
            Updated PredictionRecord
        """
        record = self.ledger.get(prediction_id)
        if record is None:
            raise ValueError(f"Prediction {prediction_id} not found")

        self._validate_resolution(record, ground_truth_source)

        brier = self.scoring.brier_score(record.probability, outcome)
        log_s = self.scoring.log_score(record.probability, outcome)
        is_surprise = self.surprise_register.check(record, outcome)

        # In production: UPDATE via DB with resolution_service role
        # DB triggers enforce: write-once, time-gate, role restriction
        now = datetime.now(timezone.utc)
        record.resolved = True
        record.resolved_outcome = outcome
        record.resolved_at = now
        record.resolved_by_service = "resolution_service_v1"
        record.brier_score = brier
        record.log_score = log_s
        record.was_surprise = is_surprise

        logger.info(
            "RESOLVED: id=%s agent=%s outcome=%s probability=%.3f brier=%.4f log=%.4f surprise=%s",
            prediction_id, record.producing_agent_id, outcome,
            record.probability, brier, log_s, is_surprise
        )

        # Update Trust Controller with the calibration signal
        self.trust_controller.ingest_resolution(record)

        if is_surprise:
            self.surprise_register.register_surprise(record, outcome)

        self.ledger.persist_resolution(record)

        return record

    def resolve_batch(self, due_by: datetime | None = None) -> list["PredictionRecord"]:
        """Resolve all predictions whose resolution_date has passed."""
        if due_by is None:
            due_by = datetime.now(timezone.utc)
        unresolved = self.ledger.list_unresolved(due_by=due_by)
        logger.info("Resolution batch: %d predictions due", len(unresolved))
        # In production: fetch actual outcomes from external ground-truth sources
        # Here we return the list for the caller to drive with real outcomes
        return unresolved

    def _validate_resolution(self, record: "PredictionRecord", ground_truth_source: str) -> None:
        now = datetime.now(timezone.utc)
        if record.resolved:
            raise ValueError(f"WRITE-ONCE VIOLATION: prediction {record.prediction_id} is already resolved")
        if now < record.resolution_date:
            raise ValueError(
                f"TIME GATE: cannot resolve before resolution_date "
                f"(now={now.isoformat()}, resolution_date={record.resolution_date.isoformat()})"
            )
        src_lower = ground_truth_source.lower()
        if "agentco_system" in src_lower:
            raise ValueError(
                f"DISQUALIFIED SOURCE: '{ground_truth_source}' is internal. "
                "Ground truth must originate outside the reasoning system."
            )
        source_tokens = set(filter(None, re.split(r"[^a-z0-9]+", src_lower)))
        for internal in INTERNAL_SOURCES:
            if internal in source_tokens:
                raise ValueError(
                    f"DISQUALIFIED SOURCE: '{ground_truth_source}' is internal. "
                    "Ground truth must originate outside the reasoning system."
                )
        # Predicting agents cannot resolve their own predictions: this is enforced
        # architecturally (agents have no handle to ResolutionService) and at the
        # data layer (only the resolution_service DB role may write resolution
        # columns — see 011_prediction_ledger.sql). resolve() itself takes no
        # resolver identity, so there is no in-method producer check to perform here.
