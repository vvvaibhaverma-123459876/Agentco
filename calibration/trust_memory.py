"""Trust memory and trajectory (Phase 3)."""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass
class TrustTrajectory:
    """Result of trust trajectory analysis."""
    trajectory: list[float]
    trend: float
    volatility: float
    recent_trust: float
    interpretation: str  # 'improving', 'stable', 'degrading'


class TrustMemoryEngine:
    """Track trust over time."""

    def __init__(self, db=None):
        self.db = db
        self.trust_history: dict[str, list[tuple[datetime, float]]] = {}

    def add_trust_observation(self, agent_id: str, trust_value: float) -> None:
        """Record trust observation."""
        if agent_id not in self.trust_history:
            self.trust_history[agent_id] = []
        self.trust_history[agent_id].append((datetime.now(timezone.utc), trust_value))

    def trust_trajectory(self, agent_id: str, domain: str = "general", days: int = 365) -> TrustTrajectory:
        """Compute trust trajectory."""
        if agent_id not in self.trust_history or len(self.trust_history[agent_id]) < 3:
            return TrustTrajectory(
                trajectory=[],
                trend=0.0,
                volatility=0.0,
                recent_trust=0.5,
                interpretation="stable",
            )

        # Get observations within lookback
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        obs = [
            (ts, val) for ts, val in self.trust_history[agent_id]
            if ts >= cutoff
        ]

        if len(obs) < 3:
            return TrustTrajectory(
                trajectory=[],
                trend=0.0,
                volatility=0.0,
                recent_trust=0.5,
                interpretation="stable",
            )

        values = np.array([val for _, val in obs])

        # Compute trend via linear regression (simplified)
        x = np.arange(len(values))
        if len(x) > 1:
            coeffs = np.polyfit(x, values, 1)
            trend = float(coeffs[0])
        else:
            trend = 0.0

        volatility = float(np.std(values))
        recent_trust = float(values[-1])

        # Interpretation
        if trend > 0.05:
            interpretation = "improving"
        elif trend < -0.02:
            interpretation = "degrading"
        else:
            interpretation = "stable"

        return TrustTrajectory(
            trajectory=values.tolist(),
            trend=trend,
            volatility=volatility,
            recent_trust=recent_trust,
            interpretation=interpretation,
        )

    def trust_repair_capability(self, agent_id: str, domain: str = "general") -> str:
        """Assess ability to repair trust."""
        trajectory = self.trust_trajectory(agent_id, domain)

        if trajectory.trend > 0.05:
            return "high"
        elif trajectory.trend > -0.02:
            return "medium"
        else:
            return "low"
