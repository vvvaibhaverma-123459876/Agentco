"""
Learning Bridge: Connects TypeScript backend learning.service with Python AutonomousLearningLoop

This bridges the TypeScript backend with the Python autonomous learning layer, enabling:
1. Signal processing through the actual learning loop
2. Insight generation
3. Proposal creation and approval
4. Memory persistence
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure Agentco modules importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from learning.cycle import AutonomousLearningLoop
from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from memory_kernel import MemoryKernel
from institutions.society import SocietyKernel


class LearningBridge:
    """Bridges TypeScript backend with Python learning loop."""

    def __init__(self):
        # Initialize learning infrastructure
        self.evidence = EvidenceKernel()
        self.uncertainty = UncertaintyStack()
        self.memory = MemoryKernel()
        self.learning_loop = AutonomousLearningLoop(
            evidence=self.evidence,
            memory=self.memory,
            uncertainty=self.uncertainty,
        )
        self.societies = SocietyKernel()

        # Bootstrap society structure
        self._initialize_society()

    def _initialize_society(self):
        """Create basic institutional structure."""
        governance = self.societies.create_institution(
            "Governance", "Decision authority and oversight"
        )
        evidence_bureau = self.societies.create_institution(
            "Evidence Bureau", "Evidence validation and sourcing"
        )
        learning_institute = self.societies.create_institution(
            "Learning Institute", "Knowledge synthesis"
        )

        self.societies.create_society(
            "Agentco",
            [governance.institution_id, evidence_bureau.institution_id, learning_institute.institution_id],
        )

    def process_signal(
        self,
        agent_id: str,
        signal_type: str,
        content: Dict[str, Any],
        provenance_ref: str,
    ) -> Dict[str, Any]:
        """
        Process a learning signal through the full pipeline.

        Returns: {
            'signal_id': str,
            'claims': List[str],
            'insights': Dict,
            'proposal': Dict or None,
        }
        """
        signal_text = self._signal_to_text(agent_id, signal_type, content)

        # Run through learning loop
        result = self.learning_loop.run(
            signal_text,
            source_uri=provenance_ref,
        )

        claims = [c.claim_text for c in result.get("claims", [])]
        hypothesis = result.get("hypothesis", {})
        proposal = result.get("adaptation_proposal")

        return {
            "signal_id": f"signal_{agent_id}_{id(result)}",
            "agent_id": agent_id,
            "signal_type": signal_type,
            "claims": claims,
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "hypothesis_text": hypothesis.get("text"),
            "proposal_id": proposal.proposal_id if proposal else None,
            "proposal_status": proposal.status if proposal else None,
            "proposal_risk": proposal.risk_level if proposal else None,
        }

    def _signal_to_text(self, agent_id: str, signal_type: str, content: Dict[str, Any]) -> str:
        """Convert signal to natural language for learning loop."""
        if signal_type == "decision":
            return (
                f"Agent {agent_id} made a decision: {content.get('decision', 'unknown')}. "
                f"Evidence: {content.get('evidence', 'none')}. "
                f"Confidence: {content.get('confidence', 0.5)}"
            )
        elif signal_type == "outcome":
            return (
                f"Agent {agent_id} decision outcome: {content.get('outcome', 'unknown')}. "
                f"Task: {content.get('task_id', 'unknown')}. "
                f"Result: {content.get('result', 'pending')}"
            )
        elif signal_type == "evidence_update":
            return (
                f"New evidence for {content.get('claim', 'unknown')}: "
                f"{content.get('evidence', 'none')}. "
                f"Source: {content.get('source', 'unknown')}"
            )
        elif signal_type == "contradiction":
            return (
                f"Contradiction detected: {content.get('claim1', 'unknown')} vs "
                f"{content.get('claim2', 'unknown')}. "
                f"Source independence: {content.get('independent', False)}"
            )
        else:
            return json.dumps(content)

    def approve_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Approve a learning proposal in institutional context."""
        # Find proposal in learning loop
        for proposal in self.learning_loop.proposals:
            if proposal.proposal_id == proposal_id:
                proposal.status = "approved"
                return {
                    "proposal_id": proposal_id,
                    "status": "approved",
                    "rationale": proposal.rationale,
                }

        return {"error": f"Proposal {proposal_id} not found"}

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "claims": len(self.evidence.claims),
            "sources": len(self.evidence.sources),
            "resolutions": len(self.evidence.resolutions),
            "proposals": len(self.learning_loop.proposals),
            "proposals_approved": sum(1 for p in self.learning_loop.proposals if p.status == "approved"),
            "memory_events": len(self.memory.experiential),
            "memory_items": len(self.memory.operational),
        }


# Global instance
_bridge: Optional[LearningBridge] = None


def get_bridge() -> LearningBridge:
    """Get or create the learning bridge."""
    global _bridge
    if _bridge is None:
        _bridge = LearningBridge()
    return _bridge


def process_signal(
    agent_id: str,
    signal_type: str,
    content: Dict[str, Any],
    provenance_ref: str,
) -> Dict[str, Any]:
    """Process a signal through the learning bridge."""
    return get_bridge().process_signal(agent_id, signal_type, content, provenance_ref)


def approve_proposal(proposal_id: str) -> Dict[str, Any]:
    """Approve a proposal."""
    return get_bridge().approve_proposal(proposal_id)


def get_stats() -> Dict[str, Any]:
    """Get learning stats."""
    return get_bridge().get_statistics()


if __name__ == "__main__":
    # Quick test
    bridge = get_bridge()
    print("Bridge initialized:", bridge.get_statistics())

    # Test signal processing
    result = bridge.process_signal(
        "test-agent",
        "decision",
        {
            "decision": "Approve request",
            "evidence": "All criteria met",
            "confidence": 0.95,
        },
        "test://signal-1",
    )
    print("Signal result:", result)
    print("Bridge stats:", bridge.get_statistics())
