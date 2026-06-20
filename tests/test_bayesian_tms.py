"""Tests for Bayesian TMS (Phase 2)."""
import pytest
from calibration.bayesian_tms import ProbabilisticBeliefNode, Justification


class TestBayesianTMS:
    """Test Bayesian truth maintenance."""

    def test_bayesian_update_with_strong_evidence(self):
        """Test Bayesian update increases belief."""
        node = ProbabilisticBeliefNode("claim_1")
        assert node.degree_of_belief == 0.5

        just = Justification("just_1", "claim_1", strength=0.9, justification_type="evidential")
        node.add_justification(just)

        posterior = node.update_from_justifications({})
        assert posterior > 0.5
        assert 0 <= posterior <= 1

    def test_conditional_justification_voiding(self):
        """Test conditional justification becomes invalid."""
        node = ProbabilisticBeliefNode("claim_1")
        cond_just = Justification(
            "just_cond", "claim_1", strength=0.8,
            is_conditional=True, condition="prerequisite_claim"
        )
        node.add_justification(cond_just)

        # Prerequisite not met
        posterior = node.update_from_justifications({"prerequisite_claim": 0.2})
        assert posterior == 0.5  # Falls back to prior

        # Prerequisite met
        posterior = node.update_from_justifications({"prerequisite_claim": 0.8})
        assert posterior > 0.5

    def test_sensitivity_analysis(self):
        """Test sensitivity to removal of justification."""
        node = ProbabilisticBeliefNode("claim_1")
        just1 = Justification("just_1", "claim_1", strength=0.8)
        just2 = Justification("just_2", "claim_1", strength=0.9)
        node.add_justification(just1)
        node.add_justification(just2)

        node.update_from_justifications({})
        original = node.degree_of_belief

        sensitivity = node.sensitivity_analysis("just_1", {})
        assert sensitivity >= 0

    def test_belief_history_tracked(self):
        """Test belief history is maintained."""
        node = ProbabilisticBeliefNode("claim_1")
        just = Justification("just_1", "claim_1", strength=0.7)
        node.add_justification(just)

        node.update_from_justifications({})
        assert len(node.history) > 0
        assert node.history[0][1] == node.degree_of_belief

    def test_multiple_justifications_combined(self):
        """Test multiple justifications combine via Bayes rule."""
        node = ProbabilisticBeliefNode("claim_1")
        just1 = Justification("just_1", "claim_1", strength=0.6)
        just2 = Justification("just_2", "claim_1", strength=0.7)
        node.add_justification(just1)
        node.add_justification(just2)

        posterior = node.update_from_justifications({})
        assert posterior > 0.5
        assert 0 <= posterior <= 1
