from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


LEARNING_ARTIFACT_VERSION = "phase11.learning-artifact.v1"
LEARNING_PIPELINE_VERSION = "phase11.controlled-learning.v1"

LearningState = Literal[
    "proposed",
    "evaluated",
    "approved",
    "canary",
    "promoted",
    "rejected",
    "rolled_back",
]

RollbackTrigger = Literal[
    "benchmark_regression",
    "calibration_degradation",
    "unsupported_claim_increase",
    "policy_or_authorization_failure",
    "audit_chain_failure",
]

ProtectedSurface = Literal["prompt", "policy", "tool", "model", "memory_rule"]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BenchmarkImpact:
    benchmark_version: str
    baseline_score: float
    candidate_score: float
    calibration_delta: float = 0.0
    unsupported_claim_delta: float = 0.0

    @property
    def regression(self) -> bool:
        return self.candidate_score < self.baseline_score


@dataclass(frozen=True)
class PromotionEvent:
    event_id: str
    artifact_id: str
    from_state: LearningState
    to_state: LearningState
    actor_id: str
    reason: str
    audit_log_id: str
    audit_backend: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass(frozen=True)
class LearningArtifact:
    artifact_id: str
    source_observations: tuple[str, ...]
    evaluation_record_ids: tuple[str, ...]
    proposed_change: dict[str, Any]
    evidence_refs: tuple[str, ...]
    benchmark_impact: BenchmarkImpact
    proposer_id: str
    approval_status: str
    artifact_version: str
    state: LearningState = "proposed"
    promotion_history: tuple[PromotionEvent, ...] = ()
    rollback_history: tuple[PromotionEvent, ...] = ()
    previous_active_artifact_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def immutable_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("state", None)
        data.pop("promotion_history", None)
        data.pop("rollback_history", None)
        data.pop("approval_status", None)
        data.pop("previous_active_artifact_id", None)
        return data

    def fingerprint(self) -> str:
        return sha256_json(self.immutable_payload())


def artifact_id_for(proposer_id: str, proposed_change: dict[str, Any], evidence_refs: tuple[str, ...]) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_json({
        "version": LEARNING_ARTIFACT_VERSION,
        "proposer_id": proposer_id,
        "proposed_change": proposed_change,
        "evidence_refs": evidence_refs,
    })))
