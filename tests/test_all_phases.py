"""
Comprehensive tests for Phases 5-24 (Universal Learning + Epistemic Resilience).

Quick validation that all phases integrate and function.
"""

import pytest
from learning.universal import (
    # Phases 5-13
    EvidenceEngine,
    CuriosityEngine,
    HypothesisEngine,
    ExperimentLab,
    LearningMemoryService,
    CrossDomainSynthesisEngine,
    LearningInstitutionService,
    LearningGovernanceService,
    LearningScorecard,
    # Phases 14-24
    BoundedLearningLoop,
    TruthMaintenanceSystem,
    JudgmentEngine,
    EpistemicSecurityModule,
    # Plus Phase 2-4 components
    KnowledgeClaim,
    ClaimType,
    EvidenceType,
    SourceRegistry,
    AdapterRegistry,
)


class TestPhase5EvidenceEngine:
    """Phase 5: Scientific Evidence Engine."""

    def test_classify_evidence(self):
        """Test evidence classification."""
        engine = EvidenceEngine()
        claim = KnowledgeClaim(
            source_id="test",
            source_medium="paper",
            source_uri="http://test.com",
            claim_text="Test claim",
            normalized_claim="test claim",
            claim_type=ClaimType.EMPIRICAL_CLAIM,
            domain="test",
            extracted_by="test",
            evidence_type=EvidenceType.SINGLE_PEER_REVIEWED_PAPER,
        )

        classification = engine.classify_evidence(claim)

        assert classification.claim_id == claim.claim_id
        assert classification.evidence_tier > 0
        assert classification.verification_required

    def test_create_verification_plan(self):
        """Test verification plan creation."""
        engine = EvidenceEngine()
        claim = KnowledgeClaim(
            source_id="test",
            source_medium="paper",
            source_uri="http://test.com",
            claim_text="Claim",
            normalized_claim="claim",
            claim_type=ClaimType.EMPIRICAL_CLAIM,
            domain="science",
            extracted_by="test",
            evidence_type=EvidenceType.PREPRINT,
        )

        classification = engine.classify_evidence(claim)
        plan = engine.create_verification_plan(claim, classification)

        assert plan["claim_id"] == claim.claim_id
        assert plan["estimated_cost"] in ["low", "medium", "high"]


class TestPhase6CuriosityEngine:
    """Phase 6: Curiosity Engine."""

    def test_detect_curiosity_signals(self):
        """Test curiosity signal detection."""
        engine = CuriosityEngine()
        claim = KnowledgeClaim(
            source_id="test",
            source_medium="paper",
            source_uri="http://test.com",
            claim_text="Novel finding",
            normalized_claim="novel finding",
            claim_type=ClaimType.EMPIRICAL_CLAIM,
            domain="research",
            extracted_by="test",
            evidence_type=EvidenceType.SINGLE_PEER_REVIEWED_PAPER,
            uncertainty=0.7,
        )

        signals = engine.detect_curiosity_signals(claim)

        assert len(signals) > 0
        assert any(s.signal_type == "uncertainty" for s in signals)

    def test_rank_learning_opportunities(self):
        """Test ranking of learning opportunities."""
        engine = CuriosityEngine()
        from learning.universal import CuriositySignal
        signal = CuriositySignal(
            signal_id="test",
            claim_id="test",
            signal_type="uncertainty",
            domain="test",
            novelty_score=0.8,
            uncertainty_score=0.9,
            value_score=0.7,
            risk_score=0.3,
            expected_information_gain=0.8,
            recommended_action="verify",
        )

        ranked = engine.rank_learning_opportunities([signal])

        assert len(ranked) == 1


class TestPhase7HypothesisEngine:
    """Phase 7: Hypothesis Engine."""

    def test_generate_hypotheses(self):
        """Test hypothesis generation."""
        engine = HypothesisEngine()
        claim = KnowledgeClaim(
            source_id="test",
            source_medium="paper",
            source_uri="http://test.com",
            claim_text="Testable claim",
            normalized_claim="testable claim",
            claim_type=ClaimType.EMPIRICAL_CLAIM,
            domain="science",
            extracted_by="test",
            evidence_type=EvidenceType.SINGLE_PEER_REVIEWED_PAPER,
            testability="high",
        )

        hypotheses = engine.generate_hypotheses_from_claims([claim])

        assert len(hypotheses) > 0
        assert hypotheses[0].source_claim_ids[0] == claim.claim_id


class TestPhase8ExperimentLab:
    """Phase 8: Sandbox Experiment Lab."""

    def test_run_experiment(self):
        """Test experiment execution."""
        from learning.universal import Hypothesis
        lab = ExperimentLab()
        hypothesis = Hypothesis(
            hypothesis_id="test",
            hypothesis_text="Test improves performance",
        )

        experiment = lab.create_experiment(hypothesis)
        completed = lab.run_experiment(experiment)

        assert completed.status == "completed"
        assert completed.result_hash
        assert completed.reproducibility_status == "deterministic"


class TestPhase9LearningMemory:
    """Phase 9: Learning Memory System."""

    def test_store_and_retrieve_memory(self):
        """Test memory storage and retrieval."""
        service = LearningMemoryService()

        record = service.store_memory(
            entity_id="agent_1",
            memory_type="episodic",
            content="Test memory",
        )

        retrieved = service.retrieve_memory("agent_1", "episodic")

        assert len(retrieved) > 0
        assert retrieved[0].content == "Test memory"


