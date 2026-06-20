"""
Skill vs Luck Analyzer — decompose performance into skill and luck components.

Uses Sharpe ratio (risk-adjusted return) to estimate skill fraction.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_SKILL = 10
RISK_FREE_RATE = np.log(0.5)  # ln(0.5) ≈ -0.693 (baseline accuracy)
BOOTSTRAP_ITERATIONS = 1000


@dataclass
class SkillDecomposition:
    """Result of skill vs luck analysis."""
    sharpe_ratio: Optional[float]  # Risk-adjusted performance
    sharpe_ci_lower: Optional[float]  # Bootstrap CI lower bound
    sharpe_ci_upper: Optional[float]  # Bootstrap CI upper bound
    estimated_skill_fraction: Optional[float]  # Skill / (skill + luck) [0, 1]
    interpretation: str  # 'high' | 'medium' | 'low' | 'insufficient'
    rationale: str


class SkillVsLuckAnalyzer:
    """
    Decomposes prediction performance into skill and luck.

    Uses Sharpe ratio: (mean_log_score - risk_free) / std_log_score
    Skill fraction = sharpe / (1 + |sharpe|)
    """

    def __init__(self, db=None):
        """Initialize skill analyzer.

        Args:
            db: Optional database connection
        """
        self.db = db

    def decompose(
        self,
        agent_id: str,
        domain: str,
        horizon: str,
        stated_confidences: list[float],
        outcomes: list[bool],
    ) -> SkillDecomposition:
        """
        Decompose performance into skill and luck.

        Args:
            agent_id: Subject ID
            domain: Domain
            horizon: Time horizon
            stated_confidences: List of stated confidences
            outcomes: List of outcomes (bool)

        Returns:
            SkillDecomposition
        """
        if len(stated_confidences) < MIN_SAMPLES_FOR_SKILL:
            return SkillDecomposition(
                sharpe_ratio=None,
                sharpe_ci_lower=None,
                sharpe_ci_upper=None,
                estimated_skill_fraction=None,
                interpretation="insufficient",
                rationale=(
                    f"Need ≥{MIN_SAMPLES_FOR_SKILL} resolved predictions; "
                    f"have {len(stated_confidences)}"
                ),
            )

        # Compute log scores
        X = np.array(stated_confidences)
        y = np.array(outcomes, dtype=float)

        # Log score: ln(p) if outcome=1, else ln(1-p)
        # Avoid log(0), log(1)
        X_clipped = np.clip(X, 1e-6, 1 - 1e-6)
        log_scores = y * np.log(X_clipped) + (1 - y) * np.log(1 - X_clipped)

        # Sharpe ratio
        mean_log_score = float(np.mean(log_scores))
        std_log_score = float(np.std(log_scores))

        if std_log_score == 0:
            return SkillDecomposition(
                sharpe_ratio=0.0,
                sharpe_ci_lower=0.0,
                sharpe_ci_upper=0.0,
                estimated_skill_fraction=0.5,
                interpretation="low",
                rationale="Zero variance in log scores (degenerate case)",
            )

        sharpe_ratio = (mean_log_score - RISK_FREE_RATE) / std_log_score

        # Bootstrap CI on Sharpe ratio
        bootstrap_sharpes = []
        n = len(log_scores)
        np.random.seed(42)  # Deterministic for tests
        for _ in range(BOOTSTRAP_ITERATIONS):
            sample_idx = np.random.choice(n, size=n, replace=True)
            sample_scores = log_scores[sample_idx]
            sample_mean = np.mean(sample_scores)
            sample_std = np.std(sample_scores)
            if sample_std > 0:
                sample_sharpe = (sample_mean - RISK_FREE_RATE) / sample_std
            else:
                sample_sharpe = 0.0
            bootstrap_sharpes.append(sample_sharpe)

        bootstrap_sharpes = np.array(bootstrap_sharpes)
        sharpe_ci_lower = float(np.percentile(bootstrap_sharpes, 2.5))
        sharpe_ci_upper = float(np.percentile(bootstrap_sharpes, 97.5))

        # Skill fraction: 0 if sharpe < -1, 1 if sharpe > 1, linear in between
        # Formula: skill_frac = sharpe / (1 + |sharpe|)
        skill_fraction = sharpe_ratio / (1 + abs(sharpe_ratio))
        skill_fraction = (skill_fraction + 1) / 2  # Normalize to [0, 1]
        skill_fraction = float(np.clip(skill_fraction, 0.0, 1.0))

        # Interpretation
        if skill_fraction > 0.6:
            interpretation = "high"
        elif skill_fraction > 0.4:
            interpretation = "medium"
        else:
            interpretation = "low"

        rationale = (
            f"Log score mean={mean_log_score:.4f}, std={std_log_score:.4f}. "
            f"Sharpe={sharpe_ratio:.3f} (risk-free={RISK_FREE_RATE:.3f}). "
            f"Bootstrap CI=[{sharpe_ci_lower:.3f}, {sharpe_ci_upper:.3f}]. "
            f"Skill fraction={skill_fraction:.3f} ({interpretation}). "
            f"n={n} predictions."
        )

        logger.debug(
            "SKILL_LUCK: %s/%s sharpe=%.3f skill=%.3f interpretation=%s",
            agent_id, domain, sharpe_ratio, skill_fraction, interpretation
        )

        return SkillDecomposition(
            sharpe_ratio=float(sharpe_ratio),
            sharpe_ci_lower=sharpe_ci_lower,
            sharpe_ci_upper=sharpe_ci_upper,
            estimated_skill_fraction=skill_fraction,
            interpretation=interpretation,
            rationale=rationale,
        )
