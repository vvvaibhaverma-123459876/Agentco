"""
Scientific Evidence Engine — Classify evidence strength and verify requirements.

Maps evidence types to a hierarchy from strongest to weakest,
identifies what verification is needed before claims can be trusted.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from .knowledge_claim import EvidenceType, KnowledgeClaim, ClaimType


@dataclass
class EvidenceClassification:
    """Classification of evidence for a claim."""

    claim_id: str
    evidence_type: EvidenceType
    evidence_tier: int  # 1 (strongest) to 11 (weakest)
    domain: str
    sample_size: Optional[int] = None
    effect_size: Optional[float] = None
    replication_count: int = 0
    external_validity: str = "unknown"
    conflicts_of_interest: Optional[str] = None
    verification_required: bool = True
    verification_priority: str = "medium"  # low|medium|high|critical
    confidence: float = 0.5


class EvidenceEngine:
    """Engine for evidence classification and verification planning."""

    EVIDENCE_HIERARCHY = [
        (1, EvidenceType.FORMAL_PROOF),
        (2, EvidenceType.RAW_DATASET),
        (3, EvidenceType.REPLICATED_PEER_REVIEWED_STUDY),
        (4, EvidenceType.META_ANALYSIS),
        (5, EvidenceType.SYSTEMATIC_REVIEW),
        (6, EvidenceType.TEXTBOOK),
        (7, EvidenceType.SINGLE_PEER_REVIEWED_PAPER),
        (8, EvidenceType.PREPRINT),
        (9, EvidenceType.EXPERT_LECTURE),
        (10, EvidenceType.BLOG_ARTICLE),
        (11, EvidenceType.FORUM_CLAIM),
        (12, EvidenceType.LLM_SUMMARY),
        (13, EvidenceType.SIMULATION_RESULT),
        (14, EvidenceType.EXPERIMENT_RESULT),
        (15, EvidenceType.UNKNOWN),
    ]

    EVIDENCE_TO_TIER = {ev_type: tier for tier, ev_type in EVIDENCE_HIERARCHY}

    def classify_evidence(self, claim: KnowledgeClaim) -> EvidenceClassification:
        """Classify evidence for a claim and determine verification needs."""
        tier = self.EVIDENCE_TO_TIER.get(claim.evidence_type, 15)

        # Determine verification priority based on claim type and evidence tier
        verification_priority = self._determine_verification_priority(
            claim.claim_type, tier, claim.risk_level
        )

        return EvidenceClassification(
            claim_id=claim.claim_id,
            evidence_type=claim.evidence_type,
            evidence_tier=tier,
            domain=claim.domain,
            verification_required=tier > 6,  # Low-tier evidence needs verification
            verification_priority=verification_priority,
            confidence=self._compute_confidence(tier, claim.evidence_type),
        )

    def _determine_verification_priority(
        self, claim_type: ClaimType, evidence_tier: int, risk_level: str
    ) -> str:
        """Determine how urgently evidence needs verification."""
        if risk_level == "high":
            return "critical"
        if evidence_tier > 10:
            return "high"
        if evidence_tier > 6:
            return "medium"
        return "low"

    def _compute_confidence(
        self, evidence_tier: int, evidence_type: EvidenceType
    ) -> float:
        """Compute initial confidence based on evidence tier."""
        # Stronger evidence = higher confidence
        if evidence_tier <= 3:
            return 0.9
        elif evidence_tier <= 6:
            return 0.7
        elif evidence_tier <= 10:
            return 0.5
        else:
            return 0.3

    def create_verification_plan(
        self, claim: KnowledgeClaim, classification: EvidenceClassification
    ) -> Dict[str, Any]:
        """Create a plan to verify the claim."""
        return {
            "claim_id": claim.claim_id,
            "verification_type": self._select_verification_type(
                claim.claim_type, classification.evidence_tier
            ),
            "estimated_cost": self._estimate_cost(classification.evidence_tier),
            "time_estimate": self._estimate_time(classification.evidence_tier),
            "required_expertise": claim.domain,
            "success_criteria": f"Independent verification or replication of {claim.normalized_claim}",
            "priority": classification.verification_priority,
        }

    def _select_verification_type(self, claim_type: ClaimType, tier: int) -> str:
        """Select the verification approach."""
        if claim_type == ClaimType.FORMAL_PROOF:
            return "mathematical_verification"
        elif claim_type in [ClaimType.EMPIRICAL_CLAIM, ClaimType.STATISTICAL_CLAIM]:
            if tier >= 9:
                return "replication"
            else:
                return "cross_validation"
        elif claim_type == ClaimType.ENGINEERING_CLAIM:
            return "reproducibility_test"
        else:
            return "expert_review"

    def _estimate_cost(self, tier: int) -> str:
        """Estimate computational/resource cost."""
        if tier <= 3:
            return "high"
        elif tier <= 7:
            return "medium"
        else:
            return "low"

    def _estimate_time(self, tier: int) -> str:
        """Estimate time to verification."""
        if tier <= 3:
            return "weeks"
        elif tier <= 7:
            return "days"
        else:
            return "hours"

    def detect_contradictions(
        self, claim1: KnowledgeClaim, claim2: KnowledgeClaim
    ) -> bool:
        """Check if two claims directly contradict each other."""
        # Deterministic heuristic: check for negation words
        negation_words = ["not", "no", "false", "cannot", "never", "opposite"]

        normalized1 = claim1.normalized_claim.lower()
        normalized2 = claim2.normalized_claim.lower()

        # Simple negation check
        for word in negation_words:
            if word in normalized1 and word not in normalized2:
                # Check if removing negation words makes them similar
                cleaned1 = normalized1.replace(word, "").strip()
                if cleaned1 in normalized2:
                    return True

        return False

    def mark_replication_needed(
        self, claim: KnowledgeClaim
    ) -> bool:
        """Mark that a claim needs replication before institutionalization."""
        tier = self.EVIDENCE_TO_TIER.get(claim.evidence_type, 15)
        # Preprints, blogs, forums, lectures need replication
        return tier >= 8

    def extract_evidence_attributes(
        self, claim: KnowledgeClaim
    ) -> Dict[str, Any]:
        """Extract evidence-specific attributes from claim metadata."""
        attrs = {
            "evidence_type": claim.evidence_type.value,
            "domain": claim.domain,
            "testability": claim.testability,
        }

        # Add metadata if present
        if hasattr(claim, "metadata"):
            attrs.update(claim.metadata)

        return attrs
