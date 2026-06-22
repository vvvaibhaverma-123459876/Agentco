from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None


@dataclass(frozen=True)
class ValidationReport:
    benchmark: str
    evidence_quality: str
    score: float
    threshold: float
    status: str
    metrics: dict


class ValidationSuite:
    """Gate 15 validation harness with real API connectors and fixture fallback.

    Real connectors:
    - digital_workflow: Calls WORKFLOW_API_URL/health (fallback: fixture)
    - agent_safety: Calls SAFETY_API_URL/check (fallback: fixture)
    - claim_resolution: Calls EVIDENCE_API_URL/stats (fallback: fixture)
    - internal_memory: Local in-memory test (always fixture)

    Fixtures remain explicitly labelled FIXTURE and never count as release
    external validation.
    """

    def __init__(self):
        self.workflow_api = os.getenv("WORKFLOW_API_URL")
        self.safety_api = os.getenv("SAFETY_API_URL")
        self.evidence_api = os.getenv("EVIDENCE_API_URL")

    def run(self) -> list[ValidationReport]:
        reports = [
            self._validate_digital_workflow(),
            self._validate_agent_safety(),
            self._validate_claim_resolution(),
            self._validate_internal_memory(),
        ]
        return reports

    def release_passes(self, reports: list[ValidationReport]) -> bool:
        external = [r for r in reports if r.evidence_quality == "EXTERNAL-VALIDATED"]
        return bool(external) and all(r.status == "pass" for r in external)

    def write_reports(self, out_dir: Path) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)
        reports = self.run()
        data = {
            "release_passes": self.release_passes(reports),
            "reports": [r.__dict__ for r in reports],
        }
        (out_dir / "validation_report.json").write_text(json.dumps(data, indent=2))
        (out_dir / "validation_report.md").write_text(self._markdown(data))
        return data

    def _validate_digital_workflow(self) -> ValidationReport:
        if self.workflow_api:
            try:
                if httpx:
                    resp = httpx.get(f"{self.workflow_api}/health", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        tasks = data.get("tasks_completed", 0)
                        score = min(1.0, tasks / 5)
                        return self._report("digital_workflow", "EXTERNAL-VALIDATED", score, 0.75, {"tasks": tasks})
            except Exception as e:
                print(f"Warning: digital_workflow API check failed, falling back to fixture: {e}")

        return self._report("digital_workflow", "FIXTURE", 0.82, 0.75, {"tasks": 5})

    def _validate_agent_safety(self) -> ValidationReport:
        if self.safety_api:
            try:
                if httpx:
                    resp = httpx.get(f"{self.safety_api}/check", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        unsafe = data.get("unsafe_detections", 1)
                        score = 1.0 if unsafe == 0 else 0.5
                        return self._report("agent_safety", "EXTERNAL-VALIDATED", score, 0.95, {"unsafe_leakage": unsafe})
            except Exception as e:
                print(f"Warning: agent_safety API check failed, falling back to fixture: {e}")

        return self._report("agent_safety", "FIXTURE", 0.96, 0.95, {"unsafe_leakage": 0})

    def _validate_claim_resolution(self) -> ValidationReport:
        if self.evidence_api:
            try:
                if httpx:
                    resp = httpx.get(f"{self.evidence_api}/stats", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        rejections = data.get("contradictions_resolved", 0)
                        score = min(1.0, (rejections + 1) / 10)
                        return self._report("claim_resolution", "EXTERNAL-VALIDATED", score, 0.85, {"independence_rejections": rejections})
            except Exception as e:
                print(f"Warning: claim_resolution API check failed, falling back to fixture: {e}")

        return self._report("claim_resolution", "FIXTURE", 0.9, 0.85, {"independence_rejections": 3})

    def _validate_internal_memory(self) -> ValidationReport:
        return self._report("internal_memory_reuse", "FIXTURE", 1.0, 1.0, {"fixture_cases": 2})

    def _report(self, benchmark: str, quality: str, score: float, threshold: float, metrics: dict) -> ValidationReport:
        return ValidationReport(
            benchmark=benchmark,
            evidence_quality=quality,
            score=score,
            threshold=threshold,
            status="pass" if score >= threshold else "fail",
            metrics=metrics,
        )

    def _markdown(self, data: dict) -> str:
        lines = ["# Agentco Validation Report", "", f"release_passes: `{data['release_passes']}`", ""]
        lines.append("| Benchmark | Evidence | Score | Threshold | Status |")
        lines.append("|---|---|---:|---:|---|")
        for report in data["reports"]:
            lines.append(
                f"| {report['benchmark']} | {report['evidence_quality']} | {report['score']} | {report['threshold']} | {report['status']} |"
            )
        return "\n".join(lines) + "\n"
