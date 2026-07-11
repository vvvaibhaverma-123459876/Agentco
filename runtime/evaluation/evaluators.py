from __future__ import annotations

import os
import json
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any, Iterable

from runtime.base_agent.audit_writer import AuditUnavailableError, AuditWriter, InMemoryAuditWriter
from runtime.evaluation.schema import (
    EVALUATION_VERSION,
    EvaluationAuditEntry,
    EvaluationInput,
    EvaluationRecord,
    EvaluatorResult,
    FailureCategory,
    stable_json,
)


class EvaluationError(RuntimeError):
    """Raised when an output cannot be evaluated under the Phase 10 contract."""


class ImmutableEvaluationStore:
    """Append-only in-memory record index used by tests and report generation."""

    def __init__(self) -> None:
        self._records: dict[str, EvaluationRecord] = {}
        self._fingerprints: dict[str, str] = {}

    def put(self, record: EvaluationRecord) -> EvaluationRecord:
        existing = self._records.get(record.evaluation_id)
        fingerprint = record.fingerprint()
        if existing is not None:
            if self._fingerprints[record.evaluation_id] != fingerprint:
                raise EvaluationError(f"evaluation record is immutable: {record.evaluation_id}")
            if existing.audit_log_id is None and record.audit_log_id is not None:
                self._records[record.evaluation_id] = record
                return record
            return existing
        self._records[record.evaluation_id] = record
        self._fingerprints[record.evaluation_id] = fingerprint
        return record

    def records(self) -> tuple[EvaluationRecord, ...]:
        return tuple(self._records.values())


class PostgresEvaluationStore(ImmutableEvaluationStore):
    """Postgres-backed immutable evaluation repository for production runtime use."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise EvaluationError("PostgresEvaluationStore requires a database DSN")
        super().__init__()
        self._dsn = dsn

    def put(self, record: EvaluationRecord) -> EvaluationRecord:
        payload = asdict(record)
        fingerprint = record.fingerprint()
        psycopg2 = _psycopg2()
        conn = psycopg2.connect(self._dsn)
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO runtime_evaluation_records
                      (evaluation_id, agent_id, task_id, attempt_id, evaluator_id,
                       evaluation_version, evaluator_result, failure_category,
                       payload, fingerprint, audit_log_id, audit_backend)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                    ON CONFLICT (evaluation_id) DO UPDATE
                       SET audit_log_id = COALESCE(runtime_evaluation_records.audit_log_id, EXCLUDED.audit_log_id),
                           audit_backend = COALESCE(runtime_evaluation_records.audit_backend, EXCLUDED.audit_backend)
                     WHERE runtime_evaluation_records.fingerprint = EXCLUDED.fingerprint
                    RETURNING payload, audit_log_id, audit_backend
                    """,
                    [
                        record.evaluation_id,
                        record.agent_id,
                        record.task_id,
                        record.attempt_id,
                        record.evaluator_id,
                        record.evaluation_version,
                        record.evaluator_result,
                        record.failure_category,
                        stable_json(payload),
                        fingerprint,
                        record.audit_log_id,
                        record.audit_backend,
                    ],
                )
                row = cur.fetchone()
                if row is None:
                    raise EvaluationError(f"evaluation record is immutable: {record.evaluation_id}")
            conn.commit()
            return _evaluation_record_from_row(row[0], row[1], row[2])
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get(self, evaluation_id: str) -> EvaluationRecord:
        psycopg2 = _psycopg2()
        conn = psycopg2.connect(self._dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload, audit_log_id, audit_backend FROM runtime_evaluation_records WHERE evaluation_id = %s",
                    [evaluation_id],
                )
                row = cur.fetchone()
                if row is None:
                    raise EvaluationError(f"unknown evaluation record: {evaluation_id}")
                return _evaluation_record_from_row(row[0], row[1], row[2])
        finally:
            conn.close()

    def records(self) -> tuple[EvaluationRecord, ...]:
        psycopg2 = _psycopg2()
        conn = psycopg2.connect(self._dsn)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT payload, audit_log_id, audit_backend FROM runtime_evaluation_records ORDER BY created_at, evaluation_id")
                return tuple(_evaluation_record_from_row(row[0], row[1], row[2]) for row in cur.fetchall())
        finally:
            conn.close()


