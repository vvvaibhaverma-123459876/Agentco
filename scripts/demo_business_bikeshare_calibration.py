#!/usr/bin/env python3
"""Business-operations demo: verifiable calibration on UCI Bike Sharing data."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg2
except ImportError as exc:  # pragma: no cover - exercised only on incomplete envs
    raise SystemExit("ERROR: psycopg2 is required for this demo. Run migrations and install project deps.") from exc

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import (
    CircularResolutionError,
    validate_independent_sources,
)
from reserve.credentials.proof_of_calibration import issue_credential, persist_credential
from reserve.scoring.scoring_function import score_agent


DATA_URL = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
CACHE_DIR = ROOT / "data" / "external" / "bike_sharing"
ZIP_PATH = CACHE_DIR / "bike_sharing_dataset.zip"
HOUR_CSV = CACHE_DIR / "hour.csv"
ACCEPTANCE_PATH = ROOT / "evals" / "acceptance" / "business_bikeshare_calibration_demo.md"

AGENT_ID = "business-bikeshare-calibration-demo-agent"
TARGET_DTTM = "2012-09-12 17:00:00"
CLAIM_SOURCE = "uci-bike-sharing-history://data/external/bike_sharing/hour.csv?rows=before-target"
RESOLUTION_SOURCE = "uci-bike-sharing-heldout://data/external/bike_sharing/hour.csv?row=target"


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


def _entry_hash(prediction_id: str, claim: str) -> str:
    return hashlib.sha256(f"{prediction_id}:{claim}".encode()).hexdigest()


def _ensure_dataset() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if HOUR_CSV.exists():
        return HOUR_CSV

    print(f"Cached dataset not found. Downloading UCI Bike Sharing dataset from {DATA_URL}")
    try:
        urllib.request.urlretrieve(DATA_URL, ZIP_PATH)
    except Exception as exc:  # pragma: no cover - depends on local network state
        raise RuntimeError(
            f"Could not download dataset and {HOUR_CSV} is not cached. "
            "Run once with network access, then the demo is offline-runnable."
        ) from exc

    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extract("hour.csv", CACHE_DIR)
    if not HOUR_CSV.exists():
        raise RuntimeError(f"Dataset archive did not produce {HOUR_CSV}")
    return HOUR_CSV


def _parse_hour_csv(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    numeric_fields = {
        "instant", "season", "yr", "mnth", "hr", "holiday", "weekday",
        "workingday", "weathersit", "casual", "registered", "cnt",
    }
    float_fields = {"temp", "atemp", "hum", "windspeed"}
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row: dict[str, object] = {}
            for key, value in raw.items():
                if key in numeric_fields:
                    row[key] = int(value)
                elif key in float_fields:
                    row[key] = float(value)
                else:
                    row[key] = value
            row["timestamp"] = datetime.strptime(str(row["dteday"]) + f" {int(row['hr']):02d}:00:00", "%Y-%m-%d %H:%M:%S")
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
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)
    return int(round(interpolated))


def _build_prior_baseline(history: list[dict[str, object]], target_features: dict[str, object]) -> dict[str, object]:
    same_hour = [r for r in history if r["hr"] == target_features["hr"]]
    threshold = _percentile([int(r["cnt"]) for r in same_hour], 0.75)

    comparable = [
        r for r in history
        if r["hr"] == target_features["hr"]
        and r["workingday"] == target_features["workingday"]
        and r["holiday"] == target_features["holiday"]
        and r["weathersit"] == target_features["weathersit"]
    ]
    stratum = "same hour, workingday, holiday, and weather situation"
    if len(comparable) < 30:
        comparable = [
            r for r in history
            if r["hr"] == target_features["hr"]
            and r["workingday"] == target_features["workingday"]
            and r["holiday"] == target_features["holiday"]
        ]
        stratum = "same hour, workingday, and holiday"
    if len(comparable) < 30:
        comparable = same_hour
        stratum = "same hour"

    hits = sum(1 for r in comparable if int(r["cnt"]) >= threshold)
    confidence = (hits + 1.0) / (len(comparable) + 2.0)
    median_prior = int(round(statistics.median(int(r["cnt"]) for r in comparable)))
    return {
        "threshold": threshold,
        "confidence": confidence,
        "history_count": len(history),
        "same_hour_count": len(same_hour),
        "comparable_count": len(comparable),
        "comparable_hits": hits,
        "median_prior_comparable": median_prior,
        "stratum": stratum,
    }


def _write_acceptance_artifact(
    *,
    prediction_id: str,
    credential_id: str,
    digest: str,
    target_timestamp: str,
    threshold: int,
    confidence: float,
    actual_cnt: int,
    outcome: bool,
    trust_before: float,
    trust_after: float,
    circular_status: str,
    baseline: dict[str, object],
) -> None:
    ACCEPTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Business Bikeshare Calibration Demo",
        "",
        "## Dataset",
        f"- Source: `{DATA_URL}`",
        f"- Cached file: `{HOUR_CSV.relative_to(ROOT)}`",
        "- File used: `hour.csv`",
        "- Historical data: Capital Bikeshare hourly rentals from 2011-2012 with weather and calendar fields.",
        "",
        "## Business Scenario",
        "A bike-rental operator must decide before a target hour whether demand will be high enough to justify extra bikes or staff.",
        "",
        "## Time Split",
        f"- Target timestamp: `{target_timestamp}`",
        f"- Training/history rows: `{baseline['history_count']}` rows strictly earlier than the target timestamp.",
        "- Held-out row: exactly the target timestamp row, with `cnt` read only during resolution.",
        "",
        "## Pre-Registered Claim",
        f"- Prediction id: `{prediction_id}`",
        f"- Ledger hash: `{digest}`",
        f"- Claim source: `{CLAIM_SOURCE}`",
        f"- Independent resolution source: `{RESOLUTION_SOURCE}`",
        f"- Claim: total rentals `cnt` at `{target_timestamp}` will be >= `{threshold}`.",
        f"- Predicted confidence: `{confidence:.4f}`",
        f"- Baseline stratum: `{baseline['stratum']}`",
        f"- Comparable history rows: `{baseline['comparable_count']}`",
        "",
        "## Resolution",
        f"- Actual `cnt`: `{actual_cnt}`",
        f"- Outcome: `{outcome}`",
        f"- Trust/calibration update: `{trust_before:.4f}` -> `{trust_after:.4f}`",
        "",
        "## Circular Verification Test",
        f"- Status: {circular_status}",
        "",
        "## Credential",
        f"- Proof/credential id: `{credential_id}`",
        f"- Recompute command: `python3 reserve/tools/recompute_credential.py {AGENT_ID}`",
        "",
    ]
    ACCEPTANCE_PATH.write_text("\n".join(lines))


def main() -> int:
    hour_csv = _ensure_dataset()
    rows = _parse_hour_csv(hour_csv)

    target_dt = datetime.strptime(TARGET_DTTM, "%Y-%m-%d %H:%M:%S")
    target_matches = [r for r in rows if r["timestamp"] == target_dt]
    if len(target_matches) != 1:
        raise RuntimeError(f"Expected one target row for {TARGET_DTTM}, found {len(target_matches)}")
    target_row = target_matches[0]
    history = [r for r in rows if r["timestamp"] < target_dt]
    if not history:
        raise RuntimeError("No prior rows available before target timestamp")

    # The prediction path receives target features only. The held-out `cnt` is
    # intentionally omitted until the independent resolution step below.
    target_features = {k: v for k, v in target_row.items() if k not in {"cnt", "casual", "registered"}}
    target_features["timestamp"] = target_features["timestamp"].isoformat()
    if int(target_features["yr"]) != 1:
        raise RuntimeError("Target row must be from 2012 in the UCI coding scheme")

    baseline = _build_prior_baseline(history, target_features)
    threshold = int(baseline["threshold"])
    confidence = round(float(baseline["confidence"]), 4)
    target_timestamp = target_dt.strftime("%Y-%m-%d %H:%M:%S")

    validate_independent_sources(CLAIM_SOURCE, RESOLUTION_SOURCE)

    db_url = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        svc_conn = psycopg2.connect(_resolution_dsn(db_url))
        svc_conn.autocommit = True
    except psycopg2.OperationalError as exc:
        raise SystemExit(
            "ERROR: Database unavailable. Start Postgres and run `make migrate`, "
            "or provide a valid DATABASE_URL."
        ) from exc

    cal = create_calibration_engine(db=conn)
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    print("\nAgentCo business demo: UCI Bike Sharing verifiable calibration")
    print("=" * 68)
    print(f"Target timestamp: {target_timestamp}")
    print(f"Claim source: {CLAIM_SOURCE}")
    print(f"Independent resolution source: {RESOLUTION_SOURCE}")
    print(f"Threshold: {threshold}")
    print(f"Predicted confidence: {confidence:.4f}")
    print(f"Baseline: {baseline['stratum']} ({baseline['comparable_count']} prior rows)")

    trust_before = trust.trusted_confidence(
        stated=confidence,
        subject_id=AGENT_ID,
        subject_type="agent",
        domain="bike_rental_operations",
        claim_type="high_demand_hour",
        horizon_class="short",
    )

    claim = f"For target timestamp {target_timestamp}, total rentals cnt will be >= {threshold}."
    reg = PredictionRegistration(
        claim=claim,
        probability=confidence,
        confidence_basis={
            "source": CLAIM_SOURCE,
            "method": "deterministic_prior_rows_baseline",
            "target_features_without_cnt": target_features,
            "baseline": baseline,
        },
        producing_agent_id=AGENT_ID,
        producing_prompt_version="demo_business_bikeshare_calibration_v1",
        resolution_criterion=(
            "Resolve TRUE iff the held-out UCI Bike Sharing hour.csv target row "
            f"for {target_timestamp} has cnt >= {threshold}."
        ),
        resolution_date=datetime.now(timezone.utc) + timedelta(seconds=2),
        ground_truth_source=RESOLUTION_SOURCE,
        horizon_class="short",
        domain="bike_rental_operations",
        claim_type="high_demand_hour",
    )
    prediction_id = ledger.pre_register(reg)
    digest = _entry_hash(prediction_id, claim)
    print(f"Ledger prediction_id: {prediction_id}")
    print(f"Ledger hash: {digest}")

    time.sleep(2.2)

    actual_cnt = int(target_row["cnt"])
    outcome = actual_cnt >= threshold
    resolved = resolution.resolve(
        prediction_id=prediction_id,
        outcome=outcome,
        ground_truth_source=RESOLUTION_SOURCE,
        evidence={
            "source_url": RESOLUTION_SOURCE,
            "cached_file": str(hour_csv.relative_to(ROOT)),
            "target_instant": target_row["instant"],
            "target_timestamp": target_timestamp,
            "actual_cnt": actual_cnt,
            "threshold": threshold,
            "independence_check": "passed",
        },
    )
    ledger._db = svc_conn
    ledger.persist_resolution(resolved)
    ledger._db = conn

    trust_after = trust.trusted_confidence(
        stated=confidence,
        subject_id=AGENT_ID,
        subject_type="agent",
        domain="bike_rental_operations",
        claim_type="high_demand_hour",
        horizon_class="short",
    )

    print(f"Actual cnt: {actual_cnt}")
    print(f"Outcome: {outcome}")
    print(f"Trust/calibration update: {trust_before:.4f} -> {trust_after:.4f}")

    try:
        validate_independent_sources(CLAIM_SOURCE, CLAIM_SOURCE)
    except CircularResolutionError as exc:
        circular_status = f"rejected as unverifiable: {exc}"
    else:
        circular_status = "NOT REJECTED"
    print(f"Circular verification test: {circular_status}")

    records = ledger.list_by_agent(AGENT_ID)
    score = score_agent(records, AGENT_ID)
    last_contacts = {
        (record.domain, record.horizon_class): record.resolved_at
        for record in records
        if record.resolved_at is not None
    }
    credential = issue_credential(score, last_contacts)
    persist_credential(credential, conn)
    print(f"Proof/credential id: {credential.credential_id}")

    recompute = subprocess.run(
        [sys.executable, str(ROOT / "reserve" / "tools" / "recompute_credential.py"), AGENT_ID, db_url],
        check=False,
        text=True,
        capture_output=True,
    )
    if recompute.returncode != 0:
        raise RuntimeError(recompute.stderr.strip() or recompute.stdout.strip())
    recomputed = json.loads(recompute.stdout)["score"]
    if (
        abs(recomputed["overall_log_score"] - credential.overall_log_score) > 1e-9
        or abs(recomputed["overall_brier_score"] - credential.overall_brier_score) > 1e-9
        or recomputed["total_sample_count"] != credential.sample_count
    ):
        raise RuntimeError("Credential does not match independent recomputation")

    _write_acceptance_artifact(
        prediction_id=prediction_id,
        credential_id=credential.credential_id,
        digest=digest,
        target_timestamp=target_timestamp,
        threshold=threshold,
        confidence=confidence,
        actual_cnt=actual_cnt,
        outcome=outcome,
        trust_before=trust_before,
        trust_after=trust_after,
        circular_status=circular_status,
        baseline=baseline,
    )
    print(f"Acceptance artifact written: {ACCEPTANCE_PATH}")

    conn.close()
    svc_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
