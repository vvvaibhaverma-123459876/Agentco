"""
Metacalibration Engine — score how well calibration curves predict future accuracy.

Measures ECE (Expected Calibration Error) on held-out test set and applies penalties.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)

ECE_EXCELLENT_THRESHOLD = 0.05
ECE_GOOD_THRESHOLD = 0.15
ECE_PENALTY_BASE = 2.0


@dataclass
class MetacalibrationScore:
    """Result of metacalibration assessment."""
    metacalibration_ece: Optional[float]  # Expected Calibration Error [0, 1]
    interpretation: str  # 'excellent' | 'good' | 'poor' | 'insufficient'
    penalty: float  # Multiplier to widen CI bands
    rationale: str


class MetacalibrationEngine:
    """
    Scores how well a calibration curve generalizes to new data.

    Uses train/test split:
    - Fit on first half of data
    - Measure ECE on second half
    - Wider CI bands if ECE is poor
    """

    def __init__(self, db=None):
        """Initialize metacalibration engine.

        Args:
            db: Optional database connection (reserved for future persistence)
        """
        self.db = db

    def score_curve_accuracy(
        self, agent_id: str, domain: str, horizon: str,
        stated_confidences: list[float], outcomes: list[bool]
    ) -> dict:
        """
        Score how well a calibration curve predicts on held-out data.

        Args:
            agent_id: Subject ID
            domain: Domain
            horizon: Time horizon
            stated_confidences: List of stated confidences
            outcomes: List of outcomes (bool)

        Returns:
            dict with metacalibration_ece, interpretation, penalty, rationale
        """
        if len(stated_confidences) < 10:
            return {
                "metacalibration_ece": None,
                "interpretation": "insufficient",
                "penalty": 0.0,
                "rationale": f"Need ≥10 samples; have {len(stated_confidences)}",
            }

        # Split: first half for training, second half for testing
        split_idx = len(stated_confidences) // 2
        X_train = np.array(stated_confidences[:split_idx])
        y_train = np.array(outcomes[:split_idx], dtype=float)
        X_test = np.array(stated_confidences[split_idx:])
        y_test = np.array(outcomes[split_idx:], dtype=float)

        # Fit isotonic model on train set
        try:
            model = IsotonicRegression(increasing=True, out_of_bounds="clip")
            model.fit(X_train, y_train)

            # Predict on test set
            y_pred = model.predict(X_test)

            # Compute ECE: mean absolute difference between confidence and accuracy
            ece = float(np.mean(np.abs(X_test - y_pred)))

        except Exception as e:
            logger.warning(
                "METACALIBRATION: failed to score curve %s/%s: %s",
                agent_id, domain, e
            )
            return {
                "metacalibration_ece": None,
                "interpretation": "error",
                "penalty": 0.5,
                "rationale": f"Error fitting curve: {e}",
            }

        # Interpret ECE
        if ece < ECE_EXCELLENT_THRESHOLD:
            interpretation = "excellent"
        elif ece < ECE_GOOD_THRESHOLD:
            interpretation = "good"
        else:
            interpretation = "poor"

        # Compute penalty: widen CI bands for poor calibration
        penalty = ECE_PENALTY_BASE * max(0, ece - ECE_EXCELLENT_THRESHOLD)

        result = {
            "metacalibration_ece": ece,
            "interpretation": interpretation,
            "penalty": float(penalty),
            "rationale": (
                f"ECE={ece:.4f} on {len(X_test)} test samples. "
                f"Train on {len(X_train)} samples. "
                f"Penalty={penalty:.3f} (widen CI by this factor)."
            ),
        }

        logger.debug(
            "METACALIBRATION: %s/%s ECE=%.4f interpretation=%s penalty=%.3f",
            agent_id, domain, ece, interpretation, penalty
        )

        return result

    def penalty_for_poor_metacalibration(
        self, agent_id: str, domain: str, horizon: str,
        stated_confidences: list[float], outcomes: list[bool]
    ) -> float:
        """
        Get the CI-widening penalty for poor metacalibration.

        Args:
            agent_id: Subject ID
            domain: Domain
            horizon: Time horizon
            stated_confidences: List of stated confidences
            outcomes: List of outcomes

        Returns:
            float: Penalty factor to multiply CI width by (0 = no penalty, 1+ = widen)
        """
        score = self.score_curve_accuracy(
            agent_id, domain, horizon, stated_confidences, outcomes
        )
        return score["penalty"]

    def get_interpretation(self, ece: float) -> str:
        """
        Interpret an ECE value.

        Args:
            ece: Expected Calibration Error

        Returns:
            Interpretation string
        """
        if ece < ECE_EXCELLENT_THRESHOLD:
            return "excellent"
        elif ece < ECE_GOOD_THRESHOLD:
            return "good"
        else:
            return "poor"
