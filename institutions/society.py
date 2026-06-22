from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class InstitutionRecord:
    institution_id: str
    name: str
    purpose: str
    status: str = "active"


@dataclass
class SocietyRecord:
    society_id: str
    name: str
    institutions: list[str] = field(default_factory=list)


class SocietyKernel:
    def __init__(self):
        self.institutions: dict[str, InstitutionRecord] = {}
        self.societies: dict[str, SocietyRecord] = {}
        self.agent_membership: dict[str, str] = {}
        self.proposals: dict[str, dict] = {}

    def create_institution(self, name: str, purpose: str) -> InstitutionRecord:
        item = InstitutionRecord(str(uuid.uuid4()), name, purpose)
        self.institutions[item.institution_id] = item
        return item

    def create_society(self, name: str, institutions: list[str]) -> SocietyRecord:
        item = SocietyRecord(str(uuid.uuid4()), name, institutions)
        self.societies[item.society_id] = item
        return item

    def assign_agent(self, agent_id: str, institution_id: str) -> None:
        if institution_id not in self.institutions:
            raise KeyError(institution_id)
        self.agent_membership[agent_id] = institution_id

    def propose_structure_change(self, society_id: str, change: dict) -> dict:
        proposal_id = str(uuid.uuid4())
        proposal = {"proposal_id": proposal_id, "society_id": society_id, "change": change, "status": "proposed"}
        self.proposals[proposal_id] = proposal
        return proposal

    def decide(self, proposal_id: str, approved: bool) -> dict:
        proposal = self.proposals[proposal_id]
        proposal["status"] = "approved" if approved else "rejected"
        return proposal
