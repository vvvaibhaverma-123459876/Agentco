from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from epistemic.claims.claim_model import StructuredClaim
from epistemic.disputes.dispute_model import ClaimDispute
from epistemic.evidence.evidence_model import EXTERNAL_EVIDENCE_TYPES, MECHANICAL_EVIDENCE_TYPES, EvidenceRecord
from epistemic.validation.validation_policy_engine import ValidationPolicyEngine


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    target_status: str | None
    reason: str
    missing_requirements: list[str]


def can_promote_claim(
    claim: StructuredClaim,
    evidence_records: list[EvidenceRecord],
    validation_results: list[dict] | None = None,
    disputes: list[ClaimDispute] | None = None,
    *,
    now: datetime | None = None,
    policy_engine: ValidationPolicyEngine | None = None,
) -> PromotionDecision:
    now = now or datetime.now(timezone.utc)
    validation_results = validation_results or []
    disputes = disputes or []
    policy = (policy_engine or ValidationPolicyEngine()).select_policy(claim)

    serious_disputes = [d for d in disputes if d.status not in {"closed", "finalized"} and d.severity in {"high", "critical"}]
    if serious_disputes:
        return PromotionDecision(False, None, "unresolved serious dispute blocks promotion", ["resolve_dispute"])

    if claim.reality_boundary == "R6_future_outcome" and claim.resolution_date and now < claim.resolution_date:
        return PromotionDecision(False, None, "future outcome cannot promote before resolution date", ["resolution_date"])

    evidence_types = {e.evidence_type for e in evidence_records if e.admissibility_status in {"admissible", "accepted", "submitted"}}
    missing = [etype for etype in policy.required_evidence if etype not in evidence_types]
    if missing:
        return PromotionDecision(False, None, "missing required evidence", missing)

    has_external = bool(evidence_types & EXTERNAL_EVIDENCE_TYPES)
    has_mechanical = bool(evidence_types & MECHANICAL_EVIDENCE_TYPES)

    if claim.reality_boundary == "R3_simulation_truth":
        return PromotionDecision(True, "simulation_validated", "simulation can validate only simulation truth", [])

    if policy.external_validation_required and not has_external and not has_mechanical:
        return PromotionDecision(False, None, "external validation required", ["external_evidence"])

    if claim.reality_boundary == "R7_normative_judgment":
        return PromotionDecision(True, "institutionally_verified", "normative claim uses governance process, not empirical truth scoring", [])

    if has_mechanical and claim.reality_boundary in {"R1_formal_truth", "R2_software_execution"}:
        return PromotionDecision(True, "mechanically_resolved", "mechanical evidence satisfies claim boundary", [])

    if policy.promotion_target == "reality_validated" and not (has_external or has_mechanical):
        return PromotionDecision(False, None, "reality validation requires external or mechanical evidence", ["external_or_mechanical_evidence"])

    return PromotionDecision(True, policy.promotion_target, "policy requirements satisfied", [])
