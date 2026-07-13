#!/usr/bin/env python3
"""Run pytest and enforce the governed skip allowlist."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / "docs" / "audit" / "current" / "TEST_SKIP_ALLOWLIST.json"


@dataclass(frozen=True)
class EnvironmentRequirement:
    name: str
    condition: str
    value: str | None = None


@dataclass(frozen=True)
class SkipEntry:
    node_id: str
    reason: str
    classification: str
    owner: str
    mandatory_for_clean_room: bool
    expiry_date: str
    required_environment: list[EnvironmentRequirement]
    finding_reference: str | None = None


def parse_environment_requirement(raw: object) -> EnvironmentRequirement:
    if isinstance(raw, str):
        if "=" in raw:
            name, value = raw.split("=", 1)
            return EnvironmentRequirement(name=name, condition="equals", value=value)
        if raw in {"AGENTCO_TEST_DATABASE_URL", "DATABASE_URL"}:
            return EnvironmentRequirement(name=raw, condition="postgres_reachable")
        if raw == "KAFKA_BROKERS":
            return EnvironmentRequirement(name=raw, condition="kafka_reachable")
        return EnvironmentRequirement(name=raw, condition="present")
    if not isinstance(raw, dict):
        raise ValueError(f"required_environment entry must be object or string, got {raw!r}")
    name = str(raw.get("name", ""))
    condition = str(raw.get("condition", ""))
    value = raw.get("value")
    if not name:
        raise ValueError("required_environment entry missing name")
    if condition not in {"present", "absent", "equals", "not_equals", "postgres_reachable", "kafka_reachable"}:
        raise ValueError(f"malformed required_environment condition for {name}: {condition}")
    if condition in {"equals", "not_equals"} and value is None:
        raise ValueError(f"required_environment condition {condition} for {name} requires value")
    return EnvironmentRequirement(name=name, condition=condition, value=str(value) if value is not None else None)


def load_allowlist(path: Path) -> list[SkipEntry]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    entries = raw.get("skips", raw if isinstance(raw, list) else [])
    return [
        SkipEntry(
            node_id=str(item["node_id"]),
            reason=str(item["reason"]),
            classification=str(item["classification"]),
            owner=str(item["owner"]),
            mandatory_for_clean_room=bool(item["mandatory_for_clean_room"]),
            expiry_date=str(item["expiry_date"]),
            required_environment=[parse_environment_requirement(value) for value in item.get("required_environment", [])],
            finding_reference=str(item["finding_reference"]) if item.get("finding_reference") else None,
        )
        for item in entries
    ]


def matches(pattern: str, node_id: str) -> bool:
    if any(token in pattern for token in "*?[]"):
        return fnmatch.fnmatch(node_id, pattern)
    return pattern == node_id


def _tcp_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def environment_available(requirement: EnvironmentRequirement) -> bool:
    current = os.environ.get(requirement.name)
    if requirement.condition == "present":
        return bool(current)
    if requirement.condition == "absent":
        return current is None
    if requirement.condition == "equals":
        return current == requirement.value
    if requirement.condition == "not_equals":
        return current is not None and current != requirement.value
    if requirement.condition == "postgres_reachable":
        if not current:
            return False
        try:
            import psycopg2  # type: ignore[import]

            conn = psycopg2.connect(current, connect_timeout=2)
            conn.close()
            return True
        except Exception:
            return False
    if requirement.condition == "kafka_reachable":
        if not current:
            return False
        brokers = current
        for broker in brokers.split(","):
            host, _, port_text = broker.strip().partition(":")
            if host and port_text.isdigit() and _tcp_reachable(host, int(port_text)):
                return True
        return False
    raise ValueError(f"unsupported required_environment condition: {requirement.condition}")


def missing_environment_names(entry: SkipEntry) -> list[str]:
    return [item.name for item in entry.required_environment if not environment_available(item)]


def skip_reason_matches_missing_environment(skip_reason: str, missing_names: list[str]) -> bool:
    if not missing_names:
        return True
    reason = skip_reason.lower()
    aliases = {
        "AGENTCO_TEST_DATABASE_URL": ["agentco_test_database_url", "postgres", "database", "decision_log", "ledger"],
        "DATABASE_URL": ["database_url", "postgres", "database"],
        "KAFKA_BROKERS": ["kafka", "broker"],
        "RUN_REAL_LLM_TESTS": ["llm", "provider", "run_real_llm_tests"],
        "SKIP_LOAD_TEST": ["load", "skip_load_test"],
        "AGENTCO_ALLOW_DESTRUCTIVE_RESERVE_TESTS": ["destructive", "reserve"],
        "AGENTCO_ALLOW_DESTRUCTIVE_MIGRATION_TESTS": ["destructive", "migration"],
    }
    for name in missing_names:
        terms = aliases.get(name, [name.lower()])
        if not any(term in reason for term in terms):
            return False
    return True


def validate_report(report: dict, allowlist: list[SkipEntry]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    collected = set(report.get("collected", []))
    skipped = report.get("skipped", [])
    xfailed = report.get("xfailed", [])
    xpassed = report.get("xpassed", [])
    deselected = report.get("deselected", [])
    if not collected:
        errors.append("pytest collected zero tests")
    if xpassed:
        errors.append(f"unexpected xpass entries: {[item['node_id'] for item in xpassed]}")
    if deselected:
        errors.append(f"unexpected deselected tests: {deselected[:10]}")

    matched_entries: set[int] = set()
    today = date.today()
    classifications: dict[str, int] = {}
    for skip in skipped + xfailed:
        node_id = skip["node_id"]
        matched = False
        for index, entry in enumerate(allowlist):
            if not matches(entry.node_id, node_id):
                continue
            matched = True
            matched_entries.add(index)
            classifications[entry.classification] = classifications.get(entry.classification, 0) + 1
            if date.fromisoformat(entry.expiry_date) < today:
                errors.append(f"expired skip allowlist entry matched {node_id}: {entry.expiry_date}")
            if entry.mandatory_for_clean_room:
                errors.append(f"mandatory clean-room test is allowlisted to skip: {node_id}")
            skip_reason = str(skip.get("reason", ""))
            missing_names = missing_environment_names(entry)
            if entry.required_environment and not missing_names:
                errors.append(f"SKIP_DESPITE_AVAILABLE_ENVIRONMENT: {node_id}")
            if missing_names and not skip_reason_matches_missing_environment(skip_reason, missing_names):
                errors.append(
                    f"SKIP_REASON_MISMATCH: {node_id} missing={missing_names} reason={skip_reason[:200]}"
                )
            if (
                entry.classification == "external_network"
                and any(item.name in {"AGENTCO_TEST_DATABASE_URL", "DATABASE_URL"} for item in entry.required_environment)
            ):
                errors.append(f"DB_SKIP_CLASSIFIED_EXTERNAL_NETWORK: {node_id}")
            if os.environ.get("AGENTCO_TEST_DATABASE_URL") and "AGENTCO_TEST_DATABASE_URL not set" in skip_reason:
                errors.append(f"DB_VAR_PRESENT_BUT_REASON_CLAIMS_MISSING: {node_id}")
            if os.environ.get("DATABASE_URL") and "DATABASE_URL not set" in skip_reason:
                errors.append(f"DB_VAR_PRESENT_BUT_REASON_CLAIMS_MISSING: {node_id}")
            break
        if not matched:
            errors.append(f"unapproved skip: {node_id} reason={skip.get('reason', '')[:200]}")

    for index, entry in enumerate(allowlist):
        if index in matched_entries:
            continue
        if not any(matches(entry.node_id, item) for item in collected):
            errors.append(f"stale skip allowlist entry matched no collected test: {entry.node_id}")
    return not errors, errors, classifications


def run_pytest(pytest_args: list[str], report_path: Path) -> int:
    env = os.environ.copy()
    env["AGENTCO_PYTEST_REPORT"] = str(report_path)
    command = [sys.executable, "-m", "pytest", "-p", "pytest_skip_report_plugin", *pytest_args]
    completed = subprocess.run(command, cwd=ROOT, text=True, env=env)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--validate-existing", action="store_true")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    pytest_args = args.pytest_args
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]
    if args.validate_existing:
        pytest_code = 0
    else:
        pytest_code = run_pytest(pytest_args or ["-q"], args.report)
    if not args.report.exists():
        print(json.dumps({"success": False, "error": "pytest report was not generated"}))
        return 2
    report = json.loads(args.report.read_text())
    allowlist = load_allowlist(args.allowlist)
    valid, errors, classifications = validate_report(report, allowlist)
    summary = {
        "success": pytest_code == 0 and valid,
        "pytest_exit_code": pytest_code,
        "collected": len(report.get("collected", [])),
        "passed": len(report.get("passed", [])),
        "failed": len(report.get("failed", [])),
        "skipped": len(report.get("skipped", [])),
        "xfailed": len(report.get("xfailed", [])),
        "xpassed": len(report.get("xpassed", [])),
        "deselected": len(report.get("deselected", [])),
        "skip_classifications": classifications,
        "errors": errors,
    }
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
