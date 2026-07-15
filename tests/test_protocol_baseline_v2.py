from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "capability_protocol_baseline_v2"


def test_protocol_v2_registry_and_cases_are_distinct_from_invalid_v1():
    registry = json.loads((BENCH / "registry.json").read_text())
    cases = json.loads((BENCH / registry["case_manifest"]).read_text())
    assert registry["benchmark_id"] == "capability-protocol-baseline-v2"
    assert registry["version"] == "2.0.0"
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


def test_protocol_v1_is_explicitly_invalidated():
    invalidation = json.loads((ROOT / "docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V1_INVALIDATION.json").read_text())
    assert invalidation["finding"]["finding_id"] == "GCR-003"
    assert invalidation["corrected_decision"] == "INVALID_CAMPAIGN"
    assert invalidation["withdrawn_decision"] == "PROTOCOL_BASELINE_ACCEPTED"
