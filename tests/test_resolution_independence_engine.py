from datetime import datetime, timedelta, timezone

import pytest

from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration
from calibration.resolution.independence_engine import (
    build_source_fingerprint,
    evaluate_resolution_independence,
    evidence_snapshot_hash,
)
from calibration.resolution.resolution_service import ResolutionService
from calibration.scoring.scoring_module import ScoringModule
from calibration.surprise.surprise_register import SurpriseRegister
from calibration.trust.trust_controller import TrustController


def _verdict(claim_url, resolution_url, **kwargs):
    return evaluate_resolution_independence(
        claim_source=build_source_fingerprint(
            claim_url,
            content_hash=kwargs.get("claim_hash"),
            publisher_owner=kwargs.get("claim_owner"),
        ),
        resolution_source=build_source_fingerprint(
            resolution_url,
            content_hash=kwargs.get("resolution_hash"),
            source_type=kwargs.get("resolution_type"),
            publisher_owner=kwargs.get("resolution_owner"),
        ),
        producing_agent_id=kwargs.get("producer", "agent-1"),
        resolver_id=kwargs.get("resolver", "resolver-1"),
        resolver_type=kwargs.get("resolver_type", "service"),
        production=kwargs.get("production", True),
    )


def test_same_canonical_url_rejected():
    verdict = _verdict("https://example.com/a", "https://example.com/a/")
    assert not verdict.independent
    assert verdict.reason == "same_canonical_url"


def test_same_url_with_tracking_params_rejected():
    verdict = _verdict(
        "https://example.com/a?utm_source=x&keep=1",
        "https://example.com/a?keep=1&utm_campaign=y",
    )
    assert not verdict.independent
    assert verdict.reason == "same_canonical_url"


def test_same_content_hash_rejected():
    verdict = _verdict("https://claims.example/a", "https://truth.example/b", claim_hash="abc", resolution_hash="abc")
    assert not verdict.independent
    assert verdict.reason == "same_content_hash"


def test_same_domain_different_url_warns_but_can_pass():
    verdict = _verdict("https://example.com/a", "https://example.com/b")
    assert verdict.independent
    assert verdict.severity == "warn"
    assert verdict.reason == "same_domain_different_canonical_url"


def test_internal_source_rejected():
    verdict = _verdict("https://claims.example/a", "agentco://sandbox/result")
    assert not verdict.independent
    assert verdict.reason == "internal_resolution_source"


def test_resolver_id_equals_producing_agent_rejected():
    verdict = _verdict("https://claims.example/a", "https://truth.example/b", producer="agent-1", resolver="agent-1")
    assert not verdict.independent
    assert verdict.reason == "producer_resolver_conflict"


def test_missing_resolver_id_rejected_in_production_mode():
    verdict = _verdict("https://claims.example/a", "https://truth.example/b", resolver=None)
    assert not verdict.independent
    assert verdict.reason == "missing_resolver_identity"


def test_evidence_snapshot_hash_is_deterministic():
    left = {"b": [2, 1], "a": {"x": True}}
    right = {"a": {"x": True}, "b": [2, 1]}
    assert evidence_snapshot_hash(left) == evidence_snapshot_hash(right)


def test_resolution_service_attaches_independence_verdict_and_snapshot():
    ledger = PredictionLedger()
    svc = ResolutionService(ledger, ScoringModule(), SurpriseRegister(), TrustController())
    pid = ledger.pre_register(
        PredictionRegistration(
            claim="A deterministic external fixture will resolve true.",
            probability=0.7,
            confidence_basis={"fixture": True},
            producing_agent_id="agent-1",
            producing_prompt_version="test",
            resolution_criterion="fixture says true",
            resolution_date=datetime.now(timezone.utc) - timedelta(seconds=1),
            ground_truth_source="https://truth.example/fixture",
            horizon_class="short",
            domain="test",
            claim_type="fixture",
            claim_source_url="https://claims.example/claim",
        )
    )

    record = svc.resolve(
        pid,
        outcome=True,
        ground_truth_source="https://truth.example/fixture",
        evidence={"source_url": "https://truth.example/fixture", "resolution_content_hash": "hash-1"},
        resolver_id="resolver-service",
        resolver_type="service",
        resolution_url="https://truth.example/fixture",
    )

    assert record.independence_verdict is not None
    assert record.independence_verdict["independent"] is True
    assert record.resolution_evidence_snapshot is not None
    assert record.resolution_evidence_snapshot["evidence_hash"]


def test_resolution_service_rejects_without_resolver_id_in_production(monkeypatch):
    monkeypatch.setenv("AGENTCO_ENV", "production")
    ledger = PredictionLedger()
    svc = ResolutionService(ledger, ScoringModule(), SurpriseRegister(), TrustController())
    pid = ledger.pre_register(
        PredictionRegistration(
            claim="A deterministic external fixture will resolve true.",
            probability=0.7,
            confidence_basis={"fixture": True},
            producing_agent_id="agent-1",
            producing_prompt_version="test",
            resolution_criterion="fixture says true",
            resolution_date=datetime.now(timezone.utc) - timedelta(seconds=1),
            ground_truth_source="https://truth.example/fixture",
            horizon_class="short",
            domain="test",
            claim_type="fixture",
            claim_source_url="https://claims.example/claim",
        )
    )

    with pytest.raises(ValueError, match="missing_resolver_identity"):
        svc.resolve(
            pid,
            outcome=True,
            ground_truth_source="https://truth.example/fixture",
            evidence={"source_url": "https://truth.example/fixture"},
        )
