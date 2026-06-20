"""
Hypothesis Engine — Convert learning into testable hypotheses.

Creates pre-registered hypotheses that can be tested and resolved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid

from .knowledge_claim import KnowledgeClaim, ClaimType


@dataclass
class Hypothesis:
    """A testable claim derived from learning."""

    hypothesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_claim_ids: List[str] = field(default_factory=list)
    hypothesis_text: str = ""
    domain: str = ""
    confidence: float = 0.5
    uncertainty: float = 0.5
    testability: str = "medium"  # high|medium|low|untestable
    expected_value: float = 0.5
    risk_level: str = "low"
    proposed_test: Optional[str] = None
    resolution_criteria: Optional[str] = None
    horizon: Optional[str] = None  # short|medium|long
    status: str = "proposed"  # proposed|registered|tested|resolved|rejected
    linked_prediction_id: Optional[str] = None
    linked_experiment_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class HypothesisEngine:
    """Engine for generating and managing hypotheses."""

    def generate_hypotheses_from_claims(
        self, claims: List[KnowledgeClaim]
    ) -> List[Hypothesis]:
        """Generate hypotheses from extracted claims."""
        hypotheses = []

        for claim in claims:
            if claim.claim_type == ClaimType.ANALOGY:
                # Analogies become transfer hypotheses
                hyp = Hypothesis(
                    source_claim_ids=[claim.claim_id],
                    hypothesis_text=f"Transfer principle from {claim.domain}: {claim.claim_text}",
                    domain=claim.domain,
                    testability="medium",
                    proposed_test="Test transfer in target domain",
                    status="proposed",
                )
                hypotheses.append(hyp)

            elif claim.testability in ["high", "medium"]:
                # Testable empirical claims become prediction hypotheses
                hyp = Hypothesis(
                    source_claim_ids=[claim.claim_id],
                    hypothesis_text=claim.normalized_claim,
                    domain=claim.domain,
                    confidence=claim.confidence,
                    uncertainty=claim.uncertainty or 0.5,
                    testability=claim.testability,
                    proposed_test=f"Test: {claim.claim_text}",
                    resolution_criteria=claim.resolution_criteria,
                    status="proposed",
                )
                hypotheses.append(hyp)

        return hypotheses

    def pre_register_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        """Pre-register a hypothesis before running tests."""
        hypothesis.status = "registered"
        hypothesis.updated_at = datetime.utcnow()
        return hypothesis

    def create_test_plan(self, hypothesis: Hypothesis) -> dict:
        """Create a test plan for a hypothesis."""
        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "test_type": self._determine_test_type(hypothesis),
            "estimated_duration": "days" if hypothesis.testability == "high" else "weeks",
            "required_data": "existing" if hypothesis.risk_level == "low" else "experimental",
            "success_criteria": hypothesis.resolution_criteria or "Hypothesis is supported by evidence",
        }

    def _determine_test_type(self, hypothesis: Hypothesis) -> str:
        """Determine appropriate test method."""
        if "transfer" in hypothesis.hypothesis_text.lower():
            return "cross_domain_test"
        elif "principle" in hypothesis.hypothesis_text.lower():
            return "replication_test"
        else:
            return "hypothesis_test"

    def mark_hypothesis_resolved(
        self, hypothesis: Hypothesis, outcome: bool, confidence: float
    ) -> Hypothesis:
        """Mark hypothesis as resolved with outcome."""
        hypothesis.status = "resolved"
        hypothesis.confidence = confidence if outcome else 1.0 - confidence
        hypothesis.updated_at = datetime.utcnow()
        return hypothesis
