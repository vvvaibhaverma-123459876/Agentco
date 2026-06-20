"""Tests for Phase 7, 8, 9 (Evidence, Resources, Integration)."""
import pytest
from civilization.services.evidence_tier_meta_analysis import EvidenceTierAnalyzer
from civilization.services.domain_specific_priors import DomainSpecificPriors
from civilization.services.temporal_decay import TemporalDecayEngine
from civilization.services.citation_context_analyzer import CitationContextAnalyzer
from civilization.services.mechanism_validity_engine import MechanismValidityEngine
from civilization.services.outside_view_corrector import OutsideViewCorrector
from civilization.services.verification_budget_optimizer import VerificationBudgetOptimizer
from civilization.services.learning_curves import LearningCurveTracker
from civilization.services.epistemic_insurance import EpistemicInsuranceManager
from civilization.services.epistemic_debt_register import EpistemicDebtRegister
from civilization.services.attention_economics import AttentionEconomicsEngine
from civilization.scorecards.learning_resilience_scorecard import LearningResilienceScorecard


class TestPhase7:
    """Phase 7: Dynamic Evidence Combination."""

    def test_tier_failure_rate(self):
        """Test tier failure tracking."""
        analyzer = EvidenceTierAnalyzer()
        analyzer.record_outcome("peer_reviewed", "biology", True)
        analyzer.record_outcome("peer_reviewed", "biology", False)

        rate = analyzer.tier_failure_rate("peer_reviewed", "biology")
        assert 0 <= rate <= 1

    def test_update_tier_hierarchy(self):
        """Test hierarchy updates empirically."""
        analyzer = EvidenceTierAnalyzer()
        analyzer.record_outcome("formal_proof", "math", True)
        analyzer.record_outcome("blog", "math", False)

        result = analyzer.update_tier_hierarchy("math")
        assert "tier_order" in result
        assert len(result["tier_order"]) > 0

    def test_domain_priors(self):
        """Test domain-specific priors."""
        priors = DomainSpecificPriors()
        assert priors.prior("math") > priors.prior("opinion")

    def test_temporal_decay(self):
        """Test decay computation."""
        decay = TemporalDecayEngine()
        weight_new = decay.decay_weight(0, "tech_benchmark")
        weight_old = decay.decay_weight(90, "tech_benchmark")

        assert weight_new > weight_old
        assert 0 <= weight_old <= 1

    def test_citation_context(self):
        """Test citation strength extraction."""
        analyzer = CitationContextAnalyzer()
        strength = analyzer.context_strength("This proves the claim")
        assert strength > 0.8

    def test_mechanism_validation(self):
        """Test mechanism validity."""
        engine = MechanismValidityEngine()
        result = engine.validate_mechanism("Claim", "causes effect")
        assert "valid" in result
        assert 0 <= result["confidence"] <= 1

    def test_outside_view_correction(self):
        """Test correction factors."""
        corrector = OutsideViewCorrector()
        factor_math = corrector.correction_factor("math")
        factor_social = corrector.correction_factor("social")

        assert factor_math > factor_social


class TestPhase8:
    """Phase 8: Resource Economics."""

    def test_budget_allocation(self):
        """Test verification budget optimization."""
        optimizer = VerificationBudgetOptimizer()

        claims = [
            {"claim_id": "c1", "voi": 0.9, "cost_tokens": 100},
            {"claim_id": "c2", "voi": 0.5, "cost_tokens": 200},
        ]

        result = optimizer.allocate_budget(claims, 300)
        assert len(result["allocation"]) > 0

    def test_learning_curve(self):
        """Test marginal cost decreases."""
        tracker = LearningCurveTracker()

        cost_1 = tracker.marginal_cost("replication", 1)
        cost_2 = tracker.marginal_cost("replication", 2)

        assert cost_2 < cost_1

    def test_escrow_allocation(self):
        """Test epistemic insurance allocation."""
        insurance = EpistemicInsuranceManager()

        escrow = insurance.allocate_escrow("claim_1", 300)
        assert escrow["initial_escrow"] + escrow["followup_escrow"] + escrow["option_value"] == 300

    def test_debt_registration(self):
        """Test debt tracking."""
        register = EpistemicDebtRegister()

        debt = register.acknowledge_unverified("claim_1", "reason", 60)
        assert "debt_id" in debt

    def test_attention_load_balance(self):
        """Test reviewer load balancing."""
        engine = AttentionEconomicsEngine()

        result = engine.load_balance_reviewers(["r1", "r2", "r3"])
        assert result["balanced"] is True or len(result["allocation"]) > 0

    def test_burnout_risk(self):
        """Test burnout risk assessment."""
        engine = AttentionEconomicsEngine(max_per_week=5)

        risk = engine.burnout_risk("reviewer_1")
        assert 0 <= risk <= 1


class TestPhase9:
    """Phase 9: Integration & Resilience."""

    def test_phase_completeness(self):
        """Test phase completeness scoring."""
        scorecard = LearningResilienceScorecard()
        scorecard.test_results["phase_1_tests"] = 1.0
        scorecard.test_results["phase_1_lint"] = 1.0
        scorecard.test_results["phase_1_integration"] = 1.0
        scorecard.test_results["phase_1_docs"] = 1.0

        score = scorecard.phase_completeness(1)
        assert score == 1.0

    def test_resilience_assessment(self):
        """Test resilience measurement."""
        scorecard = LearningResilienceScorecard()

        scenarios = [
            {"passed": True},
            {"passed": True},
            {"passed": False},
        ]

        assessment = scorecard.system_resilience(scenarios)
        assert assessment.scenarios_passed == 2

    def test_epistemic_health(self):
        """Test health assessment."""
        scorecard = LearningResilienceScorecard()
        scorecard.test_results["calibration_ece"] = 0.08
        scorecard.test_results["coherence_violations"] = 0
        scorecard.test_results["institutional_schisms"] = 0
        scorecard.test_results["adversarial_signals"] = 0

        health = scorecard.epistemic_health()
        assert health["calibration_ece"] < 0.15

    def test_final_readiness(self):
        """Test production readiness."""
        scorecard = LearningResilienceScorecard()
        scorecard.test_results["calibration_ece"] = 0.08
        scorecard.test_results["coherence_violations"] = 0
        scorecard.test_results["institutional_schisms"] = 0

        readiness = scorecard.final_readiness()
        assert "ready_for_production" in readiness
        assert isinstance(readiness["ready_for_production"], bool)
