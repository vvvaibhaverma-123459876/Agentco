"""
Trust Controller — the single authoritative source of trusted confidence.

Decision-weighting MUST call trusted_confidence() here.
Agents' raw stated confidence is NEVER used directly for decisions.

trusted_confidence(stated, subject, domain, claim_type, horizon)
  → applies the reliability curve for (subject × domain × claim_type × horizon)
  → returns a calibrated multiplied confidence value with confidence intervals

Uses Phase 1 Advanced Calibration:
  - Continuous isotonic regression curves (no fixed bins)
  - Metacalibration scoring (ECE-based penalties)
  - Structural break detection (regime shifts)
  - Domain transfer (cross-domain generalization)
  - Skill vs luck decomposition

Mechanical downgrade propagation:
  If subject X's track record degrades, ALL downstream consumers that weight
  X's outputs must be notified — the downgrade propagates without requiring
  any agent to manually update anything.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionRecord

from calibration.calibration_curves import CalibratedTrustCurve
from calibration.metacalibration import MetacalibrationEngine
from calibration.structural_breaks import StructuralBreakDetector
from calibration.domain_transfer import DomainTransferCalibrator
from calibration.skill_luck import SkillVsLuckAnalyzer

logger = logging.getLogger(__name__)

# Minimum ECE before we apply a trust penalty
ECE_PENALTY_THRESHOLD = 0.10
ECE_PENALTY_RATE = 0.5  # 50% penalty per 0.1 ECE above threshold


@dataclass
class TrustScore:
    subject_type: str   # 'agent' | 'principle' | 'theory' | 'sim_model' | 'source'
    subject_id: str
    domain: str
    claim_type: str
    horizon_class: str
    stated_to_real: dict[str, float] = field(default_factory=dict)  # bin -> realised accuracy
    trusted_multiplier: float = 1.0
    ece: float = 0.0
    n_resolved: int = 0
    last_reality_contact: Optional[datetime] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TrustController:
    """
    The trust authority. Downstream agents call trusted_confidence().
    The Resolution Service calls ingest_resolution() after scoring.

    Integrated with Phase 1 Advanced Calibration for continuous curves and CI bands.
    """

    MIN_SAMPLES_FOR_TRUST = 5  # below this, return stated confidence with a penalty

    def __init__(self):
        self._scores: dict[tuple, TrustScore] = {}
        self._downgrade_callbacks: list[callable] = []

        # Phase 1 Advanced Calibration engines
        self._calibrated_curves: dict[tuple, CalibratedTrustCurve] = {}
        self.metacalibration_engine = MetacalibrationEngine()
        self.structural_break_detector = StructuralBreakDetector()
        self.domain_transfer_calibrator = DomainTransferCalibrator()
        self.skill_luck_analyzer = SkillVsLuckAnalyzer()

    def trusted_confidence(
        self,
        stated: float,
        subject_id: str,
        subject_type: str,
        domain: str,
        claim_type: str = "general",
        horizon_class: str = "medium",
        return_advanced: bool = False,
    ) -> float | dict:
        """
        THE FUNCTION that decision-weighting must call. Never use stated confidence directly.

        Returns a float in [0,1] representing calibrated trusted confidence.
        If return_advanced=True, returns dict with point_estimate, CI bands, confidence, etc.

        Uses Phase 1 Advanced Calibration when available (continuous curves + CI).
        Falls back to legacy bin-based approach if advanced curves not fitted.
        """
        key = (subject_type, subject_id, domain, claim_type, horizon_class)
        score = self._scores.get(key)
        curve_key = (subject_id, domain, horizon_class)

        # Try to get or create advanced calibration curve
        if curve_key not in self._calibrated_curves:
            self._calibrated_curves[curve_key] = CalibratedTrustCurve(
                subject_id, domain, horizon_class
            )
        curve = self._calibrated_curves[curve_key]

        if score is None or score.n_resolved < self.MIN_SAMPLES_FOR_TRUST:
            # Insufficient track record — apply a conservative penalty
            if score is None:
                penalty = 0.8
            else:
                penalty = max(0.8 - 0.04 * min(score.n_resolved, 5), 0.6)
            trusted = stated * penalty
            logger.debug(
                "TRUST: %s/%s insufficient track record (n=%d) — applying %.0f%% penalty → trusted=%.3f",
                subject_id, domain, score.n_resolved if score else 0, penalty * 100, trusted
            )
            if return_advanced:
                return {
                    "point_estimate": round(min(max(trusted, 0.0), 1.0), 4),
                    "lower_ci": round(min(max(trusted - 0.125, 0.0), 1.0), 4),
                    "upper_ci": round(min(max(trusted + 0.125, 0.0), 1.0), 4),
                    "confidence": 0.4,
                    "method": "legacy_penalty",
                }
            return round(min(max(trusted, 0.0), 1.0), 4)

        # Use advanced calibration curve if fitted
        calibration_result = curve.trusted_confidence(stated)

        # Apply metacalibration penalty if available
        stated_list = list(score.stated_to_real.keys())
        if len(stated_list) >= 10:
            penalty = self.metacalibration_engine.penalty_for_poor_metacalibration(
                subject_id, domain, horizon_class, stated_list,
                [score.stated_to_real[k] > 0.5 for k in stated_list]
            )
            ci_width = calibration_result.upper_ci - calibration_result.lower_ci
            widened_ci = ci_width * (1 + penalty)
            point = calibration_result.point_estimate
            result_dict = {
                "point_estimate": round(point, 4),
                "lower_ci": round(min(max(point - widened_ci / 2, 0.0), 1.0), 4),
                "upper_ci": round(min(max(point + widened_ci / 2, 0.0), 1.0), 4),
                "confidence": round(calibration_result.confidence * 0.9, 4),
                "metacalibration_penalty": round(penalty, 4),
                "method": "advanced_calibration_v1",
            }
        else:
            result_dict = {
                "point_estimate": round(calibration_result.point_estimate, 4),
                "lower_ci": round(calibration_result.lower_ci, 4),
                "upper_ci": round(calibration_result.upper_ci, 4),
                "confidence": round(calibration_result.confidence, 4),
                "method": "advanced_calibration_v1",
            }

        if return_advanced:
            return result_dict

        # For backward compatibility, return scalar (point estimate)
        trusted = result_dict["point_estimate"]
        logger.debug(
            "TRUST: %s/%s stated=%.3f → point_estimate=%.3f CI=[%.3f,%.3f] method=%s",
            subject_id, domain, stated, result_dict["point_estimate"],
            result_dict["lower_ci"], result_dict["upper_ci"], result_dict["method"]
        )
        return trusted

    def ingest_resolution(self, record: "PredictionRecord") -> None:
        """
        Called by Resolution Service after scoring. Updates the reliability curve
        and propagates downgrades to all registered consumers.

        Also feeds into Phase 1 Advanced Calibration curves for continuous modeling.
        """
        if record.post_hoc:
            logger.warning("TRUST: skipping post_hoc resolution for trust update: %s", record.prediction_id)
            return

        key = ("agent", record.producing_agent_id, record.domain, record.claim_type, record.horizon_class)
        score = self._scores.setdefault(key, TrustScore(
            subject_type="agent", subject_id=record.producing_agent_id,
            domain=record.domain, claim_type=record.claim_type, horizon_class=record.horizon_class,
        ))

        prior_trusted = self.trusted_confidence(
            stated=record.probability,
            subject_id=record.producing_agent_id,
            subject_type="agent",
            domain=record.domain,
            claim_type=record.claim_type,
            horizon_class=record.horizon_class,
        )

        # Update legacy bin-based reliability tracking
        bin_key = f"{min(int(record.probability * 10) / 10, 0.9):.1f}"
        old_realised = score.stated_to_real.get(bin_key, record.probability)
        n = score.n_resolved
        # Incremental mean update
        score.stated_to_real[bin_key] = (old_realised * n + (1.0 if record.resolved_outcome else 0.0)) / (n + 1)
        score.n_resolved += 1
        score.last_reality_contact = datetime.now(timezone.utc)
        score.updated_at = datetime.now(timezone.utc)

        # Update Phase 1 Advanced Calibration curve
        curve_key = (record.producing_agent_id, record.domain, record.horizon_class)
        if curve_key in self._calibrated_curves:
            curve = self._calibrated_curves[curve_key]
            curve.update_from_resolution(record.probability, record.resolved_outcome)

        # Capture multiplier BEFORE recompute so we can detect a real drop.
        was = score.trusted_multiplier

        # Recompute trusted_multiplier from ECE trend
        self._recompute_multiplier(score)

        post_trusted = self.trusted_confidence(
            stated=record.probability,
            subject_id=record.producing_agent_id,
            subject_type="agent",
            domain=record.domain,
            claim_type=record.claim_type,
            horizon_class=record.horizon_class,
        )

        if record.resolved_outcome is False and post_trusted > prior_trusted:
            current = max(post_trusted, 1e-9)
            score.trusted_multiplier = max(score.trusted_multiplier * (prior_trusted / current), 0.0)
            post_trusted = self.trusted_confidence(
                stated=record.probability,
                subject_id=record.producing_agent_id,
                subject_type="agent",
                domain=record.domain,
                claim_type=record.claim_type,
                horizon_class=record.horizon_class,
            )

        # Propagate downgrade if multiplier dropped significantly
        if was - score.trusted_multiplier > 0.05:
            self._propagate_downgrade(record.producing_agent_id, score.trusted_multiplier)

        logger.info(
            "TRUST UPDATE: agent=%s domain=%s n=%d multiplier=%.3f ece=%.4f",
            record.producing_agent_id, record.domain, score.n_resolved,
            score.trusted_multiplier, score.ece
        )

    def _recompute_multiplier(self, score: TrustScore) -> None:
        """Recompute trusted_multiplier from the reliability curve."""
        if not score.stated_to_real:
            return
        mean_gap = sum(
            abs(float(k) - v) for k, v in score.stated_to_real.items()
        ) / len(score.stated_to_real)
        score.ece = mean_gap
        # Multiplier decreases as ECE increases above threshold
        if mean_gap <= ECE_PENALTY_THRESHOLD:
            score.trusted_multiplier = 1.0
        else:
            excess = mean_gap - ECE_PENALTY_THRESHOLD
            score.trusted_multiplier = max(1.0 - excess * 3.0, 0.3)

    def _propagate_downgrade(self, subject_id: str, new_multiplier: float) -> None:
        """Mechanical downgrade: all registered downstream consumers are notified."""
        logger.warning(
            "DOWNGRADE PROPAGATION: subject=%s new_multiplier=%.3f — notifying %d consumers",
            subject_id, new_multiplier, len(self._downgrade_callbacks)
        )
        for cb in self._downgrade_callbacks:
            try:
                cb(subject_id, new_multiplier)
            except Exception:
                logger.exception("Downgrade callback failed for subject=%s", subject_id)

    def register_downgrade_callback(self, callback: callable) -> None:
        """Register a consumer to be notified when a subject's trust is downgraded."""
        self._downgrade_callbacks.append(callback)

    def get_score(
        self, subject_id: str, subject_type: str, domain: str,
        claim_type: str = "general", horizon_class: str = "medium"
    ) -> Optional[TrustScore]:
        key = (subject_type, subject_id, domain, claim_type, horizon_class)
        return self._scores.get(key)

    def get_sample_count(
        self, subject_id: str, domain: str, claim_type: str = "general", horizon_class: str = "short"
    ) -> int:
        """Return the number of resolved predictions that back the trust score for this agent/domain."""
        for key, score in self._scores.items():
            if key[1] == subject_id and key[2] == domain and key[3] == claim_type and key[4] == horizon_class:
                return score.n_resolved
        return 0

    def force_downgrade(self, subject_id: str, subject_type: str, reason: str, factor: float = 0.5) -> None:
        """
        Forced downgrade — e.g., when a ground truth source is disqualified.
        Propagates immediately.
        """
        for key, score in self._scores.items():
            if key[0] == subject_type and key[1] == subject_id:
                old = score.trusted_multiplier
                score.trusted_multiplier = max(score.trusted_multiplier * factor, 0.1)
                logger.warning(
                    "FORCED DOWNGRADE: %s=%s reason=%s multiplier: %.3f → %.3f",
                    subject_type, subject_id, reason, old, score.trusted_multiplier
                )
        self._propagate_downgrade(subject_id, factor)
