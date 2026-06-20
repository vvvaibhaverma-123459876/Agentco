"""Goodhart defense: auto-rotate metrics (Phase 5)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class GoodhartDefender:
    """Defend against Goodhart gaming by rotating metrics."""

    def __init__(self):
        self.primary_metrics: dict[str, list[str]] = {}
        self.reserve_metrics: dict[str, list[str]] = {}
        self.rotation_schedule: dict[str, list[datetime]] = {}

    def rotate_primary_metrics(self, institution_id: str) -> dict:
        """
        Rotate primary metric to prevent gaming.

        Args:
            institution_id: Institution ID

        Returns:
            {rotated_metrics, schedule, rationale}
        """
        # Simplified: rotate every 30 days
        primary = self.primary_metrics.get(institution_id, ["accuracy", "precision", "recall"])
        reserve = self.reserve_metrics.get(institution_id, ["f1_score", "calibration_ece", "coverage"])

        # Rotate: move first primary to reserve, first reserve to primary
        if primary:
            rotated_primary = primary[1:] + [reserve[0]]
        else:
            rotated_primary = reserve

        # Schedule next rotation
        today = datetime.now(timezone.utc)
        next_rotation = today + timedelta(days=30)

        self.primary_metrics[institution_id] = rotated_primary
        self.reserve_metrics[institution_id] = reserve[1:] + [primary[0]] if primary else reserve

        schedule = [today + timedelta(days=30*i) for i in range(1, 5)]

        return {
            "rotated_metrics": rotated_primary,
            "schedule": [d.isoformat() for d in schedule],
            "rationale": "Rotate primary metric to prevent Goodhart gaming",
        }
