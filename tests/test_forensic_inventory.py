import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_forensic_inventory_covers_every_tracked_file():
    subprocess.run(
        ["python3.13", "scripts/generate_forensic_inventory.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads((ROOT / "docs/audit/FORENSIC_FILE_INVENTORY.json").read_text())
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    inventory_paths = [item["path"] for item in payload["files"]]
    assert inventory_paths == tracked
    assert payload["tracked_file_count"] == len(tracked)
    assert "Production runtime code" in payload["category_counts"]
    assert "Deployment infrastructure" in payload["category_counts"]


def test_forensic_audit_controls_cover_requirements_dependencies_and_completeness():
    subprocess.run(
        ["python3.13", "scripts/generate_forensic_audit_controls.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads((ROOT / "docs/audit/FORENSIC_AUDIT_CONTROLS.json").read_text())

    requirements = payload["requirements_to_behaviour_matrix"]
    dependencies = payload["external_dependency_audit"]
    completeness = payload["finding_completeness_ledger"]
    post_remediation = payload["independent_post_remediation_reaudit"]

    assert len(requirements) >= 8
    for row in requirements:
        for key in (
            "who_needs_it",
            "trigger",
            "input_output",
            "success_criteria",
            "failure_expectations",
            "implementing_workflow",
            "test_evidence",
            "production_evidence",
        ):
            assert row[key]
    assert {dep["name"] for dep in dependencies} >= {
        "PostgreSQL",
        "Redis",
        "Kafka",
        "OpenAI-compatible LLM provider",
        "Kubernetes cluster and Helm",
    }
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert completeness["total_files_discovered"] == len(tracked)
    assert completeness["files_inventoried"] == len(tracked)
    assert completeness["claims_discovered"] >= 4
    assert completeness["requirements_with_test_evidence"] == len(requirements)
    assert len(post_remediation) >= 5
