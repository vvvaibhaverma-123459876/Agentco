import pytest

from agents.autonomy.specialist_agent import SpecialistAgent


class RuntimeSpecialist(SpecialistAgent):
    def handle_action(self, action_spec):
        return {"observations": {"status": "ok"}, "artifacts": []}


def test_specialist_defaults_to_waitress(monkeypatch):
    monkeypatch.delenv("AGENTCO_SPECIALIST_SERVER", raising=False)
    monkeypatch.delenv("AGENTCO_ENV", raising=False)
    agent = RuntimeSpecialist("test-specialist", "researcher", {"tokens": 100, "iterations": 3, "seconds": 30})
    assert agent.select_server_backend() == "waitress"


def test_specialist_refuses_flask_dev_in_production(monkeypatch):
    monkeypatch.setenv("AGENTCO_SPECIALIST_SERVER", "flask-dev")
    monkeypatch.setenv("AGENTCO_ENV", "production")
    agent = RuntimeSpecialist("test-specialist", "researcher", {"tokens": 100, "iterations": 3, "seconds": 30})
    with pytest.raises(RuntimeError, match="Flask development server"):
        agent.select_server_backend()


def test_specialist_allows_explicit_flask_dev_outside_production(monkeypatch):
    monkeypatch.setenv("AGENTCO_SPECIALIST_SERVER", "flask-dev")
    monkeypatch.delenv("AGENTCO_ENV", raising=False)
    agent = RuntimeSpecialist("test-specialist", "researcher", {"tokens": 100, "iterations": 3, "seconds": 30})
    assert agent.select_server_backend() == "flask-dev"
