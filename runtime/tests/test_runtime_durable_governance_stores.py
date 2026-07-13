from __future__ import annotations

import os
from pathlib import Path

import pytest

from runtime.controlled_learning.pipeline import PostgresLearningArtifactStore
from runtime.controlled_learning.schema import BenchmarkImpact, LearningArtifact
from runtime.evaluation.evaluators import PostgresEvaluationStore
from runtime.evaluation.schema import EvaluationRecord, EvaluatorResult
from runtime.self_improvement.experiments import PostgresExperimentStore
from runtime.self_improvement.schema import ExperimentUsage, ImprovementExperiment, ResourceBudget


def _dsn_or_skip() -> str:
    dsn = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("live-service: no AGENTCO_TEST_DATABASE_URL or DATABASE_URL configured")
    try:
        import psycopg2
        conn = psycopg2.connect(dsn, connect_timeout=2)
        conn.close()
    except Exception as exc:
        pytest.skip(f"live-service: Postgres unavailable: {exc}")
    return dsn


def _apply_runtime_migration(dsn: str) -> None:
    import psycopg2

    migration = Path(__file__).resolve().parents[2] / "backend/src/db/migrations/127_runtime_governance_artifacts.sql"
    with psycopg2.connect(dsn, connect_timeout=2) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.decision_log')")
            if cur.fetchone()[0] is None:
                pytest.skip("live-service: decision_log table is not migrated")
            cur.execute(
                """
                SELECT
                    to_regclass('public.runtime_evaluation_records'),
                    to_regclass('public.runtime_learning_artifacts'),
                    to_regclass('public.runtime_improvement_experiments')
                """
            )
            if all(cur.fetchone()):
                return

    migration_dsn = (
        os.environ.get("RELEASE_GATE_MIGRATION_DATABASE_URL")
        or os.environ.get("RELEASE_GATE_SETUP_DATABASE_URL")
        or dsn
    )
    with psycopg2.connect(migration_dsn, connect_timeout=2) as conn:
        with conn.cursor() as cur:
            cur.execute(migration.read_text())


def _evaluation_record(evaluation_id: str) -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_id=evaluation_id,
        agent_id="ceo-agent",
        task_id="task-runtime-store",
        attempt_id=evaluation_id,
        output_or_claim="Paris is the capital of France.",
        supporting_evidence_refs=("evidence-runtime-store",),
        predicted_confidence=0.9,
        evaluator_result="passed",
        correctness_score=1.0,
        evidence_quality_score=1.0,
        calibration_error=0.1,
        failure_category="none",
        evaluation_timestamp="2026-07-11T00:00:00Z",
        evaluation_version="phase10.eval.v1",
        evaluator_id="independent-evaluator",
        brier_score=0.01,
        abstained=False,
        evaluator_results=(EvaluatorResult("factual_correctness", True, 1.0),),
    )


def test_phase10_12_runtime_stores_persist_across_instances():
    dsn = _dsn_or_skip()
    _apply_runtime_migration(dsn)

    suffix = os.getpid()
    evaluation_id = f"runtime-store-eval-{suffix}"
    artifact_id = f"runtime-store-artifact-{suffix}"
    experiment_id = f"runtime-store-experiment-{suffix}"

    PostgresEvaluationStore(dsn).put(_evaluation_record(evaluation_id))
    restored_eval = PostgresEvaluationStore(dsn).get(evaluation_id)

    assert restored_eval.evaluation_id == evaluation_id
    assert restored_eval.passed

    artifact = LearningArtifact(
        artifact_id=artifact_id,
        source_observations=("observation",),
        evaluation_record_ids=(evaluation_id,),
        proposed_change={"surface": "prompt", "subject_id": "ceo-agent", "version": "runtime-store"},
        evidence_refs=("evidence-runtime-store",),
        benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.9, 0.91),
        proposer_id="agent-proposer",
        approval_status="pending",
        artifact_version="phase11.learning-artifact.v1",
    )
    PostgresLearningArtifactStore(dsn).put(artifact)
    restored_artifact = PostgresLearningArtifactStore(dsn).get(artifact_id)

    assert restored_artifact.artifact_id == artifact_id
    assert restored_artifact.evaluation_record_ids == (evaluation_id,)

    experiment = ImprovementExperiment(
        experiment_id=experiment_id,
        hypothesis="durable store survives a new process",
        target_capability="evidence_support",
        proposed_change={"surface": "prompt", "change_type": "prompt_variant", "subject_id": "ceo-agent"},
        evidence_refs=(evaluation_id,),
        benchmark_refs=("phase10.benchmark.v1",),
        allowed_scope=("sandbox:prompt",),
        resource_budget=ResourceBudget(max_seconds=10, max_spend_cents=10, max_tool_calls=1, max_scope_items=1),
        risk_level="medium",
        evaluator="independent-evaluator",
        proposer_id="agent-proposer",
        experiment_kind="prompt_variant",
        outcome="accepted",
        promotion_recommendation="propose_phase11_artifact",
        resource_usage=ExperimentUsage(seconds=1, spend_cents=1, tool_calls=1, scope_items=1),
    )
    PostgresExperimentStore(dsn).put(experiment)
    restored_experiment = next(item for item in PostgresExperimentStore(dsn).all() if item.experiment_id == experiment_id)

    assert restored_experiment.experiment_id == experiment_id
    assert restored_experiment.evidence_refs == (evaluation_id,)
