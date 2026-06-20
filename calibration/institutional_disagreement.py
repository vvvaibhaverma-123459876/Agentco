"""Institutional disagreement analysis (Phase 3)."""
from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class InstitutionalTrustVector:
    """Institutional trust statistics."""
    point_estimate: float
    variance: float
    range: tuple[float, float]
    consensus_strength: str  # 'strong', 'moderate', 'weak'
    outlier_depts: list[str] = field(default_factory=list)
    dissent_signal: str = "weak"  # 'weak', 'moderate', 'strong'


class InstitutionalDisagreementAnalyzer:
    """Analyze institutional-level disagreement."""

    def compute_institutional_trust_vector(self, institution_id: str, dept_scores: dict[str, list[float]]) -> InstitutionalTrustVector:
        """
        Compute institutional trust vector.

        Args:
            institution_id: Identifier
            dept_scores: dict[dept_name] -> list[scores]

        Returns:
            InstitutionalTrustVector with statistics
        """
        if not dept_scores:
            return InstitutionalTrustVector(
                point_estimate=0.5,
                variance=0.0,
                range=(0.5, 0.5),
                consensus_strength="weak",
            )

        # Compute department means
        dept_means = {dept: float(np.mean(scores)) for dept, scores in dept_scores.items()}
        all_means = list(dept_means.values())

        if not all_means:
            return InstitutionalTrustVector(
                point_estimate=0.5,
                variance=0.0,
                range=(0.5, 0.5),
                consensus_strength="weak",
            )

        point_estimate = float(np.mean(all_means))
        variance = float(np.var(all_means))
        val_range = (float(min(all_means)), float(max(all_means)))

        # Find outliers (> 2σ from mean)
        std = float(np.std(all_means))
        outlier_depts = [
            dept for dept, mean in dept_means.items()
            if abs(mean - point_estimate) > 2 * std
        ] if std > 0 else []

        # Consensus strength
        if variance < 0.05:
            consensus_strength = "strong"
        elif variance < 0.15:
            consensus_strength = "moderate"
        else:
            consensus_strength = "weak"

        # Dissent signal
        if variance < 0.05:
            dissent_signal = "weak"
        elif variance < 0.15:
            dissent_signal = "moderate"
        else:
            dissent_signal = "strong"

        return InstitutionalTrustVector(
            point_estimate=point_estimate,
            variance=variance,
            range=val_range,
            consensus_strength=consensus_strength,
            outlier_depts=outlier_depts,
            dissent_signal=dissent_signal,
        )
