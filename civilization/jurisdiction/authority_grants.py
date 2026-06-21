from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    grantee_entity_type: str
    grantee_entity_id: str
    granted_by_entity_type: str
    granted_by_entity_id: str
    authority_scope: dict
    allowed_actions: list[str]
    allowed_domains: list[str]
    allowed_claim_types: list[str]
    max_risk_level: str
    status: str
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime | None = None


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    reason: str
    grant_id: str | None = None
