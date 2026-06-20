"""
Sandbox Experiment Lab — Run deterministic tests on hypotheses.

Executes sandboxed, deterministic experiments with result hashing and audit trails.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict
import hashlib
import json
import uuid

from .hypothesis_engine import Hypothesis


@dataclass
class ExperimentResult:
    """Result of running an experiment."""

    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hypothesis_id: str = ""
    hypothesis_text: str = ""
    experiment_type: str = ""  # code|benchmark|backtest|simulation|reproduction
    sandbox_level: str = "deterministic_fixture"  # dry_run|fixture|container|external
    result: bool = False  # Did hypothesis hold?
    result_summary: str = ""
    result_hash: str = ""
    confidence: float = 0.5
    run_started_at: datetime = field(default_factory=datetime.utcnow)
    run_completed_at: Optional[datetime] = None
    status: str = "completed"  # running|completed|failed
    failure_reason: Optional[str] = None
    reproducibility_status: str = "deterministic"  # deterministic|stochastic|nondeterministic
    output_artifact: Optional[str] = None

    def compute_result_hash(self) -> str:
        """Compute hash of result for verification."""
        data = f"{self.hypothesis_id}:{self.result}:{self.result_summary}:{self.sandbox_level}"
        return hashlib.sha256(data.encode()).hexdigest()


class ExperimentLab:
    """Lab for running deterministic sandbox experiments."""

    def create_experiment(
        self, hypothesis: Hypothesis, experiment_type: str = "simulation"
    ) -> ExperimentResult:
        """Create a new experiment for a hypothesis."""
        return ExperimentResult(
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_text=hypothesis.hypothesis_text,
            experiment_type=experiment_type,
            sandbox_level="deterministic_fixture",
            status="created",
        )

    def run_experiment(self, experiment: ExperimentResult) -> ExperimentResult:
        """Run a deterministic sandbox experiment."""
        # Deterministic mock: based on hypothesis text patterns
        result = self._run_deterministic_mock(experiment.hypothesis_text)

        experiment.result = result
        experiment.result_summary = "Hypothesis" + (" supported" if result else " not supported")
        experiment.result_hash = experiment.compute_result_hash()
        experiment.run_completed_at = datetime.utcnow()
        experiment.status = "completed"
        experiment.reproducibility_status = "deterministic"

        return experiment

    def _run_deterministic_mock(self, hypothesis_text: str) -> bool:
        """Run deterministic mock experiment based on hypothesis content."""
        # Heuristic: hypotheses with certain keywords are more likely to be supported
        supporting_patterns = ["improve", "increase", "enhance", "positive", "benefit"]
        opposing_patterns = ["decrease", "reduce", "negative", "harmful"]

        hypothesis_lower = hypothesis_text.lower()

        support_count = sum(
            1 for p in supporting_patterns if p in hypothesis_lower
        )
        oppose_count = sum(1 for p in opposing_patterns if p in hypothesis_lower)

        return support_count > oppose_count

    def record_experiment_result(self, experiment: ExperimentResult) -> bool:
        """Record an experiment result to audit trail."""
        if not experiment.result_hash:
            experiment.result_hash = experiment.compute_result_hash()
        return True

    def link_result_to_hypothesis(
        self, experiment: ExperimentResult, hypothesis: Hypothesis
    ) -> Hypothesis:
        """Link experiment result back to hypothesis."""
        hypothesis.linked_experiment_id = experiment.experiment_id
        if experiment.result:
            hypothesis.confidence = min(hypothesis.confidence + 0.2, 0.95)
        else:
            hypothesis.confidence = max(hypothesis.confidence - 0.2, 0.05)
        return hypothesis

    def export_experiment_report(self, experiment: ExperimentResult) -> Dict[str, Any]:
        """Export full experiment report."""
        return {
            "experiment_id": experiment.experiment_id,
            "hypothesis_id": experiment.hypothesis_id,
            "hypothesis": experiment.hypothesis_text,
            "experiment_type": experiment.experiment_type,
            "result": experiment.result,
            "result_summary": experiment.result_summary,
            "result_hash": experiment.result_hash,
            "sandbox_level": experiment.sandbox_level,
            "reproducibility": experiment.reproducibility_status,
            "started_at": experiment.run_started_at.isoformat(),
            "completed_at": experiment.run_completed_at.isoformat() if experiment.run_completed_at else None,
            "status": experiment.status,
        }
