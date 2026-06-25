import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_agentco_goal_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_agentco_goal_run", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_goal_task_expected_decision_is_escalate():
    module = load_module()
    task = module.synthetic_task()
    assert task["expected_decision"] == "escalate"
    assert task["domain"] == "vendor_risk"
    assert {item["id"] for item in task["evidence"]} == {"ev1", "ev2", "ev3"}


def test_deterministic_result_passes_schema_and_policy_checks():
    module = load_module()
    task = module.synthetic_task()
    result = module.deterministic_reasoning(task)
    checks = module.validation_checks(task, result)
    assert result["decision"] == "escalate"
    assert result["risk_level"] == "medium"
    assert 0.45 <= result["confidence"] <= 0.75
    assert checks["passed"] is True
    assert checks["cites_required_evidence"] is True
    assert checks["requests_soc2"] is True
    assert checks["requests_signed_dpa"] is True
    assert checks["requests_subprocessors"] is True


def test_hallucination_traps_are_detected():
    module = load_module()
    task = module.synthetic_task()
    bad = module.deterministic_reasoning(task)
    bad["rationale"] = "Northstar DataWorks has confirmed SOC 2 Type II and a confirmed breach at Northstar DataWorks."
    checks = module.validation_checks(task, bad)
    assert checks["does_not_confirm_soc2_type2"] is False
    assert checks["does_not_conflate_breach"] is False
    assert checks["passed"] is False


def test_unknown_evidence_id_is_rejected():
    module = load_module()
    task = module.synthetic_task()
    bad = module.deterministic_reasoning(task)
    bad["cited_evidence_ids"] = ["ev1", "ev2", "ev99"]
    checks = module.validation_checks(task, bad)
    assert checks["all_citations_known"] is False
    assert checks["passed"] is False


def test_simulated_mode_is_clearly_marked(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "load_env_file", lambda path: None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_TEST_DATABASE_URL", raising=False)
    report = module.run("offline")
    assert report["mode"] == "simulated_offline"
    assert report["llm"]["simulated"] is True
    assert report["checks"]["passed"] is True
    assert report["database"]["db_url_present"] is False
    assert report["success"] is True


def test_openai_mode_skips_safely_without_key(monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "load_env_file", lambda path: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENTCO_TEST_DATABASE_URL", raising=False)
    report = module.run("live")
    assert report["mode"] == "live_openai"
    assert report["success"] is False
    assert "missing" in report["error"].lower()
