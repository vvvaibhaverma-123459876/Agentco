from scripts.verify_agentco_goal_run import (
    SYNTHETIC_VENDOR_TASK,
    build_run,
    deterministic_vendor_decision,
    validate_goal_output,
)


def test_synthetic_goal_task_expected_decision_is_escalate():
    assert SYNTHETIC_VENDOR_TASK["expected_decision"] == "escalate"


def test_deterministic_goal_run_schema_and_validation():
    report = build_run(offline=True)
    assert report["success"] is True
    assert report["simulated"] is True
    assert report["result"]["decision"] == "escalate"
    assert 0.0 <= report["result"]["confidence"] <= 1.0


def test_goal_run_detects_hallucination_traps_and_missing_info():
    output = deterministic_vendor_decision()
    validation = validate_goal_output(output)
    assert validation["checks"]["does_not_confirm_soc2_type2"] is True
    assert validation["checks"]["does_not_conflate_breach"] is True
    assert validation["checks"]["requests_soc2_type2"] is True
    assert validation["checks"]["requests_signed_dpa"] is True
    assert validation["checks"]["requests_subprocessors"] is True


def test_supported_claims_require_evidence_ids():
    output = deterministic_vendor_decision()
    output["claims"][0]["support_source_ids"] = []
    validation = validate_goal_output(output)
    assert validation["passed"] is False
    assert validation["checks"]["supported_claims_have_sources"] is False
