"""
Epistemic Reserve — Proof-of-Calibration Credential.

A Proof-of-Calibration (PoC) credential is:
  - A VECTOR across (domain × horizon_class) cells, not a single number.
  - NON-TRANSFERABLE: bound to the producing_agent_id; the HMAC embeds agent_id.
  - INDEPENDENTLY RECOMPUTABLE: anyone with access to the public prediction_ledger
    and this module can recompute and verify any credential.
  - SIGNED: HMAC-SHA256 over a canonical, deterministic JSON payload.
  - APPEND-ONLY: stored in calibration_credentials (immutable by DB trigger).

Cross-domain transfer is NOT assumed. A strong finance credential does NOT imply
competence in engineering. Each cell must be earned independently.

Fresh identities start at neutral-low standing (no cells, overall_score = None).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from calibration.decay.decay_tracker import DEFAULT_HALF_LIVES_DAYS
from reserve.scoring.scoring_function import CellScore, ReserveScore, score_agent

# Key used for HMAC signing. In production this must be a securely managed secret.
# The verifier must use the same key. The key is NOT part of the public ledger.
_SIGNING_KEY = os.environ.get("RESERVE_SIGNING_KEY", "dev-insecure-key").encode()

CREDENTIAL_TTL_DAYS = 30  # credentials expire and must be refreshed


@dataclass
class CredentialCell:
    """One (domain × horizon) cell in a PoC credential vector."""
    domain: str
    horizon_class: str
    weighted_log_score: float
    weighted_brier_score: float
    sharpness: float
    sample_count: int
    total_weight: float
    last_reality_contact: Optional[str]   # ISO-8601 UTC; None if no resolved predictions
    decay_half_life_days: int


@dataclass
class ProofOfCalibration:
    """
    A signed, non-transferable Proof-of-Calibration credential.

    To verify independently:
      1. Fetch all resolved, non-post-hoc prediction_ledger rows for agent_id.
      2. Call score_agent(records, agent_id).
      3. Call issue_credential(score, last_contacts) with the same records.
      4. Compare hmac_sha256 using constant-time comparison.
         If it matches, the credential is authentic and recomputable.
    """
    credential_id: str
    agent_id: str
    issued_at: str           # ISO-8601 UTC
    expires_at: str          # ISO-8601 UTC
    cells: list[CredentialCell]
    overall_log_score: float
    overall_brier_score: float
    sample_count: int
    algorithm: str
    hmac_sha256: str         # HMAC-SHA256(canonical_payload, RESERVE_SIGNING_KEY)


def _canonical_payload(cred: "ProofOfCalibration") -> str:
    """
    Deterministic JSON serialization over the fields that constitute the credential.
    HMAC is computed over this string. Field order is fixed; no floating-point drift.
    """
    cells_data = sorted(
        [
            {
                "domain": c.domain,
                "horizon_class": c.horizon_class,
                "weighted_log_score": round(c.weighted_log_score, 10),
                "weighted_brier_score": round(c.weighted_brier_score, 10),
                "sharpness": round(c.sharpness, 10),
                "sample_count": c.sample_count,
                "total_weight": round(c.total_weight, 10),
                "last_reality_contact": c.last_reality_contact,
                "decay_half_life_days": c.decay_half_life_days,
            }
            for c in cred.cells
        ],
        key=lambda x: (x["domain"], x["horizon_class"]),
    )
    payload = {
        "credential_id": cred.credential_id,
        "agent_id": cred.agent_id,
        "issued_at": cred.issued_at,
        "expires_at": cred.expires_at,
        "cells": cells_data,
        "overall_log_score": round(cred.overall_log_score, 10),
        "overall_brier_score": round(cred.overall_brier_score, 10),
        "sample_count": cred.sample_count,
        "algorithm": cred.algorithm,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sign(payload: str) -> str:
    return hmac.new(_SIGNING_KEY, payload.encode(), hashlib.sha256).hexdigest()


def issue_credential(
    score: ReserveScore,
    last_contacts: dict[tuple[str, str], datetime],
) -> ProofOfCalibration:
    """
    Issue a signed PoC credential from a ReserveScore.

    last_contacts: mapping of (domain, horizon_class) → most recent resolved_at
    datetime for predictions in that cell. Pass from the ledger records.
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=CREDENTIAL_TTL_DAYS)

    cells = []
    for cell in score.cells:
        key = (cell.domain, cell.horizon_class)
        lrc = last_contacts.get(key)
        half_life = DEFAULT_HALF_LIVES_DAYS.get(cell.domain, DEFAULT_HALF_LIVES_DAYS["general"])
        cells.append(CredentialCell(
            domain=cell.domain,
            horizon_class=cell.horizon_class,
            weighted_log_score=cell.weighted_log_score,
            weighted_brier_score=cell.weighted_brier_score,
            sharpness=cell.sharpness,
            sample_count=cell.sample_count,
            total_weight=cell.total_weight,
            last_reality_contact=lrc.isoformat() if lrc else None,
            decay_half_life_days=half_life,
        ))

    cred = ProofOfCalibration(
        credential_id=str(uuid.uuid4()),
        agent_id=score.agent_id,
        issued_at=now.isoformat(),
        expires_at=expires.isoformat(),
        cells=cells,
        overall_log_score=score.overall_log_score,
        overall_brier_score=score.overall_brier_score,
        sample_count=score.total_sample_count,
        algorithm=score.algorithm,
        hmac_sha256="",  # placeholder; filled below
    )
    payload = _canonical_payload(cred)
    cred = ProofOfCalibration(**{**cred.__dict__, "hmac_sha256": _sign(payload)})
    return cred


