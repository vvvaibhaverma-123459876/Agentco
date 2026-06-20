"""
Structural Break Detector — detect when calibration shifts using Chow test.

Identifies regime changes in calibration accuracy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

MIN_HISTORY_FOR_BREAK_DETECTION = 20
CHOW_TEST_ALPHA = 0.05  # Significance level


@dataclass
class BreakDetectionResult:
    """Result of structural break detection."""
    detected: bool  # Whether a break was detected
    break_index: Optional[int] = None  # Index where break occurs
    break_date: Optional[datetime] = None  # Approximate date of break
    f_statistic: Optional[float] = None  # Chow test F-statistic
    f_critical: Optional[float] = None  # Critical F value at α=0.05
    action: Optional[str] = None  # Recommended action
    rationale: str = ""


class StructuralBreakDetector:
    """
    Detects regime changes in calibration using Chow test.

    Tests for structural breaks in the relationship between
    stated confidence and outcomes.
    """

    def __init__(self, db=None):
        """Initialize break detector.

        Args:
            db: Optional database connection
        """
        self.db = db

    def detect_break(
        self,
        agent_id: str,
        domain: str,
        horizon: str,
        stated_confidences: list[float],
        outcomes: list[bool],
        lookback_days: int = 180,
        timestamps: Optional[list[datetime]] = None,
    ) -> BreakDetectionResult:
        """
        Detect structural breaks in calibration curve.

        Uses Chow test: fit separate lines to early and late data,
        compare to single line for all data.

        Args:
            agent_id: Subject ID
            domain: Domain
            horizon: Horizon
            stated_confidences: List of stated confidences
            outcomes: List of outcomes (bool)
            lookback_days: Only consider last N days (if timestamps provided)
            timestamps: Optional timestamps for each prediction

        Returns:
            BreakDetectionResult
        """
        if len(stated_confidences) < MIN_HISTORY_FOR_BREAK_DETECTION:
            return BreakDetectionResult(
                detected=False,
                rationale=f"Insufficient history ({len(stated_confidences)} < {MIN_HISTORY_FOR_BREAK_DETECTION})",
            )

        # Filter by lookback window if timestamps provided
        if timestamps:
            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            mask = np.array([ts >= cutoff for ts in timestamps])
            X = np.array(stated_confidences)[mask]
            y = np.array(outcomes, dtype=float)[mask]
            filtered_timestamps = np.array(timestamps)[mask]
        else:
            X = np.array(stated_confidences)
            y = np.array(outcomes, dtype=float)
            filtered_timestamps = None

        if len(X) < MIN_HISTORY_FOR_BREAK_DETECTION:
            return BreakDetectionResult(
                detected=False,
                rationale=f"Insufficient recent history ({len(X)} < {MIN_HISTORY_FOR_BREAK_DETECTION})",
            )

        n = len(X)

        # Try multiple split points (middle 40% of data)
        start_idx = int(n * 0.3)
        end_idx = int(n * 0.7)
        best_f_stat = 0
        best_break_idx = None

        for break_idx in range(start_idx, end_idx):
            f_stat = self._compute_chow_statistic(X, y, break_idx)
            if f_stat > best_f_stat:
                best_f_stat = f_stat
                best_break_idx = break_idx

        # Critical F value: F(2, n-4) at α=0.05
        df1, df2 = 2, n - 4
        f_critical = stats.f.ppf(1 - CHOW_TEST_ALPHA, df1, df2)

        if best_f_stat > f_critical and best_break_idx is not None:
            # Break detected
            if filtered_timestamps is not None:
                break_date = filtered_timestamps[best_break_idx]
            else:
                break_date = datetime.now(timezone.utc)

            return BreakDetectionResult(
                detected=True,
                break_index=best_break_idx,
                break_date=break_date,
                f_statistic=float(best_f_stat),
                f_critical=float(f_critical),
                action="RETRAIN_FROM_BREAK_POINT",
                rationale=(
                    f"Chow test F={best_f_stat:.3f} > F_crit={f_critical:.3f} at α={CHOW_TEST_ALPHA}. "
                    f"Structural break at index {best_break_idx}. "
                    f"Recommend retraining from this point."
                ),
            )
        else:
            # No break detected
            return BreakDetectionResult(
                detected=False,
                f_statistic=float(best_f_stat),
                f_critical=float(f_critical),
                rationale=(
                    f"No structural break detected. "
                    f"Best F={best_f_stat:.3f} < F_crit={f_critical:.3f}."
                ),
            )

    @staticmethod
    def _compute_chow_statistic(X: np.ndarray, y: np.ndarray, break_idx: int) -> float:
        """
        Compute Chow test F-statistic for a given break point.

        Tests: H0 = single regression vs H1 = two separate regressions

        F = (RSS_restricted - RSS_unrestricted) / (k) / (RSS_unrestricted / (n - 2k))
          where k = number of parameters (2 for intercept + slope)

        Args:
            X: Predictor (stated confidence)
            y: Response (outcome)
            break_idx: Index to split at

        Returns:
            F-statistic
        """
        # Add intercept column
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        # Full regression
        try:
            beta_full = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            y_pred_full = X_with_intercept @ beta_full
            rss_full = np.sum((y - y_pred_full) ** 2)
        except np.linalg.LinAlgError:
            return 0.0

        # Split regression
        try:
            X1 = X_with_intercept[:break_idx]
            y1 = y[:break_idx]
            X2 = X_with_intercept[break_idx:]
            y2 = y[break_idx:]

            beta1 = np.linalg.lstsq(X1, y1, rcond=None)[0]
            beta2 = np.linalg.lstsq(X2, y2, rcond=None)[0]

            y_pred1 = X1 @ beta1
            y_pred2 = X2 @ beta2
            rss_split = np.sum((y1 - y_pred1) ** 2) + np.sum((y2 - y_pred2) ** 2)
        except np.linalg.LinAlgError:
            return 0.0

        # Chow statistic
        k = 2  # intercept + slope
        n = len(X)
        numerator = (rss_full - rss_split) / k
        denominator = rss_split / (n - 2 * k)

        if denominator <= 0:
            return 0.0

        f_stat = numerator / denominator
        return float(max(f_stat, 0.0))
