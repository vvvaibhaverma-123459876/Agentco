"""
Cross-Domain Synthesis — Transfer learning across domains.

Extracts principles from one domain and tests transfer to another.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from .knowledge_claim import KnowledgeClaim


@dataclass
class CrossDomainTransfer:
    """A hypothesis that a principle transfers across domains."""

    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_domain: str = ""
    target_domain: str = ""
    source_principle: str = ""
    extracted_principle: str = ""
    transfer_hypothesis: str = ""
    assumptions: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    proposed_test: Optional[str] = None
    resolution_criteria: Optional[str] = None
    confidence: float = 0.3  # Start low
    status: str = "hypothesis"  # hypothesis|tested|supported|rejected
    linked_experiment_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class CrossDomainSynthesisEngine:
    """Engine for cross-domain principle transfer."""

    def extract_principle(self, claim: KnowledgeClaim) -> str:
        """Extract abstract principle from domain-specific claim."""
        # Deterministic heuristic: remove domain-specific terms
        principle = claim.normalized_claim
        domain_terms = [claim.domain, claim.subdomain or ""]
        for term in domain_terms:
            principle = principle.replace(term.lower(), "")
        return principle.strip()

    def generate_transfer_hypothesis(
        self, source_domain: str, target_domain: str, principle: str
    ) -> CrossDomainTransfer:
        """Generate transfer hypothesis for principle."""
        return CrossDomainTransfer(
            source_domain=source_domain,
            target_domain=target_domain,
            source_principle=principle,
            extracted_principle=principle,
            transfer_hypothesis=f"If {principle} holds in {source_domain}, it may hold in {target_domain}",
            confidence=0.3,
            proposed_test=f"Test principle in {target_domain} domain",
        )

    def identify_transfer_assumptions(
        self, transfer: CrossDomainTransfer
    ) -> List[str]:
        """Identify assumptions required for transfer."""
        assumptions = [
            f"Entities in {transfer.target_domain} map to {transfer.source_domain}",
            f"Feedback mechanisms similar between domains",
            f"Timescales comparable",
        ]
        transfer.assumptions = assumptions
        return assumptions

    def identify_failure_modes(
        self, transfer: CrossDomainTransfer
    ) -> List[str]:
        """Identify ways transfer could fail."""
        modes = [
            f"Assumption violation: entities don't map",
            f"Timescale mismatch: processes operate at different speeds",
            f"Boundary effects: domain-specific constraints",
            f"Emergence: new properties at different scale",
        ]
        transfer.failure_modes = modes
        return modes

    def create_transfer_test_plan(self, transfer: CrossDomainTransfer) -> Dict[str, Any]:
        """Create test plan for transfer hypothesis."""
        return {
            "transfer_id": transfer.transfer_id,
            "source_domain": transfer.source_domain,
            "target_domain": transfer.target_domain,
            "test_objective": transfer.proposed_test,
            "assumptions_to_check": transfer.assumptions,
            "failure_modes_to_avoid": transfer.failure_modes,
            "success_criteria": f"Principle holds in {transfer.target_domain} with expected mechanism",
        }

    def mark_transfer_tested(
        self, transfer: CrossDomainTransfer, supported: bool, confidence: float
    ) -> CrossDomainTransfer:
        """Mark transfer as tested."""
        transfer.status = "supported" if supported else "rejected"
        transfer.confidence = confidence
        return transfer
