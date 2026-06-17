"""
Epistemic Reserve — Phase 3: Recursive Resolution Layer.

A credentialed oracle is an agent whose PoC credential weight in a
(domain × horizon) cell exceeds ORACLE_MIN_WEIGHT. They may resolve
predictions in that domain, and their resolution carries their credential
weight as "authority."

SELF-CORRECTION INVARIANT:
    If a downstream resolution (by a higher-authority oracle or by mechanical
    external ground truth) contradicts an earlier oracle resolution, the
    earlier oracle's standing in that cell is docked. The dock is proportional
    to the authority gap: how much stronger the contradiction was.

    Formally: if resolution R1 (authority A1) is contradicted by R2 (authority A2 > A1
    or A2 = MECHANICAL_AUTHORITY), the oracle behind R1 loses:
        standing_delta = -CONTRADICTION_PENALTY * A2

    This creates a self-correcting pressure: oracles who make resolutions that
    are later overridden by stronger downstream sources suffer reputational cost.
    An oracle cannot improve their standing by making resolutions that get
    contradicted — they can only hold or lose standing through oracle activity.

RECURSIVE PROPERTY:
    Oracle resolutions are themselves falsifiable. Round N+1 resolution
    contradicts round N. The chain terminates when a mechanical external
    source resolves (source_type='mechanical' or 'external'), which cannot
    itself be contradicted. This is the bedrock ground truth.

ORACLE THRESHOLD:
    Minimum stake weight to qualify as oracle in a (domain × horizon) cell.
    Set conservatively to require meaningful reality contact.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from reserve.credentials.proof_of_calibration import ProofOfCalibration
from reserve.staking.staking import compute_stake_weight

# Minimum cell weight to qualify as oracle.
ORACLE_MIN_WEIGHT = 0.05  # exp(log_score) - 0.5 >= 0.05 ⟺ log_score >= log(0.55) ≈ -0.598

# Mechanical/external ground truth gets this authority (uncapped).
MECHANICAL_AUTHORITY = 1.0

# Standing dock on contradiction.
CONTRADICTION_PENALTY = 0.5


@dataclass
class OracleResolution:
    resolution_id: str
    prediction_id: str
    oracle_agent_id: str
    credential_id: Optional[str]
    oracle_authority: float
    domain: str
    horizon_class: str
    resolution_round: int
    outcome: bool
    resolved_at: str         # ISO-8601 UTC
    contradicted: bool
    contradicted_by: Optional[str]
    contradicted_at: Optional[str]
    source_type: str         # 'oracle' | 'mechanical' | 'external'


@dataclass
class OracleStandingEvent:
    history_id: str
    agent_id: str
    domain: str
    horizon_class: str
    resolution_count: int
    contradiction_count: int
    current_standing: float
    standing_delta: float
    event_type: str          # 'resolution' | 'contradiction'
    event_id: str
    recorded_at: str


def is_qualified_oracle(
    credential: ProofOfCalibration,
    domain: str,
    horizon_class: str,
) -> bool:
    """Return True if the agent qualifies as an oracle in this (domain × horizon) cell."""
    weight = compute_stake_weight(credential, domain, horizon_class)
    return weight >= ORACLE_MIN_WEIGHT


def resolve_as_oracle(
    prediction_id: str,
    outcome: bool,
    credential: ProofOfCalibration,
    domain: str,
    horizon_class: str,
    db,
    prior_resolution_id: Optional[str] = None,
) -> OracleResolution:
    """
    An oracle resolves a prediction. Records the resolution with authority =
    the oracle's current cell weight.

    If prior_resolution_id is given, this is a contradiction of a prior
    resolution (round += 1). The prior resolution must have lower authority.

    Raises ValueError if the agent is not a qualified oracle in this cell,
    or if attempting to contradict with lower or equal authority.
    """
    authority = compute_stake_weight(credential, domain, horizon_class)
    if authority < ORACLE_MIN_WEIGHT:
        raise ValueError(
            f"Agent {credential.agent_id!r} does not qualify as oracle in "
            f"({domain}, {horizon_class}): weight={authority:.4f} < {ORACLE_MIN_WEIGHT}"
        )

    resolution_round = 0
    if prior_resolution_id is not None:
        prior = _load_resolution(prior_resolution_id, db)
        if prior is None:
            raise ValueError(f"Prior resolution {prior_resolution_id!r} not found")
        if prior.contradicted:
            raise ValueError(
                f"Resolution {prior_resolution_id!r} is already contradicted — "
                "cannot contradict twice"
            )
        if prior.source_type in ('mechanical', 'external'):
            raise ValueError(
                "Cannot contradict mechanical/external ground truth"
            )
        if authority <= prior.oracle_authority:
            raise ValueError(
                f"Contradiction authority {authority:.4f} must exceed prior "
                f"resolution authority {prior.oracle_authority:.4f}"
            )
        resolution_round = prior.resolution_round + 1

    resolution_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO oracle_resolutions
                (resolution_id, prediction_id, oracle_agent_id, credential_id,
                 oracle_authority, domain, horizon_class, resolution_round,
                 outcome, resolved_at, source_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'oracle')
            """,
            (
                resolution_id, prediction_id, credential.agent_id,
                str(credential.credential_id), authority,
                domain, horizon_class, resolution_round, outcome, now,
            ),
        )

    if prior_resolution_id is not None:
        _mark_contradicted(prior_resolution_id, resolution_id, now, db)
        _record_standing_event(
            agent_id=prior.oracle_agent_id,
            domain=domain,
            horizon_class=horizon_class,
            event_type='contradiction',
            event_id=resolution_id,
            standing_delta=-(CONTRADICTION_PENALTY * authority),
            db=db,
        )

    _commit(db)

    _record_standing_event(
        agent_id=credential.agent_id,
        domain=domain,
        horizon_class=horizon_class,
        event_type='resolution',
        event_id=resolution_id,
        standing_delta=0.0,   # no gain from merely resolving; gain comes from calibration
        db=db,
    )
    _commit(db)

    return OracleResolution(
        resolution_id=resolution_id,
        prediction_id=prediction_id,
        oracle_agent_id=credential.agent_id,
        credential_id=str(credential.credential_id),
        oracle_authority=authority,
        domain=domain,
        horizon_class=horizon_class,
        resolution_round=resolution_round,
        outcome=outcome,
        resolved_at=now,
        contradicted=False,
        contradicted_by=None,
        contradicted_at=None,
        source_type='oracle',
    )


