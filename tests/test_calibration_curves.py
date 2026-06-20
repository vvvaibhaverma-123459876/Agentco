"""
Tests for calibration curves (Phase 1: Advanced Calibration).
"""
import pytest
from calibration.calibration_curves import CalibratedTrustCurve, CalibrationResult


class TestCalibratedTrustCurve:
    """Test suite for CalibratedTrustCurve."""

    def test_isotonic_regression_fits_data(self):
        """Test that isotonic regression fits and queries data."""
        curve = CalibratedTrustCurve("agent_1", "biology", "short")

        # Add 6 predictions (>= 5 and divisible by 3)
        predictions = [
            (0.85, True),
            (0.80, False),
            (0.55, True),
            (0.90, False),
            (0.60, True),
            (0.75, True),
        ]
        for stated, outcome in predictions:
            curve.update_from_resolution(stated, outcome)

        # Query confidence
        result = curve.trusted_confidence(0.85)

        assert isinstance(result, CalibrationResult)
        assert 0 <= result.point_estimate <= 1
        assert 0 <= result.lower_ci <= 1
        assert 0 <= result.upper_ci <= 1
        assert 0 <= result.confidence <= 1
        assert result.lower_ci <= result.point_estimate <= result.upper_ci
        assert result.n_samples == 6

    def test_insufficient_samples_returns_conservative(self):
        """Test conservative estimate when samples < 5."""
        curve = CalibratedTrustCurve("agent_1", "biology", "short")

        # Add only 3 predictions
        curve.update_from_resolution(0.85, True)
        curve.update_from_resolution(0.80, False)
        curve.update_from_resolution(0.70, True)

        result = curve.trusted_confidence(0.85)

        assert result.n_samples == 3
        assert result.point_estimate == pytest.approx(0.85 * 0.8, abs=0.01)
        # CI should be wide
        ci_width = result.upper_ci - result.lower_ci
        assert ci_width > 0.2

    def test_refitting_only_on_multiples(self):
        """Test that refitting only happens when n % 3 == 0 and n >= 5."""
        curve = CalibratedTrustCurve("agent_1", "biology", "short")

        # Add predictions one by one
        for i in range(10):
            result = curve.update_from_resolution(0.5 + 0.05 * i, i % 2 == 0)
            if (i + 1) == 6:
                # After 6 samples (>= 5 and % 3 == 0), should refit
                assert result["refitted"] is True
            elif (i + 1) == 9:
                # After 9 samples (>= 5 and % 3 == 0), should refit
                assert result["refitted"] is True
            else:
                # Other points should not trigger refit
                assert result["refitted"] is False

    def test_ci_bands_narrow_with_more_samples(self):
        """Test that confidence intervals narrow with more samples."""
        curve = CalibratedTrustCurve("agent_1", "finance", "medium")

        # Add 6 samples
        for i in range(6):
            curve.update_from_resolution(0.6, i % 2 == 0)
        result_6 = curve.trusted_confidence(0.6)
        width_6 = result_6.upper_ci - result_6.lower_ci

        # Add 12 more samples (total 18)
        for i in range(12):
            curve.update_from_resolution(0.6, i % 2 == 0)
        result_18 = curve.trusted_confidence(0.6)
        width_18 = result_18.upper_ci - result_18.lower_ci

        # CI should be narrower with more samples
        assert width_18 <= width_6

    def test_clipping_returns_valid_probabilities(self):
        """Test that extreme inputs are clipped to [0, 1]."""
        curve = CalibratedTrustCurve("agent_1", "general", "long")

        # Add baseline data
        for i in range(6):
            curve.update_from_resolution(0.5, i % 2 == 0)

        # Query extreme values
        result_low = curve.trusted_confidence(-0.5)
        result_high = curve.trusted_confidence(1.5)

        assert 0 <= result_low.point_estimate <= 1
        assert 0 <= result_low.lower_ci <= 1
        assert 0 <= result_low.upper_ci <= 1
        assert 0 <= result_high.point_estimate <= 1
        assert 0 <= result_high.lower_ci <= 1
        assert 0 <= result_high.upper_ci <= 1

    def test_monotonic_confidence_levels(self):
        """Test that higher stated confidence generally yields higher estimates."""
        curve = CalibratedTrustCurve("agent_1", "biology", "short")

        # Add diverse data
        data = [
            (0.1, False), (0.2, False), (0.3, False),
            (0.5, True), (0.5, False),
            (0.8, True), (0.9, True),
        ]
        for stated, outcome in data:
            curve.update_from_resolution(stated, outcome)

        # Query at different levels
        result_low = curve.trusted_confidence(0.3)
        result_mid = curve.trusted_confidence(0.5)
        result_high = curve.trusted_confidence(0.8)

        # Should trend upward
        assert result_mid.point_estimate >= result_low.point_estimate
        assert result_high.point_estimate >= result_mid.point_estimate

    def test_get_state_returns_metadata(self):
        """Test that get_state() returns current state info."""
        curve = CalibratedTrustCurve("agent_1", "test_domain", "long")

        # Add data and trigger refit
        for i in range(6):
            curve.update_from_resolution(0.5, i % 2 == 0)

        state = curve.get_state()

        assert state["agent_id"] == "agent_1"
        assert state["domain"] == "test_domain"
        assert state["horizon"] == "long"
        assert state["n_samples"] == 6
        assert state["fitted"] is True
        assert state["n_fits"] >= 1
        assert state["last_fitted_at"] is not None
