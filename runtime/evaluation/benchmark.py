from __future__ import annotations

from dataclasses import dataclass

from runtime.base_agent.agent_manifest import ACTIVE_AGENT_PROFILES
from runtime.evaluation.schema import EVALUATION_VERSION, EvidenceReference, EvaluationInput


BENCHMARK_VERSION = "phase10.benchmark.v1"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    category: str
    input: EvaluationInput
    expected_pass: bool


def active_agent_benchmark_cases() -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []
    for profile in ACTIVE_AGENT_PROFILES:
        claim = f"{profile.agent_id} completed governed evaluation task"
        evidence = EvidenceReference.from_content(
            f"evidence-{profile.agent_id}",
            f"{profile.agent_id} completed governed evaluation task with audit evidence.",
            source=f"{BENCHMARK_VERSION}:{profile.runtime_contract}",
        )
        cases.append(
            BenchmarkCase(
                case_id=f"{BENCHMARK_VERSION}:{profile.agent_id}:positive",
                category=profile.runtime_contract,
                input=EvaluationInput(
                    agent_id=profile.agent_id,
                    task_id=f"task-{profile.agent_id}",
                    attempt_id=f"attempt-{profile.agent_id}",
                    output=claim,
                    claim=claim,
                    evidence=(evidence,),
                    predicted_confidence=0.9,
                    evaluator_id="phase10-independent-evaluator",
                    expected_answer=claim,
                    expected_tool_result="ok",
                    observed_tool_result="ok",
                    task_completed=True,
                    deterministic_verifier=True,
                ),
                expected_pass=True,
            )
        )
    return tuple(cases)


def negative_benchmark_cases() -> tuple[BenchmarkCase, ...]:
    unsupported = EvaluationInput(
        agent_id="ceo-agent",
        task_id="task-negative-unsupported",
        attempt_id="attempt-negative-unsupported",
        output="The market will double tomorrow.",
        claim="The market will double tomorrow.",
        evidence=(EvidenceReference.from_content("evidence-unrelated", "This evidence discusses office snacks."),),
        predicted_confidence=0.95,
        evaluator_id="phase10-independent-evaluator",
        expected_answer="The market will double tomorrow.",
        deterministic_verifier=True,
    )
    tampered_ref = EvidenceReference.from_content("evidence-tampered", "Reviewer approved safe change.")
    tampered = EvaluationInput(
        agent_id="reviewer-agent",
        task_id="task-negative-tampered",
        attempt_id="attempt-negative-tampered",
        output="Reviewer approved safe change.",
        claim="Reviewer approved safe change.",
        evidence=(EvidenceReference(tampered_ref.evidence_id, "Reviewer approved unsafe change.", tampered_ref.content_sha256, "tamper-test"),),
        predicted_confidence=0.6,
        evaluator_id="phase10-independent-evaluator",
        expected_answer="Reviewer approved safe change.",
        deterministic_verifier=True,
    )
    disagreement = EvaluationInput(
        agent_id="privacy-agent",
        task_id="task-negative-disagreement",
        attempt_id="attempt-negative-disagreement",
        output="Access request is compliant.",
        claim="Access request is compliant.",
        evidence=(EvidenceReference.from_content("evidence-privacy", "Access request is compliant."),),
        predicted_confidence=0.7,
        evaluator_id="phase10-independent-evaluator",
        expected_answer="Access request is not compliant.",
        deterministic_verifier=True,
    )
    return (
        BenchmarkCase(f"{BENCHMARK_VERSION}:negative:unsupported-high-confidence", "negative", unsupported, False),
        BenchmarkCase(f"{BENCHMARK_VERSION}:negative:tampered-evidence", "negative", tampered, False),
        BenchmarkCase(f"{BENCHMARK_VERSION}:negative:evaluator-disagreement", "negative", disagreement, False),
    )


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    return active_agent_benchmark_cases() + negative_benchmark_cases()


def benchmark_metadata() -> dict[str, object]:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "active_agent_count": len(ACTIVE_AGENT_PROFILES),
        "case_count": len(benchmark_cases()),
    }
