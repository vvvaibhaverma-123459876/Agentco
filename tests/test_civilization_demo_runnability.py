import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_civilization_demo_runs_offline_and_exports_audit_package(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["AGENTCO_DEMO_OUTPUT_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "examples/civilization_constitution_demo/run_demo.py"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    audit_path = tmp_path / "audit_package.json"
    trace_path = tmp_path / "demo_trace.md"
    assert audit_path.exists()
    assert trace_path.exists()

    package = json.loads(audit_path.read_text())
    assert package["mode"] == "offline_deterministic"
    assert package["same_source_rejected"] is True
    assert package["independent_resolution_status"] == "accepted"
    assert package["credential_id"]
    assert package["dashboard_snapshot"]["civilization"] == "agentco-civilization"

    event_types = {event["event_type"] for event in package["audit_events"]}
    expected = {
        "claim_preregistered",
        "same_source_resolution_rejected",
        "independent_resolution_accepted",
        "trust_score_updated",
        "agent_reputation_updated",
        "department_reputation_updated",
        "institution_authority_updated",
        "society_reputation_updated",
        "dispute_opened",
        "dispute_evidence_submitted",
        "ruling_issued",
        "precedent_created",
        "budget_reward_penalty_applied",
        "civilization_memory_recorded",
    }
    assert expected.issubset(event_types)


def test_offline_smoke_runs_without_llm_or_external_services() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/smoke_offline.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "offline smoke passed" in result.stdout


def test_makefile_and_compose_expose_clean_run_targets() -> None:
    makefile = (ROOT / "Makefile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()

    for target in ["doctor:", "dev-minimal:", "dev-full:", "demo:", "smoke:", "test:"]:
        assert target in makefile

    for profile in ['"minimal"', '"dev"', '"full"', '"demo"']:
        assert profile in compose

    minimal_section = compose.split("postgres:", 1)[1].split("redis:", 1)[0]
    assert '"minimal"' in minimal_section
    heavy_services = ["kafka:", "vault:", "prometheus:", "grafana:"]
    for service in heavy_services:
        service_section = compose.split(service, 1)[1].split("\n  ", 1)[0]
        assert '"minimal"' not in service_section
