"""Schism detection in institutions (Phase 4)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SchismSignal:
    """Schism detection result."""
    schism_detected: bool
    schism_index: int | None
    conflict_depts: list[str]
    severity: float  # 0-1
    rationale: str


class SchismDetector:
    """Detect institutional schisms (dept disagreement spikes)."""

    def detect_schism(self, institution_id: str, dept_vectors: list[dict], lookback_days: int = 180) -> SchismSignal:
        """
        Detect schism via variance spike.

        Args:
            institution_id: Institution ID
            dept_vectors: list of {dept_name, variance, timestamp}
            lookback_days: Historical window

        Returns:
            SchismSignal
        """
        if len(dept_vectors) < 10:
            return SchismSignal(
                schism_detected=False,
                schism_index=None,
                conflict_depts=[],
                severity=0.0,
                rationale="Insufficient history",
            )

        # Extract variances
        variances = np.array([v.get("variance", 0.0) for v in dept_vectors])

        # Detect spike: compare recent vs historical
        if len(variances) < 5:
            baseline = np.mean(variances)
            recent = variances[-1]
        else:
            baseline = np.mean(variances[:-5])
            recent = np.mean(variances[-5:])

        # Check for spike
        if baseline == 0:
            spike_factor = 1.0 if recent > 0 else 1.0
        else:
            spike_factor = recent / baseline

        schism_threshold = 2.5
        detected = spike_factor > schism_threshold

        if detected:
            schism_index = len(variances) - 1
            # Find conflicting depts (those with highest disagreement)
            conflict_depts = [
                v.get("dept", f"dept_{i}")
                for i, v in enumerate(dept_vectors[-3:])
                if v.get("variance", 0.0) > baseline * 1.5
            ]
            severity = min(1.0, (spike_factor - schism_threshold) / schism_threshold)
        else:
            schism_index = None
            conflict_depts = []
            severity = 0.0

        return SchismSignal(
            schism_detected=detected,
            schism_index=schism_index,
            conflict_depts=conflict_depts,
            severity=severity,
            rationale=f"Spike factor: {spike_factor:.2f}x (threshold: {schism_threshold}x)",
        )
