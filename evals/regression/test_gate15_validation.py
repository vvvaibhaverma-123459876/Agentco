import os
from pathlib import Path

from validation import ValidationSuite


def test_validation_suite_labels_external_and_fixture_evidence(tmp_path: Path):
    # For testing in CI without real APIs, accept FIXTURE reports
    # In production with APIs set, external validation will be used
    suite = ValidationSuite()
    data = suite.write_reports(tmp_path)
    qualities = {r["evidence_quality"] for r in data["reports"]}

    assert "FIXTURE" in qualities
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "validation_report.md").exists()

    # If APIs are configured, expect external validation
    if os.getenv("WORKFLOW_API_URL") or os.getenv("SAFETY_API_URL") or os.getenv("EVIDENCE_API_URL"):
        assert data["release_passes"] is True
        assert "EXTERNAL-VALIDATED" in qualities
    else:
        # Without APIs, release passes only on FIXTURE (deterministic)
        assert data["release_passes"] is False
