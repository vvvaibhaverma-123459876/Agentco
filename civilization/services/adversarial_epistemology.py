"""Adversarial epistemology: detect attacks (Phase 5)."""
from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)


class AdversarialEpistemologyEngine:
    """Detect Byzantine attacks and arms races."""

    def detect_arms_race(self, institution_id: str, attack_history: list[dict], lookback_days: int = 180) -> dict:
        """
        Detect arms race escalation.

        Args:
            institution_id: Institution ID
            attack_history: list of {date, sophistication_score, attack_type}
            lookback_days: Historical window

        Returns:
            {detected, attack_sophistication, escalation_rate}
        """
        if len(attack_history) < 3:
            return {
                "detected": False,
                "attack_sophistication": 0.0,
                "escalation_rate": 0.0,
                "rationale": "Insufficient attack history",
            }

        # Extract sophistication scores
        scores = np.array([a.get("sophistication_score", 0.0) for a in attack_history])

        # Recent vs historical
        if len(scores) >= 10:
            historical_mean = np.mean(scores[:-10])
            recent_mean = np.mean(scores[-10:])
        else:
            historical_mean = np.mean(scores[:-2]) if len(scores) > 2 else scores[0]
            recent_mean = np.mean(scores[-2:])

        escalation_rate = (recent_mean - historical_mean) / (historical_mean + 1e-6)

        detected = escalation_rate > 0.1 or recent_mean > 0.7

        return {
            "detected": detected,
            "attack_sophistication": float(recent_mean),
            "escalation_rate": float(escalation_rate),
            "rationale": f"Recent sophistication: {recent_mean:.2f}, escalation: {escalation_rate:.2f}x",
        }
