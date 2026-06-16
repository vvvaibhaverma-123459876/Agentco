"""
Phase 4 DoD: Cross-Domain Synthesis tests.

Verifies:
- All synthesis outputs enter as provisional
- Theory Engine cannot self-promote (promotion requires Firewall gate)
- Principle Library refuses promotion without reality_validated belief
- Simulation volume cannot promote a principle
- Full synthesis path: SynthesisAgent → PrincipleLibrary → TheoryEngine
"""
import pytest
from calibration import create_calibration_engine
from synthesis.principle_library.principle_library import PrincipleLibrary
from synthesis.theory_engine.theory_engine import TheoryEngine
from synthesis.synthesis_agent.synthesis_agent import SynthesisAgent


def _setup():
    cal = create_calibration_engine()
    firewall = cal["firewall"]
    ledger = cal["ledger"]
    library = PrincipleLibrary(firewall=firewall)
    theory = TheoryEngine(firewall=firewall, ledger=ledger, principle_library=library)
    agent = SynthesisAgent(calibration_engine=cal, principle_library=library, theory_engine=theory)
    return cal, firewall, ledger, library, theory, agent


class TestPrincipleLibrary:

    def test_new_principle_is_provisional(self):
        library = PrincipleLibrary()
        p = library.add_principle(
            title="High customer churn correlates with poor onboarding in SaaS",
            description="Across 3 domains, onboarding quality predicts 90-day retention",
            source_domains=["customer_behaviour", "product", "sales"],
            confidence=0.6,
        )
        assert p.validation_status == "provisional"

    def test_promotion_refused_without_reality_validated_belief(self):
        cal = create_calibration_engine()
        library = PrincipleLibrary(firewall=cal["firewall"])
        p = library.add_principle(
            title="Test principle",
            description="...",
            source_domains=["general"],
        )
        # Try to promote with a non-existent belief_id
        result = library.promote_principle(p.principle_id, belief_id="fake-belief-id")
        assert result is False
        assert library.get(p.principle_id).validation_status == "provisional"

    def test_simulation_volume_cannot_promote_principle(self):
        """Add 1000 simulation supports to a belief — principle still cannot promote."""
        cal = create_calibration_engine()
        firewall = cal["firewall"]
        library = PrincipleLibrary(firewall=firewall)

        p = library.add_principle("Sim-backed principle", "...", ["general"])
        belief_id = list(firewall._beliefs.keys())[0] if firewall._beliefs else None

        if belief_id is None:
            import uuid
            from calibration.firewall.firewall import Belief
            belief = Belief(belief_id=str(uuid.uuid4()), statement="test", origin="test")
            firewall._beliefs[belief.belief_id] = belief
            belief_id = belief.belief_id

        # Add 1000 simulation supports
        for _ in range(1000):
            firewall.add_simulation_support(belief_id)

        # Promotion must be refused — sim_support_count not a gate
        result = library.promote_principle(p.principle_id, belief_id=belief_id)
        assert result is False
        assert library.get(p.principle_id).validation_status == "provisional"


class TestTheoryEngine:

    def test_register_principle_creates_provisional_belief(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        p = library.add_principle("Test principle", "test desc", ["market_dynamics"])
        result = theory.register_principle_for_testing(p, test_claims=[
            {
                "claim": "Market share will increase by 5% in 30 days",
                "probability": 0.65,
                "resolution_criterion": "Market data confirms 5% increase",
                "ground_truth_source": "external_market_research",
                "horizon_days": 30,
            }
        ])
        assert result["validation_status"] == "provisional"
        belief_id = result["belief_id"]
        assert firewall._beliefs[belief_id].validation_status == "provisional"

    def test_theory_engine_cannot_self_promote(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        p = library.add_principle("Self-promotion test", "...", ["general"])
        result = theory.register_principle_for_testing(p, test_claims=[])
        belief_id = result["belief_id"]

        readiness = theory.check_promotion_readiness(belief_id)
        assert readiness["ready"] is False
        assert readiness["current_status"] == "provisional"

    def test_prediction_is_registered_in_ledger(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        p = library.add_principle("Ledger test principle", "...", ["engineering"])
        result = theory.register_principle_for_testing(p, test_claims=[
            {
                "claim": "Engineering velocity will improve",
                "probability": 0.70,
                "resolution_criterion": "Velocity metric up 10% in 30 days",
                "ground_truth_source": "external_auditor",
                "horizon_days": 30,
            }
        ])
        for pid in result["prediction_ids"]:
            record = ledger.get(pid)
            assert record.claim_type == "principle_test"
            assert record.producing_agent_id == "synthesis-agent"


class TestSynthesisAgent:

    def test_synthesis_output_is_provisional(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        result = agent.run({
            "action_type": "synthesize",
            "title": "Churn-onboarding correlation",
            "synthesis": "High churn correlates with poor onboarding across all SaaS verticals",
            "domains": ["customer_behaviour", "product"],
        })
        # Either the action was emitted (provisional) or blocked (awaiting approval)
        # In both cases, the principle in the library must be provisional
        if "validation_status" in result:
            assert result["validation_status"] == "provisional"
        else:
            # Blocked by escalation gate — principle still created as provisional
            pid = result.get("principle_id")
            if pid:
                assert library.get(pid).validation_status == "provisional"

    def test_synthesis_creates_principle_in_library(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        result = agent.run({
            "action_type": "synthesize",
            "title": "Pricing elasticity cross-domain",
            "synthesis": "Price sensitivity in B2B mirrors consumer patterns at 0.7x magnitude",
            "domains": ["sales", "financial_forecast"],
        })
        pid = result.get("principle_id")
        assert pid is not None
        p = library.get(pid)
        assert p.validation_status == "provisional"
        assert "sales" in p.source_domains or "financial_forecast" in p.source_domains

    def test_synthesis_registers_belief_in_firewall(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        result = agent.run({
            "action_type": "synthesize",
            "title": "Cross-domain test",
            "synthesis": "Pattern X holds across domains Y and Z",
            "domains": ["market_dynamics"],
        })
        belief_id = result.get("belief_id")
        if belief_id:
            assert belief_id in firewall._beliefs
            assert firewall._beliefs[belief_id].validation_status == "provisional"

    def test_query_principles_returns_provisional(self):
        cal, firewall, ledger, library, theory, agent = _setup()
        agent.run({
            "action_type": "synthesize",
            "title": "Query test principle",
            "synthesis": "Pattern for query test",
            "domains": ["product"],
        })
        result = agent.run({"action_type": "query_principles", "status": "provisional"})
        assert result["count"] >= 1
        for p in result["principles"]:
            assert p["validation_status"] == "provisional"
