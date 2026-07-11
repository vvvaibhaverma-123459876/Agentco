from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


EVALUATION_VERSION = "phase10.eval.v1"

FailureCategory = Literal[
    "none",
    "incorrect",
    "unsupported_claim",
    "tampered_evidence",
    "invalid_confidence",
    "policy_violation",
    "incomplete_task",
    "tool_mismatch",
    "self_certification",
    "evaluator_disagreement",
    "abstained_insufficient_evidence",
]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    content: str
    content_sha256: str
    source: str

    @classmethod
    def from_content(cls, evidence_id: str, content: str, *, source: str = "benchmark") -> "EvidenceReference":
        return cls(
            evidence_id=evidence_id,
            content=content,
            content_sha256=sha256_text(content),
            source=source,
        )

    def is_tampered(self) -> bool:
        return sha256_text(self.content) != self.content_sha256


@dataclass(frozen=True)
class EvaluationInput:
    agent_id: str
    task_id: str
    attempt_id: str
    output: str
    claim: str
    evidence: tuple[EvidenceReference, ...]
    predicted_confidence: float | None
    evaluator_id: str
    expected_answer: str | None = None
    expected_tool_result: str | None = None
    observed_tool_result: str | None = None
    task_completed: bool = True
    deterministic_verifier: bool = False
    abstained: bool = False
    policy_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluatorResult:
    evaluator_name: str
    passed: bool
    score: float
    failure_category: FailureCategory = "none"
    rationale: str = ""


@dataclass(frozen=True)
class EvaluationRecord:
    evaluation_id: str
    agent_id: str
    task_id: str
    attempt_id: str
    output_or_claim: str
    supporting_evidence_refs: tuple[str, ...]
    predicted_confidence: float
    evaluator_result: str
    correctness_score: float
    evidence_quality_score: float
    calibration_error: float
    failure_category: FailureCategory
    evaluation_timestamp: str
    evaluation_version: str
    evaluator_id: str
    brier_score: float
    abstained: bool
    evaluator_results: tuple[EvaluatorResult, ...]
    audit_log_id: str | None = None
    audit_backend: str | None = None

    @property
    def passed(self) -> bool:
        return self.evaluator_result == "passed"

    def without_audit_ack(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("audit_log_id", None)
        data.pop("audit_backend", None)
        return data

    def fingerprint(self) -> str:
        data = self.without_audit_ack()
        data.pop("evaluation_timestamp", None)
        return sha256_text(stable_json(data))


@dataclass(frozen=True)
class EvaluationAuditEntry:
    agent_id: str
    prompt_version: str
    action_type: str
    description: str
    stated_confidence: float
    trusted_confidence: float
    risk_level: str
    domain: str
    prediction_id: str | None
    override_id: str | None
    outcome: str
    attempt_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
