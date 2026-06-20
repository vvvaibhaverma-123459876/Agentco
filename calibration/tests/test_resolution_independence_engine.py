from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from reserve.credentials.proof_of_calibration import (
    ProofOfCalibration,
    issue_credential,
    verify_credential,
)
from reserve.scoring.scoring_function import CellScore, ReserveScore


def _register(engine, *, agent_id: str = "agent-alpha", claim_source_url: str | None = None, owner: str = "") -> str:
    return engine["ledger"].pre_register(
        PredictionRegistration(
            claim="Acme revenue will exceed forecast",
            probability=0.7,
            confidence_basis={"source": "pre-registration fixture"},
            producing_agent_id=agent_id,
            producing_prompt_version="test-v1",
            resolution_criterion="Outcome is available after quarterly report publication",
            resolution_date=datetime.now(timezone.utc) - timedelta(days=1),
            ground_truth_source=claim_source_url or "https://claims.example.com/reports/q1?utm_source=test",
            horizon_class="short",
            domain="finance",
            claim_type="forecast",
            claim_source_url=claim_source_url,
            claim_source_owner=owner,
            outcome_available_at=datetime.now(timezone.utc) - timedelta(hours=12),
        )
    )


def _resolve(engine, pid: str, **kwargs):
    defaults = {
        "prediction_id": pid,
        "outcome": True,
        "ground_truth_source": "https://independent.example.net/reports/q1-result",
        "evidence": {"snapshot": "published result"},
        "resolver_id": "resolver-service",
        "resolution_source_url": "https://independent.example.net/reports/q1-result",
    }
    defaults.update(kwargs)
    return engine["resolution"].resolve(**defaults)


def test_same_exact_url_rejected() -> None:
    engine = create_calibration_engine()
    source = "https://claims.example.com/reports/q1"
    pid = _register(engine, claim_source_url=source)

    with pytest.raises(ValueError, match="same_canonical_url"):
        _resolve(engine, pid, ground_truth_source=source, resolution_source_url=source)


def test_same_canonical_url_with_tracking_params_rejected() -> None:
    engine = create_calibration_engine()
    pid = _register(engine, claim_source_url="https://claims.example.com/reports/q1")

    with pytest.raises(ValueError, match="same_canonical_url"):
        _resolve(
            engine,
            pid,
            ground_truth_source="https://claims.example.com/reports/q1?utm_campaign=x&fbclid=abc",
            resolution_source_url="https://claims.example.com/reports/q1?utm_campaign=x&fbclid=abc",
        )


def test_same_producer_as_resolver_rejected() -> None:
    engine = create_calibration_engine()
    pid = _register(engine, agent_id="agent-alpha")

    with pytest.raises(ValueError, match="producer_cannot_resolve_own_claim"):
        _resolve(engine, pid, resolver_id="agent-alpha")


def test_resolution_before_outcome_availability_rejected() -> None:
    engine = create_calibration_engine()
    pid = _register(engine)

    with pytest.raises(ValueError, match="resolution_before_outcome_available"):
        _resolve(engine, pid, outcome_available_at=datetime.now(timezone.utc) + timedelta(hours=2))


def test_missing_source_lineage_blocks_promotion() -> None:
    engine = create_calibration_engine()
    pid = _register(engine)
    record = engine["ledger"].get(pid)
    record.claim_source_url = ""
    record.ground_truth_source = ""

    with pytest.raises(ValueError, match="missing_source_lineage"):
        _resolve(engine, pid)
    assert engine["trust"].get_sample_count("agent-alpha", "finance", "forecast", "short") == 0


def test_independent_source_allows_scoring() -> None:
    engine = create_calibration_engine()
    pid = _register(engine)

    record = _resolve(engine, pid)

    assert record.independence_status == "accepted"
    assert record.brier_score is not None
    assert engine["trust"].get_sample_count("agent-alpha", "finance", "forecast", "short") == 1


def test_same_domain_requires_additional_independent_evidence() -> None:
    engine = create_calibration_engine()
    pid = _register(engine, claim_source_url="https://publisher.example.com/claims/q1")

    with pytest.raises(ValueError, match="same_domain_or_owner"):
        _resolve(
            engine,
            pid,
            ground_truth_source="https://publisher.example.com/results/q1",
            resolution_source_url="https://publisher.example.com/results/q1",
        )

    record = _resolve(
        engine,
        pid,
        ground_truth_source="https://publisher.example.com/results/q1",
        resolution_source_url="https://publisher.example.com/results/q1",
        evidence={"snapshot": "published result", "additional_independent_evidence": True},
    )
    assert record.independence_status == "accepted"


def test_rejected_resolution_writes_audit_event() -> None:
    engine = create_calibration_engine()
    source = "https://claims.example.com/reports/q1"
    pid = _register(engine, claim_source_url=source)

    with pytest.raises(ValueError):
        _resolve(engine, pid, ground_truth_source=source, resolution_source_url=source)

    assert engine["resolution"].audit_events
    event = engine["resolution"].audit_events[-1]
    assert event["event_type"] == "resolution_rejected"
    assert event["prediction_id"] == pid
    assert "same_canonical_url" in event["reason"]


def test_trust_score_only_updates_after_valid_independent_resolution() -> None:
    engine = create_calibration_engine()
    source = "https://claims.example.com/reports/q1"
    rejected_pid = _register(engine, claim_source_url=source)
    with pytest.raises(ValueError):
        _resolve(engine, rejected_pid, ground_truth_source=source, resolution_source_url=source)
    assert engine["trust"].get_sample_count("agent-alpha", "finance", "forecast", "short") == 0

    accepted_pid = _register(engine, claim_source_url="https://claims.example.com/reports/q2")
    _resolve(
        engine,
        accepted_pid,
        ground_truth_source="https://independent.example.net/reports/q2-result",
        resolution_source_url="https://independent.example.net/reports/q2-result",
    )
    assert engine["trust"].get_sample_count("agent-alpha", "finance", "forecast", "short") == 1


def test_evidence_snapshot_hash_recorded() -> None:
    engine = create_calibration_engine()
    pid = _register(engine)

    record = _resolve(engine, pid, evidence={"snapshot": "published result", "value": 42})

    assert record.evidence_snapshot_hash
    assert len(record.evidence_snapshot_hash) == 64
    assert record.evidence_fetched_at is not None


def test_credential_recomputation_fails_if_tampered() -> None:
    score = ReserveScore(
        agent_id="agent-alpha",
        cells=[
            CellScore(
                agent_id="agent-alpha",
                domain="finance",
                horizon_class="short",
                weighted_log_score=-0.3,
                weighted_brier_score=0.09,
                sharpness=0.4,
                sample_count=5,
                total_weight=3.0,
            )
        ],
        overall_log_score=-0.3,
        overall_brier_score=0.09,
        total_sample_count=5,
        algorithm="test",
    )
    credential = issue_credential(score, {})
    tampered_cell = replace(credential.cells[0], weighted_brier_score=0.99)
    tampered = ProofOfCalibration(**{**credential.__dict__, "cells": [tampered_cell]})

    assert verify_credential(tampered) is False
