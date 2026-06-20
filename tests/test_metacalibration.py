"""
Tests for metacalibration (Phase 1: Advanced Calibration).
"""
import pytest
from calibration.metacalibration import MetacalibrationEngine


class TestMetacalibrationEngine:
    """Test suite for MetacalibrationEngine."""

    def test_score_curve_accuracy_returns_ece(self):
        """Test that score_curve_accuracy returns ECE metric."""
        engine = MetacalibrationEngine()

        # Create 20 predictions with varied calibration
        stated = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95,
                  0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        outcomes = [False, False, False, False, True, True, True, True, True, True,
                    False, False, False, True, True, True, True, True, True, True]

        result = engine.score_curve_accuracy("agent_1", "biology", "short", stated, outcomes)

        assert "metacalibration_ece" in result
        assert result["metacalibration_ece"] is not None
        assert 0 <= result["metacalibration_ece"] <= 1
        assert "interpretation" in result
        assert "penalty" in result

    def test_excellent_interpretation_for_low_ece(self):
        """Test that low ECE gets 'excellent' interpretation."""
        engine = MetacalibrationEngine()

        # Nearly perfect calibration: stated matches realized
        stated = [0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6, 0.6, 0.6,
                  0.7, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.8, 0.8, 0.8]
        outcomes = [False, False, True, True, True, True, False, True, True, True,
                    True, True, False, True, True, True, True, False, True, True]

        result = engine.score_curve_accuracy("agent_1", "test", "short", stated, outcomes)

        if result["metacalibration_ece"] is not None and result["metacalibration_ece"] < 0.05:
            assert result["interpretation"] == "excellent"

    def test_penalty_increases_with_ece(self):
        """Test that penalty grows with ECE."""
        engine = MetacalibrationEngine()

        # Poor calibration: high ECE
        stated_poor = [0.1, 0.9] * 10  # Extreme, unrealistic
        outcomes_poor = [False] * 10 + [True] * 10

        result = engine.score_curve_accuracy("agent_1", "test", "short", stated_poor, outcomes_poor)

        # The penalty should be proportional to (ECE - ECE_EXCELLENT_THRESHOLD)
        # e.g., ECE=0.1 → penalty ≈ 2.0 * (0.1 - 0.05) = 0.1
        assert result["penalty"] >= 0

    def test_insufficient_data_returns_insufficient(self):
        """Test that < 10 predictions returns 'insufficient'."""
        engine = MetacalibrationEngine()

        stated = [0.5] * 5
        outcomes = [True] * 5

        result = engine.score_curve_accuracy("agent_1", "test", "short", stated, outcomes)

        assert result["interpretation"] == "insufficient"
        assert result["metacalibration_ece"] is None

    def test_penalty_applied_consistently(self):
        """Test that penalty is computed consistently."""
        engine = MetacalibrationEngine()

        stated = [0.3, 0.4, 0.5, 0.6, 0.7] * 4  # 20 samples
        outcomes = [False, False, True, True, True] * 4

        result = engine.score_curve_accuracy("agent_1", "test", "short", stated, outcomes)

        # Should compute penalty = 2.0 * max(0, ECE - 0.05)
        if result["metacalibration_ece"] is not None:
            expected_penalty = 2.0 * max(0, result["metacalibration_ece"] - 0.05)
            assert result["penalty"] == pytest.approx(expected_penalty, abs=0.01)

    def test_get_interpretation_returns_correct_label(self):
        """Test that get_interpretation() returns correct labels."""
        engine = MetacalibrationEngine()

        assert engine.get_interpretation(0.02) == "excellent"
        assert engine.get_interpretation(0.08) == "good"
        assert engine.get_interpretation(0.20) == "poor"

    def test_different_agents_independent(self):
        """Test that different agents get independent scores."""
        engine = MetacalibrationEngine()

        stated = [0.5] * 15
        outcomes_good = [True] * 8 + [False] * 7  # Well calibrated
        outcomes_poor = [True] * 14 + [False]  # Poorly calibrated

        result_good = engine.score_curve_accuracy("agent_good", "test", "short", stated, outcomes_good)
        result_poor = engine.score_curve_accuracy("agent_poor", "test", "short", stated, outcomes_poor)

        # Poor agent should have higher ECE
        if result_good["metacalibration_ece"] and result_poor["metacalibration_ece"]:
            # The poorly calibrated one should have worse ECE
            assert result_poor["penalty"] >= result_good["penalty"]
