"""Tests for Phase 6: Normative Reasoning."""
import pytest
from civilization.services.value_specification import ValueSpecificationCommittee
from civilization.services.stakeholder_completeness import StakeholderCompletenessGraph
from civilization.services.reversibility_tracker import ReversibilityTracker
from civilization.services.precedent_tracker import PrecedentTracker
from civilization.services.moral_weight_engine import MoralWeightEngine


class TestValueSpecification:
    """Test norm definition and clarification."""

    def test_defines_norm(self):
        """Test norm creation."""
        committee = ValueSpecificationCommittee()

        norm = committee.define_norm("fairness", "Equal treatment regardless of identity")
        assert norm.status == "draft"
        assert norm.governable is True

    def test_clarifies_term(self):
        """Test term clarification."""
        committee = ValueSpecificationCommittee()

        norm = committee.define_norm("fairness", "Equal treatment")
        clarified = committee.clarify_term(norm.norm_id, "Except for special needs")

        assert clarified.status == "clarified"
        assert len(clarified.versions) > 1

    def test_retrieves_norm(self):
        """Test norm retrieval."""
        committee = ValueSpecificationCommittee()

        norm = committee.define_norm("fairness", "Equal treatment")
        retrieved = committee.get_norm(norm.norm_id)

        assert retrieved.norm_name == "fairness"


class TestStakeholderCompleteness:
    """Test stakeholder representation."""

    def test_registers_affected_parties(self):
        """Test affected parties registration."""
        graph = StakeholderCompletenessGraph()

        groups = ["patients", "doctors", "administrators"]
        graph.register_decision("decision_1", groups)

        affected = graph.affected_parties("decision_1")
        assert len(affected) == 3

    def test_scores_representation(self):
        """Test representation scoring."""
        graph = StakeholderCompletenessGraph()

        graph.register_decision("decision_1", ["patients", "doctors", "admins"])
        score = graph.representation_score("decision_1", ["patients", "doctors"])

        assert 0 <= score <= 1
        assert score < 1.0  # Not all represented

    def test_full_representation_score_one(self):
        """Test full representation."""
        graph = StakeholderCompletenessGraph()

        graph.register_decision("decision_1", ["a", "b"])
        score = graph.representation_score("decision_1", ["a", "b"])

        assert score == 1.0


class TestReversibilityTracker:
    """Test reversibility assessment."""

    def test_rates_fully_reversible(self):
        """Test reversible decision."""
        tracker = ReversibilityTracker()

        metrics = {
            "resource_cost": 100,
            "time_to_undo_days": 7,
            "irreversible_harm": False,
        }

        rating = tracker.rate_reversibility("decision_1", metrics)
        assert rating == "fully_reversible"

    def test_rates_irreversible(self):
        """Test irreversible decision."""
        tracker = ReversibilityTracker()

        metrics = {
            "resource_cost": 1e6,
            "time_to_undo_days": 1000,
            "irreversible_harm": True,
        }

        rating = tracker.rate_reversibility("decision_1", metrics)
        assert rating == "irreversible"

    def test_deliberation_bar_scales_with_reversibility(self):
        """Test deliberation bar."""
        tracker = ReversibilityTracker()

        bar_full = tracker.deliberation_bar("fully_reversible", False)
        bar_irrev = tracker.deliberation_bar("irreversible", True)

        assert bar_irrev > bar_full


class TestPrecedentTracker:
    """Test precedent compatibility."""

    def test_scores_compatibility(self):
        """Test compatibility scoring."""
        tracker = PrecedentTracker()

        past = [{"norm": "equal treatment for all"}]
        score = tracker.precedent_compatibility_score("equal treatment for all", past)

        assert 0 <= score <= 1

    def test_reviews_precedent_set(self):
        """Test precedent set review."""
        tracker = PrecedentTracker()

        decisions = [
            {"norm_id": "n1", "decision_id": "d1", "compatible": True},
            {"norm_id": "n1", "decision_id": "d2", "compatible": True},
        ]

        analysis = tracker.review_precedent_set("n1", decisions)
        assert analysis.coherence == 1.0


class TestMoralWeightEngine:
    """Test moral weight assignment."""

    def test_assigns_weight_to_human(self):
        """Test human weight."""
        engine = MoralWeightEngine()

        assign = engine.assign_moral_weight("person_1", "human")
        assert assign.weight == 1.0

    def test_assigns_lower_weight_to_animal(self):
        """Test animal weight."""
        engine = MoralWeightEngine()

        human = engine.assign_moral_weight("person", "human")
        animal = engine.assign_moral_weight("animal", "sentient_animal")

        assert animal.weight < human.weight

    def test_tracks_weight_dependencies(self):
        """Test dependency tracking."""
        engine = MoralWeightEngine()

        deps = engine.track_weight_dependencies("decision_1", ["person_1", "person_2"])
        assert "decision_id" in deps
        assert "weight_change_impact" in deps
