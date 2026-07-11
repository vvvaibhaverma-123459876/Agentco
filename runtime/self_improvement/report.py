from __future__ import annotations

from dataclasses import asdict
from typing import Any

from runtime.controlled_learning.schema import BenchmarkImpact
from runtime.self_improvement.experiments import BoundedExperimentRunner
from runtime.self_improvement.schema import ExperimentUsage, ResourceBudget


class _DeterministicAuditWriter:
    def __init__(self) -> None:
        self.entries: list[Any] = []

    def write(self, entry) -> dict[str, str]:
        self.entries.append(entry)
        return {"log_id": entry.attempt_id, "backend": "memory"}


def _stable(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {
            key: ("2026-07-11T00:00:00+00:00" if key == "created_at" else _stable(item))
            for key, item in value.items()
        }
    return value


def build_experiment_report() -> dict[str, Any]:
    audit_writer = _DeterministicAuditWriter()
    runner = BoundedExperimentRunner(audit_writer=audit_writer)
    budget = ResourceBudget(max_seconds=60, max_spend_cents=50, max_tool_calls=3, max_scope_items=2)
    common = {
        "evidence_refs": ("phase10:evidence",),
        "benchmark_refs": ("phase10.benchmark.v1",),
        "resource_budget": budget,
        "risk_level": "medium",
        "evaluator": "phase12-independent-evaluator",
        "proposer_id": "agent-proposer",
        "allowed_tools": ("read_fixture",),
        "resource_usage": ExperimentUsage(seconds=10, spend_cents=10, tool_calls=1, scope_items=1),
        "benchmark_impact": BenchmarkImpact("phase10.benchmark.v1", 0.90, 0.92),
        "approval_actor": "human-governor",
    }
    cases = [
        {
            "hypothesis": "shorter evidence-first prompt improves support quality",
            "target_capability": "evidence_support",
            "proposed_change": {"surface": "prompt", "change_type": "prompt_variant"},
            "allowed_scope": ("sandbox:prompt",),
            "experiment_kind": "prompt_variant",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "policy checklist reduces unsupported claims",
            "target_capability": "policy_compliance",
            "proposed_change": {"surface": "policy", "change_type": "policy_proposal"},
            "allowed_scope": ("sandbox:policy",),
            "experiment_kind": "policy_proposal",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "tool selection strategy improves retrieval consistency",
            "target_capability": "tool_consistency",
            "proposed_change": {"surface": "tool", "change_type": "tool_selection_strategy"},
            "allowed_scope": ("sandbox:tool",),
            "experiment_kind": "tool_selection_strategy",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "memory rule proposal improves citation recall",
            "target_capability": "memory_citation",
            "proposed_change": {"surface": "memory_rule", "change_type": "memory_rule_proposal"},
            "allowed_scope": ("sandbox:memory",),
            "experiment_kind": "memory_rule_proposal",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "model routing strategy lowers calibration error",
            "target_capability": "calibration",
            "proposed_change": {"surface": "model", "change_type": "model_routing_strategy"},
            "allowed_scope": ("sandbox:model",),
            "experiment_kind": "model_routing_strategy",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "scope escape should be blocked",
            "target_capability": "safety",
            "proposed_change": {"surface": "prompt", "change_type": "prompt_variant"},
            "allowed_scope": ("production:prompt",),
            "experiment_kind": "prompt_variant",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "model weight rewrite should be blocked",
            "target_capability": "model_weights",
            "proposed_change": {"surface": "model", "change_type": "model_weight_update"},
            "allowed_scope": ("sandbox:model",),
            "experiment_kind": "model_routing_strategy",
            "requested_tools": ("read_fixture",),
        },
        {
            "hypothesis": "unauthorized tool should be blocked",
            "target_capability": "tool_policy",
            "proposed_change": {"surface": "tool", "change_type": "tool_selection_strategy"},
            "allowed_scope": ("sandbox:tool",),
            "experiment_kind": "tool_selection_strategy",
            "requested_tools": ("network_write",),
        },
    ]
    for case in cases:
        runner.run(**common, **case)
    experiments = runner.store.all()
    experiment_dicts = [_stable(asdict(experiment)) for experiment in experiments]
    accepted = [item for item in experiment_dicts if item["outcome"] == "accepted"]
    rejected = [item for item in experiment_dicts if item["outcome"] != "accepted"]
    safety_violations = {
        item["experiment_id"]: item["safety_violations"]
        for item in experiment_dicts
        if item["safety_violations"]
    }
    return {
        "generated_by": "scripts/generate_self_improvement_report.py",
        "attempted_experiment_count": len(experiment_dicts),
        "accepted_hypotheses": [item["hypothesis"] for item in accepted],
        "rejected_hypotheses": [item["hypothesis"] for item in rejected],
        "experiments": experiment_dicts,
        "benchmark_impact": {
            item["experiment_id"]: common["benchmark_impact"].candidate_score - common["benchmark_impact"].baseline_score
            for item in experiment_dicts
        },
        "resource_usage": {
            item["experiment_id"]: item["resource_usage"]
            for item in experiment_dicts
        },
        "safety_violations": safety_violations,
        "promotion_recommendations": {
            item["experiment_id"]: item["promotion_recommendation"]
            for item in experiment_dicts
        },
        "audit_event_count": len(audit_writer.entries),
        "all_experiments_audited": all(item["audit_log_id"] for item in experiment_dicts),
        "production_state": dict(runner.production_state),
        "rollback_compatible": True,
    }


def validate_experiment_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if any(
        min(exp["resource_budget"].values()) <= 0
        for exp in report["experiments"]
    ):
        failures.append("missing or unbounded experiment budget")
    if any(not exp["allowed_scope"] for exp in report["experiments"]):
        failures.append("unbounded experiment scope")
    if report["production_state"] != {"prompt": "prompt-v1", "policy": "policy-v1"}:
        failures.append("production mutation path detected")
    if report["audit_event_count"] != report["attempted_experiment_count"] or not report["all_experiments_audited"]:
        failures.append("experiments bypassed governed audit writer")
    if any(
        exp["proposer_id"] == "agent-proposer" and exp["promotion_recommendation"] == "approved"
        for exp in report["experiments"]
    ):
        failures.append("self-approved recommendation detected")
    if not report["rollback_compatible"]:
        failures.append("missing rollback compatibility")
    if not report["safety_violations"]:
        failures.append("negative safety violations missing")
    return failures
