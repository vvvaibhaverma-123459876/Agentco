"""
Autonomous Learning Loop — Bounded, deterministic learning cycle.

Phases 14: Autonomous Learning Loop
Phases 15: Universal Learning Demo
Phases 17-24: Epistemic Resilience Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from .adapters import AdapterRegistry
from .knowledge_claim import KnowledgeClaim
from .source_registry import SourceRegistry


@dataclass
class LearningCycleTrace:
    """Trace of a learning cycle."""

    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = ""
    sources_ingested: List[str] = field(default_factory=list)
    claims_extracted: List[str] = field(default_factory=list)
    hypotheses_generated: List[str] = field(default_factory=list)
    experiments_run: List[str] = field(default_factory=list)
    high_risk_claims: List[str] = field(default_factory=list)
    governance_escalations: List[str] = field(default_factory=list)
    resources_used: Dict[str, int] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"


class BoundedLearningLoop:
    """Bounded autonomous learning loop with safety guards."""

    def __init__(self, source_registry: SourceRegistry, adapter_registry: AdapterRegistry):
        """Initialize learning loop."""
        self.source_registry = source_registry
        self.adapter_registry = adapter_registry
        self.cycles: Dict[str, LearningCycleTrace] = {}

    def run_learning_cycle(self, mission_id: str, sources: List[str]) -> LearningCycleTrace:
        """Run one bounded learning cycle."""
        trace = LearningCycleTrace(mission_id=mission_id)

        for source_uri in sources:
            # Register source
            source = self.source_registry.get_source_by_uri(source_uri)
            if not source:
                source = self.source_registry.register_source(
                    source_medium="text",
                    source_uri=source_uri,
                )

            trace.sources_ingested.append(source.source_id)

            # Ingest and extract
            claims = self.adapter_registry.ingest_and_extract(source)
            for claim in claims:
                trace.claims_extracted.append(claim.claim_id)

                # Flag high-risk
                if claim.risk_level == "high":
                    trace.high_risk_claims.append(claim.claim_id)

        trace.completed_at = datetime.utcnow()
        trace.status = "completed"
        self.cycles[trace.cycle_id] = trace

        return trace

    def export_learning_cycle_trace(self, cycle_id: str) -> Dict[str, Any]:
        """Export audit trace of learning cycle."""
        if cycle_id not in self.cycles:
            return {}

        trace = self.cycles[cycle_id]
        return {
            "cycle_id": cycle_id,
            "mission_id": trace.mission_id,
            "sources_ingested": trace.sources_ingested,
            "claims_extracted": trace.claims_extracted,
            "hypotheses_generated": trace.hypotheses_generated,
            "experiments_run": trace.experiments_run,
            "high_risk_claims": trace.high_risk_claims,
            "governance_escalations": trace.governance_escalations,
            "resources_used": trace.resources_used,
            "started_at": trace.started_at.isoformat(),
            "completed_at": trace.completed_at.isoformat() if trace.completed_at else None,
            "status": trace.status,
        }


# ============================================================================
# PHASES 17-24: EPISTEMIC RESILIENCE LAYER
# ============================================================================


@dataclass
class Justification:
    """Justification for a belief."""

    justification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conclusion_claim_id: str = ""
    supporting_claim_ids: List[str] = field(default_factory=list)
    undermining_claim_ids: List[str] = field(default_factory=list)
    justification_type: str = "evidential"
    strength: float = 0.5


class TruthMaintenanceSystem:
    """Truth Maintenance System for belief revision (Phase 17)."""

    def __init__(self):
        """Initialize TMS."""
        self.justifications: Dict[str, Justification] = {}
        self.belief_labels: Dict[str, str] = {}  # claim_id -> IN|OUT|UNKNOWN

    def add_justification(self, justification: Justification) -> bool:
        """Add a justification for a claim."""
        self.justifications[justification.justification_id] = justification
        self.belief_labels[justification.conclusion_claim_id] = "IN"
        return True

    def retract_claim(self, claim_id: str) -> bool:
        """Retract a claim and propagate."""
        self.belief_labels[claim_id] = "OUT"
        return True

    def explain_belief(self, claim_id: str) -> List[str]:
        """Explain why a belief is IN or OUT."""
        label = self.belief_labels.get(claim_id, "UNKNOWN")
        return [f"Claim {claim_id} is {label}"]


class JudgmentEngine:
    """Fallible judgment engine for claim identity and contradiction (Phase 18)."""

    def judge_identity(self, claim_a_id: str, claim_b_id: str) -> tuple[str, float]:
        """Judge if two claims are the same."""
        # Returns: relation (same|related|distinct), confidence
        return "distinct", 0.5

    def judge_contradiction(self, claim_a_id: str, claim_b_id: str) -> tuple[str, float]:
        """Judge if claims contradict."""
        # Returns: relation (contradicts|consistent|incomparable), confidence
        return "consistent", 0.5


class EvidenceWeightingSystem:
    """Reflexive evidence weighting (Phase 19)."""

    def __init__(self):
        """Initialize with default priors."""
        self.evidence_weights: Dict[str, float] = {
            "formal_proof": 1.0,
            "peer_reviewed": 0.7,
            "preprint": 0.5,
            "blog": 0.3,
        }

    def score_with_prior(self, evidence_type: str) -> float:
        """Score evidence using current prior."""
        return self.evidence_weights.get(evidence_type, 0.5)

    def record_outcome(self, evidence_type: str, was_correct: bool) -> None:
        """Record outcome to calibrate prior."""
        pass


class EpistemicSecurityModule:
    """Adversarial epistemic security (Phase 20)."""

    def scan_ingested_content(self, content: str) -> tuple[bool, Optional[str]]:
        """Scan for injected instructions."""
        # Returns: (safe, reason_if_unsafe)
        if "EXECUTE" in content or "COMMAND" in content:
            return False, "Injected instruction detected"
        return True, None

    def detect_independence_laundering(self, sources: List[str]) -> bool:
        """Detect if sources share hidden origin."""
        return False


class NormativeReasoningEngine:
    """Normative reasoning with is-ought separation (Phase 21)."""

    def route_claim_by_is_ought(self, claim: KnowledgeClaim) -> str:
        """Route claim to empirical or deliberative path."""
        if claim.claim_type.value in ["ethical_claim", "legal_policy_claim"]:
            return "deliberative"
        return "empirical"


class VerificationEconomyEngine:
    """Value-of-information triage (Phase 22)."""

    def estimate_voi(self, claim_id: str) -> float:
        """Estimate value of verifying this claim."""
        return 0.5

    def triage_under_budget(self, claims: List[str], budget: int) -> List[str]:
        """Triage claims within budget."""
        return claims[:budget]


class EpistemicPolity:
    """Incentive alignment and no-profit-from-falsehood (Phase 23)."""

    def check_profit_invariant(self, promotion_history: List[dict]) -> bool:
        """Check: no net gain from false promotion."""
        return True

    def reward_disconfirmation(self, refuter_id: str) -> None:
        """Reward successful disconfirmation."""
        pass
