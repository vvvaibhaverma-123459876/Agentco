from scripts.verify_agentco_goal_run import (
    SYNTHETIC_VENDOR_TASK,
    build_run,
    deterministic_vendor_decision,
    validate_goal_output,
)
import scripts.verify_agentco_goal_run as goal_run


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


def test_offline_goal_run_does_not_use_db_persistence(monkeypatch):
    def fail_persist(_report):
        raise AssertionError("offline fixture must not touch DB persistence")

    monkeypatch.setattr(goal_run, "persist_goal_run_to_db", fail_persist)
    report = build_run(offline=True)
    assert report["success"] is True
    assert report["audit"]["persistence"] == "file_backed"
    assert "db_persistence" not in report


def test_live_goal_run_requires_db_persistence_by_default(monkeypatch):
    monkeypatch.setattr(
        goal_run,
        "openai_goal_decision",
        lambda task: (deterministic_vendor_decision(task), {"model": "test-model", "latency_ms": 1, "usage": {"total_tokens": 1}}),
    )

    def fake_persist(report):
        assert report["simulated"] is False
        assert report["prediction"]["id"]
        return {
            "persistence": "db_backed",
            "session_id": "00000000-0000-4000-8000-000000000001",
            "prediction_id": "00000000-0000-4000-8000-000000000002",
            "decision_log_id": "00000000-0000-4000-8000-000000000003",
            "event_ids": ["00000000-0000-4000-8000-000000000004"],
            "events_written": 1,
            "prediction_resolved": True,
            "brier_score": 0.1225,
        }

    monkeypatch.setattr(goal_run, "persist_goal_run_to_db", fake_persist)
    report = build_run(offline=False)
    assert report["success"] is True
    assert report["audit"]["persistence"] == "db_backed"
    assert report["db_persistence"]["prediction_resolved"] is True
    assert report["prediction"]["id"] == "00000000-0000-4000-8000-000000000002"


def test_live_goal_run_can_explicitly_disable_db_persistence(monkeypatch):
    monkeypatch.setenv("AGENTCO_GOAL_RUN_DB_PERSISTENCE", "0")
    monkeypatch.setattr(
        goal_run,
        "openai_goal_decision",
        lambda task: (deterministic_vendor_decision(task), {"model": "test-model", "latency_ms": 1, "usage": {}}),
    )
    monkeypatch.setattr(goal_run, "persist_goal_run_to_db", lambda _report: (_ for _ in ()).throw(AssertionError("disabled")))
    report = build_run(offline=False)
    assert report["success"] is True
    assert report["audit"]["persistence"] == "file_report_with_live_llm"
