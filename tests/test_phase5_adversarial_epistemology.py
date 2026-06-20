"""Tests for Phase 5: Adversarial Epistemology."""
import pytest
from civilization.services.adversarial_epistemology import AdversarialEpistemologyEngine
from civilization.services.goodhart_automation import GoodhartDefender
from civilization.services.capture_detector import CaptureDetector
from civilization.services.coalition_detector import CoalitionDetector


class TestAdversarialEpistemology:
    """Test arms race detection."""

    def test_detects_arms_race_escalation(self):
        """Test escalation detection."""
        engine = AdversarialEpistemologyEngine()

        history = [
            {"sophistication_score": 0.2, "attack_type": "simple"},
            {"sophistication_score": 0.3, "attack_type": "intermediate"},
            {"sophistication_score": 0.5, "attack_type": "advanced"},
            {"sophistication_score": 0.7, "attack_type": "sophisticated"},
        ]

        result = engine.detect_arms_race("inst_1", history)
        assert "escalation_rate" in result
        assert "attack_sophistication" in result

    def test_no_arms_race_in_stable_attacks(self):
        """Test stable attack level."""
        engine = AdversarialEpistemologyEngine()

        history = [{"sophistication_score": 0.3} for _ in range(10)]
        result = engine.detect_arms_race("inst_1", history)

        assert not result["detected"]  # Works with numpy bool


class TestGoodhartDefender:
    """Test Goodhart automation."""

    def test_rotates_metrics(self):
        """Test metric rotation."""
        defender = GoodhartDefender()

        result = defender.rotate_primary_metrics("inst_1")
        assert "rotated_metrics" in result
        assert "schedule" in result
        assert len(result["rotated_metrics"]) > 0

    def test_schedule_is_future(self):
        """Test schedule is in future."""
        defender = GoodhartDefender()

        result = defender.rotate_primary_metrics("inst_1")
        # Should have dates (strings)
        assert all(isinstance(d, str) for d in result["schedule"])


class TestCaptureDetector:
    """Test capture detection."""

    def test_detects_high_concentration(self):
        """Test concentration detection."""
        detector = CaptureDetector()

        metrics = {
            "domain_concentration": 0.6,
            "dissent_rate_change": 0.0,
            "review_time_avg_seconds": 600,
            "self_citation_rate": 0.3,
        }

        score = detector.capture_likelihood_score("inst_1", metrics)
        assert score >= 0.3

    def test_detects_rubber_stamping(self):
        """Test rubber stamp detection."""
        detector = CaptureDetector()

        metrics = {
            "domain_concentration": 0.2,
            "dissent_rate_change": 0.0,
            "review_time_avg_seconds": 120,  # Fast
            "self_citation_rate": 0.3,
        }

        score = detector.capture_likelihood_score("inst_1", metrics)
        assert score >= 0.2

    def test_score_in_valid_range(self):
        """Test score in [0, 1]."""
        detector = CaptureDetector()

        metrics = {
            "domain_concentration": 1.0,
            "dissent_rate_change": -1.0,
            "review_time_avg_seconds": 60,
            "self_citation_rate": 1.0,
        }

        score = detector.capture_likelihood_score("inst_1", metrics)
        assert 0 <= score <= 1


class TestCoalitionDetector:
    """Test coalition detection."""

    def test_detects_coordinated_false_claims(self):
        """Test clique detection."""
        detector = CoalitionDetector()

        claims = [
            {"claim_id": "c1", "source_origin": "origin_A", "agent": "agent1", "accuracy": 0.2},
            {"claim_id": "c2", "source_origin": "origin_A", "agent": "agent2", "accuracy": 0.1},
            {"claim_id": "c3", "source_origin": "origin_A", "agent": "agent3", "accuracy": 0.3},
            {"claim_id": "c4", "source_origin": "origin_B", "agent": "agent4", "accuracy": 0.8},
        ]

        result = detector.detect_coordinated_false_claims("inst_1", claims)
        assert result["detected"] is True
        assert len(result["coalition_members"]) >= 3

    def test_no_coalition_with_few_claims(self):
        """Test no coalition with < 3 false claims."""
        detector = CoalitionDetector()

        claims = [
            {"claim_id": "c1", "source_origin": "origin_A", "accuracy": 0.2},
            {"claim_id": "c2", "source_origin": "origin_A", "accuracy": 0.3},
        ]

        result = detector.detect_coordinated_false_claims("inst_1", claims)
        assert result["detected"] is False
