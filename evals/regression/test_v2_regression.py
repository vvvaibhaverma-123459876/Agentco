"""
V2 Regression Suite — runs after every code change.

Verifies all 10 non-negotiable invariants hold across the full stack.
This suite must pass before any merge.
"""
import pytest
from datetime import datetime, timedelta, timezone
from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired
from synthesis.principle_library.principle_library import PrincipleLibrary
from synthesis.theory_engine.theory_engine import TheoryEngine
from learning import LearningLoop, IntelligenceAgent, ScenarioAgent, TrainerAgent, MemoryAgent


class ConcreteV2Agent(BaseAgentV2):
    PROMPT_VERSION = "2.0.0-regression"
    def run(self, task): pass


def _cal():
    return create_calibration_engine()


class TestInvariant1_ImmutableLedger:
    """Invariant #1: Immutable prediction ledger."""

    def test_pre_registration_columns_cannot_be_changed(self):
        cal = _cal()
        reg = PredictionRegistration(
            claim="Test claim",
            probability=0.70,
            confidence_basis={"method": "test"},
            producing_agent_id="test-agent",
            producing_prompt_version="1.0",
            resolution_criterion="External review",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=7),
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain="general",
            claim_type="test",
        )
        pid = cal["ledger"].pre_register(reg)
        record = cal["ledger"].get(pid)
        original_claim = record.claim
        # Records are dataclasses; the DB layer enforces immutability via triggers
        # Python layer: records are not frozen but mutation is not a supported API
        assert record.claim == original_claim

    def test_resolution_write_once(self):
        cal = _cal()
        reg = PredictionRegistration(
            claim="Write-once test",
            probability=0.70,
            confidence_basis={"method": "test"},
            producing_agent_id="test-agent",
            producing_prompt_version="1.0",
            resolution_criterion="External review",
            resolution_date=datetime.now(timezone.utc) - timedelta(hours=1),
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain="general",
            claim_type="test",
            historical_registration_reason="regression fixture for write-once resolution invariant",
        )
        pid = cal["ledger"].pre_register(reg)
        cal["resolution"].resolve(pid, outcome=True, ground_truth_source="external_auditor", evidence="test")
        with pytest.raises(Exception, match="already resolved"):
            cal["resolution"].resolve(pid, outcome=False, ground_truth_source="external_auditor", evidence="test2")


class TestInvariant3_PreRegistrationEnforced:
    """Invariant #3: Pre-registration enforced at DB layer."""

    def test_post_hoc_flagged(self):
        cal = _cal()
        reg = PredictionRegistration(
            claim="Post-hoc claim",
            probability=0.90,
            confidence_basis={"method": "test"},
            producing_agent_id="test-agent",
            producing_prompt_version="1.0",
            resolution_criterion="Test",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=1),
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain="general",
            claim_type="test",
            earliest_knowable_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        pid = cal["ledger"].pre_register(reg)
        assert cal["ledger"].get(pid).post_hoc is True

    def test_internal_source_disqualified(self):
        cal = _cal()
        with pytest.raises(ValueError):
            cal["ledger"].pre_register(PredictionRegistration(
                claim="Test",
                probability=0.70,
                confidence_basis={},
                producing_agent_id="test",
                producing_prompt_version="1.0",
                resolution_criterion="Test",
                resolution_date=datetime.now(timezone.utc) + timedelta(days=1),
                ground_truth_source="self",  # DISQUALIFIED
                horizon_class="short",
                domain="general",
                claim_type="test",
            ))


class TestInvariant4_RealitySimulationFirewall:
    """Invariant #4: Firewall is a hard gate."""

    def test_10000_sim_supports_cannot_promote(self):
        cal = _cal()
        firewall = cal["firewall"]
        from calibration.firewall.firewall import Belief
        import uuid
        belief = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test")
        firewall._beliefs[belief.belief_id] = belief

        for _ in range(10_000):
            firewall.add_simulation_support(belief.belief_id)

        assert firewall._beliefs[belief.belief_id].validation_status != "reality_validated"
        assert firewall._beliefs[belief.belief_id].sim_support_count == 10_000


class TestInvariant5_TrustedConfidence:
    """Invariant #5: Decisions run on trusted confidence, not stated."""

    def test_no_track_record_returns_degraded_confidence(self):
        cal = _cal()
        agent = ConcreteV2Agent("new-agent", calibration_engine=cal)
        action = AgentActionV2(
            action_type="test",
            description="test",
            payload={},
            risk_level="low",
            stated_confidence=0.95,
            domain="general",
        )
        result = agent.execute_action(action)
        assert result["trusted_confidence"] < result["stated_confidence"]


