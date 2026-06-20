"""
Domain Transfer Calibrator — estimate calibration in new domains using shrinkage.

Transfers calibration knowledge across domains with uncertainty quantification.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_TRANSFER = 5
SHRINKAGE_FACTOR = 0.5  # Balance between source and neutral (0.5)


@dataclass
class TransferEstimate:
    """Result of domain transfer estimation."""
    point_estimate: Optional[float]  # Estimated calibration in target domain
    transfer_confidence: float  # How confident we are [0, 1]
    correlation: Optional[float]  # Inter-domain correlation
    rationale: str


class DomainTransferCalibrator:
    """
    Estimates calibration in a new domain using prior calibration from another domain.

    Uses shrinkage estimation:
    - If source and target are correlated, use source estimate
    - If uncorrelated, shrink toward neutral (0.5)
    - Confidence reflects the correlation strength
    """

    def __init__(self, db=None):
        """Initialize domain transfer calibrator.

        Args:
            db: Optional database connection
        """
        self.db = db

    def estimate_calibration_in_new_domain(
        self,
        agent_id: str,
        source_domain: str,
        target_domain: str,
        source_point_estimate: float,
        correlation: Optional[float] = None,
        source_n_samples: int = 0,
    ) -> TransferEstimate:
        """
        Estimate calibration in new domain based on source domain.

        Args:
            agent_id: Subject ID
            source_domain: Domain we have data from (e.g., 'biology')
            target_domain: Domain we're estimating for (e.g., 'governance')
            source_point_estimate: Calibration accuracy in source domain [0, 1]
            correlation: Inter-domain correlation [0, 1], estimated if None
            source_n_samples: Number of samples backing source estimate

        Returns:
            TransferEstimate with point_estimate + confidence
        """
        if source_n_samples < MIN_SAMPLES_FOR_TRANSFER:
            return TransferEstimate(
                point_estimate=None,
                transfer_confidence=0.0,
                correlation=None,
                rationale=(
                    f"Source domain has insufficient data "
                    f"({source_n_samples} < {MIN_SAMPLES_FOR_TRANSFER})"
                ),
            )

        # Estimate correlation if not provided
        if correlation is None:
            correlation = self._estimate_domain_correlation(
                agent_id, source_domain, target_domain
            )

        if correlation is None:
            # Could not estimate correlation
            return TransferEstimate(
                point_estimate=0.5,
                transfer_confidence=0.3,
                correlation=None,
                rationale=(
                    f"Cannot estimate correlation between {source_domain} and {target_domain}. "
                    f"Defaulting to neutral (0.5)."
                ),
            )

        # Shrinkage: weighted average of source and neutral
        # adjusted_corr = SHRINKAGE_FACTOR + SHRINKAGE_FACTOR * correlation
        # But simpler: adjusted_corr = 0.5 + 0.5 * correlation
        adjusted_corr = SHRINKAGE_FACTOR + SHRINKAGE_FACTOR * correlation

        # Transfer estimate: weighted toward source if correlated
        point_estimate = (
            SHRINKAGE_FACTOR * source_point_estimate +
            (1 - SHRINKAGE_FACTOR) * 0.5
        ) * adjusted_corr + 0.5 * (1 - adjusted_corr)

        # Clip to valid range
        point_estimate = float(np.clip(point_estimate, 0.0, 1.0))

        # Transfer confidence: correlation squared (R²)
        transfer_confidence = float(np.clip(correlation ** 2, 0.0, 1.0))

        rationale = (
            f"Correlation r={correlation:.2f} between {source_domain} → {target_domain}. "
            f"Adjusted r={adjusted_corr:.2f}. "
            f"Transfer estimate={point_estimate:.3f} "
            f"(from source={source_point_estimate:.3f}). "
            f"Confidence (R²)={transfer_confidence:.3f}."
        )

        logger.debug(
            "DOMAIN TRANSFER: %s %s→%s correlation=%.2f estimate=%.3f confidence=%.3f",
            agent_id, source_domain, target_domain, correlation, point_estimate,
            transfer_confidence
        )

        return TransferEstimate(
            point_estimate=point_estimate,
            transfer_confidence=transfer_confidence,
            correlation=correlation,
            rationale=rationale,
        )

    @staticmethod
    def _estimate_domain_correlation(
        agent_id: str, domain1: str, domain2: str
    ) -> Optional[float]:
        """
        Estimate correlation between two domains for this agent.

        This is a heuristic; in production would query historical overlap.

        Args:
            agent_id: Subject ID
            domain1: First domain
            domain2: Second domain

        Returns:
            Estimated correlation [0, 1], or None if cannot estimate
        """
        # Hard-coded correlation matrix for demo
        # In production, would compute from historical data
        correlation_matrix = {
            ("biology", "medicine"): 0.85,
            ("medicine", "biology"): 0.85,
            ("finance", "economics"): 0.75,
            ("economics", "finance"): 0.75,
            ("biology", "governance"): 0.3,
            ("governance", "biology"): 0.3,
            ("physics", "engineering"): 0.8,
            ("engineering", "physics"): 0.8,
        }

        key = (domain1, domain2)
        if key in correlation_matrix:
            return correlation_matrix[key]

        # Default: assume low correlation for unknown pairs
        return 0.2
