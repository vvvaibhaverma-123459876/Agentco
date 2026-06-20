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
import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRecord
    from calibration.scoring.scoring_module import ScoringModule
    from calibration.surprise.surprise_register import SurpriseRegister
    from calibration.trust.trust_controller import TrustController

logger = logging.getLogger(__name__)

INTERNAL_SOURCES = frozenset({"self", "internal", "simulation", "agent", "agentco_system", "twin"})


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
        self.audit_events: list[dict] = []

    def resolve(
        self,
        prediction_id: str,
        outcome: bool,
        ground_truth_source: str,
        evidence: dict,
        *,
        resolver_id: str = "resolution_service_v1",
        resolver_type: str = "service",
        resolver_role: str = "resolver_service",
        resolution_source_url: str | None = None,
        resolution_source_owner: str | None = None,
        evidence_fetched_at: datetime | None = None,
        outcome_available_at: datetime | None = None,
        dispute_status: str = "none",
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

        try:
            self._validate_resolution(
                record,
                ground_truth_source,
                resolver_id=resolver_id,
                resolution_source_url=resolution_source_url,
                resolution_source_owner=resolution_source_owner,
                evidence=evidence,
                evidence_fetched_at=evidence_fetched_at,
                outcome_available_at=outcome_available_at,
                dispute_status=dispute_status,
            )
        except Exception as exc:
            self._write_audit_event(
                "resolution_rejected",
                prediction_id=prediction_id,
                resolver_id=resolver_id,
                reason=str(exc),
            )
            raise

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
        record.resolver_id = resolver_id
        record.resolver_type = resolver_type
        record.resolver_role = resolver_role
        record.brier_score = brier
        record.log_score = log_s
        record.was_surprise = is_surprise
        self._record_resolution_lineage(
            record,
            ground_truth_source=ground_truth_source,
            resolution_source_url=resolution_source_url,
            resolution_source_owner=resolution_source_owner,
            evidence=evidence,
            evidence_fetched_at=evidence_fetched_at,
            outcome_available_at=outcome_available_at,
            dispute_status=dispute_status,
        )

        logger.info(
            "RESOLVED: id=%s agent=%s outcome=%s probability=%.3f brier=%.4f log=%.4f surprise=%s",
            prediction_id, record.producing_agent_id, outcome,
            record.probability, brier, log_s, is_surprise
        )

        # Update Trust Controller with the calibration signal
        self.trust_controller.ingest_resolution(record)

        if is_surprise:
            self.surprise_register.register_surprise(record, outcome)

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

    def _validate_resolution(
        self,
        record: "PredictionRecord",
        ground_truth_source: str,
        *,
        resolver_id: str,
        resolution_source_url: str | None,
        resolution_source_owner: str | None,
        evidence: dict,
        evidence_fetched_at: datetime | None,
        outcome_available_at: datetime | None,
        dispute_status: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        if record.resolved:
            raise ValueError(f"WRITE-ONCE VIOLATION: prediction {record.prediction_id} is already resolved")
        if now < record.resolution_date:
            raise ValueError(
                f"TIME GATE: cannot resolve before resolution_date "
                f"(now={now.isoformat()}, resolution_date={record.resolution_date.isoformat()})"
            )
        src_lower = ground_truth_source.lower()
        for internal in INTERNAL_SOURCES:
            if internal in src_lower:
                raise ValueError(
                    f"DISQUALIFIED SOURCE: '{ground_truth_source}' is internal. "
                    "Ground truth must originate outside the reasoning system."
                )
        from calibration.resolution.source_independence import build_source_lineage, evaluate_independence

        claim_source_url = (
            f"agentco-ledger://prediction/{record.prediction_id}"
            if record.claim_source_url is None
            else record.claim_source_url
        )
        claim_source = build_source_lineage(claim_source_url, record.claim_source_owner or "")
        resolution_source = build_source_lineage(
            resolution_source_url or ground_truth_source,
            resolution_source_owner or "",
        )
        result = evaluate_independence(
            claim_source=claim_source,
            resolution_source=resolution_source,
            producer_agent_id=record.producing_agent_id,
            resolver_id=resolver_id,
            outcome_available_at=outcome_available_at or record.outcome_available_at or record.resolution_date,
            resolved_at=now,
            dispute_status=dispute_status,
            additional_independent_evidence=bool(
                isinstance(evidence, dict) and evidence.get("additional_independent_evidence")
            ),
        )
        record.independence_status = result.status
        record.independence_failure_reason = result.failure_reason or None
        record.dispute_status = dispute_status
        if result.status != "accepted":
            raise ValueError(f"INDEPENDENCE REJECTED: {result.failure_reason}")

    def _record_resolution_lineage(
        self,
        record: "PredictionRecord",
        *,
        ground_truth_source: str,
        resolution_source_url: str | None,
        resolution_source_owner: str | None,
        evidence: dict,
        evidence_fetched_at: datetime | None,
        outcome_available_at: datetime | None,
        dispute_status: str,
    ) -> None:
        from calibration.resolution.source_independence import build_source_lineage, evidence_hash

        resolution_source = build_source_lineage(
            resolution_source_url or ground_truth_source,
            resolution_source_owner or "",
        )
        record.resolution_source_url = resolution_source.raw_url
        record.resolution_source_canonical_url = resolution_source.canonical_url
        record.resolution_source_domain = resolution_source.domain
        record.resolution_source_owner = resolution_source.owner
        record.resolution_source_fingerprint = resolution_source.fingerprint
        record.evidence_snapshot_hash = evidence_hash(evidence)
        record.evidence_fetched_at = evidence_fetched_at or datetime.now(timezone.utc)
        record.outcome_available_at = outcome_available_at or record.outcome_available_at or record.resolution_date
        record.independence_status = "accepted"
        record.independence_failure_reason = None
        record.dispute_status = dispute_status

    def _write_audit_event(self, event_type: str, **fields: object) -> None:
        self.audit_events.append(
            {
                "event_type": event_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **fields,
            }
        )
