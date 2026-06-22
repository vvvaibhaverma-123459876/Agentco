from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentProfile:
    agent_id: str
    role: str
    capabilities: set[str]
    tools: set[str]
    institution: str
    trust_score: float
    domains: set[str]
    risk_limit: str = "low"
    status: str = "active"


@dataclass
class SkillProfile:
    skill_id: str
    name: str
    required_tools: set[str]
    benchmark_score: float
    owning_institution: str
    version: str = "1.0.0"


class AgentRegistry:
    def __init__(self):
        self.agents: dict[str, AgentProfile] = {}
        self.skills: dict[str, SkillProfile] = {}

    def register_agent(self, profile: AgentProfile) -> None:
        self.agents[profile.agent_id] = profile

    def register_skill(self, profile: SkillProfile) -> None:
        self.skills[profile.skill_id] = profile

    def route_task(self, capability: str, domain: str) -> AgentProfile | None:
        candidates = [
            agent for agent in self.agents.values()
            if agent.status == "active" and capability in agent.capabilities and domain in agent.domains
        ]
        return max(candidates, key=lambda a: a.trust_score, default=None)

    def propose_spawn(self, capability: str, domain: str) -> dict:
        if self.route_task(capability, domain):
            return {"status": "not_needed"}
        return {
            "status": "governance_required",
            "proposal_type": "spawn_agent",
            "capability": capability,
            "domain": domain,
        }

    def demote_on_performance(self, agent_id: str, score: float, threshold: float = 0.4) -> AgentProfile:
        agent = self.agents[agent_id]
        agent.trust_score = score
        if score < threshold:
            agent.status = "demoted"
        return agent
