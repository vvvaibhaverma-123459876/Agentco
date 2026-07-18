from __future__ import annotations

import json
from pathlib import Path

from scripts.run_governed_capability_genesis import protocol_semantic_hash


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_protocol_baseline_v3"


def test_protocol_v3_registry_and_cases_are_distinct_from_invalid_v2():
    registry = json.loads((BENCH / "registry.json").read_text())
    cases = json.loads((BENCH / registry["case_manifest"]).read_text())
    assert registry["benchmark_id"] == "capability-protocol-baseline-v3"
    assert registry["version"] == "3.0.0"
    assert len(cases) == 24
    assert {case["control_type"] for case in cases} >= {
        "malformed_provider_response",
        "provider_transport_failure",
        "response_size_rejection",
        "timeout_terminal_state",
        "retry_accounting",
        "secret_redaction",
        "audit_reference_resolution",
        "storage_persistence",
        "no_silent_provider_fallback",
    }


def test_protocol_v2_is_explicitly_invalidated():
    invalidation = json.loads((ROOT / "docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V2_INVALIDATION.json").read_text())
    assert invalidation["finding"]["finding_id"] == "GCR-004"
    assert invalidation["corrected_decision"] == "INVALID_CAMPAIGN"
    assert invalidation["withdrawn_decision"] == "PROTOCOL_BASELINE_ACCEPTED"


def test_protocol_semantic_hash_ignores_volatile_fields_and_tracks_assertions():
    manifest = {
        "campaign_id": "governed-capability-protocol-baseline-v3",
        "acceptance_predicate": {
            "request_json_schema_validation_passed": True,
            "response_json_schema_validation_passed": True,
            "negative_schema_mutations_rejected": True,
            "retry_accounting_passed": True,
            "timeout_release_passed": True,
            "persistence_reinitialization_passed": True,
            "audit_references_resolved": True,
            "no_provider_fallback": True,
        },
        "control_family_results": {"storage_persistence": True},
        "decision": "PROTOCOL_BASELINE_ACCEPTED",
        "freeze_candidate_sha": "candidate",
        "freeze_candidate_tree_hash": "tree",
        "freeze_manifest_commit_sha": "manifest",
        "freeze_binding_commit_sha": "binding",
        "freeze_manifest_blob_sha": "blob",
        "freeze_manifest_sha256": "sha256",
        "freeze_binding_logical_hash": "logical",
    }
    results = [
        {
            "case_id": "case-a",
            "control_type": "retry_accounting",
            "assertions": [{"name": "retry_count", "passed": True, "evidence": {"timestamp": "volatile-a"}}],
            "execution_evidence": {"temporary_path": "/tmp/a"},
        }
    ]
    first = protocol_semantic_hash(manifest, results)
    results[0]["execution_evidence"]["temporary_path"] = "/tmp/b"
    results[0]["assertions"][0]["evidence"]["timestamp"] = "volatile-b"
    assert protocol_semantic_hash(manifest, results) == first
    results[0]["assertions"][0]["passed"] = False
    assert protocol_semantic_hash(manifest, results) != first
