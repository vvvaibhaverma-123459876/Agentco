"""Tests for Byzantine aggregation (Phase 3)."""
import pytest
from calibration.byzantine_aggregation import ByzantineAggregator


class TestByzantineAggregation:
    """Test Byzantine-robust aggregation."""

    def test_robust_mean_removes_extremes(self):
        """Test robust mean trims outliers."""
        agg = ByzantineAggregator()

        values = [0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0, 1.0]  # Extreme outliers at ends
        # With k=1: removes 0.0 and 1.0, averages rest
        result = agg.robust_mean(values, k_outliers=1)

        # Robust mean should be reasonable
        assert 0.2 <= result <= 0.8
        assert 0 <= result <= 1

    def test_detect_adversarial_votes_finds_outliers(self):
        """Test outlier detection."""
        agg = ByzantineAggregator()

        values = [0.5, 0.51, 0.49, 0.50, 0.99]  # 4 normal, 1 extreme outlier
        outliers = agg.detect_adversarial_votes(values, threshold=3.0)

        assert len(outliers) > 0
        assert 4 in outliers  # Index 4 is the outlier

    def test_no_outliers_in_consistent_values(self):
        """Test no outliers in consistent data."""
        agg = ByzantineAggregator()

        values = [0.5, 0.51, 0.49, 0.50, 0.52]  # All similar
        outliers = agg.detect_adversarial_votes(values, threshold=3.0)

        assert len(outliers) == 0

    def test_robust_mean_with_insufficient_samples(self):
        """Test robust mean falls back with few samples."""
        agg = ByzantineAggregator()

        values = [0.3, 0.7]
        result = agg.robust_mean(values, k_outliers=2)  # k_outliers >= len

        # Should return regular mean
        assert result == 0.5

    def test_detect_adversarial_empty_input(self):
        """Test detection with empty input."""
        agg = ByzantineAggregator()

        outliers = agg.detect_adversarial_votes([], threshold=3.0)
        assert len(outliers) == 0

    def test_detect_adversarial_high_threshold(self):
        """Test high threshold requires extreme outliers."""
        agg = ByzantineAggregator()

        values = [0.5, 0.5, 0.5, 0.6]  # Mild outlier
        outliers = agg.detect_adversarial_votes(values, threshold=10.0)

        # High threshold: no detection
        assert len(outliers) == 0
