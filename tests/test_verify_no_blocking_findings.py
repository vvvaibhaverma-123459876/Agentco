from __future__ import annotations

import json

from scripts.verify_no_blocking_findings import scan_findings


def test_scan_findings_reports_open_blocking_and_hold_statuses(tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    (findings_dir / "ledger.json").write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "finding_id": "F-001",
                        "severity": "S2",
                        "status": "open_blocking",
                        "summary": "blocked",
                    },
                    {
                        "finding_id": "F-002",
                        "severity": "S3",
                        "status": "open_hold_for_more_evidence",
                        "summary": "needs evidence",
                    },
                    {
                        "finding_id": "F-003",
                        "severity": "S1",
                        "status": "resolved",
                        "summary": "closed",
                    },
                ]
            }
        )
    )

    open_items = scan_findings(findings_dir)

    assert [item["finding_id"] for item in open_items] == ["F-001", "F-002"]


def test_scan_findings_ignores_non_finding_json(tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    (findings_dir / "plain-report.json").write_text(json.dumps({"status": "open_blocking"}))

    assert scan_findings(findings_dir) == []


def test_scan_findings_treats_invalid_json_as_blocking(tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    (findings_dir / "broken.json").write_text("{")

    open_items = scan_findings(findings_dir)

    assert open_items[0]["finding_id"] == "INVALID_FINDINGS_JSON"
    assert open_items[0]["status"] == "open_blocking"
