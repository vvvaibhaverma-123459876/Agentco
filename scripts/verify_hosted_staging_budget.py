#!/usr/bin/env python3
"""Validate Batch 05 hosted staging budget and execution prerequisites.

This script is deliberately fail-closed. It never provisions resources and it
never converts missing hosted dependencies into success.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs/audit/current/HOSTED_STAGING_BUDGET_POLICY.json"
DEFAULT_CONTRACT = ROOT / "docs/audit/current/HOSTED_STAGING_EXECUTION_CONTRACT.json"

REQUIRED_LIMITS = {
    "maximum_deployment_lifetime_hours",
    "maximum_expected_infrastructure_cost_usd",
    "maximum_hourly_infrastructure_cost_usd",
    "maximum_container_or_node_count",
    "maximum_database_size_gb",
    "maximum_storage_size_gb",
    "maximum_kafka_retention_hours",
    "maximum_log_retention_days",
    "maximum_llm_requests",
    "maximum_llm_tokens",
    "maximum_provider_spend_usd",
    "maximum_load_test_requests",
    "automatic_expiry_timestamp",
    "cleanup_deadline",
    "resource_tags",
}

REQUIRED_TAGS = {"project", "environment", "owner", "managed_by", "purpose", "production"}
SUPPORTED_CLOUD_TOOLS = ("aws", "gcloud", "az")
SUPPORTED_IAC_TOOLS = ("terraform", "tofu", "pulumi")
REQUIRED_ENVIRONMENT = (
    "HOSTED_STAGING_ACCOUNT_ID",
    "HOSTED_STAGING_REGION",
    "HOSTED_STAGING_DNS_ZONE",
    "HOSTED_STAGING_STATE_BACKEND",
    "HOSTED_STAGING_REGISTRY",
    "HOSTED_STAGING_ALERT_DESTINATION",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"missing required file: {path}")
    return json.loads(path.read_text())


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def validate_policy(policy: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    errors: list[str] = []
    now = now or datetime.now(UTC)

    missing = sorted(REQUIRED_LIMITS - set(policy))
    if missing:
        errors.append(f"missing budget fields: {', '.join(missing)}")

    for field in REQUIRED_LIMITS - {"automatic_expiry_timestamp", "cleanup_deadline", "resource_tags"}:
        value = policy.get(field)
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"{field} must be a positive number")

    tags = policy.get("resource_tags")
    if not isinstance(tags, dict):
        errors.append("resource_tags must be an object")
    else:
        missing_tags = sorted(REQUIRED_TAGS - set(tags))
        if missing_tags:
            errors.append(f"missing resource tags: {', '.join(missing_tags)}")
        if tags.get("production") != "false":
            errors.append("resource_tags.production must be string false")

    for field in ("automatic_expiry_timestamp", "cleanup_deadline"):
        value = policy.get(field)
        if not isinstance(value, str):
            errors.append(f"{field} must be an ISO timestamp")
            continue
        try:
            if parse_utc(value) <= now:
                errors.append(f"{field} is expired")
        except ValueError as exc:
            errors.append(f"{field} invalid: {exc}")

    return errors


def detect_tools(names: tuple[str, ...]) -> dict[str, str | None]:
    return {name: shutil.which(name) for name in names}


def validate_prerequisites(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if contract.get("execution_status") != "READY_FOR_HOSTED_EXECUTION":
        errors.append("HOSTED_STAGING_BLOCKED: execution contract is not ready for hosted execution")

    cloud_tools = detect_tools(SUPPORTED_CLOUD_TOOLS)
    iac_tools = detect_tools(SUPPORTED_IAC_TOOLS)
    if not any(cloud_tools.values()):
        errors.append("HOSTED_STAGING_BLOCKED: no supported cloud CLI found")
    if not any(iac_tools.values()):
        errors.append("HOSTED_STAGING_BLOCKED: no supported IaC tool found")

    for name in REQUIRED_ENVIRONMENT:
        if not os.environ.get(name):
            errors.append(f"HOSTED_STAGING_BLOCKED: {name} is not set")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--check-prerequisites", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result: dict[str, Any] = {
        "success": False,
        "policy": str(args.policy),
        "contract": str(args.contract),
        "errors": [],
        "cloud_tools": detect_tools(SUPPORTED_CLOUD_TOOLS),
        "iac_tools": detect_tools(SUPPORTED_IAC_TOOLS),
    }

    try:
        policy = load_json(args.policy)
        result["errors"].extend(validate_policy(policy))
        if args.check_prerequisites:
            contract = load_json(args.contract)
            result["errors"].extend(validate_prerequisites(contract))
    except Exception as exc:
        result["errors"].append(str(exc))

    result["success"] = not result["errors"]
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["errors"]:
        for error in result["errors"]:
            print(error, file=sys.stderr)
    else:
        print("hosted staging budget policy valid")

    return 0 if result["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
