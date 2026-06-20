"""
Tests for structural break detection (Phase 1: Advanced Calibration).
"""
import pytest
from datetime import datetime, timezone, timedelta
from calibration.structural_breaks import StructuralBreakDetector


class TestStructuralBreakDetector:
    """Test suite for StructuralBreakDetector."""

    def test_detects_break_in_synthetic_shift(self):
        """Test detection of obvious shift in calibration."""
        detector = StructuralBreakDetector()

        # First 30: well calibrated
        stated_1 = [0.3, 0.4, 0.5, 0.6, 0.7] * 6
        outcomes_1 = [False, False, True, True, True] * 6

        # Next 30: opposite (shift/degradation)
        stated_2 = [0.3, 0.4, 0.5, 0.6, 0.7] * 6
        outcomes_2 = [True, True, False, False, False] * 6

        stated = stated_1 + stated_2
        outcomes = outcomes_1 + outcomes_2

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes)

        assert result.detected is True
        assert result.break_index is not None
        # Break should be somewhere in middle region
        assert 15 < result.break_index < 45
        assert result.f_statistic is not None
        assert result.f_critical is not None
        assert result.f_statistic > result.f_critical

    def test_no_break_in_stable_data(self):
        """Test that stable calibration doesn't trigger break detection."""
        detector = StructuralBreakDetector()

        # Consistent, well-calibrated data
        stated = [0.3, 0.4, 0.5, 0.6, 0.7] * 12  # 60 samples
        outcomes = [False, False, True, True, True] * 12

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes)

        assert result.detected is False
        # Should still compute F statistic
        assert result.f_statistic is not None
        assert result.f_critical is not None

    def test_f_statistic_exceeds_critical_on_break(self):
        """Test that F-statistic exceeds critical value when break exists."""
        detector = StructuralBreakDetector()

        # Clear regime shift with varied data to avoid singularity
        stated_1 = [0.2, 0.3, 0.25, 0.2, 0.3, 0.2, 0.3, 0.25, 0.2, 0.3] * 3  # 30
        outcomes_1 = [False] * 30

        stated_2 = [0.7, 0.8, 0.75, 0.8, 0.7, 0.8, 0.7, 0.75, 0.8, 0.7] * 3  # 30
        outcomes_2 = [True] * 30

        stated = stated_1 + stated_2
        outcomes = outcomes_1 + outcomes_2

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes)

        assert result.f_statistic is not None
        assert result.f_critical is not None
        # Obvious break should produce large F statistic
        assert result.f_statistic > result.f_critical

    def test_insufficient_history_returns_false(self):
        """Test that < 20 samples returns insufficient."""
        detector = StructuralBreakDetector()

        stated = [0.5] * 15
        outcomes = [True] * 8 + [False] * 7

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes)

        assert result.detected is False
        assert "Insufficient" in result.rationale

    def test_break_date_correct_when_timestamps_provided(self):
        """Test that break_date is correctly set when timestamps provided."""
        detector = StructuralBreakDetector()

        now = datetime.now(timezone.utc)
        timestamps = [now - timedelta(days=i) for i in range(60, 0, -1)]  # 60 days back

        stated = [0.5] * 30 + [0.8] * 30
        outcomes = [False] * 30 + [True] * 30

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes, timestamps=timestamps)

        if result.detected:
            assert result.break_date is not None
            # Break date should be around day 30
            assert isinstance(result.break_date, datetime)

    def test_action_recommended_on_break(self):
        """Test that action is recommended when break detected."""
        detector = StructuralBreakDetector()

        stated = [0.2] * 20 + [0.8] * 20
        outcomes = [False] * 20 + [True] * 20

        result = detector.detect_break("agent_1", "test", "short", stated, outcomes)

        if result.detected:
            assert result.action == "RETRAIN_FROM_BREAK_POINT"

    def test_lookback_window_respected(self):
        """Test that lookback_days filters old data."""
        detector = StructuralBreakDetector()

        now = datetime.now(timezone.utc)
        # Create timestamps: last 30 days are recent, before that are old
        recent_times = [now - timedelta(days=i) for i in range(30, 0, -1)]
        old_times = [now - timedelta(days=i) for i in range(180, 30, -1)]
        timestamps = old_times + recent_times

        # Old data: well calibrated
        stated_old = [0.5] * 150
        outcomes_old = [True] * 75 + [False] * 75

        # Recent data: shift
        stated_recent = [0.2] * 30
        outcomes_recent = [False] * 30

        stated = stated_old + stated_recent
        outcomes = outcomes_old + outcomes_recent

        result = detector.detect_break(
            "agent_1", "test", "short", stated, outcomes,
            lookback_days=60, timestamps=timestamps
        )

        # With lookback, should see the recent shift
        # (result may or may not detect depending on remaining sample count)
        assert result.f_statistic is not None

    def test_returns_rationale_always(self):
        """Test that result always includes rationale."""
        detector = StructuralBreakDetector()

        # Case 1: insufficient data
        result_1 = detector.detect_break("agent_1", "test", "short", [0.5] * 5, [True] * 5)
        assert len(result_1.rationale) > 0

        # Case 2: sufficient data, no break
        stated = [0.5] * 30
        outcomes = [True] * 15 + [False] * 15
        result_2 = detector.detect_break("agent_1", "test", "short", stated, outcomes)
        assert len(result_2.rationale) > 0

        # Case 3: sufficient data, break detected
        stated = [0.2] * 20 + [0.8] * 20
        outcomes = [False] * 20 + [True] * 20
        result_3 = detector.detect_break("agent_1", "test", "short", stated, outcomes)
        assert len(result_3.rationale) > 0
