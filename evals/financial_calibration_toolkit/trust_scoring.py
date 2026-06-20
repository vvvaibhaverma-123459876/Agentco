"""Trust scoring helpers."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrustSnapshot:
    trust: float
    hit_rate: float
    avg_confidence: float
    calibration_error: float
    sample_count: int


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def original_trust(history: list[dict[str, Any]]) -> TrustSnapshot:
    """STOP 2 trust formula using resolved history only."""
    if not history:
        return TrustSnapshot(0.5, 0.0, 0.5, 0.0, 0)

    hit_rate = sum(1 for r in history if r["hit"]) / len(history)
    avg_confidence = statistics.mean(r["confidence"] for r in history)
    if avg_confidence <= hit_rate:
        trust = hit_rate + 0.05 * (hit_rate - avg_confidence)
    else:
        trust = hit_rate - 0.1 * (avg_confidence - hit_rate)
    return TrustSnapshot(clamp(trust), hit_rate, avg_confidence, avg_confidence - hit_rate, len(history))

