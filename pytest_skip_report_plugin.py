"""Pytest plugin used by clean-room skip governance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REPORT: dict[str, Any] = {}


def pytest_configure(config: Any) -> None:
    global REPORT
    REPORT = {
        "collected": [],
        "passed": [],
        "failed": [],
        "skipped": [],
        "xfailed": [],
        "xpassed": [],
        "deselected": [],
    }
    config._agentco_skip_report = REPORT


def pytest_collection_finish(session: Any) -> None:
    report = session.config._agentco_skip_report
    report["collected"] = [item.nodeid for item in session.items]


def pytest_deselected(items: list[Any]) -> None:
    if not items:
        return
    config = items[0].config
    config._agentco_skip_report["deselected"].extend(item.nodeid for item in items)


def pytest_runtest_logreport(report: Any) -> None:
    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return
    data = REPORT
    entry = {"node_id": report.nodeid, "reason": str(report.longrepr)}
    if getattr(report, "wasxfail", None):
        if report.outcome == "passed":
            data["xpassed"].append(entry)
        else:
            data["xfailed"].append(entry)
    elif report.outcome == "passed":
        data["passed"].append(report.nodeid)
    elif report.outcome == "failed":
        data["failed"].append(entry)
    elif report.outcome == "skipped":
        data["skipped"].append(entry)


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    path = os.environ.get("AGENTCO_PYTEST_REPORT")
    if not path:
        return
    report = session.config._agentco_skip_report
    report["exitstatus"] = exitstatus
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
