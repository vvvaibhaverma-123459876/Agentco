from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


IMPROVEMENT_EXPERIMENT_VERSION = "phase12.improvement-experiment.v1"

ExperimentKind = Literal[
    "prompt_variant",
    "policy_proposal",
    "tool_selection_strategy",
    "memory_rule_proposal",
    "model_routing_strategy",
]

ExperimentOutcome = Literal["accepted", "rejected", "blocked", "failed"]
RiskLevel = Literal["low", "medium", "high", "critical"]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResourceBudget:
    max_seconds: int
    max_spend_cents: int
    max_tool_calls: int
    max_scope_items: int

    def validate(self) -> None:
        if min(self.max_seconds, self.max_spend_cents, self.max_tool_calls, self.max_scope_items) <= 0:
            raise ValueError("experiment budgets must be positive")


@dataclass(frozen=True)
class ExperimentUsage:
    seconds: int = 0
    spend_cents: int = 0
    tool_calls: int = 0
    scope_items: int = 0


@dataclass(frozen=True)
class ImprovementExperiment:
    experiment_id: str
    hypothesis: str
    target_capability: str
    proposed_change: dict[str, Any]
    evidence_refs: tuple[str, ...]
    benchmark_refs: tuple[str, ...]
    allowed_scope: tuple[str, ...]
    resource_budget: ResourceBudget
    risk_level: RiskLevel
    evaluator: str
    proposer_id: str
    experiment_kind: ExperimentKind
    outcome: ExperimentOutcome = "blocked"
    promotion_recommendation: str = "none"
    resource_usage: ExperimentUsage = field(default_factory=ExperimentUsage)
    safety_violations: tuple[str, ...] = ()
    audit_log_id: str | None = None
    audit_backend: str | None = None
    experiment_version: str = IMPROVEMENT_EXPERIMENT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def immutable_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("outcome", None)
        data.pop("promotion_recommendation", None)
        data.pop("resource_usage", None)
        data.pop("safety_violations", None)
        data.pop("audit_log_id", None)
        data.pop("audit_backend", None)
        data.pop("created_at", None)
        return data

    def fingerprint(self) -> str:
        return sha256_json(self.immutable_payload())


def experiment_id_for(
    *,
    hypothesis: str,
    target_capability: str,
    proposed_change: dict[str, Any],
    allowed_scope: tuple[str, ...],
    proposer_id: str,
) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_json({
        "version": IMPROVEMENT_EXPERIMENT_VERSION,
        "hypothesis": hypothesis,
        "target_capability": target_capability,
        "proposed_change": proposed_change,
        "allowed_scope": allowed_scope,
        "proposer_id": proposer_id,
    })))