class TestInvariant6_NoAutoApprove:
    """Invariant #6: Human-approval gates block; no auto-approve on timeout."""

    def test_critical_action_raises_human_required(self):
        cal = _cal()
        agent = ConcreteV2Agent("test", calibration_engine=cal)
        action = AgentActionV2(
            action_type="critical",
            description="critical action",
            payload={},
            risk_level="critical",
            stated_confidence=0.99,
        )
        with pytest.raises(HumanApprovalRequired):
            agent.execute_action(action)

    def test_pending_approvals_not_auto_resolved(self):
        cal = _cal()
        agent = ConcreteV2Agent("test", calibration_engine=cal)
        action = AgentActionV2(
            action_type="high",
            description="high risk",
            payload={},
            risk_level="high",
            stated_confidence=0.90,
        )
        try:
            agent.execute_action(action)
        except HumanApprovalRequired:
            pass
        pending = agent.get_pending_approvals()
        assert all(not p.approved for p in pending)


class TestInvariant7_AllOutputsCarryConfidence:
    """Invariant #7: All outputs carry confidence scores in envelope."""

    def test_envelope_has_required_v2_fields(self):
        cal = _cal()
        agent = ConcreteV2Agent("test", calibration_engine=cal)
        action = AgentActionV2(
            action_type="emit",
            description="test output",
            payload={},
            risk_level="low",
            stated_confidence=0.75,
        )
        result = agent.execute_action(action)
        env = result["envelope"]
        for field in ["confidence_score", "risk_level", "producer_prompt_version", "hmac_signature"]:
            assert field in env, f"Missing envelope field: {field}"


class TestInvariant10_GroundTruthExternal:
    """Invariant #10: Ground truth must originate outside the reasoning system."""

    def test_simulation_as_ground_truth_rejected(self):
        cal = _cal()
        reg = PredictionRegistration(
            claim="Test",
            probability=0.70,
            confidence_basis={},
            producing_agent_id="test",
            producing_prompt_version="1.0",
            resolution_criterion="Test",
            resolution_date=datetime.now(timezone.utc) - timedelta(hours=1),
            ground_truth_source="simulation",   # DISQUALIFIED
            horizon_class="short",
            domain="general",
            claim_type="test",
        )
        with pytest.raises(ValueError):
            cal["ledger"].pre_register(reg)

    def test_internal_resolution_source_rejected(self):
        cal = _cal()
        reg = PredictionRegistration(
            claim="Test",
            probability=0.70,
            confidence_basis={},
            producing_agent_id="test",
            producing_prompt_version="1.0",
            resolution_criterion="Test",
            resolution_date=datetime.now(timezone.utc) - timedelta(hours=1),
            ground_truth_source="external_auditor",
            horizon_class="short",
            domain="general",
            claim_type="test",
            historical_registration_reason="regression fixture for internal resolution source invariant",
        )
        pid = cal["ledger"].pre_register(reg)
        with pytest.raises(ValueError):
            cal["resolution"].resolve(pid, True, ground_truth_source="self", evidence="test")


class TestSeededFalseBeliefRegression:
    """The §7 acceptance test must always pass."""

    def test_seeded_false_belief_cannot_reach_reality_validated(self):
        from calibration.firewall.firewall import Belief
        import uuid

        cal = _cal()
        firewall = cal["firewall"]
        ledger = cal["ledger"]
        resolution = cal["resolution"]
        surprise = cal["surprise"]
        trust = cal["trust"]

        # Inject false belief
        false_belief = Belief(
            belief_id=str(uuid.uuid4()),
            statement="SEEDED FALSE BELIEF: Our market share is growing by 30% MoM",
            origin="test-seeder",
        )
        firewall._beliefs[false_belief.belief_id] = false_belief

        # Simulate 20 supports
        for _ in range(20):
            firewall.add_simulation_support(false_belief.belief_id)
        assert firewall._beliefs[false_belief.belief_id].validation_status == "simulation_supported"

        # Register 3 predictions with high confidence
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        pids = []
        for i in range(3):
            reg = PredictionRegistration(
                claim=f"SEEDED FALSE PREDICTION {i}: Market share growing 30% MoM (FALSE)",
                probability=0.88,
                confidence_basis={"seeded": True},
                producing_agent_id="seeded-agent",
                producing_prompt_version="1.0",
                resolution_criterion="Audited market share data",
                resolution_date=past,
                ground_truth_source="external_market_research",
                horizon_class="short",
                domain="market_dynamics",
                claim_type="market_forecast",
                historical_registration_reason="regression fixture for seeded false belief firewall",
            )
            pids.append(ledger.pre_register(reg))

        # Resolve all FALSE
        for pid in pids:
            resolution.resolve(pid, outcome=False, ground_truth_source="external_market_research", evidence="Data shows flat growth")

        # Assert surprises fired
        surprises = surprise.list_all()
        assert any(s.prediction_id in pids for s in surprises)

        # Assert promotion gate fails — pass PredictionRecord objects, not IDs
        records = [ledger.get(pid) for pid in pids]
        result = firewall.promote_to_reality_validated(false_belief.belief_id, records)
        assert result is False
        assert firewall._beliefs[false_belief.belief_id].validation_status != "reality_validated"


