from scripts import verify_agentco_multidomain_live_run as multidomain


def test_live_cross_domain_tasks_cover_required_domains():
    assert {task["domain"] for task in multidomain.LIVE_CROSS_DOMAIN_TASKS} == {
        "vendor_risk",
        "medical-triage-safe-info",
        "financial-risk-disclosure",
        "code-change-risk-review",
    }


def test_offline_multidomain_run_is_explicitly_simulated_and_valid():
    report = multidomain.build_run(offline=True)
    assert report["success"] is True
    assert report["mode"] == "offline_fixture"
    assert report["simulated"] is True
    assert report["llm"]["simulated"] is True
    assert report["not_proof_of_general_intelligence"] is True
    assert len(report["cases"]) == 4
    assert "db_persistence" not in report


def test_validation_rejects_missing_required_evidence():
    task = multidomain.LIVE_CROSS_DOMAIN_TASKS[0]
    answer = multidomain.deterministic_answer(task)
    answer["cited_evidence_ids"] = [task["required_evidence"][0]]
    validation = multidomain.validate_answer(task, answer)
    assert validation["passed"] is False
    assert validation["checks"]["required_evidence_recalled"] is False
    assert validation["scores"]["evidence_recall"] == 0.5


def test_validation_rejects_hallucination_traps():
    task = multidomain.LIVE_CROSS_DOMAIN_TASKS[0]
    answer = multidomain.deterministic_answer(task)
    answer["rationale"] = "Confirmed SOC 2 Type II is available."
    validation = multidomain.validate_answer(task, answer)
    assert validation["passed"] is False
    assert validation["checks"]["hallucination_traps_avoided"] is False


def test_supported_claims_require_sources():
    task = multidomain.LIVE_CROSS_DOMAIN_TASKS[0]
    answer = multidomain.deterministic_answer(task)
    answer["claims"] = [{"text": "unsupported source", "status": "supported", "support_source_ids": []}]
    validation = multidomain.validate_answer(task, answer)
    assert validation["passed"] is False
    assert validation["checks"]["supported_claims_have_sources"] is False


def test_trusted_confidence_cannot_exceed_raw_confidence():
    task = multidomain.LIVE_CROSS_DOMAIN_TASKS[0]
    answer = multidomain.deterministic_answer(task)
    answer["trusted_confidence"] = answer["confidence"] + 0.1
    validation = multidomain.validate_answer(task, answer)
    assert validation["passed"] is False
    assert validation["checks"]["trusted_confidence_not_higher"] is False


def test_live_multidomain_run_requires_db_persistence_by_default(monkeypatch):
    calls = {"persist": 0}

    def fake_openai_answer(task):
        return multidomain.normalize_answer(multidomain.deterministic_answer(task), task), {
            "model": "test-model",
            "latency_ms": 1,
            "usage": {"total_tokens": 10},
        }

    def fake_persist(report):
        calls["persist"] += 1
        assert report["simulated"] is False
        assert len(report["cases"]) == 4
        return {
            "persistence": "db_backed",
            "session_id": "00000000-0000-4000-8000-000000000001",
            "cases": [],
            "predictions_registered": 4,
            "predictions_resolved": 4,
            "events_written": 32,
            "decision_logs_written": 4,
        }

    monkeypatch.delenv("AGENTCO_MULTIDOMAIN_DB_PERSISTENCE", raising=False)
    monkeypatch.setattr(multidomain, "openai_answer", fake_openai_answer)
    monkeypatch.setattr(multidomain, "persist_to_db", fake_persist)
    report = multidomain.build_run(offline=False)
    assert report["success"] is True
    assert report["mode"] == "live_openai"
    assert report["simulated"] is False
    assert calls["persist"] == 1
    assert report["db_persistence"]["predictions_resolved"] == 4


def test_live_multidomain_db_persistence_can_be_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("AGENTCO_MULTIDOMAIN_DB_PERSISTENCE", "0")
    monkeypatch.setattr(
        multidomain,
        "openai_answer",
        lambda task: (
            multidomain.normalize_answer(multidomain.deterministic_answer(task), task),
            {"model": "test-model", "latency_ms": 1, "usage": {}},
        ),
    )
    monkeypatch.setattr(
        multidomain,
        "persist_to_db",
        lambda _report: (_ for _ in ()).throw(AssertionError("DB persistence should be disabled")),
    )
    report = multidomain.build_run(offline=False)
    assert report["success"] is True
    assert "db_persistence" not in report
