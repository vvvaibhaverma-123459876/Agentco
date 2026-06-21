from __future__ import annotations

import uuid

from epistemic.disputes.dispute_model import ClaimDispute, DisputeType


class InMemoryDisputeService:
    def __init__(self) -> None:
        self.disputes: dict[str, ClaimDispute] = {}

    def open_dispute(self, claim_id: str, opened_by: str, dispute_type: DisputeType, severity: str, metadata: dict | None = None) -> ClaimDispute:
        dispute = ClaimDispute(
            dispute_id=str(uuid.uuid4()),
            claim_id=claim_id,
            opened_by=opened_by,
            dispute_type=dispute_type,
            status="opened",
            severity=severity,
            metadata=metadata or {},
        )
        self.disputes[dispute.dispute_id] = dispute
        return dispute

    def list_for_claim(self, claim_id: str) -> list[ClaimDispute]:
        return [d for d in self.disputes.values() if d.claim_id == claim_id]

    def set_status(self, dispute_id: str, status: str) -> ClaimDispute:
        old = self.disputes[dispute_id]
        new = ClaimDispute(**{**old.__dict__, "status": status})
        self.disputes[dispute_id] = new
        return new
