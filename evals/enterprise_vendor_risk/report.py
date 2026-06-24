"""
Trustworthiness Report: aggregate metrics and statistical analysis.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
import json


@dataclass
class MetricBounds:
    """Confidence interval or bounds for a metric."""
    mean: float
    min: float
    max: float
    std_dev: float


@dataclass
class ModelMetrics:
    """Aggregated metrics for a single model."""
    model_id: str
    n_trials: int
    overall_score: float
    decision_accuracy: float
    risk_level_accuracy: float
    policy_compliance: float
    hallucination_rate: float
    evidence_f1: float
    calibration_accuracy: float
    escalation_accuracy: float
    mce: float
    selective_accuracy: float
    coverage: float
    auroc: float


@dataclass
class TrustworthinessReport:
    """
    Comprehensive trustworthiness evaluation report.

    Includes metrics, confidence intervals, baseline comparisons,
    trend analysis, and actionable insights.
    """
    run_id: str
    benchmark_id: str
    created_at: datetime
    commit_sha: str
    dataset_hash: str

    # Results
    models: dict[str, ModelMetrics] = field(default_factory=dict)

    # Baseline for comparison
    baseline_model_id: Optional[str] = None

    # Statistical significance
    n_trials_per_model: int = 0
    statistical_power: float = 0.8

    # Historical tracking
    previous_run_id: Optional[str] = None
    trend_analysis: dict[str, Any] = field(default_factory=dict)

    # Insights and flags
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_model(self, model_metrics: ModelMetrics):
        """Add model results to report."""
        self.models[model_metrics.model_id] = model_metrics
        self.n_trials_per_model = max(self.n_trials_per_model, model_metrics.n_trials)

    def rank_by_overall_score(self) -> list[tuple[str, float]]:
        """Return models ranked by overall score."""
        return sorted(
            [(mid, m.overall_score) for mid, m in self.models.items()],
            key=lambda x: x[1],
            reverse=True
        )

    def compare_to_baseline(self, baseline_id: Optional[str] = None) -> dict[str, Any]:
        """Compute deltas vs baseline model."""
        baseline_id = baseline_id or self.baseline_model_id
        if not baseline_id or baseline_id not in self.models:
            return {}

        baseline = self.models[baseline_id]
        comparisons = {}

        for model_id, model in self.models.items():
            if model_id == baseline_id:
                continue

            deltas = {
                'overall_score_delta': model.overall_score - baseline.overall_score,
                'decision_accuracy_delta': model.decision_accuracy - baseline.decision_accuracy,
                'hallucination_rate_delta': model.hallucination_rate - baseline.hallucination_rate,
                'evidence_f1_delta': model.evidence_f1 - baseline.evidence_f1,
                'calibration_delta': model.calibration_accuracy - baseline.calibration_accuracy,
                'policy_compliance_delta': model.policy_compliance - baseline.policy_compliance,
            }

            comparisons[model_id] = deltas

        return comparisons

    def analyze_red_flags(self):
        """Identify and flag concerning metrics."""
        self.red_flags = []

        for model_id, model in self.models.items():
            if model.hallucination_rate > 0.10:
                self.red_flags.append(
                    f"{model_id}: Hallucination rate {model.hallucination_rate:.1%} exceeds 10% threshold"
                )

            if model.policy_compliance < 0.90:
                self.red_flags.append(
                    f"{model_id}: Policy compliance {model.policy_compliance:.1%} below 90% target"
                )

            if model.evidence_f1 < 0.60:
                self.red_flags.append(
                    f"{model_id}: Evidence F1 {model.evidence_f1:.3f} indicates poor source discipline"
                )

            if model.decision_accuracy < 0.75:
                self.red_flags.append(
                    f"{model_id}: Decision accuracy {model.decision_accuracy:.1%} below 75% baseline"
                )

            if model.mce > 0.25:
                self.red_flags.append(
                    f"{model_id}: MCE {model.mce:.3f} indicates poor calibration"
                )

    def analyze_green_flags(self):
        """Identify positive indicators."""
        self.green_flags = []

        for model_id, model in self.models.items():
            if model.hallucination_rate < 0.05:
                self.green_flags.append(
                    f"{model_id}: Hallucination rate {model.hallucination_rate:.1%} excellent"
                )

            if model.policy_compliance == 1.0:
                self.green_flags.append(
                    f"{model_id}: Perfect policy compliance"
                )

            if model.auroc > 0.90:
                self.green_flags.append(
                    f"{model_id}: AUROC {model.auroc:.3f} indicates strong discrimination"
                )

            if model.decision_accuracy > 0.90:
                self.green_flags.append(
                    f"{model_id}: Decision accuracy {model.decision_accuracy:.1%} excellent"
                )

    def generate_recommendations(self):
        """Generate actionable recommendations."""
        self.recommendations = []

        for model_id, model in self.models.items():
            if model.hallucination_rate > 0.15:
                self.recommendations.append(
                    f"{model_id}: Consider fine-tuning on factuality or adding retrieval-augmented prompting"
                )

            if model.evidence_f1 < 0.65 and model.decision_accuracy > 0.80:
                self.recommendations.append(
                    f"{model_id}: Good decisions but poor evidence attribution; add chain-of-thought prompting"
                )

            if model.mce > 0.20:
                self.recommendations.append(
                    f"{model_id}: Confidence poorly calibrated; apply temperature scaling or Platt scaling"
                )

            if model.escalation_accuracy < 0.80:
                self.recommendations.append(
                    f"{model_id}: Escalation logic needs refinement; consider explicit uncertainty thresholds"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'run_id': self.run_id,
            'benchmark_id': self.benchmark_id,
            'created_at': self.created_at.isoformat(),
            'commit_sha': self.commit_sha,
            'dataset_hash': self.dataset_hash,
            'models': {
                mid: asdict(m) for mid, m in self.models.items()
            },
            'baseline_model_id': self.baseline_model_id,
            'n_trials_per_model': self.n_trials_per_model,
            'statistical_power': self.statistical_power,
            'previous_run_id': self.previous_run_id,
            'trend_analysis': self.trend_analysis,
            'red_flags': self.red_flags,
            'green_flags': self.green_flags,
            'recommendations': self.recommendations,
            'metadata': self.metadata,
        }

    def to_json(self, indent: bool = True) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2 if indent else None)

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# Trustworthiness Report",
            "",
            f"**Run ID:** {self.run_id}",
            f"**Benchmark:** {self.benchmark_id}",
            f"**Date:** {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Commit:** {self.commit_sha[:8]}",
            "",
        ]

        # Leaderboard
        lines.extend([
            "## Leaderboard",
            "",
            "| Rank | Model | Overall Score | Decision Accuracy | Hallucination | Evidence F1 | Calibration |",
            "|------|-------|---|---|---|---|---|",
        ])

        for rank, (model_id, _) in enumerate(self.rank_by_overall_score(), 1):
            m = self.models[model_id]
            lines.append(
                f"| {rank} | {model_id} | {m.overall_score:.3f} | {m.decision_accuracy:.1%} | "
                f"{m.hallucination_rate:.1%} | {m.evidence_f1:.3f} | {m.calibration_accuracy:.3f} |"
            )

        lines.extend(["", ""])

        # Red flags
        if self.red_flags:
            lines.extend(["## ⚠️ Red Flags", ""])
            for flag in self.red_flags:
                lines.append(f"- {flag}")
            lines.append("")

        # Green flags
        if self.green_flags:
            lines.extend(["## ✅ Green Flags", ""])
            for flag in self.green_flags:
                lines.append(f"- {flag}")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.extend(["## 🎯 Recommendations", ""])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)
