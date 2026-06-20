"""
Curiosity Engine — Identify what's worth learning next.

Detects signals (novelty, contradiction, uncertainty) and ranks learning opportunities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

from .knowledge_claim import KnowledgeClaim, ClaimStatus


@dataclass
class CuriositySignal:
    """A learning opportunity flagged by the curiosity engine."""

    signal_id: str
    claim_id: str
    signal_type: str  # novelty|contradiction|uncertainty|anomaly|stale_belief
    domain: str
    novelty_score: float  # 0.0-1.0
    uncertainty_score: float
    value_score: float  # Expected usefulness
    risk_score: float  # Consequence if wrong
    expected_information_gain: float
    recommended_action: str  # read_more|verify|experiment|resolve|archive
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"


class CuriosityEngine:
    """Engine for identifying and ranking learning opportunities."""

    def detect_curiosity_signals(self, claim: KnowledgeClaim) -> List[CuriositySignal]:
        """Detect curiosity signals from a claim."""
        signals = []

        # Novelty signal
        if self._is_novel(claim):
            signals.append(
                CuriositySignal(
                    signal_id=f"{claim.claim_id}_novelty",
                    claim_id=claim.claim_id,
                    signal_type="novelty",
                    domain=claim.domain,
                    novelty_score=0.8,
                    uncertainty_score=0.6,
                    value_score=0.7,
                    risk_score=0.3,
                    expected_information_gain=0.7,
                    recommended_action="read_more",
                )
            )

        # Uncertainty signal
        if claim.uncertainty and claim.uncertainty > 0.5:
            signals.append(
                CuriositySignal(
                    signal_id=f"{claim.claim_id}_uncertainty",
                    claim_id=claim.claim_id,
                    signal_type="uncertainty",
                    domain=claim.domain,
                    novelty_score=0.3,
                    uncertainty_score=0.9,
                    value_score=0.6,
                    risk_score=0.5,
                    expected_information_gain=0.8,
                    recommended_action="verify",
                )
            )

        # Low confidence signal
        if claim.confidence < 0.5:
            signals.append(
                CuriositySignal(
                    signal_id=f"{claim.claim_id}_low_confidence",
                    claim_id=claim.claim_id,
                    signal_type="uncertainty",
                    domain=claim.domain,
                    novelty_score=0.2,
                    uncertainty_score=0.8,
                    value_score=0.5,
                    risk_score=0.4,
                    expected_information_gain=0.6,
                    recommended_action="experiment",
                )
            )

        return signals

    def _is_novel(self, claim: KnowledgeClaim) -> bool:
        """Check if claim appears novel/interesting."""
        # Heuristic: claims with few supporting sources are novel
        return len(claim.supporting_sources) <= 1

    def rank_learning_opportunities(
        self, signals: List[CuriositySignal]
    ) -> List[CuriositySignal]:
        """Rank curiosity signals by learning value."""
        # Score = (information_gain * value * uncertainty) / risk
        def score_signal(sig: CuriositySignal) -> float:
            if sig.risk_score == 0:
                sig.risk_score = 0.1  # Avoid division by zero
            return (
                sig.expected_information_gain
                * sig.value_score
                * (1 - sig.risk_score)
            ) / sig.risk_score

        return sorted(signals, key=score_signal, reverse=True)

    def create_learning_mission(
        self, signal: CuriositySignal, claim: KnowledgeClaim
    ) -> dict:
        """Create a learning mission from a curiosity signal."""
        return {
            "mission_id": f"mission_{signal.signal_id}",
            "claim_id": claim.claim_id,
            "signal_type": signal.signal_type,
            "objective": f"Investigate {signal.signal_type} in {claim.domain}",
            "action": signal.recommended_action,
            "priority": "high" if signal.expected_information_gain > 0.7 else "medium",
            "budget_estimate": "low" if signal.value_score < 0.5 else "medium",
        }
