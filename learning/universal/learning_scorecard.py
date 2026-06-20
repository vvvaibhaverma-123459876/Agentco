"""
Learning Scorecard — Evaluation metrics for learning system performance.

Tracks accuracy, false belief detection, calibration, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class LearningScorecard:
    """Metrics for learning system evaluation."""

    total_claims_extracted: int = 0
    claims_promoted: int = 0
    claims_rejected: int = 0
    false_belief_promotion_rate: float = 0.0
    calibration_error: float = 0.0
    replication_success_rate: float = 0.0
    contradiction_detection_rate: float = 0.0
    lesson_extraction_rate: float = 0.0
    cross_domain_hypothesis_success_rate: float = 0.0
    memory_retrieval_precision: float = 0.0
    institutional_decision_improvement: float = 0.0
    time_to_correction_after_false_belief: str = "unknown"
    percentage_with_provenance: float = 100.0
    percentage_with_audit_trail: float = 100.0
    disputed_claims: int = 0
    downgraded_claims: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Export scorecard."""
        return {
            "total_claims": self.total_claims_extracted,
            "promoted": self.claims_promoted,
            "rejected": self.claims_rejected,
            "false_belief_rate": self.false_belief_promotion_rate,
            "calibration_error": self.calibration_error,
            "replication_success": self.replication_success_rate,
            "contradiction_detection": self.contradiction_detection_rate,
            "created_at": self.created_at.isoformat(),
        }
