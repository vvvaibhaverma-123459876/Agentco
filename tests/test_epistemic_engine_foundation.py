from datetime import datetime, timedelta, timezone

import pytest

from epistemic.claims.claim_model import StructuredClaim
from epistemic.disputes.dispute_model import ClaimDispute
from epistemic.evidence.evidence_store import InMemoryEvidenceStore
from epistemic.promotion.knowledge_promotion import can_promote_claim
from epistemic.validation.validation_policy_engine import ValidationPolicyEngine
from epistemic.validation.validation_rings import minimum_ring_for_claim


def claim(boundary: str, *, claim_type: str = "general", risk: str = "low", resolution_date=None) -> StructuredClaim:
    return StructuredClaim(
        claim_id=f"claim-{boundary}",
        claim_text="test claim",
        claimant_id="agent-1",
        claimant_entity_type="agent",
        claimant_institution_id=None,
        domain="test",
        claim_type=claim_type,
        reality_boundary=boundary,  # type: ignore[arg-type]
        risk_level=risk,
        probability=0.7,
        status="structured",
        resolution_date=resolution_date,
        resolution_criterion="test",
        validation_policy_id=None,
    )


def evidence(claim_id: str, evidence_type: str):
    store = InMemoryEvidenceStore()
    return store.add_evidence(
        claim_id=claim_id,
        evidence_type=evidence_type,  # type: ignore[arg-type]
        submitted_by="tester",
        submitted_by_entity_type="human",
        evidence_payload={"ok": True},
        admissibility_status="admissible",
    )


def test_internal_ledger_claim_can_internally_verify_with_audit_and_ledger_evidence():
    c = claim("R0_internal_state")
    decision = can_promote_claim(c, [evidence(c.claim_id, "ledger_row"), evidence(c.claim_id, "audit_log")])
    assert decision.allowed
    assert decision.target_status == "internally_verified"


def test_simulation_claim_cannot_promote_to_reality_validated():
    c = claim("R3_simulation_truth")
    decision = can_promote_claim(c, [evidence(c.claim_id, "dataset_snapshot")])
    assert decision.allowed
    assert decision.target_status == "simulation_validated"


def test_external_empirical_claim_requires_external_evidence():
    c = claim("R5_external_empirical_reality")
    blocked = can_promote_claim(c, [evidence(c.claim_id, "agent_assertion")])
    assert not blocked.allowed
    ok = can_promote_claim(c, [evidence(c.claim_id, "external_document")])
    assert ok.allowed
    assert ok.target_status == "externally_grounded"


def test_future_claim_cannot_promote_before_resolution_date():
    c = claim("R6_future_outcome", resolution_date=datetime.now(timezone.utc) + timedelta(days=1))
    decision = can_promote_claim(c, [evidence(c.claim_id, "external_api_response")])
    assert not decision.allowed
    assert "resolution date" in decision.reason


def test_normative_claim_uses_governance_policy_not_truth_scoring():
    c = claim("R7_normative_judgment")
    decision = can_promote_claim(c, [evidence(c.claim_id, "court_or_governance_ruling")])
    assert decision.allowed
    assert decision.target_status == "institutionally_verified"


def test_unresolved_dispute_blocks_promotion():
    c = claim("R5_external_empirical_reality")
    dispute = ClaimDispute("d1", c.claim_id, "auditor", "methodology_flawed", "opened", "high")
    decision = can_promote_claim(c, [evidence(c.claim_id, "external_document")], disputes=[dispute])
    assert not decision.allowed
    assert decision.missing_requirements == ["resolve_dispute"]


def test_mechanical_evidence_promotes_software_claim_to_mechanically_resolved():
    c = claim("R2_software_execution")
    decision = can_promote_claim(c, [evidence(c.claim_id, "test_result"), evidence(c.claim_id, "ci_build_artifact")])
    assert decision.allowed
    assert decision.target_status == "mechanically_resolved"


def test_claim_authority_ring_matches_boundary_and_risk():
    assert minimum_ring_for_claim("R5_external_empirical_reality", "low", "general") == 6
    assert minimum_ring_for_claim("R2_software_execution", "low", "general") == 7
    assert minimum_ring_for_claim("R0_internal_state", "critical", "general") == 6


def test_high_risk_claim_without_policy_is_rejected():
    engine = ValidationPolicyEngine(policies=[])
    with pytest.raises(ValueError, match="no validation policy"):
        engine.select_policy(claim("R5_external_empirical_reality", risk="high"))
