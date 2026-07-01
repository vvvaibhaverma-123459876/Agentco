from scripts import verify_mission_progress as mission


def real_world_history(count=10):
    rows = []
    for index in range(count):
        rows.append({
            "generated_at": f"2026-01-{index + 1:02d}T00:00:00Z",
            "success": True,
            "real_world": True,
            "aggregate_score": 0.50 + (index * 0.01),
        })
    rows[-1]["generated_at"] = "2026-02-05T00:00:00Z"
    return rows


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


def test_long_horizon_claim_requires_real_world_registry_entries():
    local_only = [
        {
            "generated_at": "2026-01-01T00:00:00Z",
            "success": True,
            "real_world": False,
            "aggregate_score": 0.5,
        }
        for _ in range(10)
    ]
    claim = mission.long_horizon_claim(local_only)
    assert claim.status == "unproven"
    assert "successful_real_world_longitudinal_runs=0" in claim.evidence


def test_long_horizon_claim_verifies_with_sufficient_real_world_trend():
    claim = mission.long_horizon_claim(real_world_history())
    assert claim.status == "verified"
    assert "timespan_days=35" in claim.evidence
    assert "improving_trend=True" in claim.evidence


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


def test_mission_run_registry_round_trip(tmp_path):
    path = tmp_path / "mission_run_registry.json"
    report = {
        "generated_at": "2026-01-01T00:00:00Z",
        "summary": {
            "verified_claims": 1,
            "total_claims": 5,
            "statuses": {
                "evidence_governed_calibration_civilization": "verified",
                "progressively_more_general_intelligence_over_long_horizons": "unproven",
            },
        },
    }

    entry = mission.mission_run_registry_entry(report, real_world=False)
    history = mission.append_mission_run(entry, path)

    assert history == mission.load_longitudinal_history(path)
    assert history[0]["aggregate_score"] == 0.2
    assert history[0]["real_world"] is False


def test_mission_run_registry_rejects_non_array(tmp_path):
    path = tmp_path / "mission_run_registry.json"
    path.write_text("{}\n")

    try:
        mission.load_longitudinal_history(path)
    except ValueError as exc:
        assert "JSON array" in str(exc)
    else:
        raise AssertionError("expected malformed registry to fail")
