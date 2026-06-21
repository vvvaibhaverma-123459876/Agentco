from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

RealityBoundary = Literal[
    "R0_internal_state",
    "R1_formal_truth",
    "R2_software_execution",
    "R3_simulation_truth",
    "R4_institutional_truth",
    "R5_external_empirical_reality",
    "R6_future_outcome",
    "R7_normative_judgment",
    "R8_strategic_business_claim",
]

ClaimStatus = Literal[
    "draft",
    "structured",
    "pre_registered",
    "evidence_pending",
    "under_verification",
    "internally_verified",
    "institutionally_verified",
    "adversarially_reviewed",
    "externally_grounded",
    "mechanically_resolved",
    "reality_validated",
    "simulation_validated",
    "rejected",
    "disputed",
    "contradicted",
    "overturned",
    "stale",
    "deprecated",
    "fraudulent",
    "non_falsifiable",
    "insufficient_evidence",
]


@dataclass(frozen=True)
class StructuredClaim:
    claim_id: str
    claim_text: str
    claimant_id: str
    claimant_entity_type: str
    claimant_institution_id: str | None
    domain: str
    claim_type: str
    reality_boundary: RealityBoundary
    risk_level: str
    probability: float | None
    status: ClaimStatus
    resolution_date: datetime | None
    resolution_criterion: str | None
    validation_policy_id: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
