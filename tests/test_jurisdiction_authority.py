from datetime import datetime, timedelta, timezone

from civilization.jurisdiction.authority_grants import AuthorityGrant
from civilization.jurisdiction.jurisdiction_engine import can_entity_perform_action


def grant(**overrides):
    data = {
        "grant_id": "grant-1",
        "grantee_entity_type": "institution",
        "grantee_entity_id": "inst-1",
        "granted_by_entity_type": "society",
        "granted_by_entity_id": "soc-1",
        "authority_scope": {},
        "allowed_actions": ["verify_claim"],
        "allowed_domains": ["finance"],
        "allowed_claim_types": ["forecast"],
        "max_risk_level": "high",
        "status": "active",
        "valid_from": datetime.now(timezone.utc) - timedelta(days=1),
        "valid_until": datetime.now(timezone.utc) + timedelta(days=1),
    }
    data.update(overrides)
    return AuthorityGrant(**data)


def test_authorized_entity_passes():
    decision = can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high", grants=[grant()]
    )
    assert decision.allowed


def test_expired_wrong_domain_wrong_claim_and_risk_fail():
    assert not can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high",
        grants=[grant(valid_until=datetime.now(timezone.utc) - timedelta(seconds=1))]
    ).allowed
    assert not can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="medical", claim_type="forecast", risk_level="high", grants=[grant()]
    ).allowed
    assert not can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="diagnosis", risk_level="high", grants=[grant()]
    ).allowed
    assert not can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="critical", grants=[grant(max_risk_level="high")]
    ).allowed


def test_suspended_self_low_reputation_and_dispute_fail():
    key = ("institution", "inst-1")
    assert can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high", grants=[grant()],
        suspended_entities={key},
    ).reason == "entity_suspended"
    assert can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high",
        grants=[grant(granted_by_entity_type="institution", granted_by_entity_id="inst-1")],
    ).reason == "self_authority_expansion_rejected"
    assert can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high", grants=[grant()],
        low_reputation_entities={key},
    ).reason == "low_reputation_blocks_high_risk_authority"
    assert can_entity_perform_action(
        entity_type="institution", entity_id="inst-1", action="verify_claim",
        domain="finance", claim_type="forecast", risk_level="high", grants=[grant()],
        disputed_entities={key},
    ).reason == "unresolved_dispute_blocks_high_risk_authority"
