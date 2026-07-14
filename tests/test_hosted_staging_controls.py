import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import hosted_staging_audit, verify_hosted_staging_budget


ROOT = Path(__file__).resolve().parents[1]


def valid_policy() -> dict:
    future = datetime.now(UTC) + timedelta(days=2)
    return {
        "maximum_deployment_lifetime_hours": 8,
        "maximum_expected_infrastructure_cost_usd": 75,
        "maximum_hourly_infrastructure_cost_usd": 10,
        "maximum_container_or_node_count": 6,
        "maximum_database_size_gb": 20,
        "maximum_storage_size_gb": 50,
        "maximum_kafka_retention_hours": 24,
        "maximum_log_retention_days": 7,
        "maximum_llm_requests": 20,
        "maximum_llm_tokens": 20000,
        "maximum_provider_spend_usd": 5,
        "maximum_load_test_requests": 2000,
        "automatic_expiry_timestamp": future.isoformat().replace("+00:00", "Z"),
        "cleanup_deadline": (future + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "resource_tags": {
            "project": "agentco",
            "environment": "hosted-staging-audit",
            "owner": "agentco-audit",
            "managed_by": "iac",
            "purpose": "batch-05-hosted-staging",
            "production": "false",
        },
    }


def test_budget_policy_accepts_complete_unexpired_policy():
    errors = verify_hosted_staging_budget.validate_policy(valid_policy())

    assert errors == []


def test_budget_policy_rejects_expired_policy():
    policy = valid_policy()
    past = datetime.now(UTC) - timedelta(days=1)
    policy["automatic_expiry_timestamp"] = past.isoformat().replace("+00:00", "Z")

    errors = verify_hosted_staging_budget.validate_policy(policy)

    assert any("automatic_expiry_timestamp is expired" in error for error in errors)


def test_budget_policy_requires_non_production_tags():
    policy = valid_policy()
    del policy["resource_tags"]["owner"]
    policy["resource_tags"]["production"] = "true"

    errors = verify_hosted_staging_budget.validate_policy(policy)

    assert any("missing resource tags: owner" in error for error in errors)
    assert any("resource_tags.production must be string false" in error for error in errors)


def test_prerequisites_fail_when_contract_is_blocked(monkeypatch):
    monkeypatch.delenv("HOSTED_STAGING_ACCOUNT_ID", raising=False)
    contract = {"execution_status": "BLOCKED"}

    errors = verify_hosted_staging_budget.validate_prerequisites(contract)

    assert any("execution contract is not ready" in error for error in errors)
    assert any("HOSTED_STAGING_ACCOUNT_ID is not set" in error for error in errors)


def test_hosted_make_targets_are_advertised():
    makefile = (ROOT / "Makefile").read_text()

    for target in [
        "hosted-staging-budget:",
        "hosted-staging-plan:",
        "hosted-staging-apply:",
        "audit-hosted-staging:",
        "hosted-staging-destroy:",
    ]:
        assert target in makefile


def test_hosted_staging_workflow_is_manual_and_uploads_artifacts():
    workflow = (ROOT / ".github/workflows/hosted-staging-audit.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "make audit-hosted-staging" in workflow
    assert "continue-on-error" not in workflow
    assert "actions/upload-artifact" in workflow


def test_hosted_command_fails_closed_and_writes_blocked_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(hosted_staging_audit, "ARTIFACT_ROOT", tmp_path)

    result = subprocess.run(
        ["python3.13", "scripts/hosted_staging_audit.py", "plan"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    artifact_dir = Path(result.stdout.strip())
    ledger = json.loads((artifact_dir / "EXECUTION_LEDGER.json").read_text())
    assert ledger["final_verdict"] == "BLOCKED"
    assert ledger["evidence_classification"] == "UNVERIFIED_EXTERNAL_DEPENDENCY"
    assert ledger["hosted_resources_created"] == []
    assert ledger["cleanup_required"] is False


def test_hosted_docs_do_not_claim_execution_success():
    remediation = (ROOT / "docs/audit/current/REMEDIATION_05_HOSTED_STAGING_LIVE_PROVIDERS.md").read_text()
    contract = json.loads((ROOT / "docs/audit/current/HOSTED_STAGING_EXECUTION_CONTRACT.json").read_text())

    assert "Status: `BLOCKED`" in remediation
    assert contract["execution_status"] == "BLOCKED"
    assert contract["evidence_classification"] == "UNVERIFIED_EXTERNAL_DEPENDENCY"


@pytest.mark.parametrize(
    "doc",
    [
        "HOSTED_STAGING_COMPONENT_LEDGER.json",
        "HOSTED_STAGING_TOPOLOGY.json",
        "HOSTED_IDENTITY_ACCESS_MATRIX.json",
        "HOSTED_OBSERVABILITY_ALERT_MATRIX.json",
    ],
)
def test_hosted_structural_artifacts_are_blocked_until_real_resources_exist(doc):
    data = json.loads((ROOT / "docs/audit/current" / doc).read_text())

    assert data["status"] == "BLOCKED"
