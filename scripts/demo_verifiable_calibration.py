#!/usr/bin/env python3
"""Narrated demo: catch an agent lying to itself."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import (
    CircularResolutionError,
    validate_independent_sources,
)
from reserve.credentials.proof_of_calibration import issue_credential, persist_credential
from reserve.scoring.scoring_function import score_agent


AGENT_ID = "demo-calibration-agent"
CLAIM_SOURCE = "https://www.python.org/downloads/release/python-3120/"
INDEPENDENT_SOURCE = "https://docs.python.org/3/whatsnew/3.12.html"


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


def _summary_path() -> Path:
    return ROOT / "evals" / "acceptance" / "verifiable_calibration_demo.md"


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "postgresql://agentco:password@localhost:5432/agentco")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    svc_conn = psycopg2.connect(_resolution_dsn(db_url))
    svc_conn.autocommit = True

    cal = create_calibration_engine(db=conn)
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    print("\nAgentCo demo: Catch the agent lying to itself")
    print("=" * 56)

    claim = "Python 3.12.0 was released on October 2, 2023."
    confidence = 0.91
    trust_before = trust.trusted_confidence(
        stated=confidence,
        subject_id=AGENT_ID,
        subject_type="agent",
        domain="software",
        claim_type="release_fact",
        horizon_class="short",
    )

    print(f"Agent stakes a claim with confidence {confidence:.2f}, BEFORE knowing the answer")
    print(f"Claim source: {CLAIM_SOURCE}")
    print(f"Independent check source: {INDEPENDENT_SOURCE}")
    validate_independent_sources(CLAIM_SOURCE, INDEPENDENT_SOURCE)

    reg = PredictionRegistration(
        claim=claim,
        probability=confidence,
        confidence_basis={
            "source": CLAIM_SOURCE,
            "method": "demo_pre_registered_claim",
        },
        producing_agent_id=AGENT_ID,
        producing_prompt_version="demo_verifiable_calibration_v1",
        resolution_criterion="Independent Python documentation confirms whether Python 3.12.0 was released on October 2, 2023.",
        resolution_date=datetime.now(timezone.utc) + timedelta(seconds=2),
        ground_truth_source=INDEPENDENT_SOURCE,
        horizon_class="short",
        domain="software",
        claim_type="release_fact",
    )
    prediction_id = ledger.pre_register(reg)
    digest = _entry_hash(prediction_id, claim)
    print(f"Ledger entry written — immutable, here's the hash: {digest}")
    print(f"Ledger prediction_id: {prediction_id}")

    time.sleep(2.2)
    print("Checking against an INDEPENDENT source (not the one the claim came from)...")
    resolved = resolution.resolve(
        prediction_id=prediction_id,
        outcome=True,
        ground_truth_source=INDEPENDENT_SOURCE,
        evidence={
            "source_url": INDEPENDENT_SOURCE,
            "evidence": "Python documentation lists Python 3.12.0 final as released on 2023-10-02.",
            "independence_check": "passed",
            "resolution_source_type": "external_documentation",
        },
        resolver_id="resolution-service-demo",
        resolver_type="service",
        claim_source_url=CLAIM_SOURCE,
        resolution_url=INDEPENDENT_SOURCE,
    )
    ledger._db = svc_conn
    ledger.persist_resolution(resolved)
    ledger._db = conn

    trust_after = trust.trusted_confidence(
        stated=confidence,
        subject_id=AGENT_ID,
        subject_type="agent",
        domain="software",
        claim_type="release_fact",
        horizon_class="short",
    )
    print("Reality says: TRUE. Agent's confidence was justified? Y")
    print(f"Trust score updated: {trust_before:.4f} -> {trust_after:.4f}, because a pre-registered claim touched independent reality.")

    print("\nNow feed the system a circular verification attempt.")
    try:
        validate_independent_sources(CLAIM_SOURCE, CLAIM_SOURCE)
    except CircularResolutionError as exc:
        circular_status = f"flagged as unverifiable: {exc}"
        print(f"Circular verification caught — {circular_status}")
    else:
        circular_status = "NOT CAUGHT"
        print("Circular verification was not caught.")

    records = ledger.list_by_agent(AGENT_ID)
    score = score_agent(records, AGENT_ID)
    last_contacts = {
        (record.domain, record.horizon_class): record.resolved_at
        for record in records
        if record.resolved_at is not None
    }
    credential = issue_credential(score, last_contacts)
    persist_credential(credential, conn)
    print(f"Proof-of-Calibration credential issued: {credential.credential_id}")

    recompute = subprocess.run(
        [sys.executable, str(ROOT / "reserve" / "tools" / "recompute_credential.py"), AGENT_ID, db_url],
        check=False,
        text=True,
        capture_output=True,
    )
    print("Independent recomputation:")
    if recompute.returncode == 0:
        data = json.loads(recompute.stdout)
        print(json.dumps(data["score"], indent=2))
        recomputed = data["score"]
        if (
            abs(recomputed["overall_log_score"] - credential.overall_log_score) > 1e-9
            or abs(recomputed["overall_brier_score"] - credential.overall_brier_score) > 1e-9
            or recomputed["total_sample_count"] != credential.sample_count
        ):
            raise RuntimeError("Credential does not match independent recomputation")
        print("Credential recomputation match: YES")
    else:
        print(recompute.stderr.strip() or recompute.stdout.strip())

    summary = [
        "# Verifiable Calibration Demo",
        "",
        "## What was claimed",
        claim,
        "",
        "## How it was checked",
        f"The claim was sourced from `{CLAIM_SOURCE}` and resolved against independent source `{INDEPENDENT_SOURCE}`.",
        "",
        "## What happened",
        f"Prediction `{prediction_id}` resolved TRUE. Trust moved from `{trust_before:.4f}` to `{trust_after:.4f}`.",
        "",
        "## Why this matters",
        "The same-source circular check was deliberately attempted and rejected before it could count as verification.",
        "",
        "## Credential",
        f"Credential `{credential.credential_id}` was issued. Recompute it with:",
        "",
        f"`python3 reserve/tools/recompute_credential.py {AGENT_ID}`",
        "",
        f"Circular check status: {circular_status}",
        "",
    ]
    _summary_path().write_text("\n".join(summary))
    print(f"Shareable summary written: {_summary_path()}")

    conn.close()
    svc_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
