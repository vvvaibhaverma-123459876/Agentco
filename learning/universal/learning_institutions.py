"""
Learning Institutions — Roles and responsibilities for knowledge governance.

Defines learning institutions (Discovery, Replication, Critique, etc) with separation of powers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class LearningInstitution:
    """An institution responsible for learning and knowledge governance."""

    institution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # Discovery|Replication|Evidence Audit|Adversarial Critique|Memory|Governance
    role: str = ""
    departments: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)
    required_reviewers: int = 1
    can_certify: bool = False
    can_propose_promotion: bool = False
    can_approve_promotion: bool = False
    can_challenge_beliefs: bool = False
    reputation_score: float = 0.5
    calibration_record: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class LearningInstitutionService:
    """Service for managing learning institutions."""

    def __init__(self):
        """Initialize with default learning institutions."""
        self.institutions: Dict[str, LearningInstitution] = {}
        self._create_default_institutions()

    def _create_default_institutions(self):
        """Create the default set of learning institutions."""
        institutions = [
            LearningInstitution(
                name="Discovery Institution",
                role="Find and extract claims from sources",
                departments=["Ingestion", "Extraction"],
                can_propose_promotion=True,
                can_challenge_beliefs=False,
            ),
            LearningInstitution(
                name="Replication Institution",
                role="Reproduce and verify claims",
                departments=["Reproduction", "Verification"],
                can_certify=True,
                can_challenge_beliefs=False,
            ),
            LearningInstitution(
                name="Evidence Audit Institution",
                role="Classify and audit evidence",
                departments=["Evidence Classification", "Contradiction Detection"],
                can_challenge_beliefs=True,
            ),
            LearningInstitution(
                name="Adversarial Critique Institution",
                role="Try to disprove beliefs",
                departments=["Disconfirmation", "Edge Case Testing"],
                can_challenge_beliefs=True,
            ),
            LearningInstitution(
                name="Governance Review Institution",
                role="Approve knowledge promotion",
                departments=["Institutional Review", "Authority Gating"],
                can_approve_promotion=True,
            ),
        ]

        for inst in institutions:
            self.institutions[inst.name] = inst

    def get_institution(self, name: str) -> Optional[LearningInstitution]:
        """Retrieve an institution by name."""
        return self.institutions.get(name)

    def check_separation_of_powers(
        self, proposer: str, approver: str
    ) -> tuple[bool, Optional[str]]:
        """Check if proposer and approver are separate institutions."""
        if proposer == approver:
            return False, "Same institution cannot propose and approve"
        return True, None

    def validate_promotion_routing(
        self, claim_id: str, proposer: str
    ) -> tuple[bool, Optional[str]]:
        """Validate that claim is routed through proper institutions."""
        proposer_inst = self.get_institution(proposer)

        if not proposer_inst or not proposer_inst.can_propose_promotion:
            return False, f"{proposer} cannot propose promotions"

        return True, None