def configured_evaluation_store() -> PostgresEvaluationStore:
    dsn = os.environ.get("AGENTCO_EVALUATION_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("AGENTCO_TEST_DATABASE_URL")
    if not dsn:
        raise EvaluationError("production evaluation requires AGENTCO_EVALUATION_DATABASE_URL or DATABASE_URL")
    return PostgresEvaluationStore(dsn)


def _evaluation_record_from_payload(payload: dict[str, Any]) -> EvaluationRecord:
    if isinstance(payload, str):
        payload = json.loads(payload)
    results = tuple(EvaluatorResult(**item) for item in payload.get("evaluator_results", ()))
    return EvaluationRecord(
        evaluation_id=payload["evaluation_id"],
        agent_id=payload["agent_id"],
        task_id=payload["task_id"],
        attempt_id=payload["attempt_id"],
        output_or_claim=payload["output_or_claim"],
        supporting_evidence_refs=tuple(payload.get("supporting_evidence_refs", ())),
        predicted_confidence=float(payload["predicted_confidence"]),
        evaluator_result=payload["evaluator_result"],
        correctness_score=float(payload["correctness_score"]),
        evidence_quality_score=float(payload["evidence_quality_score"]),
        calibration_error=float(payload["calibration_error"]),
        failure_category=payload["failure_category"],
        evaluation_timestamp=payload["evaluation_timestamp"],
        evaluation_version=payload["evaluation_version"],
        evaluator_id=payload["evaluator_id"],
        brier_score=float(payload["brier_score"]),
        abstained=bool(payload["abstained"]),
        evaluator_results=results,
        audit_log_id=payload.get("audit_log_id"),
        audit_backend=payload.get("audit_backend"),
    )


def _evaluation_record_from_row(payload: dict[str, Any], audit_log_id: Any, audit_backend: str | None) -> EvaluationRecord:
    record = _evaluation_record_from_payload(payload)
    return replace(
        record,
        audit_log_id=str(audit_log_id) if audit_log_id is not None else record.audit_log_id,
        audit_backend=audit_backend or record.audit_backend,
    )


def _psycopg2() -> Any:
    try:
        import psycopg2
    except Exception as exc:
        raise EvaluationError("psycopg2 is required for durable evaluation storage") from exc
    return psycopg2


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def validate_confidence(confidence: float | None) -> float:
    if confidence is None:
        raise EvaluationError("evaluated claims must record predicted confidence")
    confidence = float(confidence)
    if confidence < 0 or confidence > 1:
        raise EvaluationError("predicted confidence must be in [0, 1]")
    return confidence


def factual_correctness(inp: EvaluationInput) -> EvaluatorResult:
    if inp.abstained:
        return EvaluatorResult("factual_correctness", True, 1.0, rationale="abstention is allowed")
    if inp.expected_answer is None:
        return EvaluatorResult("factual_correctness", True, 1.0, rationale="no deterministic answer required")
    passed = normalize_text(inp.output) == normalize_text(inp.expected_answer)
    return EvaluatorResult(
        "factual_correctness",
        passed,
        1.0 if passed else 0.0,
        "none" if passed else "incorrect",
        "output matches expected answer" if passed else "output does not match expected answer",
    )


def evidence_support(inp: EvaluationInput) -> EvaluatorResult:
    if any(ref.is_tampered() for ref in inp.evidence):
        return EvaluatorResult("evidence_support", False, 0.0, "tampered_evidence", "evidence hash mismatch")
    if inp.abstained:
        return EvaluatorResult(
            "evidence_support",
            True,
            1.0,
            "abstained_insufficient_evidence",
            "abstained rather than asserting without evidence",
        )
    if not inp.evidence:
        return EvaluatorResult("evidence_support", False, 0.0, "unsupported_claim", "no evidence references")
    claim = normalize_text(inp.claim)
    supported = any(claim in normalize_text(ref.content) for ref in inp.evidence)
    return EvaluatorResult(
        "evidence_support",
        supported,
        1.0 if supported else 0.0,
        "none" if supported else "unsupported_claim",
        "claim appears in cited evidence" if supported else "claim is absent from cited evidence",
    )


def unsupported_claim(inp: EvaluationInput) -> EvaluatorResult:
    confidence = validate_confidence(inp.predicted_confidence)
    if inp.abstained:
        return EvaluatorResult("unsupported_claim", True, 1.0, "abstained_insufficient_evidence")
    support = evidence_support(inp)
    if not support.passed and confidence >= 0.8:
        return EvaluatorResult(
            "unsupported_claim",
            False,
            0.0,
            "unsupported_claim",
            "unsupported high-confidence claim",
        )
    return EvaluatorResult("unsupported_claim", True, 1.0)


def tool_result_consistency(inp: EvaluationInput) -> EvaluatorResult:
    if inp.expected_tool_result is None:
        return EvaluatorResult("tool_result_consistency", True, 1.0)
    passed = normalize_text(inp.expected_tool_result) == normalize_text(inp.observed_tool_result or "")
    return EvaluatorResult(
        "tool_result_consistency",
        passed,
        1.0 if passed else 0.0,
        "none" if passed else "tool_mismatch",
    )


def policy_compliance(inp: EvaluationInput) -> EvaluatorResult:
    prohibited = tuple(inp.policy_context.get("prohibited_terms", ()))
    output = normalize_text(inp.output)
    violated = [term for term in prohibited if normalize_text(str(term)) in output]
    return EvaluatorResult(
        "policy_compliance",
        not violated,
        0.0 if violated else 1.0,
        "policy_violation" if violated else "none",
        f"prohibited terms present: {violated}" if violated else "",
    )


def task_completion(inp: EvaluationInput) -> EvaluatorResult:
    return EvaluatorResult(
        "task_completion",
        inp.task_completed or inp.abstained,
        1.0 if inp.task_completed or inp.abstained else 0.0,
        "none" if inp.task_completed or inp.abstained else "incomplete_task",
    )


def confidence_calibration(inp: EvaluationInput, correctness_score: float) -> EvaluatorResult:
    confidence = validate_confidence(inp.predicted_confidence)
    error = abs(confidence - correctness_score)
    return EvaluatorResult(
        "confidence_calibration",
        error <= 0.5 or inp.abstained,
        round(1.0 - error, 6),
        "none" if error <= 0.5 or inp.abstained else "incorrect",
        f"absolute calibration error={error:.3f}",
    )


def evaluate_all(inp: EvaluationInput) -> tuple[EvaluatorResult, ...]:
    if inp.evaluator_id == inp.agent_id and not inp.deterministic_verifier:
        raise EvaluationError("agents cannot self-certify without a deterministic verifier")
    validate_confidence(inp.predicted_confidence)
    results = [
        factual_correctness(inp),
        evidence_support(inp),
        unsupported_claim(inp),
        tool_result_consistency(inp),
        policy_compliance(inp),
        task_completion(inp),
    ]
    correctness = _score_for(results, "factual_correctness")
    results.append(confidence_calibration(inp, correctness))
    return tuple(results)


def _score_for(results: Iterable[EvaluatorResult], evaluator_name: str) -> float:
    for result in results:
        if result.evaluator_name == evaluator_name:
            return result.score
    raise EvaluationError(f"missing evaluator result: {evaluator_name}")


def _failure_category(results: tuple[EvaluatorResult, ...]) -> FailureCategory:
    failing = [result.failure_category for result in results if not result.passed and result.failure_category != "none"]
    if not failing:
        return "none"
    if "tampered_evidence" in failing:
        return "tampered_evidence"
    if "unsupported_claim" in failing:
        return "unsupported_claim"
    if len(set(result.passed for result in results)) > 1:
        return "evaluator_disagreement"
    return failing[0]


class EvaluationService:
    def __init__(
        self,
        audit_writer: AuditWriter | None = None,
        store: ImmutableEvaluationStore | None = None,
        timestamp_factory=None,
    ):
        production = os.environ.get("AGENTCO_ENV") in {"production", "staging"} or os.environ.get("NODE_ENV") == "production"
        if production and store is None:
            store = configured_evaluation_store()
        if production and audit_writer is None:
            raise AuditUnavailableError("production evaluation requires an explicit durable audit writer")
        if production and isinstance(audit_writer, InMemoryAuditWriter):
            raise AuditUnavailableError("production evaluation cannot use InMemoryAuditWriter")
        self.audit_writer = audit_writer or InMemoryAuditWriter(allow_test_mode=True)
        self.store = store or ImmutableEvaluationStore()
        self._timestamp_factory = timestamp_factory or (lambda: datetime.now(timezone.utc).isoformat())

    def evaluate(self, inp: EvaluationInput) -> EvaluationRecord:
        results = evaluate_all(inp)
        confidence = validate_confidence(inp.predicted_confidence)
        correctness_score = _score_for(results, "factual_correctness")
        evidence_quality_score = _score_for(results, "evidence_support")
        calibration_error = abs(confidence - correctness_score)
        brier_score = (confidence - correctness_score) ** 2
        passed = all(result.passed for result in results)
        failure_category = _failure_category(results)
        evaluation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, stable_json({
            "version": EVALUATION_VERSION,
            "agent_id": inp.agent_id,
            "task_id": inp.task_id,
            "attempt_id": inp.attempt_id,
            "claim": inp.claim,
            "evaluator_id": inp.evaluator_id,
        })))
        record = EvaluationRecord(
            evaluation_id=evaluation_id,
            agent_id=inp.agent_id,
            task_id=inp.task_id,
            attempt_id=inp.attempt_id,
            output_or_claim=inp.claim,
            supporting_evidence_refs=tuple(ref.evidence_id for ref in inp.evidence),
            predicted_confidence=confidence,
            evaluator_result="passed" if passed else "failed",
            correctness_score=correctness_score,
            evidence_quality_score=evidence_quality_score,
            calibration_error=round(calibration_error, 6),
            failure_category=failure_category,
            evaluation_timestamp=self._timestamp_factory(),
            evaluation_version=EVALUATION_VERSION,
            evaluator_id=inp.evaluator_id,
            brier_score=round(brier_score, 6),
            abstained=inp.abstained,
            evaluator_results=results,
        )
        existing = self.store.put(record)
        if existing.audit_log_id:
            return existing
        ack = self._audit(record)
        audited = replace(record, audit_log_id=ack.get("log_id"), audit_backend=ack.get("backend"))
        return self.store.put(audited)

    def _audit(self, record: EvaluationRecord) -> dict[str, str]:
        entry = EvaluationAuditEntry(
            agent_id=record.agent_id,
            prompt_version=record.evaluation_version,
            action_type="decision",
            description=stable_json({
                "evaluation_id": record.evaluation_id,
                "task_id": record.task_id,
                "attempt_id": record.attempt_id,
                "claim": record.output_or_claim,
                "supporting_evidence_refs": record.supporting_evidence_refs,
                "evaluator_result": record.evaluator_result,
                "failure_category": record.failure_category,
                "evaluator_id": record.evaluator_id,
            }),
            stated_confidence=record.predicted_confidence,
            trusted_confidence=record.predicted_confidence,
            risk_level="low" if record.passed else "medium",
            domain="evaluation",
            prediction_id=None,
            override_id=None,
            outcome=record.evaluator_result,
            attempt_id=record.evaluation_id,
            timestamp=record.evaluation_timestamp,
            trace_id=record.evaluation_id,
        )
        ack = self.audit_writer.write(entry)
        if not ack or not ack.get("log_id"):
            raise AuditUnavailableError("evaluation audit writer returned no acknowledgement")
        return ack
