"""
Canonical Uncertainty Schema — unified across agents, eval runners, and scoring.

This module defines the standard representation for uncertainty signals
captured during model/agent predictions, ensuring consistency across the
evaluation measurement plane.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UncertaintySignal:
    """
    Canonical uncertainty object used across agents, eval runners, and scoring.

    All probability/confidence fields must be in [0, 1].
    All entropy fields must be non-negative.
    If abstained=True, abstain_reason must be provided.
    """

    # Core confidence signals
    stated_confidence: Optional[float] = None
    """Model/agent's stated confidence in its own answer (0–1)."""

    trusted_confidence: Optional[float] = None
    """Post-adjustment confidence (e.g., after calibration correction)."""

    # Epistemic uncertainty (predictive probability)
    p_true: Optional[float] = None
    """Model's estimated P(answer is true) from uncertainty quantification."""

    # Aleatoric uncertainty (data/task variability)
    p_ik: Optional[float] = None
    """Irreducible uncertainty: P(task outcome | task parameters)."""

    # Semantic/divergence signals
    semantic_entropy: Optional[float] = None
    """Entropy over candidate answers (e.g., from ensemble disagreement)."""

    answer_frequency: Optional[float] = None
    """Frequency of top answer in ensemble responses (if ensemble)."""

    # Token-level signals
    token_entropy: Optional[float] = None
    """Average entropy of token probabilities in generation."""

    # Abstention decision
    abstained: bool = False
    """Whether the model/agent abstained from making a prediction."""

    abstain_reason: Optional[str] = None
    """Reason for abstention (required if abstained=True)."""

    # Provenance
    method_versions: dict[str, str] = field(default_factory=dict)
    """Versions of methods used to compute uncertainty signals (e.g., {'calibration': '1.2', 'ensemble': 'v3'})."""

    raw_signals: dict[str, Any] = field(default_factory=dict)
    """Raw/unprocessed signals for debugging/replay."""

    def __post_init__(self):
        """Validate after initialization."""
        self._validate()

    def _validate(self):
        """
        Enforce invariants:
        - All probabilities/confidences in [0, 1]
        - All entropy fields non-negative
        - If abstained, abstain_reason is required
        """
        for field_name in ['stated_confidence', 'trusted_confidence', 'p_true', 'p_ik', 'answer_frequency']:
            value = getattr(self, field_name, None)
            if value is not None and not (0.0 <= value <= 1.0):
                raise ValueError(f"{field_name} must be in [0, 1], got {value}")

        for field_name in ['semantic_entropy', 'token_entropy']:
            value = getattr(self, field_name, None)
            if value is not None and value < 0.0:
                raise ValueError(f"{field_name} must be non-negative, got {value}")

        if self.abstained and not self.abstain_reason:
            raise ValueError("abstain_reason is required when abstained=True")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'stated_confidence': self.stated_confidence,
            'trusted_confidence': self.trusted_confidence,
            'p_true': self.p_true,
            'p_ik': self.p_ik,
            'semantic_entropy': self.semantic_entropy,
            'answer_frequency': self.answer_frequency,
            'token_entropy': self.token_entropy,
            'abstained': self.abstained,
            'abstain_reason': self.abstain_reason,
            'method_versions': self.method_versions,
            'raw_signals': self.raw_signals,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UncertaintySignal:
        """Deserialize from JSON-compatible dict."""
        return cls(**data)

    def get_primary_uncertainty_estimate(self) -> Optional[float]:
        """
        Get the primary uncertainty estimate in priority order:
        1. semantic_entropy (if available)
        2. token_entropy (if available)
        3. 1 - trusted_confidence (if available)
        4. 1 - stated_confidence (if available)
        """
        if self.semantic_entropy is not None:
            return self.semantic_entropy
        if self.token_entropy is not None:
            return self.token_entropy
        if self.trusted_confidence is not None:
            return 1.0 - self.trusted_confidence
        if self.stated_confidence is not None:
            return 1.0 - self.stated_confidence
        return None


# Backward compatibility helper
def from_legacy_confidence(stated: Optional[float], trusted: Optional[float] = None) -> UncertaintySignal:
    """
    Create UncertaintySignal from legacy confidence fields.
    Useful for migrating existing code.
    """
    return UncertaintySignal(
        stated_confidence=stated,
        trusted_confidence=trusted,
    )
