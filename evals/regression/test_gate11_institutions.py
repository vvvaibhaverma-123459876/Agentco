from institutions import SocietyKernel


def test_society_structural_change_routes_through_governance_lifecycle():
    kernel = SocietyKernel()
    inst = kernel.create_institution("Evidence", "Review claims")
    society = kernel.create_society("Governed Agentco", [inst.institution_id])
    kernel.assign_agent("agent-a", inst.institution_id)

    proposal = kernel.propose_structure_change(society.society_id, {"type": "create_institution", "name": "Safety"})
    assert proposal["status"] == "proposed"
    decided = kernel.decide(proposal["proposal_id"], approved=True)
    assert decided["status"] == "approved"
    assert kernel.agent_membership["agent-a"] == inst.institution_id
