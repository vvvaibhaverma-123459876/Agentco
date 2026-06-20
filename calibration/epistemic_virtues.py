"""Epistemic virtue tracking (Phase 2)."""
from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)


class EpistemicVirtueTracker:
    """Track honesty, humility, courage."""

    def __init__(self, db=None):
        self.db = db

    def honesty_score(self, agent_id: str, predictions: list[dict]) -> float:
        """Honesty: negative of overconfidence."""
        if not predictions:
            return 0.0

        overconfidence_sum = 0.0
        for pred in predictions:
            stated = pred.get("stated_confidence", 0.5)
            curve_pred = pred.get("curve_prediction", 0.5)
            overconfidence = max(0, stated - curve_pred)
            overconfidence_sum += overconfidence

        avg_overconfidence = overconfidence_sum / len(predictions)
        return -avg_overconfidence  # Negative because overconfidence is bad

    def intellectual_humility_score(self, agent_id: str, predictions: list[dict]) -> float:
        """Humility: dispersion + calibration."""
        if not predictions:
            return 0.0

        confidences = [p.get("stated_confidence", 0.5) for p in predictions]
        dispersion = float(np.std(confidences))

        # Calibration component: compute ECE
        outcomes = [p.get("outcome", 0.5) for p in predictions]
        ece = float(np.mean(np.abs(np.array(confidences) - np.array(outcomes))))
        calibration = 1.0 - ece

        return 0.3 * dispersion + 0.7 * calibration

    def intellectual_courage_score(self, agent_id: str, belief_updates: list[dict]) -> float:
        """Courage: rate of significant updates (simplified)."""
        # Placeholder: return neutral score
        # Full implementation tracks actual belief changes
        return 0.5
