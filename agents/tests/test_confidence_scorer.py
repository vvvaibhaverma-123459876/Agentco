"""Tests for the confidence scoring protocol."""
import pytest
from core.confidence_scorer import score_output, validate_confidence_attached, compute_risk_level
from core.types import RiskLevel


def test_score_output_no_evidence():
    score = score_output("result", [], "any_task", ["skill1"])
    assert score == 0.1, "No evidence should yield very low confidence"


def test_score_output_with_evidence():
    score = score_output("result", ["ev1", "ev2", "ev3"], "user_research", ["user_research"])
    assert score > 0.5


def test_score_output_capped_at_1():
    score = score_output("result", ["e"] * 100, "task", ["task"])
    assert score <= 1.0


def test_confidence_always_between_0_and_1():
    for n in range(0, 20):
        evidence = [f"e{i}" for i in range(n)]
        score = score_output("output", evidence, "task", ["task"])
        assert 0.0 <= score <= 1.0


def test_validate_raises_on_missing():
    with pytest.raises(ValueError):
        validate_confidence_attached({})


def test_validate_raises_on_negative():
    with pytest.raises(ValueError):
        validate_confidence_attached({"confidence_score": -0.1})


def test_compute_risk_irreversible():
    risk = compute_risk_level(0.95, "config_change")
    assert risk == RiskLevel.CRITICAL


def test_compute_risk_financial_low_confidence():
    risk = compute_risk_level(0.5, "spend_approval")
    assert risk == RiskLevel.HIGH
