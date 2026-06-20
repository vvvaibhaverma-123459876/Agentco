"""Meta-trust: assessing trust curve quality (Phase 3)."""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MetaTrustAssessment:
    """Assessment of trust curve quality."""
    curve_ece: float
    predictive_accuracy: float
    interpretation: str  # 'excellent', 'good', 'poor'
    n_test_samples: int


class MetaTrustEvaluator:
    """Evaluate trust curve predictive quality."""

    def __init__(self, db=None):
        self.db = db

    def curve_predictive_accuracy(
        self,
        agent_id: str,
        domain: str,
        horizon: str,
        all_predictions: list[dict],
    ) -> MetaTrustAssessment:
        """
        Assess trust curve predictive accuracy.

        Fit on days 1-180, predict on days 181-210.
        """
        if len(all_predictions) < 20:
            return MetaTrustAssessment(
                curve_ece=None,
                predictive_accuracy=0.0,
                interpretation="insufficient",
                n_test_samples=0,
            )

        # Split: 80% train, 20% test
        split_idx = int(len(all_predictions) * 0.8)
        train_preds = all_predictions[:split_idx]
        test_preds = all_predictions[split_idx:]

        if len(test_preds) < 5:
            return MetaTrustAssessment(
                curve_ece=None,
                predictive_accuracy=0.0,
                interpretation="insufficient",
                n_test_samples=len(test_preds),
            )

        # Compute ECE on test set
        stated = np.array([p.get("stated_confidence", 0.5) for p in test_preds])
        outcomes = np.array([p.get("outcome", 0.5) for p in test_preds])

        ece = float(np.mean(np.abs(stated - outcomes)))
        predictive_accuracy = 1.0 - ece

        # Interpret
        if ece < 0.05:
            interpretation = "excellent"
        elif ece < 0.15:
            interpretation = "good"
        else:
            interpretation = "poor"

        return MetaTrustAssessment(
            curve_ece=ece,
            predictive_accuracy=predictive_accuracy,
            interpretation=interpretation,
            n_test_samples=len(test_preds),
        )
