from pathlib import Path

from validation import ValidationSuite


def test_validation_suite_labels_external_and_fixture_evidence(tmp_path: Path):
    suite = ValidationSuite()
    data = suite.write_reports(tmp_path)
    qualities = {r["evidence_quality"] for r in data["reports"]}
    assert data["release_passes"] is True
    assert "EXTERNAL-VALIDATED" in qualities
    assert "FIXTURE" in qualities
    assert (tmp_path / "validation_report.json").exists()
    assert (tmp_path / "validation_report.md").exists()
