from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AbstentionDecision:
    should_abstain: bool
    reason: str
    trusted_confidence: float
    uncertainty: float


class ConformalPredictor:
    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha
        self.threshold = 1.0

    def fit(self, calibration_scores: list[float]) -> None:
        if not calibration_scores:
            self.threshold = 1.0
            return
        scores = sorted(calibration_scores)
        index = min(len(scores) - 1, math.ceil((len(scores) + 1) * (1 - self.alpha)) - 1)
        self.threshold = scores[index]

    def covers(self, nonconformity_score: float) -> bool:
        return nonconformity_score <= self.threshold


class UncertaintyStack:
    def __init__(self, abstention_threshold: float = 0.55):
        self.abstention_threshold = abstention_threshold
        self.conformal = ConformalPredictor()

    def semantic_uncertainty(self, candidates: list[str]) -> float:
        normalized = {item.casefold().strip() for item in candidates if item.strip()}
        if not candidates:
            return 1.0
        return max(0.0, min(1.0, (len(normalized) - 1) / max(1, len(candidates) - 1)))

    def trusted_confidence(self, stated: float, historical_multiplier: float = 0.8) -> float:
        return round(max(0.0, min(1.0, stated * historical_multiplier)), 4)

    def decide(self, *, stated_confidence: float, historical_multiplier: float, candidates: list[str]) -> AbstentionDecision:
        trusted = self.trusted_confidence(stated_confidence, historical_multiplier)
        semantic = self.semantic_uncertainty(candidates)
        uncertainty = max(1.0 - trusted, semantic)
        if uncertainty > self.abstention_threshold:
            return AbstentionDecision(True, "uncertainty_above_threshold", trusted, uncertainty)
        return AbstentionDecision(False, "within_uncertainty_threshold", trusted, uncertainty)

    def metrics(self, probabilities: list[float], outcomes: list[bool]) -> dict[str, float]:
        n = len(probabilities)
        if n == 0:
            return {"brier": 0.0, "log_score": 0.0, "ece": 0.0, "coverage": 0.0}
        brier = sum((p - (1.0 if o else 0.0)) ** 2 for p, o in zip(probabilities, outcomes)) / n
        log_score = sum(math.log(max(min(p if o else 1 - p, 1 - 1e-9), 1e-9)) for p, o in zip(probabilities, outcomes)) / n
        ece = sum(abs(p - (1.0 if o else 0.0)) for p, o in zip(probabilities, outcomes)) / n
        coverage = sum(1 for p, o in zip(probabilities, outcomes) if (p >= 0.5) == o) / n
        return {"brier": brier, "log_score": log_score, "ece": ece, "coverage": coverage}
