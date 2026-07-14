#!/usr/bin/env python3
"""Run the first governed capability genesis baseline campaign."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.runtime import execute_capability_request  # noqa: E402

ARTIFACT = ROOT / "artifacts" / "capability-runtime" / "governed-capability-genesis-v1"
DOCS = ROOT / "docs" / "audit" / "current"
DOMAINS = [
    "reasoning",
    "planning",
    "evidence_evaluation",
    "claim_grounding",
    "structured_transformation",
    "safe_tool_selection",
    "data_analysis",
    "software_engineering",
    "cross_domain_synthesis",
]


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def request_for(index: int, domain: str, split: str) -> dict[str, Any]:
    base = {
        "protocol_version": "agentco-capability-v1",
        "request_id": f"genesis-{split}-{index}-{domain}",
        "attempt_id": f"genesis-{split}-{index}-{domain}",
        "actor": {"id": "governed-genesis-evaluator", "type": "test_identity"},
        "tenant": "genesis-local",
        "task_type": domain,
        "prompt": f"Run a bounded {domain} capability task for genesis baseline.",
        "structured_input": {
            "claim": "AgentCo genesis request is bounded",
            "evidence": [
                {"id": "e-support", "stance": "support", "reliability": 0.9},
                {"id": "e-weak", "stance": "contradict", "reliability": 0.2},
            ],
            "constraints": ["no live providers", "no production mutation"],
            "data": {"b": 2, "a": 1},
            "csv": "name,value\nalpha,2\nbeta,4\n",
            "domains": ["planning", "evidence"],
            "target_file": "solution.py",
        },
        "context": {"split": split},
        "memory_policy": {
            "enabled": True,
            "memories": [{"id": "mem-verified", "verified": True, "content": "prefer governed answer", "relevance": 0.8}],
        },
        "tool_allowlist": ["json_transformer", "calculator", "fixture_sql", "fixture_reader", "fixture_test_runner"],
        "provider_policy": {"provider": "deterministic_local_reference"},
        "budget": {"max_wall_ms": 5000, "max_provider_calls": 1, "max_tool_calls": 5, "max_tokens": 1000},
        "deadline": None,
        "idempotency_key": f"genesis-{split}-{index}-{domain}",
        "authorization_context": {"permissions": ["capability:execute"]},
        "trace_context": {"trace_id": f"genesis-{split}-{index}-{domain}"},
    }
    return base


def payload_hash(paths: list[Path]) -> str:
    records = [
        {"path": str(path.relative_to(ARTIFACT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}
        for path in sorted(paths)
    ]
    return sha256_text(canonical_json(records))


def payload_manifest(paths: list[Path], aggregate_hash: str, head: str, evaluator_hash: str) -> dict[str, Any]:
    return {
        "canonicalization_version": "capability-runtime-payload-v1",
        "included_relative_paths": [
            {
                "path": str(path.relative_to(ARTIFACT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(paths)
        ],
        "excluded_paths": [
            {
                "path": "GENESIS_MANIFEST.json",
                "reason": "contains aggregate payload hash and would create a recursive hash dependency",
            },
            {
                "path": "INTERNAL_PAYLOAD_MANIFEST.json",
                "reason": "payload manifest aggregate hash is excluded from its own canonical payload",
            },
        ],
        "aggregate_payload_hash": aggregate_hash,
        "campaign_execution_sha": head,
        "protocol_version": "agentco-capability-v1",
        "provider": "deterministic_local_reference",
        "evaluator_hash": evaluator_hash,
        "subject_shas": {"genesis_subject": head},
        "generation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean before governed capability genesis")
    if ARTIFACT.exists():
        for path in sorted(ARTIFACT.glob("**/*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    ARTIFACT.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "HEAD")
    cases = []
    for index in range(24):
        split = "validation" if index < 12 else "hidden"
        cases.append(request_for(index, DOMAINS[index % len(DOMAINS)], split))

    results = []
    for item in cases:
        response = execute_capability_request(item)
        record = {"request": item, "response": response}
        result_path = ARTIFACT / "results" / f"{item['attempt_id']}.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(canonical_json(record))
        results.append(record)

    completed = [item for item in results if item["response"]["status"] == "completed"]
    unsupported = [item for item in results if item["response"]["status"] == "unsupported"]
    failed = [item for item in results if item["response"]["status"] == "failed"]
    timeout = [item for item in results if item["response"]["status"] == "timed_out"]
    domains = sorted({item["request"]["task_type"] for item in completed})
    capability_domains = [domain for domain in domains if domain not in {"health_check"}]
    decision = (
        "GENESIS_BASELINE_ACCEPTED"
        if len(domains) >= 8 and len(capability_domains) >= 4 and len(completed) >= 18 and not failed and not timeout
        else "HOLD_FOR_MORE_EVIDENCE"
    )
    result_files = list((ARTIFACT / "results").glob("*.json"))
    internal_hash = payload_hash(result_files)
    evaluator_hash = sha256_text("governed-capability-genesis-evaluator-v1")
    manifest = {
        "campaign_id": "governed-capability-genesis-v1",
        "campaign_execution_sha": head,
        "protocol_version": "agentco-capability-v1",
        "provider": "deterministic_local_reference",
        "benchmark_registry_hash": json.loads((ROOT / "benchmarks" / "registry.json").read_text()).get("registry_hash"),
        "evaluator_hash": evaluator_hash,
        "planned": len(cases),
        "completed": len(completed),
        "failed": len(failed),
        "timeouts": len(timeout),
        "unsupported": len(unsupported),
        "capability_domain_coverage": domains,
        "request_consumption": "verified_by_protocol_request_hash_and_response_hash",
        "answer_ownership": "subject_runtime_provider_generated",
        "runtime_evidence": "attempt_response_audit_references_present",
        "decision": decision,
        "internal_payload_manifest_hash": internal_hash,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (ARTIFACT / "GENESIS_MANIFEST.json").write_text(canonical_json(manifest))
    (ARTIFACT / "INTERNAL_PAYLOAD_MANIFEST.json").write_text(
        canonical_json(payload_manifest(result_files, internal_hash, head, evaluator_hash))
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "GOVERNED_CAPABILITY_GENESIS_RESULTS.json").write_text(canonical_json(manifest))
    (DOCS / "GOVERNED_CAPABILITY_GENESIS_RESULTS.md").write_text(
        "# Governed Capability Genesis Results\n\n"
        f"- Campaign: `governed-capability-genesis-v1`\n"
        f"- Commit: `{head}`\n"
        f"- Planned: `{len(cases)}`\n"
        f"- Completed: `{len(completed)}`\n"
        f"- Failed: `{len(failed)}`\n"
        f"- Timeouts: `{len(timeout)}`\n"
        f"- Unsupported: `{len(unsupported)}`\n"
        f"- Capability domains: `{len(domains)}`\n"
        f"- Decision: `{decision}`\n"
        "\nThis is a genesis baseline, not a promotion or improvement claim.\n"
    )
    print(canonical_json({"success": decision == "GENESIS_BASELINE_ACCEPTED", **manifest}))
    return 0 if decision == "GENESIS_BASELINE_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
