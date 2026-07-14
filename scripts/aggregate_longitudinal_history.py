#!/usr/bin/env python3
"""Aggregate longitudinal workflow attempts into a compact durable history."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_json(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def successful_scheduled_weeks(attempts: list[dict[str, Any]]) -> dict[str, str]:
    weeks: dict[str, str] = {}
    for attempt in attempts:
        if attempt.get("observation_kind") != "scheduled" or attempt.get("status") != "success":
            continue
        week = attempt.get("iso_week")
        if not week:
            continue
        if week in weeks:
            raise ValueError(f"duplicate successful scheduled observation for {week}")
        weeks[week] = attempt["observation_id"]
    return weeks


def validate_history(history: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    attempts = history.get("attempts", [])
    seen_attempts = set()
    seen_observations = set()
    prior_failed = set(history.get("failed_attempts", []))
    actual_failed = set()
    for attempt in attempts:
        attempt_id = attempt.get("attempt_id")
        if attempt_id in seen_attempts:
            errors.append("DUPLICATE_ATTEMPT_ID")
        seen_attempts.add(attempt_id)
        if attempt.get("status") == "failed":
            actual_failed.add(attempt_id)
        key = (attempt.get("observation_id"), attempt.get("status"))
        if key in seen_observations and attempt.get("status") == "success" and attempt.get("observation_kind") == "scheduled":
            errors.append("DUPLICATE_SUCCESSFUL_OBSERVATION")
        seen_observations.add(key)
        if attempt.get("observation_kind") == "manual" and attempt.get("advances_calendar_milestone"):
            errors.append("MANUAL_RUN_ADVANCES_CALENDAR_MILESTONE")
        if attempt.get("provider_classification") in {"hosted_staging", "production"}:
            errors.append("HOSTED_OR_PRODUCTION_EVIDENCE_CLAIMED")
        activation = history.get("workflow_activation_date")
        if activation and attempt.get("completed_at") and attempt["completed_at"] < activation:
            errors.append("HISTORICAL_OBSERVATION_BEFORE_WORKFLOW_ACTIVATION")
    try:
        successful_scheduled_weeks(attempts)
    except ValueError as exc:
        errors.append(str(exc))
    if not prior_failed.issubset(actual_failed):
        errors.append("PRIOR_FAILED_ATTEMPT_DISAPPEARED")
    expected = history.get("current_aggregate_hash")
    if expected:
        clone = json.loads(json.dumps(history))
        clone["current_aggregate_hash"] = ""
        if sha256_json(clone) != expected:
            errors.append("AGGREGATE_CHAIN_HASH_MISMATCH")
    return errors


def append_attempt(existing: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        existing = {
            "history_version": "longitudinal-history-v1",
            "campaign_series": attempt["campaign_series"],
            "previous_aggregate_hash": None,
            "current_aggregate_hash": "",
            "observation_windows": [],
            "attempts": [],
            "failed_attempts": [],
            "successful_attempts": [],
            "missing_windows": [],
            "benchmark_versions": {},
            "evaluator_versions": [],
            "commits": [],
            "calendar_span": {"first_observation": None, "latest_observation": None},
            "evidence_tier": "foundation_only",
            "milestone_eligibility": {"foundation": True, "cross_version": False, "four_week": False, "twelve_week": False, "hosted": False, "production": False},
            "genesis": True,
        }
    previous_hash = existing.get("current_aggregate_hash") or None
    history = json.loads(json.dumps(existing))
    history["previous_aggregate_hash"] = previous_hash
    history["attempts"].append(attempt)
    if attempt["status"] == "success":
        history["successful_attempts"].append(attempt["attempt_id"])
    else:
        history["failed_attempts"].append(attempt["attempt_id"])
    if attempt["observation_kind"] == "scheduled" and attempt.get("iso_week") not in history["observation_windows"]:
        history["observation_windows"].append(attempt["iso_week"])
    if attempt.get("commit_sha") and attempt["commit_sha"] not in history["commits"]:
        history["commits"].append(attempt["commit_sha"])
    if attempt.get("benchmark_versions"):
        history["benchmark_versions"].update(attempt["benchmark_versions"])
    if attempt.get("evaluator_versions"):
        for version in attempt["evaluator_versions"]:
            if version not in history["evaluator_versions"]:
                history["evaluator_versions"].append(version)
    timestamps = [item["completed_at"] for item in history["attempts"] if item.get("completed_at")]
    if timestamps:
        history["calendar_span"] = {"first_observation": min(timestamps), "latest_observation": max(timestamps)}
    history["current_aggregate_hash"] = ""
    history["current_aggregate_hash"] = sha256_json(history)
    errors = validate_history(history)
    if errors:
        raise SystemExit("\n".join(errors))
    return history


def attempt_from_context(context: dict[str, Any], status: str) -> dict[str, Any]:
    created = context.get("created_at") or utc_now()
    dt = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(UTC)
    iso = dt.isocalendar()
    return {
        "attempt_id": context["attempt_id"],
        "observation_id": context["observation_id"],
        "observation_kind": context["observation_kind"],
        "campaign_series": context["campaign_series"],
        "status": status,
        "event_name": context["event_name"],
        "commit_sha": context["expected_sha"],
        "iso_week": f"{iso.year}-W{iso.week:02d}",
        "started_at": created,
        "completed_at": utc_now(),
        "benchmark_versions": {},
        "evaluator_versions": ["longitudinal-evaluator-v1"],
        "provider_classification": "deterministic_fixture",
        "advances_calendar_milestone": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--status", choices=["success", "failed"], default="success")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        history = load_json(args.output)
        errors = validate_history(history)
        print(canonical_json({"success": not errors, "errors": errors}), end="")
        return 0 if not errors else 2
    context = load_json(args.context)
    existing = load_json(args.existing) if args.existing else {}
    history = append_attempt(existing, attempt_from_context(context, args.status))
    write_json(args.output, history)
    print(canonical_json({"success": True, "current_aggregate_hash": history["current_aggregate_hash"]}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
