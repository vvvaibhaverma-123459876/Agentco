"""
Calibrated Trust Curves — continuous isotonic regression with confidence intervals.

Replaces fixed bins with smooth curves + CI bands + confidence measures.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)

MIN_SAMPLES_TO_FIT = 5
REFIT_INTERVAL = 3  # Only refit if n_samples % 3 == 0 and n >= 5
CONSERVATIVE_MULTIPLIER = 0.8
SMALL_SAMPLE_CI_WIDTH = 0.25


@dataclass
class CalibrationResult:
    """Result of trust curve query."""
    point_estimate: float  # Best estimate of true confidence
    lower_ci: float  # Lower confidence interval bound [0, 1]
    upper_ci: float  # Upper confidence interval bound [0, 1]
    confidence: float  # Confidence in the estimate [0, 1]
    n_samples: int  # How many samples back this estimate
    method: str = "isotonic_regression"


@dataclass
class _CurveState:
    """Internal state of a calibration curve."""
    agent_id: str
    domain: str
    horizon: str
    stated_confidences: list[float] = field(default_factory=list)
    outcomes: list[bool] = field(default_factory=list)
    isotonic_model: Optional[IsotonicRegression] = None
    last_fitted_at: Optional[datetime] = None
    n_fits: int = 0


class CalibratedTrustCurve:
    """
    Isotonic regression-based trust curve with confidence intervals.

    Learns a continuous mapping from stated confidence → true confidence
    by fitting isotonic regression to (stated_confidence, outcome) pairs.
    """

    def __init__(self, agent_id: str, domain: str, horizon: str):
        """
        Initialize a calibration curve.

        Args:
            agent_id: Subject ID
            domain: Domain (e.g., 'biology', 'finance')
            horizon: Time horizon (e.g., 'short', 'medium', 'long')
        """
        self.agent_id = agent_id
        self.domain = domain
        self.horizon = horizon
        self._state = _CurveState(
            agent_id=agent_id, domain=domain, horizon=horizon
        )

    def update_from_resolution(self, stated_confidence: float, outcome: bool) -> dict:
        """
        Add a resolved prediction to the curve.

        Args:
            stated_confidence: Confidence agent stated [0, 1]
            outcome: Whether the prediction was correct

        Returns:
            dict with 'added', 'n_samples', 'refitted'
        """
        self._state.stated_confidences.append(stated_confidence)
        self._state.outcomes.append(outcome)
        n_samples = len(self._state.stated_confidences)

        refitted = False
        if n_samples >= MIN_SAMPLES_TO_FIT and n_samples % REFIT_INTERVAL == 0:
            self._refit_isotonic()
            refitted = True

        return {
            "added": True,
            "n_samples": n_samples,
            "refitted": refitted,
        }

    def trusted_confidence(self, stated: float) -> CalibrationResult:
        """
        Query the curve: what's the true confidence for this stated confidence?

        Args:
            stated: Stated confidence [0, 1]

        Returns:
            CalibrationResult with point estimate + CI
        """
        n_samples = len(self._state.stated_confidences)

        # Clip input to valid range
        stated = np.clip(stated, 0.0, 1.0)

        if n_samples < MIN_SAMPLES_TO_FIT:
            # Insufficient samples: return conservative estimate with wide CI
            point = stated * CONSERVATIVE_MULTIPLIER
            half_width = SMALL_SAMPLE_CI_WIDTH / 2
            return CalibrationResult(
                point_estimate=np.clip(point, 0.0, 1.0),
                lower_ci=np.clip(point - half_width, 0.0, 1.0),
                upper_ci=np.clip(point + half_width, 0.0, 1.0),
                confidence=0.3 + 0.1 * min(n_samples, 5),
                n_samples=n_samples,
            )

        # Fitted model: predict point estimate
        if self._state.isotonic_model is None:
            # Should not happen if we refitted, but fallback to conservative
            point = stated * CONSERVATIVE_MULTIPLIER
            half_width = SMALL_SAMPLE_CI_WIDTH / 2
            return CalibrationResult(
                point_estimate=np.clip(point, 0.0, 1.0),
                lower_ci=np.clip(point - half_width, 0.0, 1.0),
                upper_ci=np.clip(point + half_width, 0.0, 1.0),
                confidence=0.5,
                n_samples=n_samples,
            )

        # Predict point estimate
        point = float(self._state.isotonic_model.predict([stated])[0])
        point = np.clip(point, 0.0, 1.0)

        # Estimate CI width from residual variance
        y_pred = self._state.isotonic_model.predict(
            self._state.stated_confidences
        )
        residuals = np.array(self._state.outcomes, dtype=float) - y_pred
        residual_std = float(np.std(residuals))

        # CI width: starts at SMALL_SAMPLE_CI_WIDTH, shrinks with sqrt(n)
        ci_width = SMALL_SAMPLE_CI_WIDTH / np.sqrt(
            1 + n_samples / MIN_SAMPLES_TO_FIT
        )
        if residual_std > 0:
            ci_width = min(ci_width, residual_std * 1.96 * 2)

        half_width = ci_width / 2
        lower_ci = np.clip(point - half_width, 0.0, 1.0)
        upper_ci = np.clip(point + half_width, 0.0, 1.0)

        # Confidence: higher with more samples, lower with high residual std
        confidence = min(0.95, 0.5 + 0.45 * np.log(1 + n_samples) / np.log(20))
        if residual_std > 0.2:
            confidence *= 0.8

        return CalibrationResult(
            point_estimate=point,
            lower_ci=lower_ci,
            upper_ci=upper_ci,
            confidence=np.clip(confidence, 0.0, 1.0),
            n_samples=n_samples,
        )

    def _refit_isotonic(self) -> None:
        """Fit isotonic regression to current data."""
        if len(self._state.stated_confidences) < MIN_SAMPLES_TO_FIT:
            return

        # Sort by stated confidence
        sorted_idx = np.argsort(self._state.stated_confidences)
        X = np.array(self._state.stated_confidences)[sorted_idx]
        y = np.array(self._state.outcomes, dtype=float)[sorted_idx]

        self._state.isotonic_model = IsotonicRegression(
            increasing=True, out_of_bounds="clip"
        )
        self._state.isotonic_model.fit(X, y)
        self._state.last_fitted_at = datetime.now(timezone.utc)
        self._state.n_fits += 1

        logger.debug(
            "CALIBRATION: refitted curve for %s/%s (n=%d, fits=%d)",
            self.agent_id, self.domain, len(self._state.stated_confidences),
            self._state.n_fits
        )

    def get_state(self) -> dict:
        """Return current state for inspection."""
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "horizon": self.horizon,
            "n_samples": len(self._state.stated_confidences),
            "n_fits": self._state.n_fits,
            "last_fitted_at": self._state.last_fitted_at,
            "fitted": self._state.isotonic_model is not None,
        }
