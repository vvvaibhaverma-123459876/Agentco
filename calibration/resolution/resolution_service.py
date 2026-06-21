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
import os
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
        resolver_id: str | None = None,
        resolver_type: str = "service",
        resolver_role: str = "resolver_service",
        claim_source_url: str | None = None,
        resolution_url: str | None = None,
        claim_source_content: str | None = None,
        resolution_source_content: str | None = None,
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
                claim_source_url=claim_source_url,
                resolution_source_url=resolution_source_url or resolution_url,
                resolution_source_owner=resolution_source_owner,
                resolver_type=resolver_type,
                claim_source_content=claim_source_content,
                resolution_source_content=resolution_source_content,
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
            claim_source_url=claim_source_url,
            resolution_source_url=resolution_source_url or resolution_url,
            resolution_source_owner=resolution_source_owner,
            resolver_id=resolver_id,
            resolver_type=resolver_type,
            claim_source_content=claim_source_content,
            resolution_source_content=resolution_source_content,
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
        resolver_type: str,
        claim_source_url: str | None,
        resolution_source_url: str | None,
        resolution_source_owner: str | None,
        evidence: dict,
        claim_source_content: str | None,
        resolution_source_content: str | None,
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
        production = os.environ.get("AGENTCO_ENV") == "production"
        if production and not resolver_id:
            raise ValueError("INDEPENDENCE REJECTED: missing_resolver_identity")
        if not resolver_id:
            resolver_id = "resolution_service_v1"

        from calibration.resolution.independence_engine import (
            build_source_fingerprint,
            content_hash,
            evaluate_resolution_independence,
            source_fingerprint_hash,
            verdict_to_dict,
        )

        actual_claim_source_url = claim_source_url or (
            f"agentco-ledger://prediction/{record.prediction_id}"
            if record.claim_source_url is None
            else record.claim_source_url
        )
        metadata = evidence if isinstance(evidence, dict) else {}
        claim_source = build_source_fingerprint(
            actual_claim_source_url,
            content_hash=content_hash(claim_source_content) or record.claim_evidence_hash or metadata.get("claim_content_hash"),
            fetched_at=metadata.get("claim_fetched_at") if isinstance(metadata.get("claim_fetched_at"), datetime) else None,
            source_type=metadata.get("claim_source_type"),
            publisher=metadata.get("claim_publisher"),
            publisher_owner=record.claim_source_owner or metadata.get("claim_publisher_owner"),
        )
        resolution_source = build_source_fingerprint(
            resolution_source_url or ground_truth_source,
            content_hash=content_hash(resolution_source_content) or metadata.get("resolution_content_hash"),
            fetched_at=evidence_fetched_at,
            source_type=metadata.get("resolution_source_type"),
            publisher=metadata.get("resolution_publisher"),
            publisher_owner=resolution_source_owner or metadata.get("resolution_publisher_owner"),
        )
        verdict = evaluate_resolution_independence(
            claim_source=claim_source,
            resolution_source=resolution_source,
            producing_agent_id=record.producing_agent_id,
            resolver_id=resolver_id,
            resolver_type=resolver_type,
            production=True,
        )
        if now < (outcome_available_at or record.outcome_available_at or record.resolution_date):
            verdict_reason = "resolution_before_outcome_available"
            record.independence_status = "rejected"
            record.independence_failure_reason = verdict_reason
            raise ValueError(f"INDEPENDENCE REJECTED: {verdict_reason}")
        if dispute_status not in {"none", "resolved"}:
            verdict_reason = f"disputed_claim:{dispute_status}"
            record.independence_status = "rejected"
            record.independence_failure_reason = verdict_reason
            raise ValueError(f"INDEPENDENCE REJECTED: {verdict_reason}")
        record.claim_source_url = claim_source.raw_url
        record.claim_source_canonical_url = claim_source.canonical_url
        record.claim_source_domain = claim_source.domain
        record.claim_source_fingerprint = source_fingerprint_hash(claim_source)
        record.independence_status = (
            "accepted" if verdict.severity == "pass" else ("warn" if verdict.independent else "rejected")
        )
        record.independence_failure_reason = None if verdict.independent else verdict.reason
        record.independence_verdict = verdict_to_dict(verdict)
        record.dispute_status = dispute_status
        if not verdict.independent:
            if verdict.reason == "internal_resolution_source":
                raise ValueError(f"DISQUALIFIED SOURCE: {verdict.reason}")
            raise ValueError(f"INDEPENDENCE REJECTED: {verdict.reason}")

    def _record_resolution_lineage(
        self,
        record: "PredictionRecord",
        *,
        ground_truth_source: str,
        claim_source_url: str | None,
        resolution_source_url: str | None,
        resolution_source_owner: str | None,
        resolver_id: str | None,
        resolver_type: str,
        claim_source_content: str | None,
        resolution_source_content: str | None,
        evidence: dict,
        evidence_fetched_at: datetime | None,
        outcome_available_at: datetime | None,
        dispute_status: str,
    ) -> None:
        from calibration.resolution.independence_engine import (
            build_source_fingerprint,
            content_hash,
            evidence_snapshot_hash,
            source_fingerprint_hash,
            to_jsonable,
            verdict_to_dict,
        )
        from dataclasses import asdict

        metadata = evidence if isinstance(evidence, dict) else {}
        claim_source = build_source_fingerprint(
            claim_source_url or record.claim_source_url or f"agentco-ledger://prediction/{record.prediction_id}",
            content_hash=content_hash(claim_source_content) or record.claim_evidence_hash or metadata.get("claim_content_hash"),
            source_type=metadata.get("claim_source_type"),
            publisher=metadata.get("claim_publisher"),
            publisher_owner=record.claim_source_owner or metadata.get("claim_publisher_owner"),
        )
        resolution_source = build_source_fingerprint(
            resolution_source_url or ground_truth_source,
            content_hash=content_hash(resolution_source_content) or metadata.get("resolution_content_hash"),
            fetched_at=evidence_fetched_at,
            source_type=metadata.get("resolution_source_type"),
            publisher=metadata.get("resolution_publisher"),
            publisher_owner=resolution_source_owner or metadata.get("resolution_publisher_owner"),
        )
        if not getattr(record, "independence_verdict", None):
            from calibration.resolution.independence_engine import evaluate_resolution_independence
            verdict = evaluate_resolution_independence(
                claim_source=claim_source,
                resolution_source=resolution_source,
                producing_agent_id=record.producing_agent_id,
                resolver_id=resolver_id,
                resolver_type=resolver_type,
                production=True,
            )
            record.independence_verdict = verdict_to_dict(verdict)
        record.resolution_source_url = resolution_source.raw_url
        record.resolution_source_canonical_url = resolution_source.canonical_url
        record.resolution_source_domain = resolution_source.domain
        record.resolution_source_owner = resolution_source.publisher_owner
        record.resolution_source_fingerprint = source_fingerprint_hash(resolution_source)
        record.evidence_snapshot_hash = evidence_snapshot_hash(evidence)
        record.evidence_fetched_at = evidence_fetched_at or datetime.now(timezone.utc)
        record.outcome_available_at = outcome_available_at or record.outcome_available_at or record.resolution_date
        if record.independence_status == "unresolved":
            record.independence_status = "accepted"
            record.independence_failure_reason = None
        record.dispute_status = dispute_status
        record.resolution_evidence_snapshot = {
            "prediction_id": record.prediction_id,
            "resolver_id": resolver_id or "resolution_service_v1",
            "resolver_type": resolver_type,
            "claim_source_fingerprint": to_jsonable(asdict(claim_source)),
            "resolution_source_fingerprint": to_jsonable(asdict(resolution_source)),
            "independence_verdict": record.independence_verdict,
            "evidence": evidence,
            "evidence_hash": record.evidence_snapshot_hash,
        }

    def _write_audit_event(self, event_type: str, **fields: object) -> None:
        self.audit_events.append(
            {
                "event_type": event_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **fields,
            }
        )
