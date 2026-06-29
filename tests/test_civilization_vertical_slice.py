import pytest

from scripts import verify_civilization_vertical_slice as slice_verifier


def test_required_stages_cover_canonical_civilization_slice():
    required = set(slice_verifier.REQUIRED_STAGES)

    for stage in {
        "task_created",
        "citizen_assigned",
        "evidence_indexed",
        "claim_created",
        "prediction_preregistered",
        "budget_reserved",
        "real_reasoning_executed",
        "decision_and_audit_written",
        "bus_event_emitted",
        "independent_resolution_completed",
        "calibration_scored",
        "trust_updated",
        "credential_minted",
        "memory_promoted",
        "learning_candidate_created",
        "canary_or_human_queue_recorded",
        "generality_metric_updated",
        "coordinator_tick_recorded",
    }:
        assert stage in required


def test_validate_decision_requires_evidence_backed_claims():
    slice_verifier.validate_decision(
        {
            "decision": "approve",
            "confidence": 0.83,
            "cited_evidence_ids": ["ev-security-review", "ev-runtime-audit"],
            "claims": [
                {
                    "text": "The artifact has an external security review and runtime audit trail.",
                    "status": "supported",
                    "support_source_ids": ["ev-security-review", "ev-runtime-audit"],
                }
            ],
        }
    )


def test_validate_decision_rejects_string_claims():
    with pytest.raises(RuntimeError, match="array of objects"):
        slice_verifier.validate_decision(
            {
                "decision": "approve",
                "confidence": 0.83,
                "cited_evidence_ids": ["ev-security-review", "ev-runtime-audit"],
                "claims": ["Looks good"],
            }
        )


def test_validate_decision_rejects_claims_without_support_sources():
    with pytest.raises(RuntimeError, match="support_source_ids"):
        slice_verifier.validate_decision(
            {
                "decision": "approve",
                "confidence": 0.83,
                "cited_evidence_ids": ["ev-security-review", "ev-runtime-audit"],
                "claims": [{"text": "Looks good", "status": "supported", "support_source_ids": []}],
            }
        )


def test_hmac_credential_is_deterministic(monkeypatch):
    monkeypatch.setenv("RESERVE_SIGNING_KEY", "test-signing-key")
    score = {"overall_log_score": -0.1, "total_sample_count": 2, "cells": []}

    first = slice_verifier.hmac_credential("agent-a", score)
    second = slice_verifier.hmac_credential("agent-a", score)

    assert first == second
    assert first != slice_verifier.hmac_credential("agent-b", score)
