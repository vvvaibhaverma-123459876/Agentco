from __future__ import annotations

from dataclasses import replace

import pytest

from runtime.base_agent.agent_manifest import ACTIVE_AGENT_PROFILES
from runtime.base_agent.audit_writer import AuditUnavailableError, InMemoryAuditWriter
from runtime.evaluation.benchmark import active_agent_benchmark_cases, benchmark_cases
from runtime.evaluation.evaluators import EvaluationError, EvaluationService, ImmutableEvaluationStore
from runtime.evaluation.metrics import calibration_metrics
from runtime.evaluation.report import build_evaluation_report, validate_report
from runtime.evaluation.schema import EvidenceReference, EvaluationInput


def _service() -> EvaluationService:
    return EvaluationService(audit_writer=InMemoryAuditWriter(allow_test_mode=True))


def _input(**overrides) -> EvaluationInput:
    claim = "Paris is the capital of France."
    evidence = EvidenceReference.from_content("ev-paris", "Paris is the capital of France.")
    base = EvaluationInput(
        agent_id="ceo-agent",
        task_id="task-1",
        attempt_id="attempt-1",
        output=claim,
        claim=claim,
        evidence=(evidence,),
        predicted_confidence=0.9,
        evaluator_id="independent-evaluator",
        expected_answer=claim,
        expected_tool_result="Paris",
        observed_tool_result="Paris",
        task_completed=True,
        deterministic_verifier=True,
    )
    return replace(base, **overrides)


def test_correct_outputs_score_positively_and_are_audited():
    service = _service()
    record = service.evaluate(_input())

    assert record.passed
    assert record.correctness_score == 1.0
    assert record.evidence_quality_score == 1.0
    assert record.audit_log_id
    assert service.audit_writer.entries[0].attempt_id == record.evaluation_id


def test_incorrect_outputs_fail():
    record = _service().evaluate(_input(output="Lyon", expected_answer="Paris is the capital of France."))

    assert not record.passed
    assert record.correctness_score == 0.0
    assert record.failure_category == "evaluator_disagreement"


def test_unsupported_high_confidence_claims_fail():
    record = _service().evaluate(_input(
        claim="The moon is made of cheese.",
        output="The moon is made of cheese.",
        evidence=(EvidenceReference.from_content("ev-unrelated", "Paris is a city."),),
        expected_answer="The moon is made of cheese.",
        predicted_confidence=0.95,
    ))

    assert not record.passed
    assert record.failure_category == "unsupported_claim"


def test_tampered_evidence_is_detected():
    evidence = EvidenceReference.from_content("ev-safe", "The change is safe.")
    tampered = replace(evidence, content="The change is unsafe.")
    record = _service().evaluate(_input(
        agent_id="reviewer-agent",
        claim="The change is safe.",
        output="The change is safe.",
        evidence=(tampered,),
        expected_answer="The change is safe.",
        predicted_confidence=0.7,
    ))

    assert not record.passed
    assert record.failure_category == "tampered_evidence"


@pytest.mark.parametrize("confidence", [None, -0.1, 1.1])
def test_confidence_values_are_validated(confidence):
    with pytest.raises(EvaluationError, match="confidence"):
        _service().evaluate(_input(predicted_confidence=confidence))


def test_abstention_is_allowed_when_evidence_is_insufficient():
    record = _service().evaluate(_input(
        claim="Unverifiable claim",
        output="I abstain because evidence is insufficient.",
        evidence=(),
        expected_answer=None,
        predicted_confidence=0.2,
        abstained=True,
    ))

    assert record.passed
    assert record.abstained


def test_agents_cannot_self_certify_without_deterministic_verifier():
    with pytest.raises(EvaluationError, match="self-certify"):
        _service().evaluate(_input(evaluator_id="ceo-agent", deterministic_verifier=False))


def test_repeated_evaluation_is_idempotent():
    service = _service()
    first = service.evaluate(_input())
    second = service.evaluate(_input())

    assert second.evaluation_id == first.evaluation_id
    assert second.audit_log_id == first.audit_log_id
    assert len(service.audit_writer.entries) == 1


def test_historical_evaluation_records_are_immutable():
    store = ImmutableEvaluationStore()
    service = EvaluationService(audit_writer=InMemoryAuditWriter(allow_test_mode=True), store=store)
    record = service.evaluate(_input())
    changed = replace(record, correctness_score=0.0)

    with pytest.raises(EvaluationError, match="immutable"):
        store.put(changed)


def test_evaluator_disagreement_is_preserved_not_hidden():
    record = _service().evaluate(_input(
        claim="Access request is compliant.",
        output="Access request is compliant.",
        evidence=(EvidenceReference.from_content("ev-access", "Access request is compliant."),),
        expected_answer="Access request is not compliant.",
        predicted_confidence=0.7,
    ))

    assert record.failure_category == "evaluator_disagreement"
    assert any(result.passed for result in record.evaluator_results)
    assert any(not result.passed for result in record.evaluator_results)


def test_calibration_metrics_are_generated():
    service = _service()
    for case in benchmark_cases():
        service.evaluate(case.input)
    metrics = calibration_metrics(service.store.records())

    assert metrics["brier_score"] >= 0
    assert "expected_calibration_error" in metrics
    assert metrics["unsupported_claim_rate"] > 0
    assert metrics["evaluator_disagreement_rate"] > 0


def test_all_active_agents_have_benchmark_coverage():
    covered = {case.input.agent_id for case in active_agent_benchmark_cases()}
    assert covered == {profile.agent_id for profile in ACTIVE_AGENT_PROFILES}


def test_machine_report_validates_phase10_gate_conditions():
    report = build_evaluation_report()
    assert validate_report(report) == []
    assert report["active_agent_count"] == 11
    assert report["missing_active_agent_ids"] == []
    assert report["all_records_audited"]


def test_production_evaluation_requires_explicit_durable_dependencies(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")

    with pytest.raises(AuditUnavailableError, match="durable audit writer"):
        EvaluationService(store=ImmutableEvaluationStore())

    with pytest.raises(EvaluationError, match="durable evaluation repository"):
        EvaluationService(audit_writer=InMemoryAuditWriter(allow_test_mode=True))