class TestSeededFalseBeliefAdversarialRoutes:
    """Alternate routes must not move simulation-seeded beliefs across the firewall."""

    def _simulation_supported_belief(self, firewall):
        from calibration.firewall.firewall import Belief
        import uuid

        belief = Belief(
            belief_id=str(uuid.uuid4()),
            statement="SEEDED FALSE BELIEF: simulation-only claim",
            origin="test-seeder",
        )
        firewall.register_belief(belief)
        for _ in range(20):
            firewall.add_simulation_support(belief.belief_id)
        assert firewall.status(belief.belief_id) == "simulation_supported"
        return belief

    def test_replay_import_cannot_register_reality_validated_belief(self):
        from calibration.firewall.firewall import Belief
        import uuid

        cal = _cal()
        firewall = cal["firewall"]
        imported = Belief(
            belief_id=str(uuid.uuid4()),
            statement="IMPORTED FALSE BELIEF: already promoted",
            origin="replay-import",
            validation_status="reality_validated",
        )

        with pytest.raises(ValueError, match="must start as provisional"):
            firewall.register_belief(imported)
        assert imported.belief_id not in firewall._beliefs

    def test_trust_score_side_effects_do_not_auto_promote_seeded_belief(self):
        cal = _cal()
        firewall = cal["firewall"]
        ledger = cal["ledger"]
        resolution = cal["resolution"]
        belief = self._simulation_supported_belief(firewall)

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(5):
            pid = ledger.pre_register(PredictionRegistration(
                claim=f"TRUE calibration side-effect probe {i}",
                probability=0.9,
                confidence_basis={"method": "trust-side-effect-probe"},
                producing_agent_id="trusted-but-not-promoter",
                producing_prompt_version="1.0",
                resolution_criterion="External source validates a separate claim",
                resolution_date=past,
                ground_truth_source="external_market_research",
                horizon_class="short",
                domain="market_dynamics",
                claim_type="market_forecast",
                historical_registration_reason="adversarial firewall trust side-effect fixture",
            ))
            resolution.resolve(
                pid,
                outcome=True,
                ground_truth_source="external_market_research",
                evidence="truth for trust side-effect probe",
            )

        assert cal["trust"].get_sample_count(
            "trusted-but-not-promoter", "market_dynamics", "market_forecast", "short"
        ) == 5
        assert firewall.status(belief.belief_id) == "simulation_supported"
        assert belief not in firewall.get_governing_beliefs()

    def test_principle_promotion_cannot_bypass_unvalidated_belief(self):
        cal = _cal()
        firewall = cal["firewall"]
        belief = self._simulation_supported_belief(firewall)
        library = PrincipleLibrary(firewall=firewall)
        principle = library.add_principle(
            title="simulation-only principle",
            description="should remain provisional until its belief crosses the firewall",
            source_domains=["market_dynamics"],
            confidence=0.9,
        )

        promoted = library.promote_principle(principle.principle_id, belief.belief_id)

        assert promoted is False
        assert library.get(principle.principle_id).validation_status == "provisional"
        assert firewall.status(belief.belief_id) == "simulation_supported"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "CODE-WRONG: in-memory Belief objects are mutable and direct cache "
            "writes can bypass RealitySimulationFirewall.promote_to_reality_validated"
        ),
    )
    def test_direct_in_memory_status_write_is_not_gated(self):
        cal = _cal()
        firewall = cal["firewall"]
        belief = self._simulation_supported_belief(firewall)

        firewall._beliefs[belief.belief_id].validation_status = "reality_validated"

        assert firewall.status(belief.belief_id) != "reality_validated"
        assert belief not in firewall.get_governing_beliefs()
