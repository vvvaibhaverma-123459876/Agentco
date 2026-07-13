import json
from pathlib import Path

from scripts import audit_staging_deployment


ROOT = Path(__file__).resolve().parents[1]


def test_rti_002_is_intentional_separation_with_both_outboxes():
    findings = {item["finding_id"]: item for item in audit_staging_deployment.docs_data()["findings"]}

    assert findings["RTI-002"]["status"] == "intentional_separation"
    assert "event_outbox" in findings["RTI-002"]["evidence"]
    assert "event_bus_outbox" in findings["RTI-002"]["evidence"]


def test_hosted_environment_boundaries_remain_unverified():
    topology = audit_staging_deployment.docs_data()["topology"]

    assert topology["environment"] == "local-real Kubernetes via Kind"
    assert topology["hosted_boundaries"]["managed_kubernetes"] == "unverified"
    assert topology["hosted_boundaries"]["production_alert_destination"] == "unverified"


def test_redaction_removes_connection_credentials_and_secret_values():
    raw = (
        "DATABASE_URL=postgresql://user:password@postgres:5432/agentco "
        "REDIS_URL=redis://:secret@redis:6379 AGENTCO_API_KEY=plain"
    )

    redacted = audit_staging_deployment.redact(raw)

    assert "user:password" not in redacted
    assert ":secret@" not in redacted
    assert "AGENTCO_API_KEY=plain" not in redacted
    assert "AGENTCO_API_KEY=[REDACTED]" in redacted


def test_manifest_secret_uses_base64_not_plaintext():
    manifest = audit_staging_deployment.manifest_secret(
        "agentco-runtime-secrets",
        "agentco-test",
        {"DATABASE_URL": "postgresql://user:password@postgres:5432/agentco"},
    )

    assert "postgresql://user:password" not in manifest
    assert "kind: Secret" in manifest
    assert "DATABASE_URL:" in manifest


def test_docs_only_generation_writes_structural_deployment_docs(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    monkeypatch.setattr(audit_staging_deployment, "DOCS", docs_dir)

    audit_staging_deployment.write_docs()

    ledger = json.loads((docs_dir / "DEPLOYMENT_COMPONENT_LEDGER.json").read_text())
    findings = json.loads((docs_dir / "DEPLOYMENT_OPERATIONAL_FINDINGS.json").read_text())
    hosted = (docs_dir / "HOSTED_ENVIRONMENT_GAP_ANALYSIS.md").read_text()

    assert {component["component"] for component in ledger["components"]} >= {"backend", "frontend", "outbox-worker", "migration-job"}
    assert any(item["finding_id"] == "RTI-002" for item in findings["findings"])
    assert "Unverified hosted boundaries" in hosted


def test_staging_audit_script_records_required_cleanup_commands():
    source = (ROOT / "scripts/audit_staging_deployment.py").read_text()

    assert '"kind-delete-cluster"' in source
    assert '"kind-verify-cluster-removed"' in source
    assert '"cleanup": ctx.cleanup' in source


def test_staging_audit_script_enforces_network_policy_negative_probe():
    source = (ROOT / "scripts/audit_staging_deployment.py").read_text()

    assert "network-negative-frontend-postgres" in source
    assert "NetworkPolicy negative probe failed" in source


def test_staging_audit_workflow_runs_canonical_make_target():
    workflow = (ROOT / ".github/workflows/staging-deployment-audit.yml")
    if not workflow.exists():
        return

    content = workflow.read_text()
    assert "make audit-staging-deployment" in content
    assert "continue-on-error" not in content
