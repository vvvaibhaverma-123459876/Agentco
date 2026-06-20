#!/usr/bin/env python3
"""Accelerated business simulation over UCI Bike Sharing hourly demand."""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.request
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover - depends on local env
    raise SystemExit("ERROR: psycopg2 is required. Install project dependencies first.") from exc

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import (
    CircularResolutionError,
    validate_independent_sources,
)


DATA_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
CACHE_DIR = ROOT / "data" / "external" / "bike_sharing"
ZIP_PATH = CACHE_DIR / "bike_sharing_dataset.zip"
HOUR_CSV = CACHE_DIR / "hour.csv"

ACCEPTANCE_DIR = ROOT / "evals" / "acceptance"
REPORT_PATH = ACCEPTANCE_DIR / "accelerated_business_run.md"
DECISIONS_PATH = ACCEPTANCE_DIR / "accelerated_business_decisions.jsonl"
CALLS_PATH = ACCEPTANCE_DIR / "accelerated_business_agent_calls.csv"
SUMMARY_PATH = ACCEPTANCE_DIR / "accelerated_business_summary.json"

INSTITUTION = "Urban Mobility Venture Institution"
MISSION = "Operate a bike-rental business over replayed historical demand."
DOMAIN = "urban_mobility_bike_rentals"
CLAIM_TYPE = "high_demand_hour"
FORECASTER_AGENT_ID = "urban-mobility-demand-forecaster"

AGENTS = [
    ("Market Intelligence Team", "Venture CEO", "Institution lead"),
    ("Market Intelligence Team", "Demand Forecaster", "Pre-registered demand claims"),
    ("Operations Team", "Operations Manager", "Bike, staff, and maintenance decisions"),
    ("Finance Team", "Pricing Manager", "Price multiplier decisions"),
    ("Finance Team", "Finance Controller", "Expected economics"),
    ("Risk & Governance Team", "Risk Officer", "Verification controls"),
    ("Calibration Office", "Calibration Auditor", "Independent resolution and trust updates"),
    ("Learning Office", "Learning Agent", "Post-resolution learning"),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=300.0)
    parser.add_argument("--tick-seconds", type=float, default=10.0)
    parser.add_argument("--max-ticks", type=int, default=None)
    parser.add_argument("--offline", action="store_true", help="Refuse network download; require cached UCI data.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _resolution_dsn(db_url: str) -> str:
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db = parsed.path.lstrip("/") or "agentco"
    password = os.environ.get("RESOLUTION_SERVICE_PASSWORD")
    if not password:
        if os.environ.get("AGENTCO_ENV") == "production":
            raise RuntimeError("RESOLUTION_SERVICE_PASSWORD must be set in production")
        password = "resolution-service-dev-password"
    return f"postgresql://resolution_service:{quote(password, safe='')}@{host}:{port}/{db}"


def _ensure_dataset(offline: bool) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if HOUR_CSV.exists():
        return HOUR_CSV
    if offline:
        raise RuntimeError(f"Offline mode requested but {HOUR_CSV} is not cached.")

    print(f"Downloading UCI Bike Sharing dataset from {DATA_URL}")
    try:
        urllib.request.urlretrieve(DATA_URL, ZIP_PATH)
    except Exception as exc:  # pragma: no cover - depends on network
        raise RuntimeError(
            f"Could not download dataset and {HOUR_CSV} is not cached. "
            "Run once without --offline, then use --offline."
        ) from exc
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extract("hour.csv", CACHE_DIR)
    return HOUR_CSV


def _parse_hour_csv(path: Path) -> list[dict[str, Any]]:
    numeric_fields = {
        "instant", "season", "yr", "mnth", "hr", "holiday", "weekday",
        "workingday", "weathersit", "casual", "registered", "cnt",
    }
    float_fields = {"temp", "atemp", "hum", "windspeed"}
    rows: list[dict[str, Any]] = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if key in numeric_fields:
                    row[key] = int(value)
                elif key in float_fields:
                    row[key] = float(value)
                else:
                    row[key] = value
            row["timestamp"] = datetime.strptime(
                f"{row['dteday']} {int(row['hr']):02d}:00:00",
                "%Y-%m-%d %H:%M:%S",
            )
            rows.append(row)
    rows.sort(key=lambda r: (r["timestamp"], r["instant"]))
    return rows


def _percentile(values: list[int], q: float) -> int:
    if not values:
        raise ValueError("cannot compute percentile for empty values")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    return int(round(ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)))


