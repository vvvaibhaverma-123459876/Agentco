"""Tests for multidimensional trust (Phase 3)."""
import pytest
from calibration.multidimensional_trust import MultidimensionalTrust


class TestMultidimensionalTrust:
    """Test 4D trust model."""

    def test_context_technical_weights_competence(self):
        """Test technical context weights competence."""
        trust = MultidimensionalTrust(
            competence=0.9,
            reliability=0.3,
            integrity=0.3,
            benevolence=0.3,
        )
        technical = trust.overall_trust("technical")
        general = trust.overall_trust("general")

        # Technical should be higher (comp weighted 0.6)
        assert technical > general

    def test_context_ethical_weights_integrity(self):
        """Test ethical context weights integrity."""
        trust = MultidimensionalTrust(
            competence=0.3,
            reliability=0.3,
            integrity=0.9,
            benevolence=0.9,
        )
        ethical = trust.overall_trust("ethical")
        technical = trust.overall_trust("technical")

        # Ethical should be higher (int+ben weighted)
        assert ethical > technical

    def test_context_financial_weights_reliability(self):
        """Test financial context weights reliability."""
        trust = MultidimensionalTrust(
            competence=0.3,
            reliability=0.9,
            integrity=0.3,
            benevolence=0.3,
        )
        financial = trust.overall_trust("financial")
        ethical = trust.overall_trust("ethical")

        # Financial should be higher (rel weighted 0.6)
        assert financial > ethical

    def test_values_clipped_to_01(self):
        """Test values are clipped to [0, 1]."""
        trust = MultidimensionalTrust(
            competence=1.5,
            reliability=-0.5,
            integrity=0.5,
            benevolence=0.5,
        )
        assert 0 <= trust.competence <= 1
        assert 0 <= trust.reliability <= 1

    def test_overall_trust_in_valid_range(self):
        """Test overall trust is in [0, 1]."""
        trust = MultidimensionalTrust(0.3, 0.4, 0.5, 0.6)
        for context in ["technical", "ethical", "financial", "general"]:
            score = trust.overall_trust(context)
            assert 0 <= score <= 1

    def test_get_profile_returns_dict(self):
        """Test profile export."""
        trust = MultidimensionalTrust(0.6, 0.7, 0.8, 0.5)
        profile = trust.get_profile()

        assert profile["competence"] == 0.6
        assert profile["reliability"] == 0.7
        assert profile["integrity"] == 0.8
        assert profile["benevolence"] == 0.5
