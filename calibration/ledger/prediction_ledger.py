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
    claim_source_url: Optional[str] = None
    claim_source_canonical_url: Optional[str] = None
    claim_source_domain: Optional[str] = None
    claim_source_owner: Optional[str] = None
    claim_source_fingerprint: Optional[str] = None
    claim_evidence_hash: Optional[str] = None
    outcome_available_at: Optional[datetime] = None


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
    resolved_by_service: Optional[str] = None
    brier_score: Optional[float] = None
    log_score: Optional[float] = None
    was_surprise: bool = False
    claim_source_url: Optional[str] = None
    claim_source_canonical_url: Optional[str] = None
    claim_source_domain: Optional[str] = None
    claim_source_owner: Optional[str] = None
    claim_source_fingerprint: Optional[str] = None
    claim_evidence_hash: Optional[str] = None
    resolver_id: Optional[str] = None
    resolver_type: Optional[str] = None
    resolver_role: Optional[str] = None
    resolution_source_url: Optional[str] = None
    resolution_source_canonical_url: Optional[str] = None
    resolution_source_domain: Optional[str] = None
    resolution_source_owner: Optional[str] = None
    resolution_source_fingerprint: Optional[str] = None
    evidence_snapshot_hash: Optional[str] = None
    evidence_fetched_at: Optional[datetime] = None
    outcome_available_at: Optional[datetime] = None
    independence_status: str = "unresolved"
    independence_failure_reason: Optional[str] = None
    dispute_status: str = "none"
    independence_verdict: Optional[dict[str, Any]] = None
    resolution_evidence_snapshot: Optional[dict[str, Any]] = None


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
        # db is an optional psycopg2-style connection (must expose .cursor()).
        # When present, pre-registrations are durably INSERTed into the
        # prediction_ledger table; the DB triggers in 011_prediction_ledger.sql
        # enforce immutability. _in_memory stays as a write-through cache so the
        # record object handed to the Resolution Service keeps stable identity
        # (the service mutates it in place); persist_resolution() mirrors the
        # resolution columns back to the DB. With db=None, behaviour is the
        # original pure in-memory dev fallback.
        self._db = db
        self._in_memory: dict[str, PredictionRecord] = {}
        if self._db is not None:
            self._load_from_db()

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
        try:
            from calibration.resolution.source_independence import build_source_lineage, evidence_hash
            claim_url = reg.claim_source_url
            if claim_url is None:
                claim_url = f"agentco-ledger://prediction/{prediction_id}"
            lineage = build_source_lineage(claim_url, reg.claim_source_owner or "")
            claim_hash = reg.claim_evidence_hash or evidence_hash(
                {
                    "claim": reg.claim,
                    "confidence_basis": reg.confidence_basis,
                    "resolution_criterion": reg.resolution_criterion,
                    "source": claim_url,
                }
            )
        except Exception:
            claim_url = reg.claim_source_url
            if claim_url is None:
                claim_url = f"agentco-ledger://prediction/{prediction_id}"
            lineage = None
            claim_hash = reg.claim_evidence_hash

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
            claim_source_url=claim_url,
            claim_source_canonical_url=reg.claim_source_canonical_url or (lineage.canonical_url if lineage else None),
            claim_source_domain=reg.claim_source_domain or (lineage.domain if lineage else None),
            claim_source_owner=reg.claim_source_owner or (lineage.owner if lineage else None),
            claim_source_fingerprint=reg.claim_source_fingerprint or (lineage.fingerprint if lineage else None),
            claim_evidence_hash=claim_hash,
            outcome_available_at=reg.outcome_available_at or reg.resolution_date,
        )

        self._in_memory[prediction_id] = record
        if self._db is not None:
            self._insert_record(record)
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

    def list_all(self) -> list[PredictionRecord]:
        return list(self._in_memory.values())

    def persist_resolution(self, record: PredictionRecord) -> None:
        """
        Mirror a record's resolution columns to the DB. The Resolution Service
        mutates the cached record object in place; calling this writes those
        resolution columns through to prediction_ledger. The connection must be
        authenticated as the resolution_service role — the DB trigger enforces
        role, write-once, and the time gate regardless of what app code does.
        No-op when running with the in-memory fallback (db=None).
        """
        if self._db is None:
            return
        old_autocommit = getattr(self._db, "autocommit", None)
        if old_autocommit is True:
            self._db.autocommit = False
        try:
            if record.resolution_evidence_snapshot:
                self.persist_resolution_evidence_snapshot(record)
            else:
                raise RuntimeError("resolution cannot persist without independence verdict/evidence snapshot")
            with self._db.cursor() as cur:
                cur.execute(
                    """
                    UPDATE prediction_ledger
                       SET resolved = %s,
                           resolved_outcome = %s,
                           resolved_at = %s,
                           resolved_by_service = %s,
                           brier_score = %s,
                           log_score = %s,
                           was_surprise = %s
                     WHERE prediction_id = %s
                    """,
                    (
                        record.resolved, record.resolved_outcome, record.resolved_at,
                        record.resolved_by_service, record.brier_score,
                        record.log_score, record.was_surprise, record.prediction_id,
                    ),
                )
            self._commit()
        except Exception:
            rollback = getattr(self._db, "rollback", None)
            if callable(rollback):
                rollback()
            raise
        finally:
            if old_autocommit is True:
                self._db.autocommit = True

    def persist_resolution_evidence_snapshot(self, record: PredictionRecord) -> None:
        """Append durable evidence metadata for a resolved prediction when supported."""
        if self._db is None or not record.resolution_evidence_snapshot:
            return
        import json
        snapshot = record.resolution_evidence_snapshot
        with self._db.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO resolution_evidence_snapshots
                        (id, prediction_id, resolver_id, resolver_type,
                         claim_source_fingerprint, resolution_source_fingerprint,
                         independence_verdict, evidence, evidence_hash)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        record.prediction_id,
                        snapshot["resolver_id"],
                        snapshot["resolver_type"],
                        json.dumps(snapshot["claim_source_fingerprint"], default=str),
                        json.dumps(snapshot["resolution_source_fingerprint"], default=str),
                        json.dumps(snapshot["independence_verdict"], default=str),
                        json.dumps(snapshot["evidence"], default=str),
                        snapshot["evidence_hash"],
                    ),
                )
            except Exception as exc:
                raise RuntimeError(
                    "resolution evidence snapshot could not be persisted; refusing partial resolution metadata"
                ) from exc

    # ------------------------------------------------------------------ DB I/O

    def _insert_record(self, record: PredictionRecord) -> None:
        hardness = 2.0 * record.probability * (1.0 - record.probability)
        with self._db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO prediction_ledger
                    (prediction_id, claim, probability, confidence_basis,
                     producing_agent_id, producing_prompt_version, resolution_criterion,
                     resolution_date, ground_truth_source, horizon_class, domain,
                     claim_type, correlation_id, created_at, post_hoc, hardness)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    record.prediction_id, record.claim, record.probability,
                    self._json(record.confidence_basis), record.producing_agent_id,
                    record.producing_prompt_version, record.resolution_criterion,
                    record.resolution_date, record.ground_truth_source,
                    record.horizon_class, record.domain, record.claim_type,
                    record.correlation_id, record.created_at, record.post_hoc,
                    hardness,
                ),
            )
        self._commit()

    def _load_from_db(self) -> None:
        """Hydrate the cache from the durable ledger on startup."""
        with self._db.cursor() as cur:
            cur.execute(
                """
                SELECT prediction_id, claim, probability, confidence_basis,
                       producing_agent_id, producing_prompt_version, resolution_criterion,
                       resolution_date, ground_truth_source, horizon_class, domain,
                       claim_type, correlation_id, created_at, post_hoc,
                       resolved, resolved_outcome, resolved_at, brier_score,
                       log_score, was_surprise
                  FROM prediction_ledger
                """
            )
            for row in cur.fetchall():
                rec = PredictionRecord(
                    prediction_id=str(row[0]), claim=row[1], probability=float(row[2]),
                    confidence_basis=row[3] or {}, producing_agent_id=row[4],
                    producing_prompt_version=row[5], resolution_criterion=row[6],
                    resolution_date=row[7], ground_truth_source=row[8],
                    horizon_class=row[9], domain=row[10], claim_type=row[11],
                    correlation_id=str(row[12]) if row[12] else None,
                    created_at=row[13], post_hoc=row[14], resolved=row[15],
                    resolved_outcome=row[16], resolved_at=row[17],
                    brier_score=float(row[18]) if row[18] is not None else None,
                    log_score=float(row[19]) if row[19] is not None else None,
                    was_surprise=row[20],
                )
                self._in_memory[rec.prediction_id] = rec

    @staticmethod
    def _json(value: Any) -> str:
        import json
        return json.dumps(value)

    def _commit(self) -> None:
        commit = getattr(self._db, "commit", None)
        if callable(commit):
            self._db.commit()

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
