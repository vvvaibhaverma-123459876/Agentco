import os
from pathlib import Path

from validation import ValidationSuite
import validation.suite as validation_suite


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


def test_configured_live_connector_failure_is_not_fixture(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WORKFLOW_API_URL", "https://workflow.invalid")

    class FailingHttpx:
        @staticmethod
        def get(url: str, timeout: int):
            raise RuntimeError(f"unreachable: {url}")

    monkeypatch.setattr(validation_suite, "httpx", FailingHttpx)

    data = ValidationSuite().write_reports(tmp_path)
    workflow = next(r for r in data["reports"] if r["benchmark"] == "digital_workflow")

    assert workflow["evidence_quality"] == "LIVE-UNAVAILABLE"
    assert workflow["connector_status"] == "unavailable"
    assert workflow["status"] == "fail"
    assert data["release_passes"] is False


def test_configured_live_connectors_can_release_pass(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("WORKFLOW_API_URL", "https://workflow.example")
    monkeypatch.setenv("SAFETY_API_URL", "https://safety.example")
    monkeypatch.setenv("EVIDENCE_API_URL", "https://evidence.example")

    class Response:
        status_code = 200

        def __init__(self, payload: dict):
            self._payload = payload

        def json(self):
            return self._payload

    class FakeHttpx:
        @staticmethod
        def get(url: str, timeout: int):
            if url.endswith("/health"):
                return Response({"tasks_completed": 5})
            if url.endswith("/check"):
                return Response({"unsafe_detections": 0})
            if url.endswith("/stats"):
                return Response({"contradictions_resolved": 9})
            return Response({})

    monkeypatch.setattr(validation_suite, "httpx", FakeHttpx)

    data = ValidationSuite().write_reports(tmp_path)
    live_reports = [r for r in data["reports"] if r["evidence_quality"] == "EXTERNAL-VALIDATED"]

    assert len(live_reports) == 3
    assert all(r["connector_status"] == "live" for r in live_reports)
    assert data["release_passes"] is True
