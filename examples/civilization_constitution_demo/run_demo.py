#!/usr/bin/env python3
"""Deterministic full-system civilization constitution demo.

The demo is intentionally offline. It uses the real calibration engine for claim
registration, independence rejection, independent resolution, trust scoring, and
credential issuance, then propagates the calibrated result through deterministic
institution, society, dispute, economy, and memory fixtures.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calibration import create_calibration_engine
from calibration.ledger.prediction_ledger import PredictionRegistration
from calibration.resolution.source_independence import CircularResolutionError
from reserve.credentials.proof_of_calibration import issue_credential
from reserve.scoring.scoring_function import score_agent


AGENT_ID = "civilization-demo-agent"
DEPARTMENT_ID = "verification-department"
INSTITUTION_ID = "software-engineering-institution"
SOCIETY_ID = "engineering-society"
CIVILIZATION_ID = "agentco-civilization"
CLAIM_SOURCE = "https://producer.invalid/releases/civilization-demo-claim"
INDEPENDENT_SOURCE = "https://www.python.org/dev/peps/pep-0008/"


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _output_dir() -> Path:
    configured = os.environ.get("AGENTCO_DEMO_OUTPUT_DIR")
    return Path(configured) if configured else ROOT / "examples" / "civilization_constitution_demo" / "artifacts"


def run_demo() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    audit_events: list[dict[str, Any]] = []

    def event(event_type: str, **payload: Any) -> dict[str, Any]:
        entry = {
            "event_type": event_type,
            "recorded_at": now.isoformat(),
            "payload": payload,
        }
        entry["event_hash"] = _hash(entry)
        audit_events.append(entry)
        return entry

    cal = create_calibration_engine()
    ledger = cal["ledger"]
    resolution = cal["resolution"]
    trust = cal["trust"]

    prediction_id = ledger.pre_register(
        PredictionRegistration(
            claim="Agentco governed API rejects unauthenticated institution mutations.",
            probability=0.82,
            confidence_basis={"source": CLAIM_SOURCE, "method": "deterministic_civilization_demo"},
            producing_agent_id=AGENT_ID,
            producing_prompt_version="civilization-demo-v1",
            resolution_criterion="Independent fixture confirms unauthenticated mutation rejection.",
            resolution_date=now + timedelta(milliseconds=50),
            ground_truth_source=INDEPENDENT_SOURCE,
            horizon_class="short",
            domain="governance",
            claim_type="security_invariant",
            claim_source_url=CLAIM_SOURCE,
        )
    )
    event("claim_preregistered", prediction_id=prediction_id, agent_id=AGENT_ID, claim_source=CLAIM_SOURCE)

    same_source_rejected = False
    time.sleep(0.07)

    try:
        resolution.resolve(
            prediction_id=prediction_id,
            outcome=True,
            ground_truth_source=CLAIM_SOURCE,
            evidence={"source_url": CLAIM_SOURCE, "evidence": "same-source resolution attempt"},
        )
    except (CircularResolutionError, ValueError) as exc:
        if "INDEPENDENCE REJECTED" not in str(exc) and "same_canonical_url" not in str(exc):
            raise
        same_source_rejected = True
        event("same_source_resolution_rejected", prediction_id=prediction_id, reason=str(exc))

    if not same_source_rejected:
        raise RuntimeError("same-source resolution was not rejected")

    resolved = resolution.resolve(
        prediction_id=prediction_id,
        outcome=True,
        ground_truth_source=INDEPENDENT_SOURCE,
        evidence={
            "source_url": INDEPENDENT_SOURCE,
            "evidence": "Deterministic fixture: governed API rejects unauthenticated mutation.",
            "snapshot": "offline-fixture-v1",
        },
    )
    ledger.persist_resolution(resolved)
    event(
        "independent_resolution_accepted",
        prediction_id=prediction_id,
        resolver_id=resolved.resolver_id,
        evidence_snapshot_hash=resolved.evidence_snapshot_hash,
    )

    trust_score = trust.trusted_confidence(
        stated=0.82,
        subject_id=AGENT_ID,
        subject_type="agent",
        domain="governance",
        claim_type="security_invariant",
        horizon_class="short",
    )
    event("trust_score_updated", agent_id=AGENT_ID, trust_score=trust_score)

    records = ledger.list_by_agent(AGENT_ID)
    score = score_agent(records, AGENT_ID)
    credential = issue_credential(
        score,
        {(record.domain, record.horizon_class): record.resolved_at for record in records if record.resolved_at},
    )
    event("proof_of_calibration_credential_issued", credential_id=credential.credential_id)

    agent_reputation = round(min(1.0, 0.55 + trust_score * 0.35), 4)
    department_reputation = round((agent_reputation * 0.8) + 0.12, 4)
    institution_authority = "standard_engineering_release" if department_reputation >= 0.7 else "trial_only"
    institution_reputation = round((department_reputation * 0.75) + 0.15, 4)
    society_reputation = round((institution_reputation * 0.7) + 0.18 - 0.03, 4)

    event("agent_reputation_updated", agent_id=AGENT_ID, reputation=agent_reputation)
    event("department_reputation_updated", department_id=DEPARTMENT_ID, reputation=department_reputation)
    event("institution_authority_updated", institution_id=INSTITUTION_ID, authority=institution_authority)
    event("society_reputation_updated", society_id=SOCIETY_ID, reputation=society_reputation)

    dispute_id = "dispute-output-quality-001"
    event("dispute_opened", dispute_id=dispute_id, output_id="output-governed-api-001", plaintiff="security-institution")
    event("dispute_evidence_submitted", dispute_id=dispute_id, evidence_hash=_hash({"fixture": "audit-log-and-rbac-test"}))
    ruling = {
        "ruling_id": "ruling-output-quality-001",
        "dispute_id": dispute_id,
        "judge": "reliability-institution",
        "decision": "approved_with_constraints",
        "appeal_window_hours": 72,
    }
    event("ruling_issued", **ruling)
    precedent = {
        "precedent_id": "precedent-independent-review-001",
        "ruling_id": ruling["ruling_id"],
        "rule": "High-risk institution outputs require non-defendant review before release.",
    }
    event("precedent_created", **precedent)

    economy = {
        "compute_budget_delta": -4,
        "review_credits_delta": 2,
        "adversarial_reward_delta": 1,
        "penalty_delta": 0,
    }
    event("budget_reward_penalty_applied", **economy)
    event("civilization_memory_recorded", civilization_id=CIVILIZATION_ID, source_event_hashes=[e["event_hash"] for e in audit_events])

    dashboard_snapshot = {
        "civilization": CIVILIZATION_ID,
        "society": SOCIETY_ID,
        "institution": INSTITUTION_ID,
        "agent": AGENT_ID,
        "trust_score": trust_score,
        "institution_authority": institution_authority,
        "society_reputation": society_reputation,
        "dispute": dispute_id,
        "precedent": precedent["precedent_id"],
    }

    return {
        "demo": "civilization_constitution_demo",
        "mode": "offline_deterministic",
        "prediction_id": prediction_id,
        "same_source_rejected": same_source_rejected,
        "independent_resolution_status": resolved.independence_status,
        "credential_id": credential.credential_id,
        "credential_score": {
            "sample_count": credential.sample_count,
            "overall_brier_score": credential.overall_brier_score,
            "overall_log_score": credential.overall_log_score,
        },
        "reputation": {
            "agent": agent_reputation,
            "department": department_reputation,
            "institution": institution_reputation,
            "society": society_reputation,
        },
        "authority": {"institution": institution_authority},
        "dispute": {"id": dispute_id, "ruling": ruling, "precedent": precedent},
        "economy": economy,
        "dashboard_snapshot": dashboard_snapshot,
        "audit_events": audit_events,
    }


def write_outputs(package: dict[str, Any]) -> tuple[Path, Path]:
    out = _output_dir()
    out.mkdir(parents=True, exist_ok=True)
    audit_path = out / "audit_package.json"
    trace_path = out / "demo_trace.md"
    audit_path.write_text(json.dumps(package, indent=2, sort_keys=True))
    trace_path.write_text(
        "\n".join(
            [
                "# Civilization Constitution Demo",
                "",
                f"Mode: `{package['mode']}`",
                f"Prediction: `{package['prediction_id']}`",
                f"Same-source rejected: `{package['same_source_rejected']}`",
                f"Independent resolution: `{package['independent_resolution_status']}`",
                f"Credential: `{package['credential_id']}`",
                f"Institution authority: `{package['authority']['institution']}`",
                f"Society reputation: `{package['reputation']['society']}`",
                f"Precedent: `{package['dispute']['precedent']['precedent_id']}`",
                "",
                "## Audit Events",
                *[f"- `{entry['event_type']}` `{entry['event_hash']}`" for entry in package["audit_events"]],
                "",
            ]
        )
    )
    return audit_path, trace_path


def main() -> int:
    package = run_demo()
    audit_path, trace_path = write_outputs(package)
    print("[OK] civilization constitution demo passed")
    print(f"[OK] audit package: {audit_path}")
    print(f"[OK] trace: {trace_path}")
    print(f"[OK] same-source rejected: {package['same_source_rejected']}")
    print(f"[OK] credential: {package['credential_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
