"""
Learning Governance — Knowledge promotion workflow and rules.

Controls how claims move up the knowledge status ladder through institutional review.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from .knowledge_claim import KnowledgeClaim, ClaimStatus


@dataclass
class PromotionProposal:
    """Proposal to promote a claim to next status."""

    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    claim_id: str = ""
    current_status: str = ""
    proposed_status: str = ""
    proposer_institution: str = ""
    evidence_summary: str = ""
    contradictions_resolved: bool = False
    adversarial_review_passed: bool = False
    required_reviews: List[str] = field(default_factory=list)
    completed_reviews: List[str] = field(default_factory=list)
    approval_status: str = "pending"  # pending|approved|rejected|blocked
    created_at: datetime = field(default_factory=datetime.utcnow)


class LearningGovernanceService:
    """Service for knowledge promotion governance."""

    def __init__(self):
        """Initialize governance service."""
        self.proposals: Dict[str, PromotionProposal] = {}

    def propose_knowledge_promotion(
        self, claim: KnowledgeClaim, proposer: str
    ) -> PromotionProposal:
        """Propose promotion of a claim."""
        # Determine next status
        next_status = self._get_next_status(claim.status)

        proposal = PromotionProposal(
            claim_id=claim.claim_id,
            current_status=claim.status.value,
            proposed_status=next_status.value,
            proposer_institution=proposer,
            evidence_summary=f"Claim has been {claim.status.value}",
            required_reviews=self._get_required_reviews(claim),
        )

        self.proposals[proposal.proposal_id] = proposal
        return proposal

    def _get_next_status(self, current_status: ClaimStatus) -> ClaimStatus:
        """Get next status in ladder."""
        ladder = [
            ClaimStatus.OBSERVED,
            ClaimStatus.PARSED,
            ClaimStatus.UNDERSTOOD,
            ClaimStatus.HYPOTHESIZED,
            ClaimStatus.SUPPORTED,
            ClaimStatus.TESTED,
            ClaimStatus.REPLICATED,
            ClaimStatus.CALIBRATED,
            ClaimStatus.INSTITUTIONALIZED,
        ]

        idx = ladder.index(current_status)
        return ladder[min(idx + 1, len(ladder) - 1)]

    def _get_required_reviews(self, claim: KnowledgeClaim) -> List[str]:
        """Determine which institutions must review."""
        reviews = []

        if claim.risk_level == "high":
            reviews.append("Adversarial Critique Institution")

        if claim.status.value in ["supported", "tested"]:
            reviews.append("Evidence Audit Institution")

        if claim.promotion_level >= 7:  # High-level promotion
            reviews.append("Governance Review Institution")

        return reviews or ["Evidence Audit Institution"]

    def approve_knowledge_promotion(self, proposal_id: str, approver: str) -> bool:
        """Approve a promotion proposal."""
        if proposal_id not in self.proposals:
            return False

        proposal = self.proposals[proposal_id]

        # Check if all required reviews completed
        if len(proposal.completed_reviews) < len(proposal.required_reviews):
            return False

        proposal.approval_status = "approved"
        return True

    def reject_knowledge_promotion(self, proposal_id: str, reason: str) -> bool:
        """Reject a promotion proposal."""
        if proposal_id not in self.proposals:
            return False

        proposal = self.proposals[proposal_id]
        proposal.approval_status = "rejected"
        return True

    def promote_knowledge(
        self, claim: KnowledgeClaim, proposal: PromotionProposal
    ) -> bool:
        """Execute promotion of knowledge."""
        if proposal.approval_status != "approved":
            return False

        next_status = self._get_next_status(claim.status)
        return claim.update_status(next_status)

    def export_promotion_audit(self, proposal_id: str) -> Dict[str, Any]:
        """Export audit trail for a promotion."""
        if proposal_id not in self.proposals:
            return {}

        proposal = self.proposals[proposal_id]
        return {
            "proposal_id": proposal_id,
            "claim_id": proposal.claim_id,
            "current_status": proposal.current_status,
            "proposed_status": proposal.proposed_status,
            "proposer": proposal.proposer_institution,
            "required_reviews": proposal.required_reviews,
            "completed_reviews": proposal.completed_reviews,
            "approval_status": proposal.approval_status,
            "created_at": proposal.created_at.isoformat(),
        }
