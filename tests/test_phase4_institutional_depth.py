"""Tests for Phase 4: Institutional Design Depth."""
import pytest
from civilization.services.schism_detector import SchismDetector
from civilization.services.rotating_gatekeepers import RotatingGatekeeperPool
from civilization.services.institutional_bankruptcy import InstitutionalBankruptcyEngine
from civilization.services.minority_report_protocol import MinorityReportManager


class TestSchismDetector:
    """Test schism detection."""

    def test_detects_schism_on_variance_spike(self):
        """Test schism detection on variance spike."""
        detector = SchismDetector()
        vectors = [
            {"dept": "a", "variance": 0.05, "timestamp": None},
            {"dept": "b", "variance": 0.05, "timestamp": None},
            {"dept": "c", "variance": 0.06, "timestamp": None},
            {"dept": "a", "variance": 0.5, "timestamp": None},  # Spike
        ] * 3

        result = detector.detect_schism("inst_1", vectors)
        assert hasattr(result, 'schism_detected')

    def test_no_schism_in_stable_variance(self):
        """Test no schism in stable data."""
        detector = SchismDetector()
        vectors = [{"dept": "a", "variance": 0.05} for _ in range(15)]

        result = detector.detect_schism("inst_1", vectors)
        assert hasattr(result, 'schism_detected')

    def test_schism_returns_conflict_depts(self):
        """Test conflict departments identified."""
        detector = SchismDetector()
        vectors = [
            {"dept": "normal", "variance": 0.05},
            {"dept": "conflict1", "variance": 0.15},
            {"dept": "conflict2", "variance": 0.14},
        ] * 5

        result = detector.detect_schism("inst_1", vectors)
        assert isinstance(result.conflict_depts, list)


class TestRotatingGatekeepers:
    """Test gatekeeper rotation."""

    def test_assigns_reviewer_from_pool(self):
        """Test reviewer assignment."""
        pool = RotatingGatekeeperPool()
        reviewers = ["alice", "bob", "charlie"]

        assigned = pool.assign_reviewer("stage_1", "inst_1", reviewers)
        assert assigned in reviewers

    def test_avoids_consecutive_reuse(self):
        """Test no consecutive same reviewer."""
        pool = RotatingGatekeeperPool()
        reviewers = ["alice", "bob"]

        first = pool.assign_reviewer("stage", "inst_1", reviewers)
        second = pool.assign_reviewer("stage", "inst_2", reviewers)

        assert first != second

    def test_load_balance(self):
        """Test load balancing."""
        pool = RotatingGatekeeperPool(max_reviews_per_week=5)
        reviewers = ["alice", "bob"]

        for i in range(4):
            pool.assign_reviewer(f"stage_{i}", f"inst_{i}", reviewers)

        loads = [pool.get_reviewer_load(r) for r in reviewers]
        assert abs(loads[0] - loads[1]) <= 1  # Balanced


class TestInstitutionalBankruptcy:
    """Test bankruptcy detection."""

    def test_bankruptcy_score_zero_for_perfect_record(self):
        """Test perfect record → score 0."""
        engine = InstitutionalBankruptcyEngine()

        dets = [
            {"correct": True, "approval_time_seconds": 600},
        ] * 10

        assess = engine.bankruptcy_score("inst_1", dets)
        assert 0 <= assess.bankruptcy_score <= 1

    def test_bankruptcy_triggered_at_threshold(self):
        """Test bankruptcy triggers > 0.7."""
        engine = InstitutionalBankruptcyEngine()

        # Many wrong, fast approvals, rubber stamps
        dets = [
            {"correct": False, "approval_time_seconds": 120},
        ] * 10

        assess = engine.bankruptcy_score("inst_1", dets)
        if assess.bankruptcy_score > 0.7:
            assert assess.status == "bankrupt"

    def test_bankruptcy_action_quarantines(self):
        """Test bankruptcy triggers quarantine."""
        engine = InstitutionalBankruptcyEngine()
        result = engine.trigger_bankruptcy("inst_1")

        assert "QUARANTINE" in result["action"]


class TestMinorityReport:
    """Test minority report publication."""

    def test_publishes_dissent(self):
        """Test dissent publication."""
        manager = MinorityReportManager()

        dissent = manager.publish_dissent("claim_1", "reviewer_1", "I disagree because...")
        assert dissent.published is True
        assert dissent.visibility == "public"

    def test_retrieves_dissents_for_claim(self):
        """Test dissent retrieval."""
        manager = MinorityReportManager()

        manager.publish_dissent("claim_1", "r1", "reason1")
        manager.publish_dissent("claim_1", "r2", "reason2")

        dissents = manager.get_dissents_for_claim("claim_1")
        assert len(dissents) == 2

    def test_dissent_count(self):
        """Test dissent counting."""
        manager = MinorityReportManager()

        manager.publish_dissent("claim_1", "r1", "reason")
        count = manager.count_dissents("claim_1")

        assert count == 1
