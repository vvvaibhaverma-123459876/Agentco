from scripts import verify_mission_progress as mission


def test_build_ledger_claim_requires_termination_and_green_gates():
    report = {
        "meta": {"termination_predicate_met": True},
        "rollups": {"verified": 67, "total_items": 67},
        "gates": {"reachability": "green", "firewall": "green"},
    }
    claim = mission.build_ledger_claim(report)
    assert claim.status == "verified"

    report["gates"]["firewall"] = "red"
    assert mission.build_ledger_claim(report).status == "blocked"


def test_long_horizon_claim_does_not_overclaim_without_history():
    claim = mission.long_horizon_claim([])
    assert claim.status == "unproven"
    assert claim.required_next_evidence


def test_durable_improvement_is_partial_with_mechanisms_but_no_repeated_runs():
    claim = mission.durable_improvement_claim(
        {"success": True, "mode": "live_openai"},
        {"verified": True, "repeated_real_world_runs": 0},
    )
    assert claim.status == "partial"
    assert "real-world improvement cycles" in " ".join(claim.required_next_evidence).lower()


def test_open_domain_transfer_stays_partial_for_bounded_live_verifier():
    claim = mission.open_domain_transfer_claim({
        "success": True,
        "simulated": False,
        "domains": ["a", "b", "c", "d"],
        "not_proof_of_general_intelligence": True,
    })
    assert claim.status == "partial"
    assert "bounded" in claim.summary


def test_hosted_ops_is_partial_for_local_green_posture_without_hosted_certification():
    claim = mission.hosted_ops_claim(
        {"can_continue": True},
        {"gates": {"reachability": "green", "firewall": "green"}},
    )
    assert claim.status == "partial"
    assert "hosted production" in claim.summary.lower()
