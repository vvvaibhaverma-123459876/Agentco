"""
Phase 3 DoD: Continuous Learning Loop tests.

Verifies:
- Full cycle runs: Intelligence → Scenario → Trainer → Memory
- Trainer proposal always blocks for human approval
- Memory writes blocked without human_approved=True
- Memory-Agent never writes reality_validated entries
- apply_approved_proposal() succeeds after human approves
"""
import pytest
from calibration import create_calibration_engine
from learning.intelligence_agent.intelligence_agent import IntelligenceAgent
from learning.scenario_agent.scenario_agent import ScenarioAgent
from learning.trainer_agent.trainer_agent import TrainerAgent
from learning.memory_agent.memory_agent import MemoryAgent
from learning.learning_loop import LearningLoop


def _make_loop(cal=None):
    cal = cal or create_calibration_engine()
    intelligence = IntelligenceAgent(calibration_engine=cal)
    scenario = ScenarioAgent(calibration_engine=cal)
    trainer = TrainerAgent(calibration_engine=cal)
    memory = MemoryAgent(calibration_engine=cal)
    loop = LearningLoop(intelligence, scenario, trainer, memory)
    return loop, cal, memory


class TestIntelligenceAgent:

    def test_analyze_returns_signal_with_required_keys(self):
        cal = create_calibration_engine()
        agent = IntelligenceAgent(calibration_engine=cal)
        signal = agent.analyze_calibration_state("test-cycle-1")

        for key in ["cycle_id", "high_ece_domains", "surprise_patterns",
                    "degraded_agents", "recommended_focus_areas", "n_predictions_analyzed"]:
            assert key in signal

    def test_analyze_empty_ledger_returns_no_surprises(self):
        cal = create_calibration_engine()
        agent = IntelligenceAgent(calibration_engine=cal)
        signal = agent.analyze_calibration_state("test-cycle-2")
        assert signal["n_predictions_analyzed"] == 0
        assert signal["surprise_patterns"] == []


class TestScenarioAgent:

    def test_generates_hypotheses_for_focus_areas(self):
        cal = create_calibration_engine()
        agent = ScenarioAgent(calibration_engine=cal)
        signal = {
            "recommended_focus_areas": ["market_dynamics", "financial_forecast"],
            "degraded_agents": [],
            "surprise_patterns": [],
        }
        result = agent.generate_hypotheses(signal, "test-cycle-3")
        assert result["count"] >= 1
        assert len(result["hypotheses"]) >= 1

    def test_hypotheses_are_pre_registered_in_ledger(self):
        cal = create_calibration_engine()
        agent = ScenarioAgent(calibration_engine=cal)
        signal = {
            "recommended_focus_areas": ["product"],
            "degraded_agents": [],
            "surprise_patterns": [],
        }
        result = agent.generate_hypotheses(signal, "test-cycle-4")
        for hyp in result["hypotheses"]:
            if hyp.get("prediction_id"):
                record = cal["ledger"].get(hyp["prediction_id"])
                assert record.claim_type == "learning_hypothesis"
                break

    def test_hypotheses_are_provisional(self):
        cal = create_calibration_engine()
        agent = ScenarioAgent(calibration_engine=cal)
        signal = {
            "recommended_focus_areas": ["engineering"],
            "degraded_agents": [],
            "surprise_patterns": [],
        }
        result = agent.generate_hypotheses(signal, "test-cycle-5")
        for hyp in result["hypotheses"]:
            assert hyp["status"] == "provisional"
            assert hyp["status"] != "reality_validated"


class TestTrainerAgent:

    def test_proposal_requires_human_approval(self):
        cal = create_calibration_engine()
        agent = TrainerAgent(calibration_engine=cal)
        hypotheses = [
            {
                "hypothesis_id": "h-1",
                "domain": "market_dynamics",
                "description": "Adjust weights",
                "proposed_change": {"type": "trust_weight_adjustment", "domain": "market_dynamics"},
                "expected_ece_improvement": 0.03,
                "confidence": 0.60,
                "prediction_id": None,
            }
        ]
        result = agent.evaluate_and_propose(hypotheses, "test-cycle-6")
        assert result["status"] == "awaiting_human_approval"
        assert result["requires_human_approval"] is True

    def test_backtest_note_warns_about_simulation(self):
        cal = create_calibration_engine()
        agent = TrainerAgent(calibration_engine=cal)
        result = agent.evaluate_and_propose([], "test-cycle-7")
        assert "SIMULATION" in result["backtest_note"]
        assert "reality_validated" in result["backtest_note"]


class TestMemoryAgent:

    def test_write_blocked_without_human_approved(self):
        cal = create_calibration_engine()
        agent = MemoryAgent(calibration_engine=cal)
        result = agent.run({
            "action_type": "store_cycle_outcomes",
            "cycle_id": "c-1",
            "approved_changes": [{"description": "test", "domain": "general", "confidence": 0.5}],
            "human_approved": False,   # NOT approved
        })
        assert result["status"] == "blocked"

    def test_memory_entries_never_reality_validated(self):
        cal = create_calibration_engine()
        agent = MemoryAgent(calibration_engine=cal)
        agent.run({
            "action_type": "store_cycle_outcomes",
            "cycle_id": "c-2",
            "approved_changes": [{"description": "test entry", "domain": "product", "confidence": 0.6}],
            "proposal_id": "prop-1",
            "human_approved": True,
        })
        retrieve = agent.run({"action_type": "retrieve", "domain": "product"})
        for entry in retrieve["entries"]:
            assert entry["validation_status"] != "reality_validated"
            assert entry["validation_status"] == "provisional"

    def test_retrieve_note_warns_about_provisional(self):
        cal = create_calibration_engine()
        agent = MemoryAgent(calibration_engine=cal)
        result = agent.run({"action_type": "retrieve"})
        assert "provisional" in result["note"].lower()
        assert "reality_validated" in result["note"]


class TestLearningLoop:

    def test_full_cycle_runs(self):
        loop, cal, memory = _make_loop()
        result = loop.run_cycle()
        assert "cycle_id" in result
        assert "signal" in result
        assert "trainer" in result

    def test_cycle_requires_human_approval(self):
        loop, cal, memory = _make_loop()
        result = loop.run_cycle()
        assert result["awaiting_human_approval"] is True

    def test_apply_approved_proposal_writes_memory(self):
        loop, cal, memory = _make_loop()
        cycle_result = loop.run_cycle()
        cycle_id = cycle_result["cycle_id"]

        apply_result = loop.apply_approved_proposal(
            cycle_id=cycle_id,
            approved_changes=[{
                "description": "Apply trust weight adjustment for general domain",
                "domain": "general",
                "confidence": 0.60,
            }],
            proposal_id="prop-test-1",
            approved_by="human-governor-1",
        )
        assert apply_result["status"] == "memory_updated"
        assert apply_result["validation_status"] == "provisional"

    def test_cycle_log_records_unapplied_state(self):
        loop, cal, memory = _make_loop()
        result = loop.run_cycle()
        cycle_id = result["cycle_id"]
        log = loop.get_cycle_log()
        entry = next(e for e in log if e["cycle_id"] == cycle_id)
        assert entry["applied"] is False   # not applied until human approves
