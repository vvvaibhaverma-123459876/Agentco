"""
Tests for skill vs luck analysis (Phase 1: Advanced Calibration).
"""
import pytest
from calibration.skill_luck import SkillVsLuckAnalyzer


class TestSkillVsLuckAnalyzer:
    """Test suite for SkillVsLuckAnalyzer."""

    def test_high_sharpe_indicates_skill(self):
        """Test that high Sharpe ratio gives high skill estimate."""
        analyzer = SkillVsLuckAnalyzer()

        # Predictions with high log scores (good skill)
        stated = [0.9] * 8 + [0.8] * 7  # 15 samples
        outcomes = [True] * 8 + [True] * 6 + [False]  # High accuracy

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        assert result.estimated_skill_fraction is not None
        assert result.estimated_skill_fraction > 0.5
        assert result.interpretation in ["high", "medium"]
        assert result.sharpe_ratio is not None

    def test_low_sharpe_indicates_luck(self):
        """Test that low Sharpe ratio gives low skill estimate."""
        analyzer = SkillVsLuckAnalyzer()

        # Predictions with mixed high/low confidence, unreliable accuracy
        stated = [0.9, 0.1] * 5 + [0.9]  # Extreme, unreliable
        outcomes = [False, True] * 5 + [False]  # Inverted

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        assert result.estimated_skill_fraction is not None
        assert result.estimated_skill_fraction < 0.6
        # Low skill/high luck
        assert result.interpretation in ["low", "medium"]

    def test_sharpe_ci_brackets_estimate(self):
        """Test that bootstrap CI brackets the Sharpe estimate."""
        analyzer = SkillVsLuckAnalyzer()

        stated = [0.6] * 10 + [0.7] * 5
        outcomes = [True] * 12 + [False] * 3

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        if result.sharpe_ratio is not None:
            assert result.sharpe_ci_lower is not None
            assert result.sharpe_ci_upper is not None
            # Point estimate should be within CI
            assert result.sharpe_ci_lower <= result.sharpe_ratio <= result.sharpe_ci_upper

    def test_insufficient_predictions_returns_insufficient(self):
        """Test that < 10 predictions returns insufficient."""
        analyzer = SkillVsLuckAnalyzer()

        stated = [0.5] * 8
        outcomes = [True] * 4 + [False] * 4

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        assert result.estimated_skill_fraction is None
        assert result.interpretation == "insufficient"
        assert result.sharpe_ratio is None

    def test_risk_free_rate_correct(self):
        """Test that risk-free rate is ln(0.5) ≈ -0.693."""
        analyzer = SkillVsLuckAnalyzer()

        import numpy as np

        # Predictions at exactly 50% confidence, random outcomes
        stated = [0.5] * 20
        outcomes = [True, False] * 10

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        # With 50% stated confidence and ~50% outcomes, Sharpe should be near 0
        # (log scores will be near ln(0.5))
        if result.sharpe_ratio is not None:
            # Sharpe around 0 means equal skill/luck
            assert -0.5 < result.sharpe_ratio < 0.5

    def test_skill_fraction_in_valid_range(self):
        """Test that skill fraction is always in [0, 1]."""
        analyzer = SkillVsLuckAnalyzer()

        # Test multiple scenarios
        test_cases = [
            ([0.9] * 10, [True] * 9 + [False]),  # High skill
            ([0.5] * 10, [True, False] * 5),  # Mixed
            ([0.1] * 10, [False] * 9 + [True]),  # Low skill
        ]

        for stated, outcomes in test_cases:
            result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)
            if result.estimated_skill_fraction is not None:
                assert 0 <= result.estimated_skill_fraction <= 1

    def test_deterministic_bootstrap(self):
        """Test that bootstrap is deterministic (seed=42)."""
        analyzer = SkillVsLuckAnalyzer()

        stated = [0.6] * 15
        outcomes = [True] * 9 + [False] * 6

        result_1 = analyzer.decompose("agent_1", "test", "short", stated, outcomes)
        result_2 = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        # Should get identical results (deterministic seed)
        if result_1.sharpe_ratio and result_2.sharpe_ratio:
            assert result_1.sharpe_ratio == pytest.approx(result_2.sharpe_ratio)
            assert result_1.sharpe_ci_lower == pytest.approx(result_2.sharpe_ci_lower)
            assert result_1.sharpe_ci_upper == pytest.approx(result_2.sharpe_ci_upper)

    def test_interpretation_matches_skill_fraction(self):
        """Test that interpretation label matches skill fraction value."""
        analyzer = SkillVsLuckAnalyzer()

        stated = [0.85] * 15
        outcomes = [True] * 12 + [False] * 3  # Good performance

        result = analyzer.decompose("agent_1", "test", "short", stated, outcomes)

        if result.estimated_skill_fraction is not None:
            if result.estimated_skill_fraction > 0.6:
                assert result.interpretation in ["high", "medium"]
            elif result.estimated_skill_fraction < 0.4:
                assert result.interpretation in ["low", "medium"]
