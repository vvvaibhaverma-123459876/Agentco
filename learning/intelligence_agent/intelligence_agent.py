"""
Intelligence-Agent — Step 1 of the 6-hour learning loop.

Reads the calibration ledger and surprise register to identify:
- Domains/horizons with highest calibration error
- Patterns in surprise events
- Agents with degraded trust scores

Produces a LearningSignal: a ranked list of areas where the system's
predictions are least calibrated. Does NOT propose changes — that's Scenario-Agent.
All findings are provisional until backed by sufficient resolved predictions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

if TYPE_CHECKING:
    from calibration.scoring.scoring_module import CalibrationReport

logger = logging.getLogger(__name__)


@dataclass
class LearningSignal:
    generated_at: datetime
    cycle_id: str
    high_ece_domains: list[dict]          # domains with ECE > 0.10
    surprise_patterns: list[dict]         # clusters of surprise events
    degraded_agents: list[dict]           # agents with trust_factor < 0.5
    recommended_focus_areas: list[str]    # what Scenario-Agent should probe
    confidence: float                     # trusted_confidence of this signal
    n_predictions_analyzed: int


class IntelligenceAgent(BaseAgentV2):

    AGENT_ID = "intelligence-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-sonnet-4-6"
    DEPARTMENT = "learning"

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)
        self._cal = calibration_engine or {}

    def run(self, task: dict):
        return self.analyze_calibration_state(task.get("cycle_id", "unknown"))

    def analyze_calibration_state(self, cycle_id: str) -> dict:
        """
        Scan calibration ledger + surprise register for weak spots.
        Returns a LearningSignal dict. Does not propose any changes.
        """
        scoring = self._cal.get("scoring")
        surprise = self._cal.get("surprise")
        trust = self._cal.get("trust")
        ledger = self._cal.get("ledger")

        all_records = ledger.list_all() if ledger else []
        resolved = [r for r in all_records if r.resolved and not r.post_hoc]
        n_resolved = len(resolved)

        # Analyze calibration report
        high_ece_domains = []
        if scoring and n_resolved >= 5:
            report = scoring.calibration_report(resolved)
            if report.ece and report.ece > 0.10:
                high_ece_domains.append({
                    "domain": "overall",
                    "ece": report.ece,
                    "n": n_resolved,
                })

        # Analyze surprise events
        surprise_events = surprise.list_all() if surprise else []
        uninvestigated = [s for s in surprise_events if not s.investigated]
        surprise_patterns = []
        if uninvestigated:
            # Group by domain
            by_domain: dict[str, list] = {}
            for s in uninvestigated:
                by_domain.setdefault(s.domain, []).append(s)
            for domain, events in by_domain.items():
                if len(events) >= 2:
                    surprise_patterns.append({
                        "domain": domain,
                        "count": len(events),
                        "avg_score": sum(e.surprise_score for e in events) / len(events),
                    })

        # Degraded agents
        degraded_agents = []
        if trust:
            for key, score in trust._scores.items():
                if score.trusted_multiplier < 0.5:
                    degraded_agents.append({
                        "agent_id": score.subject_id,
                        "domain": score.domain,
                        "trust_factor": score.trusted_multiplier,
                        "n_resolved": score.n_resolved,
                    })

        focus_areas = (
            [d["domain"] for d in high_ece_domains]
            + [p["domain"] for p in surprise_patterns]
            + list({a["domain"] for a in degraded_agents})
        )

        signal = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cycle_id": cycle_id,
            "high_ece_domains": high_ece_domains,
            "surprise_patterns": surprise_patterns,
            "degraded_agents": degraded_agents,
            "recommended_focus_areas": list(set(focus_areas)),
            "n_predictions_analyzed": n_resolved,
            "status": "signal_ready",
        }

        action = AgentActionV2(
            action_type="emit_learning_signal",
            description=f"Emit learning signal for cycle {cycle_id}: {len(focus_areas)} focus areas identified",
            payload=signal,
            risk_level="low",
            stated_confidence=0.80,
            domain="learning",
            claim_type="calibration_analysis",
        )

        try:
            result = self.execute_action(action)
            return {**signal, "envelope": result.get("envelope")}
        except HumanApprovalRequired as exc:
            return {**signal, "status": "awaiting_human_approval", "override_id": exc.override_id}
