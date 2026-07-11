from __future__ import annotations

import pytest

from runtime.base_agent.audit_writer import AuditUnavailableError
from runtime.controlled_learning.schema import BenchmarkImpact
from runtime.evaluation.schema import EvaluationRecord, EvaluatorResult
from runtime.self_improvement.experiments import BoundedExperimentRunner, ExperimentStore, PostgresExperimentStore, SelfImprovementError
from runtime.self_improvement.report import build_experiment_report, validate_experiment_report
from runtime.self_improvement.schema import ExperimentUsage, ImprovementExperiment, ResourceBudget


class MemoryAuditWriter:
    def __init__(self) -> None:
        self.entries = []

    def write(self, entry):
        self.entries.append(entry)
        return {"log_id": entry.attempt_id, "backend": "memory"}


class EvaluationStoreStub:
    def __init__(self, records):
        self.records = records

    def get(self, evaluation_id):
        if evaluation_id not in self.records:
            from runtime.evaluation.evaluators import EvaluationError
            raise EvaluationError(f"unknown evaluation record: {evaluation_id}")
        return self.records[evaluation_id]


def eval_record(*, evaluation_id="eval-record-1", agent_id="ceo-agent", passed=True):
    return EvaluationRecord(
        evaluation_id=evaluation_id,
        agent_id=agent_id,
        task_id="task-1",
        attempt_id="attempt-1",
        output_or_claim="claim",
        supporting_evidence_refs=("evidence-1",),
        predicted_confidence=0.9,
        evaluator_result="passed" if passed else "failed",
        correctness_score=1.0 if passed else 0.0,
        evidence_quality_score=1.0,
        calibration_error=0.1,
        failure_category="none" if passed else "incorrect",
        evaluation_timestamp="2026-07-11T00:00:00Z",
        evaluation_version="phase10.eval.v1",
        evaluator_id="independent-evaluator",
        brier_score=0.01,
        abstained=False,
        evaluator_results=(EvaluatorResult("factual_correctness", passed, 1.0 if passed else 0.0),),
        audit_log_id="00000000-0000-0000-0000-000000000001",
        audit_backend="stub",
    )


def budget() -> ResourceBudget:
    return ResourceBudget(max_seconds=10, max_spend_cents=20, max_tool_calls=2, max_scope_items=2)


def runner() -> tuple[BoundedExperimentRunner, MemoryAuditWriter]:
    audit = MemoryAuditWriter()
    return BoundedExperimentRunner(audit_writer=audit), audit


def run_experiment(agent: BoundedExperimentRunner, **overrides):
    params = {
        "hypothesis": "bounded experiment improves evidence support",
        "target_capability": "evidence_support",
        "proposed_change": {"surface": "prompt", "change_type": "prompt_variant"},
        "evidence_refs": ("phase10:evidence",),
        "benchmark_refs": ("phase10.benchmark.v1",),
        "allowed_scope": ("sandbox:prompt",),
        "resource_budget": budget(),
        "risk_level": "medium",
        "evaluator": "independent-evaluator",
        "proposer_id": "agent-proposer",
        "experiment_kind": "prompt_variant",
        "requested_tools": ("read_fixture",),
        "allowed_tools": ("read_fixture",),
        "resource_usage": ExperimentUsage(seconds=1, spend_cents=1, tool_calls=1, scope_items=1),
        "benchmark_impact": BenchmarkImpact("phase10.benchmark.v1", 0.90, 0.91),
        "approval_actor": "human-approver",
    }
    params.update(overrides)
    return agent.run(**params)


