from __future__ import annotations

import uuid
from dataclasses import dataclass

from calibration.evidence import EvidenceKernel
from calibration.uncertainty import UncertaintyStack
from ingestion import IngestionPipeline
from ingestion.adapters import TextAdapter
from memory_kernel import MemoryKernel


@dataclass
class AdaptationProposal:
    proposal_id: str
    claim_id: str
    risk_level: str
    status: str
    rationale: str


class AutonomousLearningLoop:
    """Observe -> Extract -> Evaluate -> Experiment -> Learn -> Adapt -> Govern."""

    def __init__(
        self,
        evidence: EvidenceKernel | None = None,
        memory: MemoryKernel | None = None,
        uncertainty: UncertaintyStack | None = None,
    ):
        self.evidence = evidence or EvidenceKernel()
        self.memory = memory or MemoryKernel()
        self.uncertainty = uncertainty or UncertaintyStack()
        self.ingestion = IngestionPipeline(self.evidence)
        self.proposals: list[AdaptationProposal] = []

    def run(self, signal_text: str, *, source_uri: str = "memory://signal") -> dict:
        ingested = self.ingestion.ingest_document(TextAdapter().ingest(signal_text, source_uri))
        claims = ingested["claims"]
        hypothesis = {
            "hypothesis_id": str(uuid.uuid4()),
            "claim_id": claims[0].claim_id if claims else None,
            "text": f"Test whether: {claims[0].claim_text}" if claims else "No claim extracted",
        }
        experiment = {
            "experiment_id": str(uuid.uuid4()),
            "hypothesis_id": hypothesis["hypothesis_id"],
            "method": "external_resolution_required",
            "status": "proposed",
        }
        memory_event = self.memory.write_experience(
            "learning-loop",
            "prediction_lesson",
            {"signal": signal_text, "hypothesis": hypothesis, "experiment": experiment},
            provenance_ref=ingested["audit_event"]["source_uri"],
        )
        decision = self.uncertainty.decide(
            stated_confidence=0.7,
            historical_multiplier=0.8,
            candidates=[hypothesis["text"], hypothesis["text"]],
        )
        proposal = AdaptationProposal(
            proposal_id=str(uuid.uuid4()),
            claim_id=hypothesis["claim_id"] or "",
            risk_level="medium" if decision.should_abstain else "low",
            status="governance_required",
            rationale="Learning loop proposes adaptation; governance must approve before activation.",
        )
        self.proposals.append(proposal)
        return {
            "claims": claims,
            "hypothesis": hypothesis,
            "experiment": experiment,
            "memory_event": memory_event,
            "adaptation_proposal": proposal,
            "governed": proposal.status == "governance_required",
        }
