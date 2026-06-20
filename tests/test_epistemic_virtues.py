"""Tests for epistemic virtues (Phase 2)."""
import pytest
from calibration.epistemic_virtues import EpistemicVirtueTracker


class TestEpistemicVirtues:
    """Test virtue tracking."""

    def test_honesty_detects_overconfidence(self):
        """Test honesty penalizes overconfidence."""
        tracker = EpistemicVirtueTracker()

        # Agent 1: honest
        preds_honest = [
            {"stated_confidence": 0.7, "curve_prediction": 0.7},
            {"stated_confidence": 0.6, "curve_prediction": 0.6},
        ]

        # Agent 2: overconfident
        preds_over = [
            {"stated_confidence": 0.9, "curve_prediction": 0.6},
            {"stated_confidence": 0.8, "curve_prediction": 0.5},
        ]

        score_honest = tracker.honesty_score("agent_1", preds_honest)
        score_over = tracker.honesty_score("agent_2", preds_over)

        # Overconfident should have lower (more negative) score
        assert score_honest > score_over

    def test_humility_rewards_dispersion(self):
        """Test humility increases with confidence dispersion."""
        tracker = EpistemicVirtueTracker()

        # Conservative: varied confidences
        preds_varied = [
            {"stated_confidence": 0.3},
            {"stated_confidence": 0.7},
            {"stated_confidence": 0.5},
        ]

        # Extreme: all high confidences
        preds_extreme = [
            {"stated_confidence": 0.95},
            {"stated_confidence": 0.90},
            {"stated_confidence": 0.92},
        ]

        score_varied = tracker.intellectual_humility_score("agent_1", preds_varied)
        score_extreme = tracker.intellectual_humility_score("agent_2", preds_extreme)

        assert score_varied > score_extreme

    def test_courage_returns_neutral(self):
        """Test courage returns reasonable value."""
        tracker = EpistemicVirtueTracker()

        updates = [{"belief_change": 0.1}, {"belief_change": 0.2}]
        score = tracker.intellectual_courage_score("agent_1", updates)

        assert 0 <= score <= 1

    def test_scores_in_valid_range(self):
        """Test all scores are in [0, 1] or unbounded negative."""
        tracker = EpistemicVirtueTracker()

        preds = [
            {"stated_confidence": 0.5, "curve_prediction": 0.5, "outcome": 0.5},
        ]

        honesty = tracker.honesty_score("agent_1", preds)
        humility = tracker.intellectual_humility_score("agent_1", preds)
        courage = tracker.intellectual_courage_score("agent_1", [])

        assert honesty <= 0  # Honesty is non-positive
        assert 0 <= humility <= 1
        assert 0 <= courage <= 1