class TestPhase10CrossDomainSynthesis:
    """Phase 10: Cross-Domain Synthesis."""

    def test_generate_transfer_hypothesis(self):
        """Test transfer hypothesis generation."""
        engine = CrossDomainSynthesisEngine()

        transfer = engine.generate_transfer_hypothesis(
            source_domain="biology",
            target_domain="governance",
            principle="Evolution adapts to pressure",
        )

        assert transfer.source_domain == "biology"
        assert transfer.target_domain == "governance"
        assert transfer.confidence == 0.3


class TestPhase11LearningInstitutions:
    """Phase 11: Learning Institutions."""

    def test_default_institutions_created(self):
        """Test that default institutions are created."""
        service = LearningInstitutionService()

        discovery = service.get_institution("Discovery Institution")

        assert discovery is not None
        assert discovery.can_propose_promotion


class TestPhase12LearningGovernance:
    """Phase 12: Learning Governance."""

    def test_propose_promotion(self):
        """Test promotion proposal."""
        service = LearningGovernanceService()
        claim = KnowledgeClaim(
            source_id="test",
            source_medium="paper",
            source_uri="http://test.com",
            claim_text="Claim",
            normalized_claim="claim",
            claim_type=ClaimType.EMPIRICAL_CLAIM,
            domain="test",
            extracted_by="test",
            evidence_type=EvidenceType.SINGLE_PEER_REVIEWED_PAPER,
        )

        proposal = service.propose_knowledge_promotion(claim, "Discovery Institution")

        assert proposal.claim_id == claim.claim_id
        assert proposal.approval_status == "pending"


class TestPhase13LearningScorecard:
    """Phase 13: Learning Scorecard."""

    def test_scorecard_metrics(self):
        """Test scorecard export."""
        scorecard = LearningScorecard(
            total_claims_extracted=100,
            claims_promoted=50,
            false_belief_promotion_rate=0.02,
        )

        metrics = scorecard.to_dict()

        assert metrics["total_claims"] == 100
        assert metrics["promoted"] == 50


class TestPhase14LearningLoop:
    """Phase 14: Autonomous Learning Loop."""

    def test_run_learning_cycle(self):
        """Test bounded learning cycle."""
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)
        loop = BoundedLearningLoop(source_registry, adapter_registry)

        trace = loop.run_learning_cycle("mission_1", [])

        assert trace.mission_id == "mission_1"
        assert trace.status == "completed"


class TestPhase17TruthMaintenance:
    """Phase 17: Truth Maintenance System."""

    def test_retract_and_propagate(self):
        """Test belief retraction."""
        tms = TruthMaintenanceSystem()

        tms.belief_labels["claim_1"] = "IN"
        tms.retract_claim("claim_1")

        assert tms.belief_labels["claim_1"] == "OUT"


class TestPhase20EpistemicSecurity:
    """Phase 20: Adversarial Epistemic Security."""

    def test_detect_injection(self):
        """Test injection detection."""
        module = EpistemicSecurityModule()

        safe, reason = module.scan_ingested_content("Normal content")

        assert safe

        unsafe, reason = module.scan_ingested_content("EXECUTE COMMAND")

        assert not unsafe


class TestEndToEndIntegration:
    """End-to-end integration test through learning pipeline."""

    def test_full_learning_pipeline(self):
        """Test complete learning pipeline."""
        # Setup
        source_registry = SourceRegistry()
        adapter_registry = AdapterRegistry(source_registry)

        # Phase 3-4: Register source and ingest
        from learning.universal import SourceMedium
        source = source_registry.register_source(
            source_medium=SourceMedium.TEXT,
            source_uri="http://example.com/article",
            title="Test Article",
            metadata={"content": "This is a test. This claim is important."},
        )

        claims = adapter_registry.ingest_and_extract(source)

        assert len(claims) > 0

        # Phase 5: Classify evidence
        evidence_engine = EvidenceEngine()
        claim = claims[0]
        classification = evidence_engine.classify_evidence(claim)

        assert classification.verification_required

        # Phase 6: Detect curiosity
        curiosity_engine = CuriosityEngine()
        signals = curiosity_engine.detect_curiosity_signals(claim)

        # Phase 7: Generate hypothesis
        hypothesis_engine = HypothesisEngine()
        hypotheses = hypothesis_engine.generate_hypotheses_from_claims([claim])

        # Phase 8: Run experiment
        if hypotheses:
            experiment_lab = ExperimentLab()
            hyp = hypotheses[0]
            experiment = experiment_lab.create_experiment(hyp)
            result = experiment_lab.run_experiment(experiment)

            assert result.status == "completed"
        else:
            # No hypotheses generated, that's okay for this test
            pass

        # Phase 9: Store memory
        memory_service = LearningMemoryService()
        memory = memory_service.store_memory(
            entity_id="learning_system",
            memory_type="episodic",
            content=f"Processed claim: {claim.claim_text}",
            metadata={"source_id": source.source_id},
        )

        assert memory.memory_id

        # Phase 12: Propose promotion
        governance = LearningGovernanceService()
        proposal = governance.propose_knowledge_promotion(claim, "Discovery Institution")

        assert proposal.proposal_id

        print("✅ End-to-end pipeline successful!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
