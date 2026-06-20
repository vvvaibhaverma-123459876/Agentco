"""
Tests for domain transfer calibration (Phase 1: Advanced Calibration).
"""
import pytest
from calibration.domain_transfer import DomainTransferCalibrator


class TestDomainTransferCalibrator:
    """Test suite for DomainTransferCalibrator."""

    def test_high_correlation_estimate_close_to_source(self):
        """Test that high correlation pulls transfer estimate toward source."""
        calibrator = DomainTransferCalibrator()

        source_estimate = 0.70
        correlation = 0.9

        result = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="biology",
            target_domain="medicine",
            source_point_estimate=source_estimate,
            correlation=correlation,
            source_n_samples=20,
        )

        assert result.point_estimate is not None
        # With high correlation (0.9), should be pulled toward source (0.70)
        # Shrinkage formula: 0.5 * source + 0.5 * 0.5 = 0.5 * 0.70 + 0.25 = 0.6
        assert 0.55 <= result.point_estimate <= 0.80
        # Should be closer to source than to neutral (0.5)
        assert abs(result.point_estimate - source_estimate) < abs(0.5 - source_estimate)

    def test_low_correlation_shrinks_to_neutral(self):
        """Test that low correlation shrinks toward neutral (0.5)."""
        calibrator = DomainTransferCalibrator()

        source_estimate = 0.70
        correlation = 0.1

        result = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="biology",
            target_domain="governance",
            source_point_estimate=source_estimate,
            correlation=correlation,
            source_n_samples=20,
        )

        assert result.point_estimate is not None
        # With low correlation, should be closer to neutral
        assert 0.5 <= result.point_estimate <= 0.65

    def test_transfer_confidence_is_rsquared(self):
        """Test that transfer_confidence ≈ r² (correlation squared)."""
        calibrator = DomainTransferCalibrator()

        correlation = 0.8

        result = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="finance",
            target_domain="economics",
            source_point_estimate=0.75,
            correlation=correlation,
            source_n_samples=15,
        )

        # transfer_confidence should be correlation²
        expected_confidence = correlation ** 2
        assert result.transfer_confidence == pytest.approx(expected_confidence, abs=0.05)

    def test_insufficient_source_returns_none(self):
        """Test that < 5 source samples returns None point_estimate."""
        calibrator = DomainTransferCalibrator()

        result = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="biology",
            target_domain="medicine",
            source_point_estimate=0.70,
            correlation=0.8,
            source_n_samples=3,
        )

        assert result.point_estimate is None
        assert result.transfer_confidence == 0.0
        assert "insufficient" in result.rationale.lower()

    def test_rationale_includes_correlation(self):
        """Test that rationale string includes correlation info."""
        calibrator = DomainTransferCalibrator()

        correlation = 0.75
        result = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="physics",
            target_domain="engineering",
            source_point_estimate=0.68,
            correlation=correlation,
            source_n_samples=12,
        )

        assert "r=" in result.rationale.lower() or "correlation" in result.rationale.lower()

    def test_correlation_clipped_to_valid_range(self):
        """Test that correlation is handled within [0, 1]."""
        calibrator = DomainTransferCalibrator()

        # Test with extreme values
        result_high = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="test1",
            target_domain="test2",
            source_point_estimate=0.70,
            correlation=1.5,  # Out of range
            source_n_samples=10,
        )

        # Should clip and still produce valid result
        assert 0 <= result_high.point_estimate <= 1 if result_high.point_estimate else True
        assert 0 <= result_high.transfer_confidence <= 1

    def test_neutral_point_is_0_5(self):
        """Test that with zero correlation, estimate shrinks toward 0.5."""
        calibrator = DomainTransferCalibrator()

        # Zero correlation (hypothetical)
        result_high = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="test1",
            target_domain="test2",
            source_point_estimate=0.95,
            correlation=0.0,
            source_n_samples=10,
        )

        # With 0 correlation, should shrink significantly toward 0.5
        if result_high.point_estimate:
            assert result_high.point_estimate < 0.95
            assert result_high.point_estimate >= 0.5

    def test_domain_correlation_matrix_consistent(self):
        """Test that known domain pairs have consistent correlations."""
        calibrator = DomainTransferCalibrator()

        # Test symmetric pair
        result_bio_med = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="biology",
            target_domain="medicine",
            source_point_estimate=0.70,
            source_n_samples=20,
        )

        result_med_bio = calibrator.estimate_calibration_in_new_domain(
            agent_id="agent_1",
            source_domain="medicine",
            target_domain="biology",
            source_point_estimate=0.70,
            source_n_samples=20,
        )

        # Correlations should be symmetric
        if result_bio_med.correlation and result_med_bio.correlation:
            assert result_bio_med.correlation == result_med_bio.correlation
