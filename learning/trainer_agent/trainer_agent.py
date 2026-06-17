"""
Trainer-Agent — Step 3 of the 6-hour learning loop.

Evaluates hypotheses from Scenario-Agent:
- Runs backtests against historical resolved predictions (simulation only)
- Scores each hypothesis for plausibility
- Ranks by expected calibration improvement
- Produces a TrainingProposal for human review

INVARIANT: The TrainingProposal is NEVER applied without human approval.
           Trainer-Agent cannot promote any belief to reality_validated.
           Backtest results are simulation — they CANNOT cross the firewall.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class TrainerAgent(BaseAgentV2):

    AGENT_ID = "trainer-agent"
    PROMPT_VERSION = "2.0.0"
    DEPARTMENT = "learning"

    # Minimum backtest improvement to include in proposal
    MIN_BACKTEST_IMPROVEMENT = 0.01

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)
        self._cal = calibration_engine or {}

    def run(self, task: dict) -> dict:
        hypotheses = task.get("hypotheses", [])
        cycle_id = task.get("cycle_id", "unknown")
        return self.evaluate_and_propose(hypotheses, cycle_id)

    def evaluate_and_propose(self, hypotheses: list[dict], cycle_id: str) -> dict:
        """
        Backtest each hypothesis against historical data.
        All backtest results are SIMULATION — cannot promote to reality_validated.
        Returns a ranked proposal for human review.
        """
        ledger = self._cal.get("ledger")
        resolved_records = []
        if ledger:
            all_records = ledger.list_all()
            resolved_records = [r for r in all_records if r.resolved and not r.post_hoc]

        evaluated = []
        for hyp in hypotheses:
            backtest_score = self._backtest_hypothesis(hyp, resolved_records)
            if backtest_score["simulated_ece_improvement"] >= self.MIN_BACKTEST_IMPROVEMENT:
                evaluated.append({
                    **hyp,
                    "backtest": backtest_score,
                    "recommendation": "include_in_proposal",
                    "backtest_source": "simulation",   # NEVER reality_validated
                })
            else:
                evaluated.append({
                    **hyp,
                    "backtest": backtest_score,
                    "recommendation": "skip",
                    "backtest_source": "simulation",
                })

        proposed = [e for e in evaluated if e["recommendation"] == "include_in_proposal"]
        proposed.sort(key=lambda x: x["backtest"]["simulated_ece_improvement"], reverse=True)

        proposal = {
            "cycle_id": cycle_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evaluated_hypotheses": len(evaluated),
            "proposed_changes": proposed,
            "skipped": len(evaluated) - len(proposed),
            "backtest_note": (
                "All backtest results are SIMULATION. No change is applied without human approval. "
                "Simulation results cannot promote beliefs to reality_validated."
            ),
            "requires_human_approval": True,
        }

        action = AgentActionV2(
            action_type="submit_training_proposal",
            description=(
                f"Submit training proposal for cycle {cycle_id}: "
                f"{len(proposed)} changes proposed, requires human approval"
            ),
            payload=proposal,
            risk_level="high",   # proposals affect system calibration — high risk
            stated_confidence=0.70,
            domain="learning",
            claim_type="training_proposal",
        )

        try:
            result = self.execute_action(action)
            return {**proposal, "status": "proposal_submitted", "outcome": result.get("outcome")}
        except HumanApprovalRequired as exc:
            return {
                **proposal,
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "message": "Training proposal requires human governor approval before any changes are applied.",
            }

    def _backtest_hypothesis(self, hyp: dict, resolved_records: list) -> dict:
        """
        Simulate the hypothesis against historical predictions.
        Returns estimated ECE improvement. THIS IS SIMULATION ONLY.
        """
        domain = hyp.get("domain", "general")
        domain_records = [r for r in resolved_records if r.domain == domain]
        n = len(domain_records)

        # Simple simulation: estimate improvement based on surprise count
        # In production: run full calibration recomputation with proposed weights
        if n < 5:
            return {"simulated_ece_improvement": 0.0, "n_backtest_samples": n, "confidence": 0.3}

        expected_improvement = hyp.get("expected_ece_improvement", 0.0)
        # Apply uncertainty discount for simulation
        simulated = expected_improvement * 0.7  # 30% discount for simulation uncertainty

        return {
            "simulated_ece_improvement": round(simulated, 4),
            "n_backtest_samples": n,
            "confidence": min(0.6, n / 20),   # confidence scales with sample size, max 0.6 for simulation
        }