def resolve_as_mechanical(
    prediction_id: str,
    outcome: bool,
    source_name: str,
    domain: str,
    horizon_class: str,
    db,
    prior_resolution_id: Optional[str] = None,
) -> OracleResolution:
    """
    Mechanical/external ground truth resolution. Authority = MECHANICAL_AUTHORITY.
    Can contradict any oracle resolution. Cannot itself be contradicted.
    """
    resolution_round = 0
    if prior_resolution_id is not None:
        prior = _load_resolution(prior_resolution_id, db)
        if prior is None:
            raise ValueError(f"Prior resolution {prior_resolution_id!r} not found")
        if prior.source_type in ('mechanical', 'external'):
            raise ValueError("Cannot contradict mechanical/external ground truth")
        resolution_round = prior.resolution_round + 1

    resolution_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO oracle_resolutions
                (resolution_id, prediction_id, oracle_agent_id, credential_id,
                 oracle_authority, domain, horizon_class, resolution_round,
                 outcome, resolved_at, source_type)
            VALUES (%s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, 'mechanical')
            """,
            (
                resolution_id, prediction_id, source_name,
                MECHANICAL_AUTHORITY, domain, horizon_class,
                resolution_round, outcome, now,
            ),
        )

    if prior_resolution_id is not None:
        prior = _load_resolution(prior_resolution_id, db)
        _mark_contradicted(prior_resolution_id, resolution_id, now, db)
        _record_standing_event(
            agent_id=prior.oracle_agent_id,
            domain=domain,
            horizon_class=horizon_class,
            event_type='contradiction',
            event_id=resolution_id,
            standing_delta=-(CONTRADICTION_PENALTY * MECHANICAL_AUTHORITY),
            db=db,
        )

    _commit(db)

    return OracleResolution(
        resolution_id=resolution_id,
        prediction_id=prediction_id,
        oracle_agent_id=source_name,
        credential_id=None,
        oracle_authority=MECHANICAL_AUTHORITY,
        domain=domain,
        horizon_class=horizon_class,
        resolution_round=resolution_round,
        outcome=outcome,
        resolved_at=now,
        contradicted=False,
        contradicted_by=None,
        contradicted_at=None,
        source_type='mechanical',
    )


def get_current_standing(agent_id: str, domain: str, horizon_class: str, db) -> dict:
    """
    Return the latest standing summary for an agent in a (domain × horizon) cell.
    Returns neutral standing if no history exists.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT resolution_count, contradiction_count, current_standing, recorded_at
              FROM oracle_standing_history
             WHERE agent_id = %s AND domain = %s AND horizon_class = %s
             ORDER BY recorded_at DESC
             LIMIT 1
            """,
            (agent_id, domain, horizon_class),
        )
        row = cur.fetchone()
    if row is None:
        return {
            "agent_id": agent_id, "domain": domain, "horizon_class": horizon_class,
            "resolution_count": 0, "contradiction_count": 0, "current_standing": 0.0,
        }
    return {
        "agent_id": agent_id, "domain": domain, "horizon_class": horizon_class,
        "resolution_count": row[0], "contradiction_count": row[1],
        "current_standing": float(row[2]), "last_updated": row[3].isoformat(),
    }


# ─── Internal helpers ────────────────────────────────────────────────────────

def _load_resolution(resolution_id: str, db) -> Optional[OracleResolution]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT resolution_id, prediction_id, oracle_agent_id, credential_id,
                   oracle_authority, domain, horizon_class, resolution_round,
                   outcome, resolved_at, contradicted, contradicted_by,
                   contradicted_at, source_type
              FROM oracle_resolutions WHERE resolution_id = %s
            """,
            (resolution_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return OracleResolution(
        resolution_id=str(row[0]), prediction_id=str(row[1]),
        oracle_agent_id=row[2], credential_id=str(row[3]) if row[3] else None,
        oracle_authority=float(row[4]), domain=row[5], horizon_class=row[6],
        resolution_round=int(row[7]), outcome=bool(row[8]),
        resolved_at=row[9].isoformat() if hasattr(row[9], 'isoformat') else str(row[9]),
        contradicted=bool(row[10]),
        contradicted_by=str(row[11]) if row[11] else None,
        contradicted_at=row[12].isoformat() if row[12] and hasattr(row[12], 'isoformat') else None,
        source_type=row[13],
    )


def _mark_contradicted(resolution_id: str, contradicted_by: str, now: str, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE oracle_resolutions
               SET contradicted = TRUE, contradicted_by = %s, contradicted_at = %s
             WHERE resolution_id = %s
            """,
            (contradicted_by, now, resolution_id),
        )


def _record_standing_event(
    agent_id: str,
    domain: str,
    horizon_class: str,
    event_type: str,
    event_id: str,
    standing_delta: float,
    db,
) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT resolution_count, contradiction_count, current_standing
              FROM oracle_standing_history
             WHERE agent_id = %s AND domain = %s AND horizon_class = %s
             ORDER BY recorded_at DESC LIMIT 1
            """,
            (agent_id, domain, horizon_class),
        )
        row = cur.fetchone()

    if row is None:
        res_count = 1 if event_type == 'resolution' else 0
        contra_count = 1 if event_type == 'contradiction' else 0
        current = max(0.0, standing_delta)
    else:
        res_count = row[0] + (1 if event_type == 'resolution' else 0)
        contra_count = row[1] + (1 if event_type == 'contradiction' else 0)
        current = max(0.0, float(row[2]) + standing_delta)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO oracle_standing_history
                (agent_id, domain, horizon_class, resolution_count,
                 contradiction_count, current_standing, standing_delta,
                 event_type, event_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                agent_id, domain, horizon_class, res_count, contra_count,
                current, standing_delta, event_type, event_id,
            ),
        )


def _commit(db) -> None:
    if callable(getattr(db, "commit", None)):
        db.commit()
