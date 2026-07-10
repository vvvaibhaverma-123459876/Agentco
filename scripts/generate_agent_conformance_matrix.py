#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.base_agent.agent_manifest import (
    ACTIVE_AGENT_PROFILES,
    ALL_AGENT_PROFILES,
    AgentProtocolProfile,
    PYTHON_ACTIVE_AGENT_PROFILES,
    TS_DURABLE_ACTIVE_AGENT_PROFILES,
)
from runtime.base_agent.base_agent_v2 import BaseAgentV2

MATRIX_PATH = ROOT / "docs" / "audit" / "AGENT_PROTOCOL_CONFORMANCE_MATRIX.json"
TS_REGISTRY = ROOT / "backend" / "src" / "agent-registry.ts"
TS_DURABLE_SERVICE = ROOT / "backend" / "src" / "services" / "durable-execution.service.ts"
TS_CIVILIZATION_SERVICE = ROOT / "backend" / "src" / "services" / "civilization.service.ts"
PROTECTED_LEDGER_PATTERNS = (
    re.compile(r"\bINSERT\s+INTO\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+decision_log\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\s+prediction_ledger\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+prediction_ledger\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\s+prediction_ledger\b", re.IGNORECASE),
)


def _load_class(implementation: str) -> type[Any]:
    module_name, class_name = implementation.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def _source_path(cls: type[Any]) -> Path:
    return Path(inspect.getsourcefile(cls) or "").resolve()


def _protected_ledger_writes(path: Path) -> list[str]:
    text = path.read_text()
    findings: list[str] = []
    for pattern in PROTECTED_LEDGER_PATTERNS:
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            findings.append(f"{path.relative_to(ROOT)}:{line_no}:{match.group(0)}")
    return findings


def _registry_entries() -> dict[str, dict[str, Any]]:
    text = TS_REGISTRY.read_text()
    entries: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r"entry\('([^']+)'.*?\)", text):
        call = match.group(0)
        agent_id = match.group(1)
        entries[agent_id] = {
            "runnable": "'unsupported'" not in call and "'library_only'" not in call,
            "allowed_task_types": (
                "record_observation_only"
                if "['record_observation']" in call
                else "default"
            ),
        }
    return entries


def _active_row(profile: AgentProtocolProfile) -> dict[str, Any]:
    if profile.runtime_contract == "TypeScript DurableExecutionService":
        registry = _registry_entries().get(profile.agent_id, {})
        durable_text = TS_DURABLE_SERVICE.read_text()
        civilization_text = TS_CIVILIZATION_SERVICE.read_text()
        direct_writes = _protected_ledger_writes(TS_DURABLE_SERVICE)
        uses_canonical_audit = "auditLog.append" in durable_text
        records_provenance = "provenance.attestAction" in durable_text
        finalizes_failure = "SET status='failed'" in durable_text
        routed_from_civilization = profile.agent_id in civilization_text
        status = (
            registry.get("runnable")
            and registry.get("allowed_task_types") == "record_observation_only"
            and uses_canonical_audit
            and records_provenance
            and finalizes_failure
            and routed_from_civilization
            and not direct_writes
        )
        return {
            "agent_id": profile.agent_id,
            "classification": profile.classification,
            "implementation": profile.implementation,
            "source": str(TS_DURABLE_SERVICE.relative_to(ROOT)),
            "entrypoint": profile.entrypoint,
            "allowed_actions": list(profile.allowed_actions),
            "runtime_contract": profile.runtime_contract,
            "authorization": "agent-registry assertAgentCanRunTask",
            "tool_policy": "DurableExecutionService task-type allowlist",
            "budget": "DurableExecutionService bounded task contract; no direct model call for record_observation",
            "evidence": "provenance.attestAction action_attestation_id",
            "audit": "auditLog.append canonical decision_log writer",
            "finalization": "workflow_tasks status/result/error",
            "retry_attempt_id": "workflow task_id session boundary; no direct decision_log write",
            "direct_protected_ledger_writes": direct_writes,
            "status": "PASS" if status else "FAIL",
        }
    if profile.implementation is None:
        return {
            "agent_id": profile.agent_id,
            "classification": profile.classification,
            "status": "FAIL",
            "reason": "active profile missing implementation",
        }
    cls = _load_class(profile.implementation)
    source = _source_path(cls)
    is_v2 = issubclass(cls, BaseAgentV2)
    direct_writes = _protected_ledger_writes(source)
    return {
        "agent_id": profile.agent_id,
        "classification": profile.classification,
        "implementation": profile.implementation,
        "source": str(source.relative_to(ROOT)),
        "entrypoint": profile.entrypoint,
        "allowed_actions": list(profile.allowed_actions),
        "runtime_contract": profile.runtime_contract,
        "authorization": "BaseAgentV2._authorize_action",
        "tool_policy": "BaseAgentV2.execute_tool allowlist",
        "budget": "SpendGuardrail.check_before_call",
        "evidence": "BaseAgentV2._capture_evidence",
        "audit": "DurableAuditWriter/InMemoryAuditWriter via BaseAgentV2._write_audit",
        "finalization": "BaseAgentV2 protocol success/failure records",
        "retry_attempt_id": "AuditEntryV2.attempt_id -> DurableAuditWriter idempotent retries",
        "direct_protected_ledger_writes": direct_writes,
        "status": "PASS" if is_v2 and not direct_writes else "FAIL",
    }


