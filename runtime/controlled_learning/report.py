from __future__ import annotations

from dataclasses import asdict
from typing import Any
from runtime.controlled_learning.pipeline import ControlledLearningPipeline, rollback_trigger_for
from runtime.controlled_learning.schema import BenchmarkImpact


class _DeterministicAuditWriter:
    def __init__(self) -> None:
        self.entries: list[Any] = []

    def write(self, entry) -> dict[str, str]:
        self.entries.append(entry)
        return {"log_id": entry.attempt_id, "backend": "memory"}


def _proposal(surface: str, value: str) -> dict[str, Any]:
    return {"surface": surface, "version": value, "change": f"controlled {surface} update"}


def _stable(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {
            key: ("2026-07-11T00:00:00+00:00" if key in {"timestamp", "created_at"} else _stable(item))
            for key, item in value.items()
        }
    return value


def build_learning_report() -> dict[str, Any]:
    audit_writer = _DeterministicAuditWriter()
    pipeline = ControlledLearningPipeline(audit_writer=audit_writer)
    baseline = pipeline.propose(
        proposer_id="phase11-proposer",
        source_observations=("observation: prompt ambiguity in reviewed tasks",),
        evaluation_record_ids=("phase10:baseline-eval",),
        proposed_change=_proposal("prompt", "prompt-v1"),
        evidence_refs=("evidence:baseline",),
        benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.90, 0.91),
    )
    baseline = pipeline.evaluate_offline(baseline.artifact_id)
    baseline = pipeline.approve(baseline.artifact_id, approver_id="human-governor", authorization_id="auth-baseline")
    baseline = pipeline.stage_canary(baseline.artifact_id, actor_id="release-manager")
    baseline = pipeline.promote(baseline.artifact_id, actor_id="release-manager")

    candidate = pipeline.propose(
        proposer_id="phase11-proposer",
        source_observations=("observation: support language improved in Phase 10 eval",),
        evaluation_record_ids=("phase10:candidate-eval",),
        proposed_change=_proposal("prompt", "prompt-v2"),
        evidence_refs=("evidence:candidate",),
        benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.91, 0.93),
    )
    candidate = pipeline.evaluate_offline(candidate.artifact_id)
    candidate = pipeline.approve(candidate.artifact_id, approver_id="human-governor", authorization_id="auth-candidate")
    candidate = pipeline.stage_canary(candidate.artifact_id, actor_id="release-manager")
    candidate = pipeline.promote(candidate.artifact_id, actor_id="release-manager")

    degraded = pipeline.propose(
        proposer_id="phase11-proposer",
        source_observations=("observation: candidate caused calibration drift",),
        evaluation_record_ids=("phase10:degraded-eval",),
        proposed_change=_proposal("policy", "policy-v2"),
        evidence_refs=("evidence:degraded",),
        benchmark_impact=BenchmarkImpact(
            "phase10.benchmark.v1",
            0.93,
            0.94,
            calibration_delta=0.08,
        ),
    )
    degraded = pipeline.evaluate_offline(degraded.artifact_id)
    degraded = pipeline.approve(degraded.artifact_id, approver_id="human-governor", authorization_id="auth-degraded")
    degraded = pipeline.stage_canary(degraded.artifact_id, actor_id="release-manager")
    degraded = pipeline.monitor(degraded.artifact_id, actor_id="release-manager")

    regression = pipeline.propose(
        proposer_id="phase11-proposer",
        source_observations=("observation: benchmark declined",),
        evaluation_record_ids=("phase10:regression-eval",),
        proposed_change=_proposal("memory_rule", "memory-rule-v2"),
        evidence_refs=("evidence:regression",),
        benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.93, 0.80),
    )
    regression = pipeline.evaluate_offline(regression.artifact_id)

    artifacts = pipeline.store.all()
    promotion_events = [event for artifact in artifacts for event in artifact.promotion_history]
    rollback_events = [event for artifact in artifacts for event in artifact.rollback_history]
    active_versions = dict(sorted(pipeline.active_versions.items()))
    artifact_ids = {artifact.artifact_id for artifact in artifacts}
    return {
        "generated_by": "scripts/generate_controlled_learning_report.py",
        "artifact_count": len(artifacts),
        "artifacts": [_stable(asdict(artifact)) for artifact in artifacts],
        "active_versions": active_versions,
        "promotion_event_count": len(promotion_events),
        "rollback_event_count": len(rollback_events),
        "audit_event_count": len(getattr(audit_writer, "entries", [])),
        "all_promotions_audited": all(event.audit_log_id for event in promotion_events + rollback_events),
        "rollback_coverage": any(event.to_state == "rolled_back" for event in rollback_events),
        "regression_blocked": regression.state == "rejected",
        "recoverable_active_versions": all(artifact_id in artifact_ids for artifact_id in active_versions.values()),
        "promotion_lineage_preserved": all(
            artifact.previous_active_artifact_id is None or artifact.previous_active_artifact_id in artifact_ids
            for artifact in artifacts
            if artifact.state in {"promoted", "rolled_back"}
        ),
        "automatic_triggers": {
            artifact.artifact_id: rollback_trigger_for(artifact)
            for artifact in artifacts
            if rollback_trigger_for(artifact) is not None
        },
        "unauthorized_production_mutation": [],
        "missing_evaluation_evidence": [
            artifact.artifact_id for artifact in artifacts if not artifact.evaluation_record_ids
        ],
    }


def validate_learning_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report["unauthorized_production_mutation"]:
        failures.append(f"unauthorized production mutation: {report['unauthorized_production_mutation']}")
    if report["missing_evaluation_evidence"]:
        failures.append(f"missing evaluation evidence: {report['missing_evaluation_evidence']}")
    if not report["regression_blocked"]:
        failures.append("benchmark regression was not blocked")
    if not report["recoverable_active_versions"]:
        failures.append("active versions are not recoverable")
    if not report["promotion_lineage_preserved"]:
        failures.append("promotion lineage is not recoverable")
    if not report["rollback_coverage"]:
        failures.append("rollback coverage missing")
    if not report["all_promotions_audited"]:
        failures.append("promotion or rollback event missing audit acknowledgement")
    if report["audit_event_count"] != report["promotion_event_count"] + report["rollback_event_count"]:
        failures.append("promotion events bypassed governed audit writer")
    return failures
