"""
Epistemic Reserve — Proof-of-Calibration Credential.

A Proof-of-Calibration (PoC) credential provides TWO INDEPENDENT guarantees:

  1. CORRECTNESS (recomputable by anyone, no key required):
     The score embedded in the credential is identical to what you get by
     fetching the agent's resolved prediction_ledger rows and running the
     published scoring function. Use reserve/tools/recompute_credential.py.
     This guarantee requires no trust in the operator.

  2. AUTHORSHIP (verifiable by anyone with the published public key):
     The credential carries an Ed25519 signature over the canonical payload,
     signed by AgentCo's private key. Anyone can verify this signature using
     the published public key at reserve/keys/agentco_reserve_public.key.
     This proves the credential was issued by AgentCo, not altered in transit.
     Verification requires NO SECRET — only the public key.

These two guarantees are DISTINCT:
  - Correctness: verifiable by recomputation alone (no key at all).
  - Authorship: verifiable by the public key (no secret).
  - Neither requires trusting the operator's private state.

Trust model (honest statement):
  AgentCo OPERATES the Reserve and issues credentials with its private key.
  This is operator-run, not decentralised. There is a single issuer. Full
  trustlessness is future work. What IS true now: any score is independently
  recomputable; authorship is publicly verifiable; the resolved-prediction log
  is tamper-evident (Phase C). The operator cannot rig a score undetected.

Cross-domain transfer is NOT assumed. Each cell must be earned independently.
Fresh identities start at neutral-low standing (no cells, overall_score = None).

Signing key env vars:
  RESERVE_PRIVATE_KEY  — base64-encoded Ed25519 private key (operator-held, secret)
  RESERVE_SIGNING_KEY  — legacy HMAC key (deprecated; kept for test compat only)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from calibration.decay.decay_tracker import DEFAULT_HALF_LIVES_DAYS
from reserve.scoring.scoring_function import CellScore, ReserveScore, score_agent

# ---------------------------------------------------------------------------
# Ed25519 signing (asymmetric — anyone verifies with the published public key)
# ---------------------------------------------------------------------------
_PRIVATE_KEY_B64 = os.environ.get("RESERVE_PRIVATE_KEY", "")
_PUBLIC_KEY_FILE = Path(__file__).resolve().parents[1] / "keys" / "agentco_reserve_public.pem"

# Legacy HMAC key retained only for backward compat in unit tests.
_LEGACY_HMAC_KEY = os.environ.get("RESERVE_SIGNING_KEY", "dev-insecure-key").encode()

CREDENTIAL_TTL_DAYS = 30  # credentials expire and must be refreshed


def _get_private_key():
    """Load Ed25519 private key from env. Returns None if not configured."""
    if not _PRIVATE_KEY_B64:
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
        raw = base64.b64decode(_PRIVATE_KEY_B64)
        return Ed25519PrivateKey.from_private_bytes(raw)
    except Exception:
        return None


def _get_public_key_bytes() -> Optional[bytes]:
    """Load published Ed25519 public key from the well-known file. No secret required."""
    try:
        raw_b64 = _PUBLIC_KEY_FILE.read_text().strip()
        return base64.b64decode(raw_b64)
    except Exception:
        return None


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

    Two independent verification paths:

    CORRECTNESS (no key required):
      1. Fetch all resolved, non-post-hoc prediction_ledger rows for agent_id.
      2. Run: python3 reserve/tools/recompute_credential.py <agent_id>
      3. Compare recomputed scores against this credential's numeric fields.
         Mismatch means the operator embedded a different score than the ledger
         rows dictate — i.e., the score was rigged.

    AUTHORSHIP (public key required, no secret):
      1. Load reserve/keys/agentco_reserve_public.key
      2. Call verify_credential(cred) — uses only the published public key.
         Returns True if signature matches; False if the credential was altered.
    """
    credential_id: str
    agent_id: str
    issued_at: str            # ISO-8601 UTC
    expires_at: str           # ISO-8601 UTC
    cells: list[CredentialCell]
    overall_log_score: float
    overall_brier_score: float
    sample_count: int
    algorithm: str
    hmac_sha256: str          # DEPRECATED: legacy HMAC; kept for compat. Use ed25519_signature.
    ed25519_signature: str = ""  # Ed25519 signature over canonical payload (hex). Verify with public key.


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


def _legacy_hmac(payload: str) -> str:
    """Deprecated HMAC-SHA256 signature. Kept for unit-test backward compat."""
    return hmac.new(_LEGACY_HMAC_KEY, payload.encode(), hashlib.sha256).hexdigest()


def _ed25519_sign(payload: str) -> str:
    """
    Sign payload with the operator's Ed25519 private key.
    Returns hex-encoded signature, or "" if RESERVE_PRIVATE_KEY is not set
    (dev / test environments without a configured key).
    """
    priv = _get_private_key()
    if priv is None:
        return ""
    sig_bytes = priv.sign(payload.encode())
    return sig_bytes.hex()


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
        hmac_sha256="",       # placeholder; filled below (legacy)
        ed25519_signature="", # placeholder; filled below
    )
    payload = _canonical_payload(cred)
    cred = ProofOfCalibration(**{
        **cred.__dict__,
        "hmac_sha256": _legacy_hmac(payload),
        "ed25519_signature": _ed25519_sign(payload),
    })
    return cred


def verify_credential(cred: ProofOfCalibration) -> bool:
    """
    Verify credential authorship using the published Ed25519 public key.
    No secret is required — only the public key at reserve/keys/agentco_reserve_public.key.

    Returns True if the signature is valid.
    Returns False if the credential was tampered with or the public key is unavailable.

    Falls back to HMAC verification if no Ed25519 signature is present (legacy credentials).

    NOTE: This verifies AUTHORSHIP (the credential was signed by AgentCo), not
    CORRECTNESS (the scores are consistent with the ledger rows). To verify
    correctness, use reserve/tools/recompute_credential.py — no key needed.
    """
    # Canonical payload does not include the signatures.
    bare = ProofOfCalibration(**{**cred.__dict__, "hmac_sha256": "", "ed25519_signature": ""})
    payload = _canonical_payload(bare)

    if cred.ed25519_signature:
        # Preferred path: asymmetric verification, no secret required.
        pub_bytes = _get_public_key_bytes()
        if pub_bytes is None:
            return False
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
            pub.verify(bytes.fromhex(cred.ed25519_signature), payload.encode())
            return True
        except Exception:
            return False

    # Legacy path: HMAC (requires shared secret; deprecated).
    expected = _legacy_hmac(payload)
    return hmac.compare_digest(cred.hmac_sha256, expected)


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
                 overall_score, sample_count, algorithm, hmac_sha256,
                 ed25519_signature)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
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
                cred.ed25519_signature or None,
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
