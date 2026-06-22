from simulation import WorldLab


def test_simulation_is_quarantined_and_external_evidence_can_promote_related_claim():
    lab = WorldLab()
    scenario = lab.create_scenario("stress evidence promotion")
    result = lab.run_simulation(scenario.scenario_id)
    claim = lab.convert_to_hypothesis(result["result_id"])

    lab.evidence.attach_evidence(
        claim.claim_id,
        source_uri="simulation://support",
        source_type="simulation",
        supports_or_refutes="supports",
        strength=1.0,
        evidence_quality="simulated",
        raw_excerpt_or_pointer="simulated support",
    )
    assert not lab.evidence.promote_claim(claim.claim_id).allowed

    external = lab.evidence.create_claim("external validated simulation insight", source_uri="https://agentco.example/claim", source_type="internal")
    lab.evidence.attach_evidence(
        external.claim_id,
        source_uri="https://external.example/validation",
        source_type="benchmark",
        supports_or_refutes="supports",
        strength=1.0,
        evidence_quality="EXTERNAL-VALIDATED",
        raw_excerpt_or_pointer="validated",
    )
    assert lab.evidence.promote_claim(external.claim_id).allowed
