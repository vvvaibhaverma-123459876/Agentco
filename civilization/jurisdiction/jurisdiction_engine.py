from __future__ import annotations

from datetime import datetime, timezone

from civilization.jurisdiction.authority_grants import AuthorityDecision, AuthorityGrant

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def can_entity_perform_action(
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    domain: str,
    claim_type: str,
    risk_level: str,
    grants: list[AuthorityGrant],
    suspended_entities: set[tuple[str, str]] | None = None,
    low_reputation_entities: set[tuple[str, str]] | None = None,
    disputed_entities: set[tuple[str, str]] | None = None,
    now: datetime | None = None,
) -> AuthorityDecision:
    now = now or datetime.now(timezone.utc)
    key = (entity_type, entity_id)
    if key in (suspended_entities or set()):
        return AuthorityDecision(False, "entity_suspended")
    if risk_level in {"high", "critical"} and key in (low_reputation_entities or set()):
        return AuthorityDecision(False, "low_reputation_blocks_high_risk_authority")
    if risk_level in {"high", "critical"} and key in (disputed_entities or set()):
        return AuthorityDecision(False, "unresolved_dispute_blocks_high_risk_authority")

    for grant in grants:
        if grant.grantee_entity_type != entity_type or grant.grantee_entity_id != entity_id:
            continue
        if grant.status != "active":
            continue
        if grant.granted_by_entity_type == entity_type and grant.granted_by_entity_id == entity_id:
            return AuthorityDecision(False, "self_authority_expansion_rejected")
        if grant.valid_from > now or (grant.valid_until and grant.valid_until <= now):
            continue
        if action not in grant.allowed_actions and "*" not in grant.allowed_actions:
            continue
        if domain not in grant.allowed_domains and "*" not in grant.allowed_domains:
            continue
        if claim_type not in grant.allowed_claim_types and "*" not in grant.allowed_claim_types:
            continue
        if RISK_ORDER.get(risk_level, 99) > RISK_ORDER.get(grant.max_risk_level, -1):
            continue
        return AuthorityDecision(True, "authorized", grant.grant_id)
    return AuthorityDecision(False, "no_applicable_authority_grant")
