#!/usr/bin/env python3
"""Offline smoke check for calibration-first civilization invariants."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import CircularResolutionError, validate_independent_sources


def main() -> int:
    cal = create_calibration_engine()
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    claim_source = "https://producer.invalid/claim/calibration-smoke"
    independent_source = "https://www.python.org/dev/peps/pep-0008/"
    validate_independent_sources(claim_source, independent_source)

    prediction_id = ledger.pre_register(
        PredictionRegistration(
            claim="Offline smoke claim resolves only through independent evidence.",
            probability=0.8,
            confidence_basis={"source": claim_source},
            producing_agent_id="offline-smoke-agent",
            producing_prompt_version="offline-smoke-v1",
            resolution_criterion="Independent resolver confirms the deterministic fixture outcome.",
            resolution_date=datetime.now(timezone.utc) + timedelta(milliseconds=50),
            ground_truth_source=independent_source,
            horizon_class="short",
            domain="runnability",
            claim_type="smoke",
            claim_source_url=claim_source,
        )
    )

    time.sleep(0.07)

    try:
        resolution.resolve(
            prediction_id=prediction_id,
            outcome=True,
            ground_truth_source=claim_source,
            evidence={"source_url": claim_source, "evidence": "same source should fail"},
        )
    except (CircularResolutionError, ValueError) as exc:
        if "INDEPENDENCE REJECTED" not in str(exc) and "same_canonical_url" not in str(exc):
            raise
        same_source_rejected = True
    else:
        same_source_rejected = False

    if not same_source_rejected:
        print("[FAIL] same-source resolution was not rejected")
        return 1

    resolved = resolution.resolve(
        prediction_id=prediction_id,
        outcome=True,
        ground_truth_source=independent_source,
        evidence={"source_url": independent_source, "evidence": "deterministic independent fixture"},
    )
    ledger.persist_resolution(resolved)
    trusted = trust.trusted_confidence(
        stated=0.8,
        subject_id="offline-smoke-agent",
        subject_type="agent",
        domain="runnability",
        claim_type="smoke",
        horizon_class="short",
    )

    if trusted <= 0:
        print("[FAIL] valid independent resolution did not produce trusted confidence")
        return 1

    print("[OK] offline smoke passed")
    print(f"[OK] prediction_id={prediction_id}")
    print(f"[OK] trusted_confidence={trusted:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
