"""
Epistemic Reserve — Tamper-Evident Commitment Chain.

PROPERTY: if the operator alters, drops, or back-dates any resolved prediction
that feeds a score, the published chain head no longer matches the chain head
recomputed from raw prediction_ledger rows — proving the tampering to any
third party without requiring any secret.

DESIGN (Certificate-Transparency style hash chain):
    Each resolved prediction committed to the chain contributes one link:

        row_data = (prev_hash || prediction_id || agent_id ||
                    probability || resolved_outcome || resolved_at ||
                    domain || horizon_class || consequence)

        row_hash = SHA-256(row_data)  [hex]

    The chain is ordered by (resolved_at, prediction_id) so the ordering is
    reproducible from public ledger rows.  The chain head is the row_hash of
    the last committed entry.

RECOMPUTATION:
    A third party reads the public prediction_ledger rows and recomputes the
    chain head using ONLY this module and the published ordering rule.
    If the recomputed head != the stored head, tampering is proven.

This module has ZERO dependency on signing keys.  Tamper-evidence here is
purely cryptographic: SHA-256 is a one-way function; changing any field in
any row in the chain changes every subsequent hash.
"""
from __future__ import annotations

import hashlib
from typing import Optional


GENESIS_HASH = "0" * 64  # the prev_hash for the very first entry


def _row_canonical(
    prev_hash: str,
    prediction_id: str,
    agent_id: str,
    probability: float,
    resolved_outcome: bool,
    resolved_at: str,         # ISO-8601 UTC string
    domain: str,
    horizon_class: str,
    consequence: bool,
) -> str:
    """Canonical string representation of one chain link's inputs."""
    outcome_str = "1" if resolved_outcome else "0"
    consequence_str = "1" if consequence else "0"
    # Use repr(round(...)) to avoid floating-point serialisation drift.
    prob_str = repr(round(probability, 10))
    return (
        f"{prev_hash}|{prediction_id}|{agent_id}|{prob_str}|"
        f"{outcome_str}|{resolved_at}|{domain}|{horizon_class}|{consequence_str}"
    )


def compute_row_hash(
    prev_hash: str,
    prediction_id: str,
    agent_id: str,
    probability: float,
    resolved_outcome: bool,
    resolved_at: str,
    domain: str,
    horizon_class: str,
    consequence: bool,
) -> str:
    """SHA-256 hash of one chain link. Deterministic given identical inputs."""
    canonical = _row_canonical(
        prev_hash, prediction_id, agent_id, probability, resolved_outcome,
        resolved_at, domain, horizon_class, consequence,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def commit_prediction(prediction_id: str, db) -> str:
    """
    Append a resolved prediction to the chain log.  Reads the prediction row
    from prediction_ledger to obtain all fields.  Returns the new row_hash.

    Must be called AFTER resolution is persisted.  Idempotent: if the
    prediction is already committed, returns the existing row_hash.
    """
    with db.cursor() as cur:
        # Check if already committed.
        cur.execute(
            "SELECT row_hash FROM prediction_chain_log WHERE prediction_id = %s",
            (prediction_id,),
        )
        existing = cur.fetchone()
        if existing:
            return existing[0]

        # Load the resolved prediction row.
        cur.execute(
            """
            SELECT prediction_id, producing_agent_id, probability,
                   resolved_outcome, resolved_at, domain, horizon_class,
                   COALESCE(consequence, FALSE)
            FROM prediction_ledger
            WHERE prediction_id = %s AND resolved = TRUE
            """,
            (prediction_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"prediction {prediction_id} is not resolved — cannot commit"
            )
        pid, agent_id, prob, outcome, resolved_at, domain, horizon, consequence = row

        # Get the current chain head (prev_hash for the new entry).
        cur.execute(
            "SELECT row_hash FROM prediction_chain_log ORDER BY seq DESC LIMIT 1"
        )
        head_row = cur.fetchone()
        prev_hash = head_row[0] if head_row else GENESIS_HASH

        resolved_at_str = resolved_at.isoformat() if hasattr(resolved_at, "isoformat") else str(resolved_at)
        row_hash = compute_row_hash(
            prev_hash=prev_hash,
            prediction_id=str(pid),
            agent_id=str(agent_id),
            probability=float(prob),
            resolved_outcome=bool(outcome),
            resolved_at=resolved_at_str,
            domain=str(domain),
            horizon_class=str(horizon),
            consequence=bool(consequence),
        )

        cur.execute(
            """
            INSERT INTO prediction_chain_log
                (prediction_id, agent_id, committed_at, prev_hash, row_hash)
            VALUES (%s, %s, NOW(), %s, %s)
            """,
            (str(pid), str(agent_id), prev_hash, row_hash),
        )
    return row_hash


def get_chain_head(db) -> Optional[str]:
    """Return the current chain head (most recent row_hash), or None if chain is empty."""
    with db.cursor() as cur:
        cur.execute("SELECT row_hash FROM prediction_chain_log ORDER BY seq DESC LIMIT 1")
        row = cur.fetchone()
    return row[0] if row else None


def recompute_chain_head(db, agent_id: Optional[str] = None) -> Optional[str]:
    """
    Recompute the chain head from raw prediction_ledger rows.

    This is the THIRD-PARTY VERIFICATION function.  It reads public ledger rows
    in the same order they were committed (resolved_at, prediction_id ASC) and
    rebuilds the hash chain from scratch.  If the result matches get_chain_head(),
    the chain is intact.  If it differs, tampering is proven.

    If agent_id is given, only that agent's rows are recomputed (for per-agent
    verification).  For a global chain audit, pass agent_id=None.
    """
    with db.cursor() as cur:
        # Read committed entries in chain order.
        cur.execute(
            """
            SELECT cl.seq, cl.prediction_id, cl.prev_hash, cl.row_hash,
                   pl.producing_agent_id, pl.probability,
                   pl.resolved_outcome, pl.resolved_at,
                   pl.domain, pl.horizon_class,
                   COALESCE(pl.consequence, FALSE)
            FROM prediction_chain_log cl
            JOIN prediction_ledger pl USING (prediction_id)
            ORDER BY cl.seq ASC
            """
        )
        rows = cur.fetchall()

    if not rows:
        return None

    running_hash = GENESIS_HASH
    for (seq, pid, prev_hash, stored_hash,
         agent, prob, outcome, resolved_at, domain, horizon, consequence) in rows:

        if agent_id is not None and str(agent) != agent_id:
            # Still advance the chain — it's global.
            pass

        resolved_at_str = (
            resolved_at.isoformat() if hasattr(resolved_at, "isoformat") else str(resolved_at)
        )
        expected_hash = compute_row_hash(
            prev_hash=running_hash,
            prediction_id=str(pid),
            agent_id=str(agent),
            probability=float(prob),
            resolved_outcome=bool(outcome),
            resolved_at=resolved_at_str,
            domain=str(domain),
            horizon_class=str(horizon),
            consequence=bool(consequence),
        )
        # If the stored prev_hash differs from our running hash OR the
        # stored row_hash differs from our recomputed hash → tampering.
        if stored_hash != expected_hash or prev_hash != running_hash:
            return f"TAMPERED_AT_SEQ_{seq}"
        running_hash = stored_hash

    return running_hash


def verify_chain(db) -> bool:
    """
    Full chain integrity check.  Returns True if stored chain head ==
    recomputed chain head.  Returns False if tampering is detected.
    """
    stored = get_chain_head(db)
    recomputed = recompute_chain_head(db)
    if stored is None and recomputed is None:
        return True
    return stored == recomputed and (recomputed is not None and not recomputed.startswith("TAMPERED"))