def _choose_start_index(rows: list[dict[str, Any]], seed: int, max_ticks: int) -> int:
    rng = random.Random(seed)
    latest_start = len(rows) - max_ticks - 1
    candidates = [
        i for i, row in enumerate(rows)
        if 0 < i <= latest_start
        and row["timestamp"].year == 2012
        and 7 <= int(row["hr"]) <= 19
        and len([r for r in rows[:i] if r["hr"] == row["hr"]]) >= 50
    ]
    if not candidates:
        raise RuntimeError("No eligible 2012 target hours with sufficient prior history.")
    return candidates[rng.randrange(len(candidates))]


def _baseline(history: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    same_hour = [r for r in history if r["hr"] == target["hr"]]
    threshold = _percentile([int(r["cnt"]) for r in same_hour], 0.75)
    comparable = [
        r for r in history
        if r["hr"] == target["hr"]
        and r["workingday"] == target["workingday"]
        and r["holiday"] == target["holiday"]
        and r["weathersit"] == target["weathersit"]
    ]
    stratum = "same hour, workingday, holiday, and weather situation"
    if len(comparable) < 30:
        comparable = [
            r for r in history
            if r["hr"] == target["hr"]
            and r["workingday"] == target["workingday"]
            and r["holiday"] == target["holiday"]
        ]
        stratum = "same hour, workingday, and holiday"
    if len(comparable) < 30:
        comparable = same_hour
        stratum = "same hour"

    hits = sum(1 for r in comparable if int(r["cnt"]) >= threshold)
    confidence = round((hits + 1.0) / (len(comparable) + 2.0), 4)
    expected_rides = int(round(statistics.median(int(r["cnt"]) for r in comparable)))
    p60 = _percentile([int(r["cnt"]) for r in comparable], 0.60)
    return {
        "threshold": threshold,
        "confidence": confidence,
        "expected_rides": expected_rides,
        "p60": p60,
        "history_rows": len(history),
        "comparable_rows": len(comparable),
        "comparable_hits": hits,
        "stratum": stratum,
    }


def _operation_decision(base: dict[str, Any], high_confidence: float) -> dict[str, Any]:
    demand_anchor = max(int(base["expected_rides"]), int(base["p60"]))
    surge_buffer = 1.18 if high_confidence >= 0.40 else 1.08
    bikes = max(20, int(math.ceil(demand_anchor * surge_buffer / 5.0) * 5))
    staff = max(1, min(12, int(math.ceil(bikes / 95.0))))
    maintenance_buffer = max(3, int(round(bikes * 0.05)))
    return {
        "bikes_to_prepare": bikes,
        "staff_count": staff,
        "maintenance_buffer": maintenance_buffer,
    }


def _pricing_decision(base: dict[str, Any], confidence: float, operation: dict[str, Any]) -> dict[str, Any]:
    if confidence >= 0.50:
        multiplier = 1.15
        reason = "prior comparable rows imply elevated probability of high demand"
    elif int(operation["bikes_to_prepare"]) < int(base["threshold"]):
        multiplier = 1.05
        reason = "capacity is below the high-demand threshold, so price is nudged upward"
    else:
        multiplier = 1.00
        reason = "confidence does not justify a demand surcharge"
    return {"price_multiplier": multiplier, "pricing_reason": reason}


def _finance_estimate(
    base: dict[str, Any],
    operation: dict[str, Any],
    pricing: dict[str, Any],
) -> dict[str, Any]:
    expected_rides = min(int(base["expected_rides"]), int(operation["bikes_to_prepare"]))
    revenue = expected_rides * 3.25 * float(pricing["price_multiplier"])
    staff_cost = int(operation["staff_count"]) * 28.0
    rebalancing_cost = int(operation["bikes_to_prepare"]) * 0.16
    maintenance_cost = int(operation["maintenance_buffer"]) * 4.0
    expected_cost = staff_cost + rebalancing_cost + maintenance_cost
    return {
        "expected_rides": expected_rides,
        "expected_revenue": round(revenue, 2),
        "expected_cost": round(expected_cost, 2),
        "expected_profit": round(revenue - expected_cost, 2),
    }


def _business_metrics(actual: int, operation: dict[str, Any], pricing: dict[str, Any]) -> dict[str, Any]:
    bikes = int(operation["bikes_to_prepare"])
    served = min(actual, bikes)
    lost = max(actual - bikes, 0)
    revenue = served * 3.25 * float(pricing["price_multiplier"])
    staff_cost = int(operation["staff_count"]) * 28.0
    rebalancing_cost = bikes * 0.16
    maintenance_cost = int(operation["maintenance_buffer"]) * 4.0
    profit = revenue - staff_cost - rebalancing_cost - maintenance_cost
    return {
        "actual_demand": actual,
        "bikes_prepared": bikes,
        "served_rides": served,
        "lost_rides": lost,
        "utilization": round(served / bikes, 4) if bikes else 0.0,
        "service_level": round(served / actual, 4) if actual else 1.0,
        "revenue": round(revenue, 2),
        "staff_cost": round(staff_cost, 2),
        "rebalancing_cost": round(rebalancing_cost, 2),
        "maintenance_cost": round(maintenance_cost, 2),
        "profit": round(profit, 2),
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _call_event(
    *,
    run_id: str,
    tick: int,
    simulated_timestamp: str,
    team: str,
    agent: str,
    role: str,
    call_type: str,
    input_sources: list[str],
    decision: dict[str, Any],
    confidence: float | None,
    prediction_id: str | None,
    claim_source: str | None,
    resolution_source: str | None,
    actual_outcome: Any,
    trust_before: float | None,
    trust_after: float | None,
    business_impact: dict[str, Any] | None,
    rationale: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "wall_time": datetime.now(timezone.utc).isoformat(),
        "tick": tick,
        "simulated_timestamp": simulated_timestamp,
        "institution": INSTITUTION,
        "team": team,
        "agent": agent,
        "role": role,
        "call_type": call_type,
        "input_sources": input_sources,
        "decision": _json_safe(decision),
        "confidence": confidence,
        "prediction_id": prediction_id,
        "claim_source": claim_source,
        "resolution_source": resolution_source,
        "actual_outcome": actual_outcome,
        "trust_before": trust_before,
        "trust_after": trust_after,
        "business_impact": business_impact,
        "rationale": rationale,
    }


def _write_outputs(
    *,
    run_id: str,
    args: argparse.Namespace,
    events: list[dict[str, Any]],
    ticks: list[dict[str, Any]],
    circular_rejection: str,
) -> None:
    ACCEPTANCE_DIR.mkdir(parents=True, exist_ok=True)
    with DECISIONS_PATH.open("w") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True) + "\n")

    with CALLS_PATH.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "run_id", "tick", "simulated_timestamp", "team", "agent",
                "role", "call_type", "confidence", "prediction_id", "rationale",
            ],
        )
        writer.writeheader()
        for event in events:
            writer.writerow({
                "run_id": event["run_id"],
                "tick": event["tick"],
                "simulated_timestamp": event["simulated_timestamp"],
                "team": event["team"],
                "agent": event["agent"],
                "role": event["role"],
                "call_type": event["call_type"],
                "confidence": "" if event["confidence"] is None else event["confidence"],
                "prediction_id": event["prediction_id"] or "",
                "rationale": event["rationale"],
            })

    total_profit = round(sum(t["metrics"]["profit"] for t in ticks), 2)
    total_revenue = round(sum(t["metrics"]["revenue"] for t in ticks), 2)
    total_lost = sum(t["metrics"]["lost_rides"] for t in ticks)
    avg_service = round(sum(t["metrics"]["service_level"] for t in ticks) / len(ticks), 4) if ticks else 0.0
    correct_ticks = [t for t in ticks if t["prediction_true"]]
    wrong_ticks = [t for t in ticks if not t["prediction_true"]]
    biggest_correct = max(correct_ticks, key=lambda t: t["metrics"]["profit"], default=None)
    biggest_wrong = max(wrong_ticks, key=lambda t: abs(t["metrics"]["lost_rides"]), default=None)
    next_policy = (
        "Raise prepared-bike buffer by 8% when comparable-prior median is below the high-demand threshold "
        "but the target is a commute hour."
        if total_lost > 0 else
        "Maintain the current prior-row baseline and keep monitoring calibration before increasing capacity."
    )
    learned = (
        "The institution learned that calibration and operating performance diverge: a true high-demand call "
        "can still lose rides when capacity rules are too conservative."
        if total_lost > 0 else
        "The institution learned that the current capacity rule covered this replay window without lost rides."
    )

    summary = {
        "run_id": run_id,
        "institution": INSTITUTION,
        "dataset": DATA_URL,
        "duration_seconds": args.duration_seconds,
        "tick_seconds": args.tick_seconds,
        "ticks_completed": len(ticks),
        "simulated_hours": len(ticks),
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_lost_rides": total_lost,
        "average_service_level": avg_service,
        "correct_predictions": len(correct_ticks),
        "wrong_predictions": len(wrong_ticks),
        "circular_verification_rejection": circular_rejection,
        "biggest_correct_call": biggest_correct,
        "biggest_wrong_call": biggest_wrong,
        "what_the_institution_learned": learned,
        "next_operating_policy": next_policy,
    }
    SUMMARY_PATH.write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True))

    roster_rows = "\n".join(f"| {team} | {agent} | {role} |" for team, agent, role in AGENTS)
    decision_rows = "\n".join(
        "| {tick} | {ts} | {threshold} | {confidence:.4f} | {bikes} | {staff} | {price:.2f} | {actual} | {outcome} | {service:.3f} | {profit:.2f} | {trust_before:.4f}->{trust_after:.4f} |".format(
            tick=t["tick"],
            ts=t["simulated_timestamp"],
            threshold=t["threshold"],
            confidence=t["confidence"],
            bikes=t["operation"]["bikes_to_prepare"],
            staff=t["operation"]["staff_count"],
            price=t["pricing"]["price_multiplier"],
            actual=t["metrics"]["actual_demand"],
            outcome=t["was_high_demand"],
            service=t["metrics"]["service_level"],
            profit=t["metrics"]["profit"],
            trust_before=t["trust_before"],
            trust_after=t["trust_after"],
        )
        for t in ticks
    )
    call_rows = "\n".join(
        f"| {event['tick']} | {event['team']} | {event['agent']} | {event['call_type']} | {event['rationale']} |"
        for event in events
    )
    claim_rows = "\n".join(
        f"| {t['tick']} | `{t['prediction_id']}` | {t['claim']} | {t['claim_source']} | {t['resolution_source']} |"
        for t in ticks
    )
    resolution_rows = "\n".join(
        f"| {t['tick']} | {t['metrics']['actual_demand']} | {t['was_high_demand']} | {t['prediction_true']} | {t['trust_before']:.4f} | {t['trust_after']:.4f} | {t['calibration_delta']:.4f} |"
        for t in ticks
    )

    report = [
        "# Accelerated Business Run",
        "",
        "## Institution Charter",
        f"**Name:** {INSTITUTION}",
        f"**Mission:** {MISSION}",
        "",
        "## Compressed Time Settings",
        f"- Run id: `{run_id}`",
        f"- Default duration seconds requested: `{args.duration_seconds}`",
        f"- Tick interval seconds: `{args.tick_seconds}`",
        f"- Simulated time per tick: `1 historical operating hour`",
        f"- Ticks completed: `{len(ticks)}`",
        f"- Seed: `{args.seed}`",
        "",
        "## Dataset Source",
        f"- UCI Bike Sharing dataset: `{DATA_URL}`",
        f"- Cached file: `{HOUR_CSV.relative_to(ROOT)}`",
        "- File used: `hour.csv`; target column: `cnt`.",
        "",
        "## Business Objective",
        "Operate a bike-rental business over replayed historical demand while making capacity, pricing, finance, risk, calibration, and learning calls before each target hour's demand is revealed.",
        "",
        "## Agent Roster",
        "| Team | Agent | Role |",
        "|---|---|---|",
        roster_rows,
        "",
        "## Tick-by-Tick Decision Table",
        "| Tick | Simulated timestamp | HIGH threshold | Confidence | Bikes | Staff | Price x | Actual demand | HIGH? | Service level | Profit | Trust change |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|",
        decision_rows,
        "",
        "## What Agent Took What Call",
        "| Tick | Team | Agent | Call type | Rationale |",
        "|---:|---|---|---|---|",
        call_rows,
        "",
        "## Pre-Registered Claims",
        "| Tick | Prediction id | Claim | Claim source | Resolution source |",
        "|---:|---|---|---|---|",
        claim_rows,
        "",
        "## Resolution Outcomes",
        "| Tick | Actual `cnt` | Was high demand | Prediction true | Trust before | Trust after | Calibration delta |",
        "|---:|---:|---|---|---:|---:|---:|",
        resolution_rows,
        "",
        "## Circular Verification Rejection",
        circular_rejection,
        "",
        "## Trust/Calibration Changes",
        f"- Correct predictions: `{len(correct_ticks)}`",
        f"- Wrong predictions: `{len(wrong_ticks)}`",
        f"- Final tick trust: `{ticks[-1]['trust_after']:.4f}`" if ticks else "- Final tick trust: `n/a`",
        "",
        "## P&L Summary",
        f"- Total revenue: `{total_revenue:.2f}`",
        f"- Total profit: `{total_profit:.2f}`",
        f"- Total lost rides: `{total_lost}`",
        f"- Average service level: `{avg_service:.4f}`",
        "",
        "## Biggest Correct Call",
        json.dumps(_json_safe(biggest_correct), sort_keys=True) if biggest_correct else "No correct call recorded.",
        "",
        "## Biggest Wrong Call",
        json.dumps(_json_safe(biggest_wrong), sort_keys=True) if biggest_wrong else "No wrong call recorded.",
        "",
        "## What The Institution Learned",
        learned,
        "",
        "## Next Operating Policy",
        next_policy,
        "",
    ]
    REPORT_PATH.write_text("\n".join(report))


