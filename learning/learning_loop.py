"""
LearningLoop — orchestrates the 6-hour cycle.

Cycle: Intelligence → Scenario → Trainer → [Human gate] → Memory

The human gate is mandatory. The loop does not auto-apply any changes.
If no human approves the TrainingProposal within the cycle window,
it is logged as deferred and the cycle ends without effect.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class LearningLoop:

    CYCLE_HOURS = 6

    def __init__(
        self,
        intelligence_agent,
        scenario_agent,
        trainer_agent,
        memory_agent,
    ):
        self._intelligence = intelligence_agent
        self._scenario = scenario_agent
        self._trainer = trainer_agent
        self._memory = memory_agent
        self._cycle_log: list[dict] = []

    def run_cycle(self, external_signal: Optional[dict] = None) -> dict:
        """
        Run one 6-hour learning cycle.
        Returns cycle result. Memory writes only happen if human_approved=True
        is passed in a subsequent call to apply_approved_proposal().
        """
        cycle_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info("LEARNING LOOP: starting cycle %s", cycle_id)

        # Step 1: Intelligence
        signal = self._intelligence.analyze_calibration_state(cycle_id)

        # Step 2: Scenario
        scenario_result = self._scenario.generate_hypotheses(signal, cycle_id)
        hypotheses = scenario_result.get("hypotheses", [])

        # Step 3: Trainer (produces a proposal requiring human approval)
        trainer_result = self._trainer.evaluate_and_propose(hypotheses, cycle_id)

        cycle_record = {
            "cycle_id": cycle_id,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "signal_focus_areas": signal.get("recommended_focus_areas", []),
            "hypotheses_generated": len(hypotheses),
            "proposal_status": trainer_result.get("status"),
            "proposal_override_id": trainer_result.get("override_id"),
            "changes_proposed": len(trainer_result.get("proposed_changes", [])),
            "applied": False,   # only True after human approves + apply_approved_proposal() called
        }
        self._cycle_log.append(cycle_record)

        logger.info(
            "LEARNING LOOP: cycle %s complete — %d hypotheses, proposal status=%s",
            cycle_id, len(hypotheses), trainer_result.get("status")
        )

        return {
            "cycle_id": cycle_id,
            "signal": signal,
            "scenario": scenario_result,
            "trainer": trainer_result,
            "awaiting_human_approval": trainer_result.get("status") == "awaiting_human_approval",
        }

    def apply_approved_proposal(
        self,
        cycle_id: str,
        approved_changes: list[dict],
        proposal_id: str,
        approved_by: str,
    ) -> dict:
        """
        Called by a human governor after approving the TrainingProposal.
        Writes to Memory-Agent with human_approved=True.
        """
        logger.info(
            "LEARNING LOOP: human %s approved proposal %s for cycle %s",
            approved_by, proposal_id, cycle_id
        )

        result = self._memory.run({
            "action_type": "store_cycle_outcomes",
            "cycle_id": cycle_id,
            "approved_changes": approved_changes,
            "proposal_id": proposal_id,
            "human_approved": True,
        })

        # Update cycle log
        for record in self._cycle_log:
            if record["cycle_id"] == cycle_id:
                record["applied"] = result.get("status") == "memory_updated"
                record["approved_by"] = approved_by
                record["proposal_id"] = proposal_id

        return result

    def get_cycle_log(self) -> list[dict]:
        return list(self._cycle_log)
