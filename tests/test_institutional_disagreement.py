"""Tests for institutional disagreement (Phase 3)."""
import pytest
from calibration.institutional_disagreement import InstitutionalDisagreementAnalyzer


class TestInstitutionalDisagreement:
    """Test institutional-level analysis."""

    def test_institutional_vector_strong_consensus(self):
        """Test strong consensus detected."""
        analyzer = InstitutionalDisagreementAnalyzer()

        dept_scores = {
            "dept_a": [0.50, 0.51, 0.49],
            "dept_b": [0.52, 0.50, 0.51],
            "dept_c": [0.49, 0.50, 0.52],
        }

        vector = analyzer.compute_institutional_trust_vector("inst_1", dept_scores)

        assert vector.consensus_strength == "strong"
        assert vector.dissent_signal == "weak"
        assert 0.45 <= vector.point_estimate <= 0.55

    def test_institutional_vector_strong_dissent(self):
        """Test strong dissent detected."""
        analyzer = InstitutionalDisagreementAnalyzer()

        dept_scores = {
            "dept_a": [0.1, 0.05, 0.15],  # Mean 0.1
            "dept_b": [0.9, 0.95, 0.85],  # Mean 0.9
        }

        vector = analyzer.compute_institutional_trust_vector("inst_1", dept_scores)

        # Variance should be large (high disagreement)
        assert vector.variance > 0.1
        # Range should be wide
        assert vector.range[1] - vector.range[0] > 0.5

    def test_outlier_detection(self):
        """Test outlier departments identified."""
        analyzer = InstitutionalDisagreementAnalyzer()

        dept_scores = {
            "normal_a": [0.5, 0.5, 0.5],
            "normal_b": [0.50, 0.50, 0.50],
            "normal_c": [0.49, 0.51, 0.50],
            "outlier": [0.01, 0.01, 0.01],  # Extreme outlier (mean 0.01)
        }

        vector = analyzer.compute_institutional_trust_vector("inst_1", dept_scores)

        # Should detect at least one outlier dept
        assert len(vector.outlier_depts) >= 1 or vector.range[0] < 0.2

    def test_empty_dept_scores(self):
        """Test handling of empty scores."""
        analyzer = InstitutionalDisagreementAnalyzer()

        vector = analyzer.compute_institutional_trust_vector("inst_1", {})

        assert vector.point_estimate == 0.5
        assert vector.variance == 0.0

    def test_range_computed(self):
        """Test range is correct."""
        analyzer = InstitutionalDisagreementAnalyzer()

        dept_scores = {
            "low": [0.2, 0.25],
            "high": [0.8, 0.85],
        }

        vector = analyzer.compute_institutional_trust_vector("inst_1", dept_scores)

        assert vector.range[0] < vector.range[1]
        assert 0.2 <= vector.range[0] <= 0.3
        assert 0.8 <= vector.range[1] <= 0.85