@pytest.mark.parametrize(
    ("kind", "surface", "change_type"),
    [
        ("prompt_variant", "prompt", "prompt_variant"),
        ("policy_proposal", "policy", "policy_proposal"),
        ("tool_selection_strategy", "tool", "tool_selection_strategy"),
        ("memory_rule_proposal", "memory_rule", "memory_rule_proposal"),
        ("model_routing_strategy", "model", "model_routing_strategy"),
    ],
)
def test_supported_experiment_types_are_isolated_and_audited(kind, surface, change_type):
    agent, audit = runner()
    experiment = run_experiment(
        agent,
        hypothesis=f"{kind} improves benchmark result",
        proposed_change={"surface": surface, "change_type": change_type},
        allowed_scope=(f"sandbox:{surface}",),
        experiment_kind=kind,
    )
    assert experiment.outcome == "accepted"
    assert experiment.promotion_recommendation == "propose_phase11_artifact"
    assert experiment.audit_log_id == experiment.experiment_id
    assert len(audit.entries) == 1
    assert agent.production_state == {"prompt": "prompt-v1", "policy": "policy-v1"}


def test_scope_escape_is_blocked():
    agent, _ = runner()
    experiment = run_experiment(agent, allowed_scope=("production:prompt",))
    assert experiment.outcome == "blocked"
    assert "scope_escape" in experiment.safety_violations


@pytest.mark.parametrize(
    ("usage", "violation"),
    [
        (ExperimentUsage(seconds=11, spend_cents=1, tool_calls=1, scope_items=1), "time_budget_exceeded"),
        (ExperimentUsage(seconds=1, spend_cents=21, tool_calls=1, scope_items=1), "spend_budget_exceeded"),
        (ExperimentUsage(seconds=1, spend_cents=1, tool_calls=3, scope_items=1), "tool_budget_exceeded"),
        (ExperimentUsage(seconds=1, spend_cents=1, tool_calls=1, scope_items=3), "scope_budget_exceeded"),
    ],
)
def test_budget_overruns_stop_execution(usage, violation):
    agent, _ = runner()
    experiment = run_experiment(agent, resource_usage=usage)
    assert experiment.outcome == "blocked"
    assert violation in experiment.safety_violations


def test_unauthorized_tools_are_blocked():
    agent, _ = runner()
    experiment = run_experiment(agent, requested_tools=("network_write",), allowed_tools=("read_fixture",))
    assert experiment.outcome == "blocked"
    assert "unauthorized_tool" in experiment.safety_violations


def test_production_mutation_is_rejected():
    agent, _ = runner()
    experiment = run_experiment(agent, wants_production_mutation=True)
    assert experiment.outcome == "blocked"
    assert "production_mutation_rejected" in experiment.safety_violations
    assert agent.production_state == {"prompt": "prompt-v1", "policy": "policy-v1"}


def test_self_approval_is_rejected():
    agent, _ = runner()
    experiment = run_experiment(agent, approval_actor="agent-proposer")
    assert experiment.outcome == "blocked"
    assert "self_approval_rejected" in experiment.safety_violations


def test_tampered_evidence_is_rejected():
    agent, _ = runner()
    experiment = run_experiment(agent, evidence_refs=("tampered:evidence",))
    assert experiment.outcome == "blocked"
    assert "tampered_evidence" in experiment.safety_violations


def test_failed_experiments_leave_production_unchanged():
    agent, _ = runner()
    experiment = run_experiment(agent, benchmark_impact=BenchmarkImpact("phase10.benchmark.v1", 0.90, 0.70))
    assert experiment.outcome == "rejected"
    assert experiment.promotion_recommendation == "none"
    assert agent.production_state == {"prompt": "prompt-v1", "policy": "policy-v1"}


def test_duplicate_experiment_requests_are_idempotent():
    agent, audit = runner()
    first = run_experiment(agent)
    second = run_experiment(agent)
    assert second.experiment_id == first.experiment_id
    assert second.audit_log_id == first.audit_log_id
    assert len(audit.entries) == 1


