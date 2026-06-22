from agents.registry import AgentProfile, AgentRegistry, SkillProfile


def test_task_routing_spawn_and_demotion_are_trust_weighted():
    registry = AgentRegistry()
    registry.register_agent(AgentProfile("a1", "researcher", {"research"}, {"web"}, "evidence", 0.6, {"claims"}))
    registry.register_agent(AgentProfile("a2", "researcher", {"research"}, {"web"}, "evidence", 0.9, {"claims"}))
    registry.register_skill(SkillProfile("s1", "research", {"web"}, 0.8, "evidence"))

    assert registry.route_task("research", "claims").agent_id == "a2"
    assert registry.propose_spawn("coding", "repo")["status"] == "governance_required"
    assert registry.demote_on_performance("a2", 0.2).status == "demoted"