def build_matrix() -> dict[str, Any]:
    active_rows = [_active_row(profile) for profile in ACTIVE_AGENT_PROFILES]
    registry_entries = _registry_entries()
    runnable = {agent_id for agent_id, entry in registry_entries.items() if entry["runnable"]}
    active_ids = {profile.agent_id for profile in ACTIVE_AGENT_PROFILES}
    deprecated_ids = {profile.agent_id for profile in ALL_AGENT_PROFILES if profile.classification == "deprecated"}
    return {
        "generated_by": "scripts/generate_agent_conformance_matrix.py",
        "active_count": len(active_rows),
        "registry_runnable_ids": sorted(runnable),
        "manifest_active_ids": sorted(active_ids),
        "deprecated_exposed_as_runnable": sorted(runnable & deprecated_ids),
        "active_missing_from_registry": sorted(active_ids - runnable),
        "registry_runnable_not_active": sorted(runnable - active_ids),
        "agents": active_rows + [
            {
                "agent_id": profile.agent_id,
                "classification": profile.classification,
                "implementation": profile.implementation,
                "entrypoint": profile.entrypoint,
                "status": "NOT_ACTIVE",
                "notes": profile.notes,
            }
            for profile in ALL_AGENT_PROFILES
            if profile.classification != "active"
        ],
    }


def validate(matrix: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if matrix["deprecated_exposed_as_runnable"]:
        failures.append(f"deprecated agents exposed as runnable: {matrix['deprecated_exposed_as_runnable']}")
    if matrix["active_missing_from_registry"]:
        failures.append(f"active agents missing from runnable registry: {matrix['active_missing_from_registry']}")
    if matrix["registry_runnable_not_active"]:
        failures.append(f"registry runnable agents not active in manifest: {matrix['registry_runnable_not_active']}")
    for row in matrix["agents"]:
        if row.get("classification") == "active" and row.get("status") != "PASS":
            failures.append(f"active agent failed conformance matrix: {row['agent_id']} {row.get('direct_protected_ledger_writes') or row.get('reason')}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()
    matrix = build_matrix()
    failures = validate(matrix)
    if args.check:
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        expected = json.dumps(matrix, indent=2, sort_keys=True) + "\n"
        if MATRIX_PATH.exists() and MATRIX_PATH.read_text() != expected:
            print(f"FAIL: {MATRIX_PATH.relative_to(ROOT)} is stale")
            return 1
        print("agent conformance matrix ok")
        return 0
    MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    MATRIX_PATH.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"wrote {MATRIX_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
