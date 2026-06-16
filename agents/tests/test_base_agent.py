"""Tests for BaseAgent core guarantees."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.types import AgentOutput, RiskLevel
from core.confidence_scorer import validate_confidence_attached


def test_validate_confidence_attached_passes():
    validate_confidence_attached({"confidence_score": 0.85})


def test_validate_confidence_attached_missing():
    with pytest.raises(ValueError, match="confidence_score missing"):
        validate_confidence_attached({"content": "hello"})


def test_validate_confidence_attached_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        validate_confidence_attached({"confidence_score": 1.5})


def test_agent_output_trust_levels():
    cases = [
        (0.95, "verified"),
        (0.80, "trusted"),
        (0.60, "provisional"),
        (0.40, "unverified"),
        (0.20, "rejected"),
    ]
    for score, expected_trust in cases:
        output = AgentOutput(content={}, confidence_score=score, risk_level=RiskLevel.LOW, rationale="test")
        assert output.trust_level().value == expected_trust, f"score={score}"


def test_risk_level_from_confidence():
    from core.confidence_scorer import compute_risk_level
    assert compute_risk_level(0.95, "general") == RiskLevel.LOW
    assert compute_risk_level(0.60, "general") == RiskLevel.MEDIUM
    assert compute_risk_level(0.40, "general") == RiskLevel.HIGH
    assert compute_risk_level(0.20, "config_change") == RiskLevel.CRITICAL
