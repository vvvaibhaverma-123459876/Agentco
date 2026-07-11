from __future__ import annotations

from dataclasses import replace

import pytest

from runtime.base_agent.audit_writer import InMemoryAuditWriter
from runtime.controlled_learning.pipeline import (
    ControlledLearningError,
    ControlledLearningPipeline,
    FileLearningArtifactStore,
    LearningArtifactStore,
)
from runtime.controlled_learning.report import build_learning_report, validate_learning_report
from runtime.controlled_learning.schema import BenchmarkImpact


def _pipeline(store=None) -> ControlledLearningPipeline:
    return ControlledLearningPipeline(store=store, audit_writer=InMemoryAuditWriter(allow_test_mode=True))


def _artifact(pipeline: ControlledLearningPipeline, **overrides):
    params = {
        "proposer_id": "agent-proposer",
        "source_observations": ("observation: eval showed better wording",),
        "evaluation_record_ids": ("phase10:evaluation-record",),
        "proposed_change": {"surface": "prompt", "version": "prompt-v2", "change": "tighten evidence wording"},
        "evidence_refs": ("evidence:record",),
        "benchmark_impact": BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.92),
    }
    params.update(overrides)
    return pipeline.propose(**params)


def _approved_canary(pipeline: ControlledLearningPipeline):
    artifact = _artifact(pipeline)
    artifact = pipeline.evaluate_offline(artifact.artifact_id)
    artifact = pipeline.approve(artifact.artifact_id, approver_id="human-governor", authorization_id="auth-1")
    return pipeline.stage_canary(artifact.artifact_id, actor_id="release-manager")


def test_learning_artifacts_persist_across_runs(tmp_path):
    path = tmp_path / "learning-artifacts.json"
    first = _pipeline(store=FileLearningArtifactStore(path))
    artifact = _artifact(first)

    second_store = FileLearningArtifactStore(path)
    restored = second_store.get(artifact.artifact_id)

    assert restored.artifact_id == artifact.artifact_id
    assert restored.proposed_change == artifact.proposed_change


def test_unevaluated_artifacts_cannot_be_promoted():
    pipeline = _pipeline()
    artifact = _artifact(pipeline)

    with pytest.raises(ControlledLearningError, match="only canary"):
        pipeline.promote(artifact.artifact_id, actor_id="release-manager")


def test_self_approved_changes_are_rejected():
    pipeline = _pipeline()
    artifact = pipeline.evaluate_offline(_artifact(pipeline).artifact_id)

    with pytest.raises(ControlledLearningError, match="self-approved"):
        pipeline.approve(artifact.artifact_id, approver_id="agent-proposer", authorization_id="auth-1")


def test_tampered_evidence_is_rejected():
    pipeline = _pipeline()
    artifact = _artifact(pipeline, evidence_refs=("tampered:evidence",))

    with pytest.raises(ControlledLearningError, match="tampered evidence"):
        pipeline.evaluate_offline(artifact.artifact_id)


def test_failed_candidates_do_not_affect_production():
    pipeline = _pipeline()
    artifact = _artifact(
        pipeline,
        benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.6),
    )

    rejected = pipeline.evaluate_offline(artifact.artifact_id)

    assert rejected.state == "rejected"
    assert pipeline.active_versions == {}


def test_duplicate_promotion_requests_are_idempotent():
    pipeline = _pipeline()
    canary = _approved_canary(pipeline)
    first = pipeline.promote(canary.artifact_id, actor_id="release-manager")
    second = pipeline.promote(canary.artifact_id, actor_id="release-manager")

    assert second.artifact_id == first.artifact_id
    assert len(second.promotion_history) == len(first.promotion_history)
    assert len(pipeline.audit_writer.entries) == 2  # canary + first promotion


def test_rollback_restores_previous_active_version():
    pipeline = _pipeline()
    baseline = _approved_canary(pipeline)
    baseline = pipeline.promote(baseline.artifact_id, actor_id="release-manager")
    candidate = _artifact(
        pipeline,
        proposed_change={"surface": "prompt", "version": "prompt-v3", "change": "candidate update"},
        evidence_refs=("evidence:candidate",),
    )
    candidate = pipeline.evaluate_offline(candidate.artifact_id)
    candidate = pipeline.approve(candidate.artifact_id, approver_id="human-governor", authorization_id="auth-2")
    candidate = pipeline.stage_canary(candidate.artifact_id, actor_id="release-manager")
    candidate = pipeline.promote(candidate.artifact_id, actor_id="release-manager")
    rolled_back = pipeline.rollback(candidate.artifact_id, actor_id="release-manager", trigger="benchmark_regression")

    assert rolled_back.state == "rolled_back"
    assert pipeline.active_versions["prompt"] == baseline.artifact_id


def test_historical_artifacts_cannot_be_altered():
    store = LearningArtifactStore()
    pipeline = _pipeline(store=store)
    artifact = _artifact(pipeline)
    altered = replace(artifact, proposed_change={"surface": "prompt", "version": "evil"})

    with pytest.raises(ControlledLearningError, match="cannot be altered"):
        store.put(altered)


def test_unauthorized_direct_production_mutation_is_blocked():
    pipeline = _pipeline()
    canary = _approved_canary(pipeline)

    with pytest.raises(ControlledLearningError, match="proposer cannot directly modify"):
        pipeline.promote(canary.artifact_id, actor_id="agent-proposer")


@pytest.mark.parametrize(
    ("impact", "trigger"),
    [
        (BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.8), "benchmark_regression"),
        (BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.91, calibration_delta=0.06), "calibration_degradation"),
        (BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.91, unsupported_claim_delta=0.03), "unsupported_claim_increase"),
    ],
)
def test_automatic_rollback_triggers(impact, trigger):
    pipeline = _pipeline()
    artifact = _artifact(pipeline, proposed_change={"surface": "policy", "version": trigger}, benchmark_impact=impact)
    if impact.regression:
        assert pipeline.evaluate_offline(artifact.artifact_id).state == "rejected"
        return
    artifact = pipeline.evaluate_offline(artifact.artifact_id)
    artifact = pipeline.approve(artifact.artifact_id, approver_id="human-governor", authorization_id=f"auth-{trigger}")
    artifact = pipeline.stage_canary(artifact.artifact_id, actor_id="release-manager")
    monitored = pipeline.monitor(artifact.artifact_id, actor_id="release-manager")

    assert monitored.state == "rolled_back"
    assert monitored.rollback_history[-1].reason == f"rollback:{trigger}"


def test_machine_report_validates_phase11_gate_conditions():
    report = build_learning_report()

    assert validate_learning_report(report) == []
    assert report["rollback_coverage"]
    assert report["regression_blocked"]
    assert report["all_promotions_audited"]
