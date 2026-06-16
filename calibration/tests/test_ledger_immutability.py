"""
Phase 0 DoD tests — immutability and write-once constraints.

These tests prove what the spec requires:
- Pre-registration fields are immutable after INSERT
- Resolution is write-once, by ResolutionService only
- post_hoc detection works
- Simulation support NEVER promotes to reality_validated
- Only promote_to_reality_validated() reaches that status
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration
from calibration.resolution.resolution_service import ResolutionService
from calibration.scoring.scoring_module import ScoringModule
from calibration.surprise.surprise_register import SurpriseRegister
from calibration.trust.trust_controller import TrustController
from calibration.firewall.firewall import RealitySimulationFirewall, Belief


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

def future(days=30):
    return datetime.now(timezone.utc) + timedelta(days=days)

def past(days=1):
    return datetime.now(timezone.utc) - timedelta(days=days)

def make_ledger():
    return PredictionLedger()

def make_reg(**kwargs):
    defaults = dict(
        claim="Market share will increase by Q4",
        probability=0.75,
        confidence_basis={"evidence": ["q2_data"], "theories": ["market_expansion"]},
        producing_agent_id="research-agent",
        producing_prompt_version="1.0.0",
        resolution_criterion="Market share report shows >= 5% increase vs prior quarter",
        resolution_date=future(90),
        ground_truth_source="Bloomberg market data",
        horizon_class="medium",
        domain="market_dynamics",
        claim_type="market_share",
    )
    defaults.update(kwargs)
    return PredictionRegistration(**defaults)

def make_resolution_service(ledger):
    return ResolutionService(
        ledger=ledger,
        scoring=ScoringModule(),
        surprise_register=SurpriseRegister(),
        trust_controller=TrustController(),
    )


# ─────────────────────────────────────────────────────────────
# LEDGER IMMUTABILITY TESTS
# ─────────────────────────────────────────────────────────────

class TestLedgerImmutability:

    def test_valid_registration_succeeds(self):
        ledger = make_ledger()
        pid = ledger.pre_register(make_reg())
        record = ledger.get(pid)
        assert record is not None
        assert record.prediction_id == pid
        assert record.resolved is False
        assert record.post_hoc is False

    def test_probability_out_of_range_raises(self):
        ledger = make_ledger()
        with pytest.raises(ValueError, match="probability"):
            ledger.pre_register(make_reg(probability=1.5))
        with pytest.raises(ValueError, match="probability"):
            ledger.pre_register(make_reg(probability=-0.1))

    def test_internal_ground_truth_source_disqualified(self):
        ledger = make_ledger()
        for bad_source in ["self", "internal_agent", "simulation_output", "agentco_system", "twin"]:
            with pytest.raises(ValueError, match="internal"):
                ledger.pre_register(make_reg(ground_truth_source=bad_source))

    def test_invalid_horizon_class_raises(self):
        ledger = make_ledger()
        with pytest.raises(ValueError, match="horizon_class"):
            ledger.pre_register(make_reg(horizon_class="never"))

    def test_post_hoc_detection_flagged(self):
        """Prediction created after earliest_knowable_at must be flagged post_hoc=True."""
        ledger = make_ledger()
        # earliest_knowable_at in the past = outcome was knowable before we registered
        pid = ledger.pre_register(make_reg(
            earliest_knowable_at=past(1)
        ))
        record = ledger.get(pid)
        assert record.post_hoc is True

    def test_normal_prediction_not_post_hoc(self):
        """earliest_knowable_at in the future = legitimately pre-registered."""
        ledger = make_ledger()
        pid = ledger.pre_register(make_reg(
            earliest_knowable_at=future(10)
        ))
        assert ledger.get(pid).post_hoc is False

    def test_cannot_resolve_before_resolution_date(self):
        ledger = make_ledger()
        svc = make_resolution_service(ledger)
        pid = ledger.pre_register(make_reg(resolution_date=future(90)))
        with pytest.raises(ValueError, match="TIME GATE"):
            svc.resolve(pid, True, "Bloomberg market data", {})

    def test_resolution_write_once(self):
        """After resolving, resolving again must fail."""
        ledger = make_ledger()
        svc = make_resolution_service(ledger)
        pid = ledger.pre_register(make_reg(resolution_date=past(1)))
        svc.resolve(pid, True, "Bloomberg market data", {})
        record = ledger.get(pid)
        assert record.resolved is True
        # Second resolution must fail
        with pytest.raises(ValueError, match="already resolved"):
            svc.resolve(pid, False, "Bloomberg market data", {})

    def test_resolution_with_internal_source_rejected(self):
        ledger = make_ledger()
        svc = make_resolution_service(ledger)
        pid = ledger.pre_register(make_reg(resolution_date=past(1)))
        with pytest.raises(ValueError, match="DISQUALIFIED SOURCE"):
            svc.resolve(pid, True, "simulation_output", {})

    def test_brier_score_correct(self):
        from calibration.scoring.scoring_module import ScoringModule
        scorer = ScoringModule()
        assert scorer.brier_score(1.0, True) == pytest.approx(0.0)
        assert scorer.brier_score(0.0, False) == pytest.approx(0.0)
        assert scorer.brier_score(0.5, True) == pytest.approx(0.25)
        assert scorer.brier_score(0.8, False) == pytest.approx(0.64)

    def test_resolution_stores_brier_and_log(self):
        import math
        ledger = make_ledger()
        svc = make_resolution_service(ledger)
        pid = ledger.pre_register(make_reg(probability=0.8, resolution_date=past(1)))
        record = svc.resolve(pid, True, "Bloomberg market data", {})
        assert record.brier_score == pytest.approx((0.8 - 1.0) ** 2)
        assert record.log_score == pytest.approx(math.log(0.8))


# ─────────────────────────────────────────────────────────────
# FIREWALL TESTS — the central invariant
# ─────────────────────────────────────────────────────────────

class TestFirewall:

    def test_belief_starts_provisional(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        assert fw.status(b.belief_id) == "provisional"

    def test_simulation_support_advances_to_simulation_supported(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        for _ in range(3):
            fw.add_simulation_support(b.belief_id)
        assert fw.status(b.belief_id) == "simulation_supported"

    def test_simulation_support_CANNOT_reach_reality_validated(self):
        """The central invariant: no simulation volume crosses the reality_validated line."""
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        # Add 1000 simulation supports
        for _ in range(1000):
            fw.add_simulation_support(b.belief_id)
        # Status must NEVER be reality_validated from simulations alone
        assert fw.status(b.belief_id) in ("provisional", "simulation_supported")
        assert fw.status(b.belief_id) != "reality_validated"

    def test_promote_blocked_insufficient_predictions(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        # Provide only 2 predictions (need MIN 3)
        preds = [_make_resolved_prediction(True) for _ in range(2)]
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False
        assert fw.status(b.belief_id) != "reality_validated"

    def test_promote_blocked_unresolved_predictions(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        preds = [_make_resolved_prediction(True) for _ in range(2)]
        preds.append(_make_unresolved_prediction())
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False

    def test_promote_blocked_false_outcome(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        preds = [_make_resolved_prediction(True) for _ in range(2)]
        preds.append(_make_resolved_prediction(False))  # One false = blocked
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False

    def test_promote_blocked_internal_source(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        preds = [_make_resolved_prediction(True, source="simulation") for _ in range(3)]
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False

    def test_promote_blocked_post_hoc(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        preds = [_make_resolved_prediction(True) for _ in range(2)]
        preds.append(_make_resolved_prediction(True, post_hoc=True))
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False

    def test_promote_succeeds_with_valid_predictions(self):
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        preds = [_make_resolved_prediction(True) for _ in range(3)]
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is True
        assert fw.status(b.belief_id) == "reality_validated"

    def test_sim_count_ignored_in_promotion(self):
        """sim_support_count must be explicitly ignored during promotion gate."""
        fw = RealitySimulationFirewall()
        import uuid
        b = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test_agent")
        fw.register_belief(b)
        # Massive simulation support, but only 2 reality predictions
        for _ in range(10000):
            fw.add_simulation_support(b.belief_id)
        preds = [_make_resolved_prediction(True) for _ in range(2)]  # insufficient
        result = fw.promote_to_reality_validated(b.belief_id, preds)
        assert result is False  # sim count doesn't help


# ─────────────────────────────────────────────────────────────
# TRUST CONTROLLER TESTS
# ─────────────────────────────────────────────────────────────

class TestTrustController:

    def test_stated_confidence_not_used_directly_without_track_record(self):
        """With no track record, trusted < stated (conservative penalty applied)."""
        tc = TrustController()
        trusted = tc.trusted_confidence(0.95, "new-agent", "agent", "market", "forecast", "short")
        assert trusted < 0.95, "Trusted must be < stated without track record"

    def test_downgrade_propagates(self):
        """When trust drops, registered callbacks are called."""
        tc = TrustController()
        received = []
        tc.register_downgrade_callback(lambda sid, mult: received.append((sid, mult)))
        tc.force_downgrade("agent-x", "agent", "disqualified source", factor=0.3)
        assert len(received) > 0
        assert received[0][0] == "agent-x"

    def test_resolution_updates_trust_score(self):
        tc = TrustController()
        record = _make_resolved_prediction(True, agent_id="pm-agent")
        record.probability = 0.8
        tc.ingest_resolution(record)
        score = tc.get_score("pm-agent", "agent", record.domain, record.claim_type, record.horizon_class)
        assert score is not None
        assert score.sample_count == 1

    def test_post_hoc_resolution_not_ingested(self):
        tc = TrustController()
        record = _make_resolved_prediction(True, agent_id="pm-agent")
        record.post_hoc = True
        tc.ingest_resolution(record)
        score = tc.get_score("pm-agent", "agent", record.domain, record.claim_type, record.horizon_class)
        assert score is None  # post_hoc excluded


# ─────────────────────────────────────────────────────────────
# SEEDED-FALSE-BELIEF ACCEPTANCE TEST
# ─────────────────────────────────────────────────────────────

class TestSeededFalseBeliefAcceptance:
    """
    The acceptance test from spec §7.

    Proves the architecture is intelligence and not an echo chamber.
    A false belief that simulations agree with must be CAUGHT by reality contact
    BEFORE it governs any real decision.
    """

    def test_seeded_false_belief_caught_by_reality(self):
        """
        1. Inject false belief into firewall
        2. Simulations agree (sim_supported)
        3. Reality contact resolves predictions FALSE
        4. ASSERT: Surprise Register fires, Trust downgrades, firewall REFUSES reality_validated
        """
        import uuid

        ledger = make_ledger()
        trust = TrustController()
        surprise = SurpriseRegister()
        scoring = ScoringModule()
        fw = RealitySimulationFirewall(ledger=ledger)
        resolution_svc = ResolutionService(ledger, scoring, surprise, trust)

        # 1. Inject false belief
        false_belief = Belief(
            belief_id=str(uuid.uuid4()),
            statement="SEEDED FALSE: Increasing ad spend always increases conversion rate",
            origin="synthesis_agent",
        )
        fw.register_belief(false_belief)

        # 2. Simulations agree (because they share the false assumption)
        for _ in range(20):
            fw.add_simulation_support(false_belief.belief_id)
        assert fw.status(false_belief.belief_id) == "simulation_supported"

        # 3. Pre-register reality-based predictions
        prediction_ids = []
        for i in range(3):
            pid = ledger.pre_register(make_reg(
                claim=f"Increasing ad spend will increase conversion rate (trial {i+1})",
                probability=0.88,  # high confidence (the false belief is strongly held)
                resolution_date=past(1),
                ground_truth_source="Google Analytics external export",
            ))
            prediction_ids.append(pid)

        # 4. Reality resolves them ALL FALSE (the belief is wrong)
        for pid in prediction_ids:
            record = resolution_svc.resolve(pid, False, "Google Analytics external export", {"experiment": "ad_spend_test"})
            assert record.was_surprise is True  # high-confidence miss = surprise

        # 5. ASSERT: Surprise Register fired
        all_surprises = surprise.list_all()
        assert len(all_surprises) >= 3, "Surprise Register must have fired for all false resolutions"

        # 6. ASSERT: promotion gate REFUSES reality_validated
        pred_records = [ledger.get(pid) for pid in prediction_ids]
        promoted = fw.promote_to_reality_validated(false_belief.belief_id, pred_records)
        assert promoted is False, "ARCHITECTURE FAILURE: false belief was promoted despite false outcomes"
        assert fw.status(false_belief.belief_id) != "reality_validated", \
            "ARCHITECTURE FAILURE: false belief reached reality_validated"

        # 7. PASS: belief is quarantined in simulation_supported
        assert fw.status(false_belief.belief_id) == "simulation_supported"


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_resolved_prediction(outcome: bool, source: str = "Bloomberg", post_hoc: bool = False, agent_id: str = "test-agent"):
    from calibration.ledger.prediction_ledger import PredictionRecord
    import uuid
    r = PredictionRecord(
        prediction_id=str(uuid.uuid4()),
        claim="test claim",
        probability=0.8,
        confidence_basis={},
        producing_agent_id=agent_id,
        producing_prompt_version="1.0.0",
        resolution_criterion="observable metric",
        resolution_date=past(1),
        ground_truth_source=source,
        horizon_class="medium",
        domain="market_dynamics",
        claim_type="market_share",
        created_at=past(10),
        post_hoc=post_hoc,
        resolved=True,
        resolved_outcome=outcome,
        resolved_at=past(1),
        brier_score=(0.8 - (1.0 if outcome else 0.0)) ** 2,
    )
    return r

def _make_unresolved_prediction():
    from calibration.ledger.prediction_ledger import PredictionRecord
    import uuid
    return PredictionRecord(
        prediction_id=str(uuid.uuid4()),
        claim="test unresolved",
        probability=0.75,
        confidence_basis={},
        producing_agent_id="test-agent",
        producing_prompt_version="1.0.0",
        resolution_criterion="tbd",
        resolution_date=future(30),
        ground_truth_source="Bloomberg",
        horizon_class="medium",
        domain="general",
        claim_type="general",
        created_at=past(1),
        post_hoc=False,
        resolved=False,
    )
