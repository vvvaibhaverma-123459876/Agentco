"""Mandatory confidence scoring module. Every agent output must pass through this."""
from __future__ import annotations
from typing import Any
from .types import RiskLevel


def compute_risk_level(confidence_score: float, action_category: str) -> RiskLevel:
    """Derive risk level from confidence and action category."""
    irreversible_actions = {"config_change", "agent_retirement", "contract_sign", "data_delete"}
    financial_actions = {"spend_approval", "budget_allocation", "vendor_payment"}

    if action_category in irreversible_actions or confidence_score < 0.3:
        return RiskLevel.CRITICAL
    if action_category in financial_actions and confidence_score < 0.7:
        return RiskLevel.HIGH
    if confidence_score < 0.5:
        return RiskLevel.HIGH
    if confidence_score < 0.7:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def score_output(
    output: Any,
    evidence_items: list[str],
    task_type: str,
    agent_competency_areas: list[str],
) -> float:
    """
    Assess confidence for an agent output.
    Returns float 0.0–1.0. Never returns a value without evidence.
    """
    if not evidence_items:
        return 0.1

    base_score = min(len(evidence_items) * 0.15, 0.6)

    competency_bonus = 0.2 if task_type in agent_competency_areas else 0.0
    specificity_bonus = 0.2 if output and str(output).strip() else 0.0

    raw = base_score + competency_bonus + specificity_bonus
    return round(min(max(raw, 0.0), 1.0), 3)


def validate_confidence_attached(output_dict: dict) -> None:
    """Raises if confidence_score is missing or out of range — enforces protocol."""
    if "confidence_score" not in output_dict:
        raise ValueError("Protocol violation: confidence_score missing from agent output")
    score = output_dict["confidence_score"]
    if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
        raise ValueError(f"Protocol violation: confidence_score {score!r} out of range [0,1]")
