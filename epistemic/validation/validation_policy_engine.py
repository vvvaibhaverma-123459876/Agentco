from __future__ import annotations

from epistemic.claims.claim_model import StructuredClaim
from epistemic.validation.validation_policy import SEED_POLICIES, ValidationPolicy
from epistemic.validation.validation_rings import minimum_ring_for_claim


class ValidationPolicyError(ValueError):
    pass


class ValidationPolicyEngine:
    def __init__(self, policies: list[ValidationPolicy] | None = None) -> None:
        self.policies = SEED_POLICIES if policies is None else policies

    def select_policy(self, claim: StructuredClaim) -> ValidationPolicy:
        candidates = [
            p for p in self.policies
            if p.active
            and p.boundary == claim.reality_boundary
            and (p.domain is None or p.domain == claim.domain)
            and (p.claim_type is None or p.claim_type == claim.claim_type)
            and (p.risk_level is None or p.risk_level == claim.risk_level)
        ]
        if not candidates:
            if claim.risk_level.lower() in {"high", "critical"}:
                raise ValidationPolicyError("no validation policy exists for high-risk claim")
            raise ValidationPolicyError("no validation policy exists for claim")
        selected = candidates[0]
        required_ring = minimum_ring_for_claim(claim.reality_boundary, claim.risk_level, claim.claim_type)
        if selected.minimum_validation_ring < required_ring:
            return ValidationPolicy(
                **{**selected.__dict__, "minimum_validation_ring": required_ring}
            )
        return selected
