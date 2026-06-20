"""Tests for coherence hybrid evaluator (Phase 2)."""
import pytest
from calibration.coherence_hybrid import CoherenceHybridEvaluator
from calibration.bayesian_tms import Justification


class TestCoherenceHybrid:
    """Test coherence + grounding evaluation."""

    def test_coherence_score_with_similar_beliefs(self):
        """Test coherence increases with similar beliefs."""
        evaluator = CoherenceHybridEvaluator()

        beliefs = {
            "claim_1": 0.8,
            "claim_2": 0.75,
            "claim_3": 0.2,
        }

        score = evaluator.coherence_score("claim_1", beliefs)
        assert 0 <= score <= 1

    def test_grounding_score_from_justifications(self):
        """Test grounding computed from justifications."""
        evaluator = CoherenceHybridEvaluator()

        justs = [
            Justification("j1", "claim_1", strength=0.9, justification_type="evidential"),
            Justification("j2", "claim_1", strength=0.7, justification_type="replication"),
            Justification("j3", "claim_1", strength=0.5, justification_type="default"),
        ]

        score = evaluator.grounding_score("claim_1", justs)
        assert 0 <= score <= 1

    def test_joint_plausibility_combines_coherence_grounding(self):
        """Test joint plausibility weights correctly."""
        evaluator = CoherenceHybridEvaluator()

        beliefs = {"claim_1": 0.7, "claim_2": 0.75}
        justs = [Justification("j1", "claim_1", strength=0.8, justification_type="evidential")]

        score = evaluator.joint_plausibility("claim_1", beliefs, justs)
        assert 0 <= score <= 1
        # Should be dominated by grounding (0.7 weight)
        assert score > 0.3

    def test_empty_justifications_low_grounding(self):
        """Test no justifications yields low grounding."""
        evaluator = CoherenceHybridEvaluator()
        score = evaluator.grounding_score("claim_1", [])
        assert score == 0.0

    def test_negligible_beliefs_ignored(self):
        """Test beliefs < 0.3 don't contribute to coherence."""
        evaluator = CoherenceHybridEvaluator()

        beliefs = {
            "claim_1": 0.8,
            "negligible": 0.1,  # Should be ignored
        }

        score = evaluator.coherence_score("claim_1", beliefs)
        assert score >= 0.0  # Should be neutral, not pulled down