def main() -> int:
    args = _parse_args()
    if args.duration_seconds <= 0 or args.tick_seconds <= 0:
        raise SystemExit("ERROR: --duration-seconds and --tick-seconds must be positive.")
    max_ticks = args.max_ticks or max(1, int(args.duration_seconds // args.tick_seconds))

    hour_csv = _ensure_dataset(args.offline)
    rows = _parse_hour_csv(hour_csv)
    start_index = _choose_start_index(rows, args.seed, max_ticks)
    run_id = f"urban-mobility-{uuid.uuid4()}"

    db_url = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        svc_conn = psycopg2.connect(_resolution_dsn(db_url))
        svc_conn.autocommit = True
    except psycopg2.OperationalError as exc:
        raise SystemExit("ERROR: Database unavailable. Start Postgres and run `make migrate`.") from exc

    cal = create_calibration_engine(db=conn)
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    print(f"Starting {INSTITUTION}: run_id={run_id}")
    print(f"Runtime target={args.duration_seconds}s, tick={args.tick_seconds}s, max_ticks={max_ticks}")

    events: list[dict[str, Any]] = []
    ticks: list[dict[str, Any]] = []
    circular_rejection = "No circular verification attempted."
    start_wall = time.monotonic()

    for tick in range(1, max_ticks + 1):
        if time.monotonic() - start_wall >= args.duration_seconds:
            break
        tick_started = time.monotonic()
        target = rows[start_index + tick - 1]
        history = [r for r in rows if r["timestamp"] < target["timestamp"]]
        simulated_timestamp = target["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        claim_source = f"uci-bike-sharing-history://hour.csv?before={simulated_timestamp}"
        resolution_source = f"uci-bike-sharing-heldout://hour.csv?instant={target['instant']}"
        validate_independent_sources(claim_source, resolution_source)

        base = _baseline(history, target)
        threshold = int(base["threshold"])
        confidence = float(base["confidence"])
        claim = f"For target timestamp {simulated_timestamp}, demand will be HIGH."
        trust_before = trust.trusted_confidence(
            stated=confidence,
            subject_id=FORECASTER_AGENT_ID,
            subject_type="agent",
            domain=DOMAIN,
            claim_type=CLAIM_TYPE,
            horizon_class="short",
        )

        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Market Intelligence Team", agent="Venture CEO", role="Institution lead",
            call_type="select_target_hour", input_sources=[claim_source],
            decision={"target_timestamp": simulated_timestamp, "target_instant": target["instant"]},
            confidence=None, prediction_id=None, claim_source=claim_source,
            resolution_source=resolution_source, actual_outcome=None,
            trust_before=None, trust_after=None, business_impact=None,
            rationale="selected the next held-out historical operating hour",
        ))

        reg = PredictionRegistration(
            claim=claim,
            probability=confidence,
            confidence_basis={
                "source": claim_source,
                "method": "prior_rows_comparable_hour_workingday_weather",
                "threshold": threshold,
                "baseline": base,
                "target_features_without_cnt": {
                    k: _json_safe(v) for k, v in target.items()
                    if k not in {"cnt", "casual", "registered"}
                },
            },
            producing_agent_id=FORECASTER_AGENT_ID,
            producing_prompt_version="accelerated_business_simulation_v1",
            resolution_criterion=f"Resolve TRUE iff held-out UCI hour.csv row has cnt >= {threshold}.",
            resolution_date=datetime.now(timezone.utc) + timedelta(seconds=0.1),
            ground_truth_source=resolution_source,
            horizon_class="short",
            domain=DOMAIN,
            claim_type=CLAIM_TYPE,
        )
        prediction_id = ledger.pre_register(reg)
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Market Intelligence Team", agent="Demand Forecaster", role="Pre-registered demand claims",
            call_type="pre_register_high_demand_claim", input_sources=[claim_source],
            decision={"claim": claim, "threshold": threshold, "baseline": base},
            confidence=confidence, prediction_id=prediction_id, claim_source=claim_source,
            resolution_source=resolution_source, actual_outcome=None,
            trust_before=trust_before, trust_after=None, business_impact=None,
            rationale="computed HIGH threshold and confidence from rows strictly earlier than target",
        ))

        operation = _operation_decision(base, confidence)
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Operations Team", agent="Operations Manager", role="Bike, staff, and maintenance decisions",
            call_type="capacity_plan", input_sources=[claim_source, prediction_id],
            decision=operation, confidence=None, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source, actual_outcome=None,
            trust_before=None, trust_after=None, business_impact=None,
            rationale="prepared capacity from comparable prior median, p60, and forecast confidence",
        ))

        pricing = _pricing_decision(base, confidence, operation)
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Finance Team", agent="Pricing Manager", role="Price multiplier decisions",
            call_type="pricing_plan", input_sources=[claim_source, prediction_id],
            decision=pricing, confidence=None, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source, actual_outcome=None,
            trust_before=None, trust_after=None, business_impact=None,
            rationale=str(pricing["pricing_reason"]),
        ))

        finance = _finance_estimate(base, operation, pricing)
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Finance Team", agent="Finance Controller", role="Expected economics",
            call_type="financial_estimate", input_sources=[claim_source, prediction_id],
            decision=finance, confidence=None, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source, actual_outcome=None,
            trust_before=None, trust_after=None, business_impact=None,
            rationale="estimated rides, revenue, cost, and profit before actual demand was revealed",
        ))

        blindly_trusted = confidence > 0.80
        risk_decision = {
            "claim_pre_registered": bool(prediction_id),
            "source_non_circular": claim_source != resolution_source,
            "confidence_blindly_trusted": blindly_trusted,
            "approved_for_resolution": bool(prediction_id) and claim_source != resolution_source and not blindly_trusted,
        }
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Risk & Governance Team", agent="Risk Officer", role="Verification controls",
            call_type="risk_check", input_sources=[claim_source, resolution_source, prediction_id],
            decision=risk_decision, confidence=None, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source, actual_outcome=None,
            trust_before=trust_before, trust_after=None, business_impact=None,
            rationale="checked preregistration, source independence, and trust gating before resolution",
        ))
        if not risk_decision["approved_for_resolution"]:
            raise RuntimeError(f"Risk Officer blocked tick {tick}: {risk_decision}")

        if tick == 1:
            try:
                validate_independent_sources(claim_source, claim_source)
            except CircularResolutionError as exc:
                circular_rejection = f"Rejected deliberate circular verification attempt on tick 1: {exc}"
            else:
                raise RuntimeError("Circular verification attempt was not rejected")

        while time.monotonic() - tick_started < 0.12:
            time.sleep(0.01)

        actual = int(target["cnt"])
        was_high = actual >= threshold
        resolved = resolution.resolve(
            prediction_id=prediction_id,
            outcome=was_high,
            ground_truth_source=resolution_source,
            evidence={
                "source_url": resolution_source,
                "cached_file": str(hour_csv.relative_to(ROOT)),
                "target_instant": target["instant"],
                "target_timestamp": simulated_timestamp,
                "actual_cnt": actual,
                "threshold": threshold,
                "independence_check": "passed",
            },
        )
        ledger._db = svc_conn
        ledger.persist_resolution(resolved)
        ledger._db = conn

        trust_after = trust.trusted_confidence(
            stated=confidence,
            subject_id=FORECASTER_AGENT_ID,
            subject_type="agent",
            domain=DOMAIN,
            claim_type=CLAIM_TYPE,
            horizon_class="short",
        )
        calibration_delta = round(trust_after - trust_before, 6)
        prediction_true = was_high
        metrics = _business_metrics(actual, operation, pricing)

        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Calibration Office", agent="Calibration Auditor", role="Independent resolution and trust updates",
            call_type="resolve_held_out_outcome", input_sources=[resolution_source],
            decision={
                "was_high_demand": was_high,
                "prediction_true": prediction_true,
                "actual_cnt": actual,
                "threshold": threshold,
                "calibration_delta": calibration_delta,
            },
            confidence=confidence, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source,
            actual_outcome=was_high, trust_before=trust_before, trust_after=trust_after,
            business_impact=metrics,
            rationale="resolved only against the held-out UCI row after preregistration",
        ))

        mistake = None
        if metrics["lost_rides"] > 0:
            mistake = "capacity was lower than revealed demand"
        elif metrics["utilization"] < 0.65:
            mistake = "capacity was materially above revealed demand"
        lesson = (
            "commute-hour capacity buffers need to account for upside demand"
            if metrics["lost_rides"] > 0 else
            "capacity rule covered demand without lost rides"
        )
        adjustment = (
            "increase next comparable-hour bike buffer"
            if metrics["lost_rides"] > 0 else
            "keep buffer stable and continue calibration"
        )
        learning = {"lesson": lesson, "mistake": mistake, "next_policy_adjustment": adjustment}
        events.append(_call_event(
            run_id=run_id, tick=tick, simulated_timestamp=simulated_timestamp,
            team="Learning Office", agent="Learning Agent", role="Post-resolution learning",
            call_type="learning_update", input_sources=[resolution_source, prediction_id],
            decision=learning, confidence=None, prediction_id=prediction_id,
            claim_source=claim_source, resolution_source=resolution_source,
            actual_outcome=was_high, trust_before=trust_before, trust_after=trust_after,
            business_impact=metrics,
            rationale="converted resolved outcome and business impact into the next operating adjustment",
        ))

        ticks.append({
            "tick": tick,
            "simulated_timestamp": simulated_timestamp,
            "prediction_id": prediction_id,
            "claim": claim,
            "claim_source": claim_source,
            "resolution_source": resolution_source,
            "threshold": threshold,
            "confidence": confidence,
            "operation": operation,
            "pricing": pricing,
            "finance": finance,
            "risk": risk_decision,
            "actual_cnt": actual,
            "was_high_demand": was_high,
            "prediction_true": prediction_true,
            "trust_before": trust_before,
            "trust_after": trust_after,
            "calibration_delta": calibration_delta,
            "metrics": metrics,
            "learning": learning,
        })

        print(
            f"tick={tick} simulated={simulated_timestamp} confidence={confidence:.4f} "
            f"actual={actual} high={was_high} profit={metrics['profit']:.2f}"
        )
        elapsed = time.monotonic() - tick_started
        remaining = args.tick_seconds - elapsed
        if remaining > 0 and tick < max_ticks:
            time.sleep(remaining)

    _write_outputs(
        run_id=run_id,
        args=args,
        events=events,
        ticks=ticks,
        circular_rejection=circular_rejection,
    )
    print(f"Completed {len(ticks)} ticks.")
    print(f"Report: {REPORT_PATH}")
    print(f"Decisions: {DECISIONS_PATH}")
    print(f"Agent calls: {CALLS_PATH}")
    print(f"Summary: {SUMMARY_PATH}")

    conn.close()
    svc_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
