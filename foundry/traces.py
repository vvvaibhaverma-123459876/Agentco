from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class TraceRecord:
    trace_id: str
    task_request: str
    claims_used: list[str]
    evidence_used: list[str]
    actions: list[str]
    outcome: str
    calibration_update: dict
    approvals: list[str] = field(default_factory=list)


@dataclass
class TrainingExample:
    example_id: str
    trace_id: str
    category: str
    input_text: str
    output_text: str
    lineage_refs: list[str]
    trust_weight: float


class ModelFoundry:
    def __init__(self):
        self.traces: dict[str, TraceRecord] = {}
        self.datasets: dict[str, list[TrainingExample]] = {}

    def capture_trace(self, **kwargs) -> TraceRecord:
        trace = TraceRecord(trace_id=str(uuid.uuid4()), **kwargs)
        self.traces[trace.trace_id] = trace
        return trace

    def build_example(self, trace_id: str, category: str = "evidence-evaluation") -> TrainingExample:
        trace = self.traces[trace_id]
        weight = float(trace.calibration_update.get("trusted_confidence", 0.5))
        example = TrainingExample(
            example_id=str(uuid.uuid4()),
            trace_id=trace_id,
            category=category,
            input_text=trace.task_request,
            output_text=trace.outcome,
            lineage_refs=[*trace.claims_used, *trace.evidence_used, *trace.actions],
            trust_weight=weight,
        )
        return example

    def add_to_dataset(self, dataset: str, example: TrainingExample) -> None:
        self.datasets.setdefault(dataset, []).append(example)

    def export_dataset(self, dataset: str) -> list[dict]:
        return [example.__dict__ for example in self.datasets.get(dataset, [])]
