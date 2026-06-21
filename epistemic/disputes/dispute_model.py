from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

DisputeType = Literal[
    "evidence_invalid",
    "resolver_conflict",
    "claim_ambiguous",
    "source_unreliable",
    "methodology_flawed",
    "statistical_error",
    "overgeneralization",
    "policy_violation",
    "jurisdiction_violation",
    "fraudulent_claim",
    "non_falsifiable",
    "circular_resolution",
    "simulation_reality_confusion",
]


@dataclass(frozen=True)
class ClaimDispute:
    dispute_id: str
    claim_id: str
    opened_by: str
    dispute_type: DisputeType
    status: str
    severity: str
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)
