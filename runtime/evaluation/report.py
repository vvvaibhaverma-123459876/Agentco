from __future__ import annotations

from dataclasses import asdict
from typing import Any

from runtime.base_agent.agent_manifest import ACTIVE_AGENT_PROFILES
from runtime.base_agent.audit_writer import InMemoryAuditWriter
from runtime.evaluation.benchmark import benchmark_cases, benchmark_metadata
from runtime.evaluation.evaluators import EvaluationService
from runtime.evaluation.metrics import calibration_metrics, records_as_dicts


def build_evaluation_report() -> dict[str, Any]:
    audit_writer = InMemoryAuditWriter(allow_test_mode=True)
    service = EvaluationService(
        audit_writer=audit_writer,
        timestamp_factory=lambda: "2026-07-11T00:00:00+00:00",
    )
    case_results: list[dict[str, Any]] = []
    for case in benchmark_cases():
        record = service.evaluate(case.input)
        case_results.append({
            "case_id": case.case_id,
            "category": case.category,
            "agent_id": case.input.agent_id,
            "expected_pass": case.expected_pass,
            "actual_pass": record.passed,
            "failure_category": record.failure_category,
            "evaluation_id": record.evaluation_id,
            "audit_log_id": record.audit_log_id,
            "audit_backend": record.audit_backend,
        })
    records = service.store.records()
    active_ids = {profile.agent_id for profile in ACTIVE_AGENT_PROFILES}
    covered_ids = {result["agent_id"] for result in case_results if result["agent_id"] in active_ids}
    unsupported_high_conf_passed = [
        result for result in case_results
        if "unsupported-high-confidence" in result["case_id"] and result["actual_pass"]
    ]
    return {
        "generated_by": "scripts/generate_evaluation_calibration_report.py",
        **benchmark_metadata(),
        "active_agent_ids": sorted(active_ids),
        "covered_active_agent_ids": sorted(covered_ids),
        "missing_active_agent_ids": sorted(active_ids - covered_ids),
        "case_results": case_results,
        "metrics": calibration_metrics(records),
        "records": records_as_dicts(records),
        "audit_record_count": len(getattr(audit_writer, "entries", [])),
        "all_records_audited": all(record.audit_log_id for record in records),
        "unsupported_high_confidence_passed": unsupported_high_conf_passed,
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if report["missing_active_agent_ids"]:
        failures.append(f"active agents missing evaluation coverage: {report['missing_active_agent_ids']}")
    if not report["case_results"]:
        failures.append("benchmark results are missing")
    if report["metrics"]["record_count"] != len(report["records"]):
        failures.append("calibration metrics record count does not match records")
    if not report["all_records_audited"]:
        failures.append("evaluation records missing audit acknowledgements")
    if report["audit_record_count"] != len(report["records"]):
        failures.append("evaluation records bypassed governed audit writer")
    if report["unsupported_high_confidence_passed"]:
        failures.append("unsupported high-confidence claims passed evaluation")
    for result in report["case_results"]:
        if result["actual_pass"] != result["expected_pass"]:
            failures.append(f"benchmark case expectation mismatch: {result['case_id']}")
    return failures