@pytest.mark.parametrize("change_type", ["model_weight_update", "unrestricted_code_rewrite"])
def test_model_weight_modification_and_unrestricted_code_rewriting_are_blocked(change_type):
    agent, _ = runner()
    experiment = run_experiment(agent, proposed_change={"surface": "model", "change_type": change_type})
    assert experiment.outcome == "blocked"
    assert "forbidden_change_type" in experiment.safety_violations


def test_historical_experiments_cannot_be_altered():
    store = ExperimentStore()
    agent = BoundedExperimentRunner(store=store, audit_writer=MemoryAuditWriter())
    original = run_experiment(agent)
    tampered = ImprovementExperiment(
        **{
            **original.__dict__,
            "proposed_change": {"surface": "prompt", "change_type": "prompt_variant", "tampered": True},
        }
    )
    with pytest.raises(SelfImprovementError, match="historical experiment cannot be altered"):
        store.put(tampered)


def test_machine_report_validates_phase12_gate_conditions():
    report = build_experiment_report()
    assert validate_experiment_report(report) == []
    assert report["attempted_experiment_count"] == 8
    assert report["all_experiments_audited"] is True
    assert report["safety_violations"]


def test_production_self_improvement_requires_explicit_durable_dependencies(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_EXPERIMENT_DATABASE_URL", raising=False)

    with pytest.raises(SelfImprovementError, match="AGENTCO_EXPERIMENT_DATABASE_URL"):
        BoundedExperimentRunner(audit_writer=MemoryAuditWriter())

    with pytest.raises(AuditUnavailableError, match="durable audit writer"):
        BoundedExperimentRunner(store=ExperimentStore())


def test_production_self_improvement_rejects_in_memory_audit_writer(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    monkeypatch.setenv("AGENTCO_EXPERIMENT_DATABASE_URL", "postgresql://example.invalid/agentco")
    monkeypatch.setenv("AGENTCO_EVALUATION_DATABASE_URL", "postgresql://example.invalid/agentco")

    from runtime.base_agent.audit_writer import InMemoryAuditWriter

    with pytest.raises(AuditUnavailableError, match="InMemoryAuditWriter"):
        BoundedExperimentRunner(audit_writer=InMemoryAuditWriter(allow_test_mode=True))


def test_production_self_improvement_auto_selects_postgres_store(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    monkeypatch.setenv("AGENTCO_EXPERIMENT_DATABASE_URL", "postgresql://example.invalid/agentco")
    monkeypatch.setenv("AGENTCO_EVALUATION_DATABASE_URL", "postgresql://example.invalid/agentco")

    runner = BoundedExperimentRunner(audit_writer=MemoryAuditWriter())

    assert isinstance(runner.store, PostgresExperimentStore)


def test_production_self_improvement_requires_record_backed_evidence(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    record = eval_record(evaluation_id="eval-record-1", agent_id="ceo-agent", passed=True)
    agent = BoundedExperimentRunner(
        store=ExperimentStore(),
        audit_writer=MemoryAuditWriter(),
        evaluation_store=EvaluationStoreStub({record.evaluation_id: record}),
    )

    accepted = run_experiment(
        agent,
        evidence_refs=(record.evaluation_id,),
        proposed_change={"surface": "prompt", "change_type": "prompt_variant", "subject_id": "ceo-agent"},
    )

    assert accepted.outcome == "accepted"


def test_production_self_improvement_blocks_missing_or_failed_evidence_records(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    failed = eval_record(evaluation_id="failed-eval", passed=False)
    agent = BoundedExperimentRunner(
        store=ExperimentStore(),
        audit_writer=MemoryAuditWriter(),
        evaluation_store=EvaluationStoreStub({"failed-eval": failed}),
    )

    missing = run_experiment(agent, evidence_refs=("missing-eval",))
    failed_result = run_experiment(
        agent,
        hypothesis="failed eval cannot support bounded experiment",
        evidence_refs=("failed-eval",),
    )

    assert "missing_evaluation_record" in missing.safety_violations
    assert "failed_evaluation_record" in failed_result.safety_violations