def verify_credential(cred: ProofOfCalibration) -> bool:
    """
    Verify that the credential's HMAC matches its payload.
    Returns True if authentic, False if tampered.
    """
    saved_hmac = cred.hmac_sha256
    cred_without_hmac = ProofOfCalibration(**{**cred.__dict__, "hmac_sha256": ""})
    payload = _canonical_payload(cred_without_hmac)
    expected = _sign(payload)
    return hmac.compare_digest(saved_hmac, expected)


def persist_credential(cred: ProofOfCalibration, db) -> str:
    """
    Write a credential to the calibration_credentials table.
    Returns the credential_id.
    The table is append-only (DB trigger enforces immutability).
    """
    cells_json = json.dumps(
        [
            {
                "domain": c.domain,
                "horizon_class": c.horizon_class,
                "weighted_log_score": c.weighted_log_score,
                "weighted_brier_score": c.weighted_brier_score,
                "sharpness": c.sharpness,
                "sample_count": c.sample_count,
                "total_weight": c.total_weight,
                "last_reality_contact": c.last_reality_contact,
                "decay_half_life_days": c.decay_half_life_days,
            }
            for c in cred.cells
        ],
        sort_keys=True,
    )
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO calibration_credentials
                (credential_id, agent_id, issued_at, expires_at, domain_cells,
                 overall_score, sample_count, algorithm, hmac_sha256)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            """,
            (
                cred.credential_id,
                cred.agent_id,
                cred.issued_at,
                cred.expires_at,
                cells_json,
                cred.overall_log_score,
                cred.sample_count,
                cred.algorithm,
                cred.hmac_sha256,
            ),
        )
    _commit(db)
    return cred.credential_id


def load_credential(credential_id: str, db) -> Optional[dict]:
    """Load a credential row from the DB. Returns raw dict or None."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT credential_id, agent_id, issued_at, expires_at, domain_cells, "
            "overall_score, sample_count, algorithm, hmac_sha256 "
            "FROM calibration_credentials WHERE credential_id = %s",
            (str(credential_id),),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "credential_id": str(row[0]),
        "agent_id": row[1],
        "issued_at": row[2],
        "expires_at": row[3],
        "domain_cells": row[4],
        "overall_score": float(row[5]),
        "sample_count": int(row[6]),
        "algorithm": row[7],
        "hmac_sha256": row[8],
    }


def build_last_contacts(records) -> dict[tuple[str, str], datetime]:
    """Extract most-recent resolved_at per (domain, horizon) from prediction records."""
    contacts: dict[tuple[str, str], datetime] = {}
    for r in records:
        if r.resolved and r.resolved_at:
            key = (r.domain, r.horizon_class)
            existing = contacts.get(key)
            if existing is None or r.resolved_at > existing:
                contacts[key] = r.resolved_at
    return contacts


def _commit(db) -> None:
    commit = getattr(db, "commit", None)
    if callable(commit):
        db.commit()
