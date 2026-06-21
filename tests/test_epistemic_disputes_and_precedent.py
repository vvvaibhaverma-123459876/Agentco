from epistemic.claims.claim_model import StructuredClaim
from epistemic.disputes.dispute_service import InMemoryDisputeService
from epistemic.disputes.precedent_service import InMemoryPrecedentService
from epistemic.disputes.ruling_service import InMemoryRulingService
from epistemic.evidence.evidence_store import InMemoryEvidenceStore
from epistemic.promotion.knowledge_promotion import can_promote_claim


def _claim(status: str = "externally_grounded") -> StructuredClaim:
    from datetime import datetime, timezone
    return StructuredClaim(
        claim_id="claim-1",
        claim_text="external claim",
        claimant_id="agent-1",
        claimant_entity_type="agent",
        claimant_institution_id=None,
        domain="test",
        claim_type="general",
        reality_boundary="R5_external_empirical_reality",
        risk_level="high",
        probability=0.7,
        status=status,  # type: ignore[arg-type]
        resolution_date=datetime.now(timezone.utc),
        resolution_criterion="external evidence",
        validation_policy_id=None,
    )


def _external_evidence(claim_id: str):
    return InMemoryEvidenceStore().add_evidence(
        claim_id=claim_id,
        evidence_type="external_document",
        submitted_by="auditor",
        submitted_by_entity_type="human",
        evidence_payload={"source": "external"},
        admissibility_status="admissible",
    )


def test_open_dispute_and_unresolved_dispute_blocks_promotion():
    claim = _claim()
    disputes = InMemoryDisputeService()
    dispute = disputes.open_dispute(claim.claim_id, "auditor", "methodology_flawed", "high")
    decision = can_promote_claim(claim, [_external_evidence(claim.claim_id)], disputes=[dispute])
    assert not decision.allowed
    assert decision.reason == "unresolved serious dispute blocks promotion"


def test_final_overturned_ruling_changes_claim_state():
    disputes = InMemoryDisputeService()
    rulings = InMemoryRulingService()
    dispute = disputes.open_dispute("claim-1", "auditor", "evidence_invalid", "high")
    ruling = rulings.add_ruling(dispute.dispute_id, "court-1", "overturned", "source was invalid", final=True)
    assert rulings.apply_final_ruling_status("externally_grounded", ruling) == "overturned"


def test_precedent_created_from_ruling():
    disputes = InMemoryDisputeService()
    rulings = InMemoryRulingService()
    precedents = InMemoryPrecedentService()
    dispute = disputes.open_dispute("claim-1", "auditor", "policy_violation", "high")
    ruling = rulings.add_ruling(dispute.dispute_id, "court-1", "policy_violation", "policy was violated", precedent_created=True, final=True)
    precedent = precedents.create_from_ruling(
        ruling,
        summary="Policy violations block promotion",
        binding_scope="institution",
        binding_level="advisory",
        applies_to_policy_ids=["external_empirical_claim_v1"],
    )
    assert precedent.source_ruling_id == ruling.ruling_id
    assert precedent.applies_to_policy_ids == ["external_empirical_claim_v1"]


def test_fraudulent_ruling_marks_claim_fraudulent():
    rulings = InMemoryRulingService()
    ruling = rulings.add_ruling("dispute-1", "court-1", "fraudulent", "fabricated source", penalties={"reputation": -1}, final=True)
    assert rulings.apply_final_ruling_status("externally_grounded", ruling) == "fraudulent"
    assert ruling.penalties == {"reputation": -1}
