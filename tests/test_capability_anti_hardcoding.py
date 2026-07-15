from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_protocol_runner_has_no_named_control_hardcoded_passes():
    source = (ROOT / "scripts/run_governed_capability_genesis.py").read_text()
    forbidden = [
        'if ctype in {"malformed_provider_response"',
        "passed = True",
        "return success without inspecting execution evidence",
    ]
    for pattern in forbidden:
        assert pattern not in source


def test_pr_body_must_not_reference_stale_v2_acceptance_language():
    invalidation = (ROOT / "docs/audit/current/GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V1_INVALIDATION.md").read_text()
    assert "corrected to `INVALID_CAMPAIGN`" in invalidation
