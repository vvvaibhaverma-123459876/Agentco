#!/usr/bin/env python3
"""Verify AgentCo mission progress without overclaiming general intelligence.

This verifier aggregates the current build ledger and latest runtime evidence
into explicit mission claims. It is intentionally stricter than the build
ledger: architecture completion and local production smoke do not prove
long-horizon general intelligence, durable autonomous improvement, broad
open-domain transfer, or hosted production certification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
MISSION_JSON = REPORT_DIR / "mission_progress_verification.json"
MISSION_MD = REPORT_DIR / "mission_progress_verification.md"


@dataclass(frozen=True)
class Claim:
    name: str
    status: str
    summary: str
    evidence: list[str]
    required_next_evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "evidence": self.evidence,
            "required_next_evidence": self.required_next_evidence,
        }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    return json.loads(path.read_text())


def build_ledger_claim(report: dict[str, Any]) -> Claim:
    rollups = report.get("rollups", {})
    gates = report.get("gates", {})
    verified = rollups.get("verified")
    total = rollups.get("total_items")
    termination = report.get("meta", {}).get("termination_predicate_met") is True
    gate_failures = [
        name for name, status in gates.items()
        if not name.startswith("_") and status != "green"
    ]
    ok = verified == total and termination and not gate_failures
    return Claim(
        name="evidence_governed_calibration_civilization",
        status="verified" if ok else "blocked",
        summary=(
            "Build-ledger architecture is complete with green safety gates."
            if ok else "Build-ledger architecture or safety gates are not complete."
        ),
        evidence=[
            f"build ledger verified={verified}/{total}",
            f"termination_predicate_met={termination}",
            f"non_green_gates={gate_failures}",
        ],
        required_next_evidence=[] if ok else ["Restore 100% build-ledger verification and green gates."],
    )


def long_horizon_claim(history: list[dict[str, Any]]) -> Claim:
    # Current repo has latest reports, not a longitudinal run registry. Require a
    # minimum time span and trend before allowing a stronger claim.
    successful = [row for row in history if row.get("success") is True]
    timestamps = [parse_time(row.get("generated_at")) for row in successful if row.get("generated_at")]
    timestamps = [ts for ts in timestamps if ts is not None]
    spans_days = 0
    if len(timestamps) >= 2:
        spans_days = (max(timestamps) - min(timestamps)).days
    proven = len(successful) >= 10 and spans_days >= 30 and trend_improves(successful)
    return Claim(
        name="progressively_more_general_intelligence_over_long_horizons",
        status="verified" if proven else "unproven",
        summary=(
            "Longitudinal evidence shows improving cross-domain performance over at least 30 days."
            if proven else "No sufficient longitudinal evidence yet for progressive general intelligence."
        ),
        evidence=[
            f"successful_longitudinal_runs={len(successful)}",
            f"timespan_days={spans_days}",
            f"improving_trend={trend_improves(successful)}",
        ],
        required_next_evidence=[] if proven else [
            "Persist a longitudinal mission-run registry with at least 10 successful real runs.",
            "Cover at least 30 calendar days.",
            "Show statistically meaningful improvement across held-out domains without lowering safety gates.",
        ],
    )


def durable_improvement_claim(memory_report: dict[str, Any], promotion_evidence: dict[str, Any]) -> Claim:
    memory_ok = memory_report.get("success") is True and memory_report.get("mode") == "live_openai"
    promotion_ok = promotion_evidence.get("verified") is True
    proven = memory_ok and promotion_ok and promotion_evidence.get("repeated_real_world_runs", 0) >= 3
    return Claim(
        name="durable_autonomous_improvement_from_repeated_real_world_operation",
        status="verified" if proven else ("partial" if memory_ok and promotion_ok else "unproven"),
        summary=(
            "Repeated real-world runs prove durable autonomous improvement."
            if proven else "Mechanisms exist, but repeated real-world autonomous improvement is not yet proven."
        ),
        evidence=[
            f"memory_influence_live_success={memory_ok}",
            f"vca_promotion_mechanism_verified={promotion_ok}",
            f"repeated_real_world_runs={promotion_evidence.get('repeated_real_world_runs', 0)}",
        ],
        required_next_evidence=[] if proven else [
            "Run at least 3 real-world improvement cycles where a prior lesson/skill measurably improves later performance.",
            "Persist before/after scores, promotion proof, rollback/canary result, and event-log lineage for each cycle.",
        ],
    )


def open_domain_transfer_claim(cross_domain_report: dict[str, Any]) -> Claim:
    success = cross_domain_report.get("success") is True
    simulated = cross_domain_report.get("simulated") is True
    domains = cross_domain_report.get("domains") or []
    bounded_flag = cross_domain_report.get("not_proof_of_general_intelligence") is True
    broad_enough = success and not simulated and len(domains) >= 12 and not bounded_flag
    return Claim(
        name="broad_open_domain_transfer_beyond_bounded_verifiers",
        status="verified" if broad_enough else ("partial" if success and not simulated else "unproven"),
        summary=(
            "Open-domain transfer is demonstrated beyond bounded verifier scenarios."
            if broad_enough else "Current cross-domain evidence is bounded and should not be read as open-domain transfer."
        ),
        evidence=[
            f"live_cross_domain_success={success}",
            f"simulated={simulated}",
            f"domain_count={len(domains)}",
            f"bounded_not_gi_flag={bounded_flag}",
        ],
        required_next_evidence=[] if broad_enough else [
            "Run live held-out domains selected after the verifier is written.",
            "Use at least 12 domains with unseen task schemas and independent evidence sources.",
            "Remove the bounded-verifier limitation only after independent adjudication.",
        ],
    )


def hosted_ops_claim(posture: dict[str, Any], release: dict[str, Any]) -> Claim:
    local_posture_ok = posture.get("can_continue") is True
    release_ok = release.get("success") is True or all(
        status == "green" for status in (release.get("gates") or {}).values()
    )
    hosted_evidence = posture.get("hosted_production_certification") is True
    verified = local_posture_ok and release_ok and hosted_evidence
    return Claim(
        name="hosted_production_operations_certification",
        status="verified" if verified else ("partial" if local_posture_ok and release_ok else "blocked"),
        summary=(
            "Hosted production operations are certified with SLO/DR/backup/monitoring evidence."
            if verified else "Local production posture is not the same as hosted production operations certification."
        ),
        evidence=[
            f"local_production_posture_can_continue={local_posture_ok}",
            f"release_gates_green={release_ok}",
            f"hosted_production_certification={hosted_evidence}",
        ],
        required_next_evidence=[] if verified else [
            "Record hosted deployment environment identity and release artifact.",
            "Verify SLO dashboards, alert routing, backup/restore, DR runbook, and incident response.",
            "Run production smoke/load/security gates against hosted production or staging with production-equivalent controls.",
        ],
    )


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)
    except ValueError:
        return None


def trend_improves(rows: list[dict[str, Any]]) -> bool:
    if len(rows) < 2:
        return False
    scores = [row.get("aggregate_score") for row in rows]
    scores = [float(score) for score in scores if isinstance(score, int | float)]
    return len(scores) >= 2 and scores[-1] > scores[0]


def build_report() -> dict[str, Any]:
    build_ledger = load_json(REPORT_DIR / "build_ledger_report.json")
    memory = load_json(REPORT_DIR / "memory_influence_verification.json")
    cross_domain = load_json(REPORT_DIR / "live_cross_domain_goal_run.json")
    posture = load_json(REPORT_DIR / "production_posture_verification.json")
    release = load_json(REPORT_DIR / "release_gate_verification.json")
    promotion_evidence = {
        "verified": build_ledger.get("rollups", {}).get("verified") == build_ledger.get("rollups", {}).get("total_items"),
        "repeated_real_world_runs": 0,
    }
    history: list[dict[str, Any]] = []

    claims = [
        build_ledger_claim(build_ledger),
        long_horizon_claim(history),
        durable_improvement_claim(memory, promotion_evidence),
        open_domain_transfer_claim(cross_domain),
        hosted_ops_claim(posture, release),
    ]
    statuses = {claim.name: claim.status for claim in claims}
    verified_count = sum(1 for status in statuses.values() if status == "verified")
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mission": (
            "AgentCo exists to evolve into progressively more general intelligence by operating as an "
            "evidence-governed, calibration-driven AI civilization that learns continuously, improves "
            "itself safely, and expands its capability across domains over time."
        ),
        "claims": [claim.to_dict() for claim in claims],
        "summary": {
            "verified_claims": verified_count,
            "total_claims": len(claims),
            "statuses": statuses,
            "mission_fully_proven": verified_count == len(claims),
        },
    }


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Mission Progress Verification",
        "",
        f"Generated: {report['generated_at']}",
        "",
        report["mission"],
        "",
        f"Mission fully proven: `{report['summary']['mission_fully_proven']}`",
        "",
        "| Claim | Status | Summary |",
        "|---|---|---|",
    ]
    for claim in report["claims"]:
        lines.append(f"| `{claim['name']}` | `{claim['status']}` | {claim['summary']} |")
    lines.extend(["", "## Required Next Evidence", ""])
    for claim in report["claims"]:
        if claim["required_next_evidence"]:
            lines.append(f"### {claim['name']}")
            lines.extend(f"- {item}" for item in claim["required_next_evidence"])
            lines.append("")
    MISSION_MD.write_text("\n".join(lines).rstrip() + "\n")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    MISSION_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report)
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
